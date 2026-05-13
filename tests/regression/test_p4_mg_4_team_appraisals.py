"""P4-MG-4 regression tests — team appraisal surface.

New BE endpoints:
- GET  /api/appraisals/to-review           — manager review queue
- POST /api/appraisals/{id}/manager-review — manager submits review

Also widens GET /appraisals/{id} so line managers can read their
direct reports' appraisals.

Origin: workspaces/obayashi/04-validate/09-redteam-roles-2026-05-12.md
finding P1-A.
"""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException

REPO_ROOT = Path(__file__).resolve().parents[2]
APPRAISALS_ROUTER = (
    REPO_ROOT / "src" / "hr_advisory" / "api" / "routers" / "appraisals.py"
)
TEAM_ROUTER = (
    REPO_ROOT / "src" / "hr_advisory" / "api" / "routers" / "team.py"
)
TEAM_PAGE = (
    REPO_ROOT
    / "apps"
    / "web"
    / "src"
    / "app"
    / "(dashboard)"
    / "team"
    / "page.tsx"
)


# ---------------------------------------------------------------------------
# Source-level: endpoints exist + route ordering is correct.
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_mg4_to_review_endpoint_exists():
    src = APPRAISALS_ROUTER.read_text()
    assert '@router.get("/to-review")' in src, (
        "Manager review queue endpoint missing (P4-MG-4)."
    )


@pytest.mark.regression
def test_mg4_manager_review_endpoint_exists():
    src = APPRAISALS_ROUTER.read_text()
    assert '@router.post("/{appraisal_id}/manager-review")' in src, (
        "manager-review POST endpoint missing (P4-MG-4)."
    )


@pytest.mark.regression
def test_mg4_to_review_registered_before_id_path():
    """`/to-review` must register BEFORE `/{appraisal_id}` so FastAPI
    doesn't try to coerce the literal string 'to-review' into int.
    A regression here would 422 the queue request silently."""
    src = APPRAISALS_ROUTER.read_text()
    to_review_pos = src.index('@router.get("/to-review")')
    id_get_pos = src.index('@router.get("/{appraisal_id}")')
    assert to_review_pos < id_get_pos, (
        "/to-review must be declared before /{appraisal_id} in "
        "appraisals.py — otherwise FastAPI matches the path param "
        "first and tries int('to-review') → 422."
    )


# ---------------------------------------------------------------------------
# Behavioural — list_appraisals_to_review.
# ---------------------------------------------------------------------------


@pytest.mark.regression
async def test_mg4_to_review_returns_empty_for_ic():
    """A regular employee with no reports gets `[]`, not 403."""
    from hr_advisory.api.routers.appraisals import list_appraisals_to_review

    marcus = {"sub": "11", "role": "employee", "company_id": 1}
    with patch(
        "hr_advisory.services.dataflow_crud.list_records",
        return_value=[
            {"id": 1, "employee_id": 6, "status": "submitted",
             "company_id": 1},
        ],
    ), patch(
        "hr_advisory.services.manager_scope.get_managed_employee_ids",
        return_value=set(),
    ):
        result = await list_appraisals_to_review(current_user=marcus)
    assert result == {"appraisals": [], "count": 0}


@pytest.mark.regression
async def test_mg4_to_review_scopes_to_team_for_managers():
    """Line manager sees only their direct reports' submissions."""
    from hr_advisory.api.routers.appraisals import list_appraisals_to_review

    rajesh = {"sub": "4", "role": "employee", "company_id": 1}

    def fake_list(model_name, filter_dict=None, **kwargs):
        f = filter_dict or {}
        if model_name == "Appraisal" and f.get("status") == "submitted":
            return [
                {"id": 1, "employee_id": 10, "status": "submitted",
                 "company_id": 1, "submitted_at": "2026-05-01"},  # on-team
                {"id": 2, "employee_id": 99, "status": "submitted",
                 "company_id": 1, "submitted_at": "2026-05-02"},  # off-team
            ]
        if model_name == "Employee":
            return [{"id": f.get("id"), "user_id": 11}] if f.get("id") == 10 else []
        if model_name == "User":
            return [{"id": 11, "name": "Marcus Tan"}] if f.get("id") == 11 else []
        return []

    with patch(
        "hr_advisory.services.dataflow_crud.list_records", side_effect=fake_list
    ), patch(
        "hr_advisory.services.manager_scope.get_managed_employee_ids",
        return_value={10},
    ):
        result = await list_appraisals_to_review(current_user=rajesh)
    assert result["count"] == 1
    assert result["appraisals"][0]["id"] == 1
    assert result["appraisals"][0]["employee_name"] == "Marcus Tan"


@pytest.mark.regression
async def test_mg4_to_review_owner_sees_company_wide():
    """Owner role bypasses the team filter — they see everyone."""
    from hr_advisory.api.routers.appraisals import list_appraisals_to_review

    owner = {"sub": "1", "role": "owner", "company_id": 1}

    def fake_list(model_name, filter_dict=None, **kwargs):
        if model_name == "Appraisal":
            return [
                {"id": 1, "employee_id": 10, "status": "submitted",
                 "company_id": 1},
                {"id": 2, "employee_id": 99, "status": "submitted",
                 "company_id": 1},
            ]
        return []

    with patch(
        "hr_advisory.services.dataflow_crud.list_records", side_effect=fake_list
    ):
        result = await list_appraisals_to_review(current_user=owner)
    assert result["count"] == 2


# ---------------------------------------------------------------------------
# Behavioural — manager_review_appraisal.
# ---------------------------------------------------------------------------


class _FakeRequest:
    def __init__(self, body):
        self._body = body

    async def json(self):
        return self._body


