"""Engagement-survey termination sweep (T17 / red-team C1).

When an employee is terminated, any of their pending engagement-survey
responses must be voided so they can't be filled in afterwards. This
preserves the round-1 anonymity invariants — terminated employees
shouldn't:
  - Show on the response list (PII leakage).
  - Be counted in aggregate stats (skews the score).
  - Be reachable via in-app form.

Z04 semantics (round-2 amendment): only responses with
`submitted_at IS NULL` are voided. Submitted responses were given while
the employee was active and stay in the aggregate — voiding them would
rewrite history.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from hr_advisory.services import dataflow_crud

logger = logging.getLogger(__name__)

__all__ = ["void_pending_engagement_responses"]


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def void_pending_engagement_responses(employee_id: int) -> dict:
    """Void all pending engagement-survey responses for an employee.

    Idempotent: re-running on an already-voided employee is a no-op.

    Args:
        employee_id: the terminated employee's ID.

    Returns:
        `{voided: N, surveys_affected: M}` dict for telemetry / tests.
    """
    if employee_id <= 0:
        raise ValueError("employee_id must be > 0.")

    rows = dataflow_crud.list_records(
        "EngagementSurveyResponse",
        {"employee_id": int(employee_id)},
        cache_ttl=0,
    )
    # Z04: only sweep responses still pending. Submitted responses
    # stay in the aggregate (they were given while the employee was
    # active).
    pending = [
        r for r in rows
        if r.get("submitted_at") is None
        and not r.get("is_void")
    ]
    if not pending:
        return {"voided": 0, "surveys_affected": 0}

    now = _now()
    # B6 (red-team): track ACTUAL voids per survey, not the original
    # pending count. Partial failure now bumps voided_count by the
    # number of rows that successfully wrote — never more.
    successfully_voided_by_survey: dict[int, int] = {}
    voided_count = 0
    for response in pending:
        try:
            dataflow_crud.update(
                "EngagementSurveyResponse",
                int(response["id"]),
                {"is_void": True, "voided_at": now, "updated_at": now},
            )
            voided_count += 1
            sid = int(response.get("survey_id") or 0)
            if sid:
                successfully_voided_by_survey[sid] = (
                    successfully_voided_by_survey.get(sid, 0) + 1
                )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "engagement_response_void_failed",
                extra={"response_id": response.get("id"), "error": str(exc)},
            )

    # Bump each parent survey's voided_count by the count of rows that
    # ACTUALLY voided — not the count that we attempted to void.
    for survey_id, n_voided in successfully_voided_by_survey.items():
        try:
            survey_rows = dataflow_crud.list_records(
                "EngagementSurvey",
                {"id": survey_id},
                cache_ttl=0,
            )
            if not survey_rows:
                continue
            survey = survey_rows[0]
            new_count = int(survey.get("voided_count") or 0) + n_voided
            dataflow_crud.update(
                "EngagementSurvey",
                int(survey_id),
                {"voided_count": new_count, "updated_at": now},
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "engagement_survey_voided_count_bump_failed",
                extra={"survey_id": survey_id, "error": str(exc)},
            )

    surveys_affected = set(successfully_voided_by_survey.keys())

    logger.info(
        "engagement_responses_voided_on_termination",
        extra={
            "employee_id": employee_id,
            "voided": voided_count,
            "surveys_affected": len(surveys_affected),
        },
    )
    return {
        "voided": voided_count,
        "surveys_affected": len(surveys_affected),
    }
