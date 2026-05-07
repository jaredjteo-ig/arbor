"""Engagement-survey library template seed (T16, P1 scope).

Round-3 trim: P1 ships TWO library templates; Trust Index + Singapore
SME quarterly defer to M8 T82 / T83 after `sg-employment-law-expert`
review.

Idempotent — `seed_library_for_company(company_id)` is a no-op if the
company already has any engagement template. Called from the
templates-list GET handler on first access.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from hr_advisory.services import dataflow_crud

logger = logging.getLogger(__name__)

__all__ = [
    "seed_library_for_company",
    "GALLUP_Q12_TEMPLATE",
    "MONTHLY_PULSE_TEMPLATE",
]


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# Gallup Q12 paraphrase. The 12 statements are paraphrased — Gallup
# owns the original wording. Each is rendered as a Likert-5 question
# (Strongly disagree … Strongly agree).
GALLUP_Q12_TEMPLATE = {
    "name": "Gallup Q12 (paraphrased)",
    "description": (
        "Twelve research-backed statements covering basic needs, "
        "managerial support, teamwork, and growth. Quarterly cadence "
        "is the recommended default."
    ),
    "methodology": "gallup_q12",
    "sections": [
        {
            "title": "Basic needs",
            "questions": [
                {
                    "id": "q1",
                    "text": "I know what is expected of me at work.",
                    "type": "likert5",
                    "is_required": True,
                },
                {
                    "id": "q2",
                    "text": "I have the materials and equipment I need to do my work well.",
                    "type": "likert5",
                    "is_required": True,
                },
            ],
        },
        {
            "title": "Management support",
            "questions": [
                {
                    "id": "q3",
                    "text": "At work, I have the opportunity to do what I do best every day.",
                    "type": "likert5",
                    "is_required": True,
                },
                {
                    "id": "q4",
                    "text": "In the last seven days, I have received recognition or praise for doing good work.",
                    "type": "likert5",
                    "is_required": True,
                },
                {
                    "id": "q5",
                    "text": "My supervisor, or someone at work, seems to care about me as a person.",
                    "type": "likert5",
                    "is_required": True,
                },
                {
                    "id": "q6",
                    "text": "There is someone at work who encourages my development.",
                    "type": "likert5",
                    "is_required": True,
                },
            ],
        },
        {
            "title": "Teamwork",
            "questions": [
                {
                    "id": "q7",
                    "text": "At work, my opinions seem to count.",
                    "type": "likert5",
                    "is_required": True,
                },
                {
                    "id": "q8",
                    "text": "The mission or purpose of my company makes me feel my job is important.",
                    "type": "likert5",
                    "is_required": True,
                },
                {
                    "id": "q9",
                    "text": "My coworkers are committed to doing quality work.",
                    "type": "likert5",
                    "is_required": True,
                },
                {
                    "id": "q10",
                    "text": "I have a best friend at work.",
                    "type": "likert5",
                    "is_required": True,
                },
            ],
        },
        {
            "title": "Growth",
            "questions": [
                {
                    "id": "q11",
                    "text": "In the last six months, someone at work has talked to me about my progress.",
                    "type": "likert5",
                    "is_required": True,
                },
                {
                    "id": "q12",
                    "text": "This last year, I have had opportunities at work to learn and grow.",
                    "type": "likert5",
                    "is_required": True,
                },
            ],
        },
    ],
}

# Monthly pulse — short. Pseudonymous by default. Round-3 owner kept
# this at 4 questions (rejected 1-question micro-pulse).
MONTHLY_PULSE_TEMPLATE = {
    "name": "Monthly pulse",
    "description": (
        "Four-question pulse for monthly cadence. Defaults to "
        "pseudonymous so cross-survey trends still work without "
        "de-identifying respondents."
    ),
    "methodology": "pulse",
    "sections": [
        {
            "title": "How are you doing?",
            "questions": [
                {
                    "id": "q1_overall",
                    "text": "Overall, how are you feeling about work this month?",
                    "type": "likert5",
                    "is_required": True,
                },
                {
                    "id": "q2_enps",
                    "text": "How likely are you to recommend this company as a place to work?",
                    "type": "enps",
                    "is_required": True,
                },
                {
                    "id": "q3_blockers",
                    "text": "What's getting in your way right now?",
                    "type": "multi",
                    "options": [
                        "manager",
                        "comp",
                        "growth",
                        "workload",
                        "culture",
                        "role",
                    ],
                    "is_required": False,
                },
                {
                    "id": "q4_freeform",
                    "text": "Anything else you want to share?",
                    "type": "long_text",
                    "max_length": 1000,
                    "is_required": False,
                },
            ],
        },
    ],
}


def _company_already_has_engagement_templates(company_id: int) -> bool:
    # NOTE: DataFlow has a bug where express list with limit=10000 (the
    # dataflow_crud default) returns 0 rows for recently-created records.
    # Passing an explicit smaller limit avoids it. A company will have
    # at most a few dozen templates, so limit=200 is safely above bound.
    rows = dataflow_crud.list_records(
        "EngagementSurveyTemplate",
        {"company_id": int(company_id)},
        limit=200,
        cache_ttl=0,
    )
    # Filter out archived templates so a "soft-delete then reseed" is
    # possible (admin tooling later).
    return any(not r.get("is_archived") for r in rows)


def _create_template(company_id: int, template_def: dict) -> dict:
    now = _now()
    return dataflow_crud.create(
        "EngagementSurveyTemplate",
        {
            "company_id": int(company_id),
            "name": template_def["name"],
            "description": template_def["description"],
            "methodology": template_def["methodology"],
            "sections": json.dumps(template_def["sections"]),
            "is_archived": False,
            "created_by": 0,  # 0 = system seed
            "created_at": now,
            "updated_at": now,
        },
    )


def seed_library_for_company(company_id: int) -> int:
    """Seed the P1 library for a company. Returns the count seeded.

    No-op if the company already has any non-archived engagement
    template.
    """
    if company_id <= 0:
        raise ValueError("company_id must be > 0.")

    if _company_already_has_engagement_templates(company_id):
        return 0

    seeded = 0
    for template_def in (GALLUP_Q12_TEMPLATE, MONTHLY_PULSE_TEMPLATE):
        try:
            _create_template(company_id, template_def)
            seeded += 1
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "engagement_template_seed_failed",
                extra={
                    "company_id": company_id,
                    "template_name": template_def["name"],
                    "error": str(exc),
                },
            )
    logger.info(
        "engagement_library_seeded",
        extra={"company_id": company_id, "seeded": seeded},
    )
    return seeded