@pytest.mark.regression
async def test_mg4_manager_review_blocks_self_review():
    """An employee cannot review their own appraisal — even if they
    are listed as their own manager through a data bug."""
    from hr_advisory.api.routers.appraisals import manager_review_appraisal

    rajesh = {"sub": "4", "role": "employee", "company_id": 1}

    def fake_list(model_name, filter_dict=None, **kwargs):
        # Rajesh's user_id=4 → employee_id=3
        if model_name == "Employee":
            return [{"id": 3, "user_id": 4}]
        return []

    with patch(
        "hr_advisory.services.dataflow_crud.read",
        return_value={"id": 100, "employee_id": 3, "company_id": 1,
                      "status": "submitted"},
    ), patch(
        "hr_advisory.services.dataflow_crud.list_records",
        side_effect=fake_list,
    ), patch(
        "hr_advisory.api.middleware.rate_limit.check_rate_limit"
    ):
        with pytest.raises(HTTPException) as exc:
            await manager_review_appraisal(
                appraisal_id=100,
                request=_FakeRequest({}),
                current_user=rajesh,
            )
    assert exc.value.status_code == 403
    assert "your own appraisal" in exc.value.detail.lower()


@pytest.mark.regression
async def test_mg4_manager_review_rejects_cross_team():
    """A line manager cannot review someone outside their team."""
    from hr_advisory.api.routers.appraisals import manager_review_appraisal

    rajesh = {"sub": "4", "role": "employee", "company_id": 1}

    with patch(
        "hr_advisory.services.dataflow_crud.read",
        return_value={"id": 100, "employee_id": 99, "company_id": 1,
                      "status": "submitted"},
    ), patch(
        "hr_advisory.services.dataflow_crud.list_records",
        return_value=[{"id": 3, "user_id": 4}],  # Rajesh's emp row
    ), patch(
        "hr_advisory.services.manager_scope.is_manager_of",
        return_value=False,
    ), patch(
        "hr_advisory.api.middleware.rate_limit.check_rate_limit"
    ):
        with pytest.raises(HTTPException) as exc:
            await manager_review_appraisal(
                appraisal_id=100,
                request=_FakeRequest({}),
                current_user=rajesh,
            )
    assert exc.value.status_code == 403
    assert "not the manager" in exc.value.detail.lower()


@pytest.mark.regression
async def test_mg4_manager_review_rejects_wrong_status():
    """Can only review when status='submitted'. A draft or already-
    reviewed appraisal must 400."""
    from hr_advisory.api.routers.appraisals import manager_review_appraisal

    owner = {"sub": "1", "role": "owner", "company_id": 1}

    with patch(
        "hr_advisory.services.dataflow_crud.read",
        return_value={"id": 100, "employee_id": 99, "company_id": 1,
                      "status": "in_progress"},  # not yet submitted
    ), patch(
        "hr_advisory.services.dataflow_crud.list_records",
        return_value=[],
    ), patch(
        "hr_advisory.api.middleware.rate_limit.check_rate_limit"
    ):
        with pytest.raises(HTTPException) as exc:
            await manager_review_appraisal(
                appraisal_id=100,
                request=_FakeRequest({}),
                current_user=owner,
            )
    assert exc.value.status_code == 400
    assert "submitted" in exc.value.detail.lower()


@pytest.mark.regression
async def test_mg4_manager_review_happy_path():
    """Line manager reviewing a direct report's submitted appraisal
    transitions status to 'reviewed' and records reviewer + score."""
    from hr_advisory.api.routers.appraisals import manager_review_appraisal

    rajesh = {"sub": "4", "role": "employee", "company_id": 1}
    captured: dict = {}

    def fake_update(model_name, record_id, updates):
        captured["updates"] = updates
        captured["id"] = record_id
        return {"id": record_id, **updates}

    with patch(
        "hr_advisory.services.dataflow_crud.read",
        return_value={"id": 100, "employee_id": 10, "company_id": 1,
                      "status": "submitted"},
    ), patch(
        "hr_advisory.services.dataflow_crud.list_records",
        return_value=[{"id": 3, "user_id": 4}],  # Rajesh's emp row (not target)
    ), patch(
        "hr_advisory.services.manager_scope.is_manager_of",
        return_value=True,
    ), patch(
        "hr_advisory.services.dataflow_crud.update", side_effect=fake_update
    ), patch(
        "hr_advisory.api.middleware.rate_limit.check_rate_limit"
    ):
        result = await manager_review_appraisal(
            appraisal_id=100,
            request=_FakeRequest({
                "reviewer_comments": "Strong delivery this quarter",
                "overall_score": 4.5,
            }),
            current_user=rajesh,
        )
    assert result["detail"] == "Manager review recorded."
    assert captured["updates"]["status"] == "reviewed"
    assert captured["updates"]["reviewed_by"] == 4
    assert captured["updates"]["overall_score"] == 4.5
    assert captured["updates"]["reviewer_comments"] == "Strong delivery this quarter"


# ---------------------------------------------------------------------------
# Team dashboard now surfaces the appraisal count.
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_mg4_team_dashboard_includes_appraisals_count():
    src = TEAM_ROUTER.read_text()
    assert '"appraisals": appraisals_to_review_count' in src, (
        "Team dashboard pending_approvals must include the appraisals "
        "to-review count alongside leave/claims/timesheets."
    )
    assert "appraisals_to_review_count" in src, (
        "Team dashboard must compute an appraisals_to_review_count."
    )


@pytest.mark.regression
def test_mg4_team_page_renders_appraisal_card():
    src = TEAM_PAGE.read_text()
    assert "appraisals" in src.lower(), (
        "Team page must surface the appraisals count in the "
        "pending-approvals card (P4-MG-4)."
    )
    assert "Review appraisals" in src, (
        "Team page must link to /appraisals for the manager review "
        "queue."
    )