"""Engagement-survey action loop service (T36 + T37 + T38).

The action loop is the round-3 product addition that distinguishes
engagement surveys from a survey tool: HR sees a low-scoring cohort,
gets AI-suggested actions, accepts one, optionally creates a Goal,
and the next pulse measures whether the action moved the needle.

This module owns:
- `suggest_actions(survey_id)` — returns 3 actions for the lowest-
  scoring cohort. Tries the LLM first; falls back deterministically
  when LLM is disabled, capped, or errors.
- `aggregate_for_loop_closing(company_id)` — payload for the employee
  view's loop-closing card.
- Deterministic fallback templates per theme (D8). Reviewed by
  `sg-employment-law-expert` for TAFEP/FWA neutrality (round-3
  legal-review pass on 2026-05-07).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from hr_advisory.services import dataflow_crud

logger = logging.getLogger(__name__)

__all__ = [
    "suggest_actions_for_lowest_cohort",
    "deterministic_suggestions_for_theme",
    "compute_loop_closing_payload",
    "DETERMINISTIC_FALLBACK_BY_THEME",
]


# Round-3 legal-review pass (2026-05-07): wording reviewed by
# sg-employment-law-expert for TAFEP/FWA/EFMA/EA/CPF neutrality.
# 4 wording tweaks applied. DO NOT modify these strings without
# re-running the legal review.
DETERMINISTIC_FALLBACK_BY_THEME: dict[str, list[str]] = {
    "growth": [
        "Run a skip-level on growth aspirations",
        "Audit promo cycle clarity",
        "Launch L&D pilot with a per-head learning budget for the cohort",
    ],
    "manager": [
        "Run 1:1 effectiveness training for managers",
        "Audit workload balance across team",
        "Introduce skip-level rotation",
    ],
    "comp": [
        "Benchmark salary against market for affected band",
        "Audit promo-comp alignment",
        "Communicate comp philosophy openly",
    ],
    "workload": [
        "Audit on-call rotation and review any flexible-work requests in scope",
        "Pilot a no-meetings Wednesday",
        "Run capacity planning workshop with the team",
    ],
    "culture": [
        "Run a team norms and ways-of-working workshop",
        "Audit recognition cadence",
        "Introduce peer-recognition channel",
    ],
    "role": [
        "Audit role clarity matrix",
        "Run a skill-mapping exercise to inform development plans",
        "Pair employees with mentors outside their reporting line",
    ],
}


def deterministic_suggestions_for_theme(theme: str) -> list[str]:
    """Return 3 deterministic suggestions for a theme.

    Falls back to "growth" templates if the theme isn't in the map.
    Used as the safety net when the LLM call fails or budget caps.
    """
    return DETERMINISTIC_FALLBACK_BY_THEME.get(
        (theme or "").lower(),
        DETERMINISTIC_FALLBACK_BY_THEME["growth"],
    )


def suggest_actions_for_lowest_cohort(
    survey_id: int,
    *,
    aggregate_data: dict,
) -> dict:
    """Build the suggested-actions payload for a survey.

    Args:
        survey_id: parent survey.
        aggregate_data: the result of T33 aggregator. Used to pick the
            lowest-scoring cohort with n>=5 and its top theme.

    Returns:
        ```
        {
          "cohort_label": "Engineering",
          "theme": "growth",
          "score": 2.1,
          "suggestions": [
              {"text": "Launch L&D pilot...", "source": "deterministic"},
              ...
          ],
          "source": "deterministic" | "llm"
        }
        ```
        When no cohort has n>=5, returns
        `{"suggestions": [], "reason": "insufficient_cohort_size"}`.
    """
    by_cohort = aggregate_data.get("by_cohort") or []
    visible_cohorts = [
        c for c in by_cohort
        if c.get("is_anonymity_safe")
        and c.get("avg_likert") is not None
    ]
    if not visible_cohorts:
        return {
            "suggestions": [],
            "reason": "insufficient_cohort_size",
        }

    visible_cohorts.sort(key=lambda c: c.get("avg_likert") or 5.0)
    lowest = visible_cohorts[0]
    cohort_label = lowest.get("label", "")
    score = lowest.get("avg_likert")

    # Top theme for that cohort. Aggregator returns themes per cell.
    top_theme = "growth"
    cohort_themes = lowest.get("themes") or []
    if cohort_themes:
        # Themes ordered by count desc.
        top_theme = cohort_themes[0].get("theme", "growth")

    # P1 always uses deterministic. M9 T96 swaps in LLM-driven richer
    # suggestions when the LLM and budget allow.
    suggestions = [
        {"text": s, "source": "deterministic"}
        for s in deterministic_suggestions_for_theme(top_theme)
    ]

    return {
        "cohort_label": cohort_label,
        "theme": top_theme,
        "score": score,
        "suggestions": suggestions,
        "source": "deterministic",
    }


def compute_loop_closing_payload(company_id: int) -> dict | None:
    """Build the loop-closing card payload for `/my-engagement-surveys` (T38).

    Three response states (D3 — red-team Phase 2):
      - No closed pulse → return None (card hidden)
      - Closed + matching accepted action → "HR did Y" with linked goal
      - Closed + no action + admin viewed → status="under_review"
        ("HR is reviewing")
      - Closed + no action + admin NOT viewed → status="notified"
        ("HR has been notified")

    D4 (red-team Phase 2): action lookup uses the action's `theme` field
    when set (exact match), with a fallback to substring of
    finding_summary/suggested_action_text for actions created before
    the field landed.
    """
    surveys = dataflow_crud.list_records(
        "EngagementSurvey",
        {"company_id": int(company_id), "is_archived": False},
        limit=200,
        cache_ttl=0,
    )
    closed = [s for s in surveys if s.get("closed_at")]
    if not closed:
        return None

    closed.sort(key=lambda s: s.get("closed_at") or "", reverse=True)
    latest = closed[0]
    survey_id = int(latest["id"])

    # Compute top theme across all submitted responses.
    responses = dataflow_crud.list_records(
        "EngagementSurveyResponse",
        {"survey_id": survey_id},
        limit=1000,
        cache_ttl=0,
    )
    submitted = [
        r for r in responses
        if r.get("submitted_at") and not r.get("is_void")
    ]
    theme_counts: dict[str, int] = {}
    for r in submitted:
        themes_raw = r.get("themes") or ""
        try:
            themes = json.loads(themes_raw) if themes_raw else []
        except json.JSONDecodeError:
            themes = []
        for t in themes:
            theme_counts[t] = theme_counts.get(t, 0) + 1
    top_theme = ""
    if theme_counts:
        top_theme = max(theme_counts.items(), key=lambda kv: kv[1])[0]

    # D4: find an accepted EngagementAction for this theme. Exact match
    # on action.theme first (the new structured field). Fall back to
    # substring scan for actions created before the theme field landed.
    actions = dataflow_crud.list_records(
        "EngagementAction",
        {"company_id": int(company_id), "status": "accepted"},
        limit=200,
        cache_ttl=0,
    )
    top_theme_lower = (top_theme or "").lower()
    exact_match = [
        a for a in actions
        if (a.get("theme") or "").lower() == top_theme_lower
        and top_theme_lower
    ]
    if exact_match:
        relevant = exact_match
    else:
        # Legacy fallback — pre-D4 actions had no theme field.
        relevant = [
            a for a in actions
            if not (a.get("theme") or "")
            and top_theme_lower
            and (
                (a.get("finding_summary") or "").lower().find(top_theme_lower) >= 0
                or (a.get("suggested_action_text") or "").lower().find(top_theme_lower) >= 0
            )
        ]
    relevant.sort(key=lambda a: a.get("created_at") or "", reverse=True)
    chosen_action = relevant[0] if relevant else None

    action_payload = None
    next_pulse_question = ""
    if chosen_action:
        # Resolve linked goal label if present.
        linked_goal_label = ""
        if chosen_action.get("linked_goal_id"):
            goal = dataflow_crud.read("Goal", int(chosen_action["linked_goal_id"]))
            if goal:
                linked_goal_label = goal.get("title", "") or goal.get("name", "")
        action_payload = {
            "headline": chosen_action.get("suggested_action_text", ""),
            "linked_goal_label": linked_goal_label,
        }
        next_pulse_question = chosen_action.get("next_pulse_question", "") or ""

    # D3: 3-state status. The frontend uses this to choose copy.
    #   "action_taken"  → action_payload populated; show "HR did Y"
    #   "under_review"  → admin opened the survey detail at least once
    #   "notified"      → no admin view yet
    if action_payload is not None:
        status = "action_taken"
    elif latest.get("last_viewed_by_admin_at"):
        status = "under_review"
    else:
        status = "notified"

    return {
        "last_pulse_closed_at": latest.get("closed_at"),
        "top_theme": top_theme,
        "status": status,
        "action_taken": action_payload,
        "next_pulse_anchored_question": next_pulse_question,
    }
