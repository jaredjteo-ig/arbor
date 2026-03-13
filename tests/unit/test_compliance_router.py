"""Unit tests for the compliance router endpoints.

Tests the compliance check, status, and gap-analysis logic using
mocked KB functions (search_provisions, get_kb_stats). Validates:

1. POST /check: domain-based compliance evaluation with real provision counts
2. GET /status/{company_id}: domain coverage summary from KB
3. POST /gap-analysis: detailed gap analysis with severity and recommendations
4. Error handling: graceful degradation when KB is unavailable
5. Status classification: compliant / review_needed / non_compliant logic
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hr_advisory.api.routers.compliance import router


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


def _make_app() -> FastAPI:
    """Build a minimal FastAPI app with the compliance router mounted."""
    app = FastAPI()
    app.include_router(router, prefix="/compliance")
    return app


def _fake_user(company_id: int = 1, role: str = "owner") -> dict:
    return {
        "sub": 10,
        "email": "test@example.com",
        "role": role,
        "company_id": company_id,
    }


def _provision(domain_name: str, section: str = "s1", title: str = "Test Provision") -> dict:
    """Build a minimal provision dict matching DataFlow output shape."""
    return {
        "id": 1,
        "domain_id": 1,
        "domain_name": domain_name,
        "section": section,
        "title": title,
        "formal_text": "Some formal text.",
        "is_active": True,
    }


@pytest.fixture()
def client():
    """Test client with auth dependency overridden."""
    from hr_advisory.api.middleware.auth_middleware import get_current_user

    app = _make_app()
    app.dependency_overrides[get_current_user] = lambda: _fake_user()
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 1. POST /check -- compliance check
# ---------------------------------------------------------------------------


class TestComplianceCheck:
    """POST /compliance/check evaluates KB coverage per domain."""

    @patch("hr_advisory.api.routers.compliance.search_provisions")
    def test_all_domains_covered_returns_compliant(self, mock_search, client):
        """When provisions exist for every requested domain, status is 'compliant'."""
        mock_search.return_value = [_provision("employment_act")] * 5
        resp = client.post(
            "/compliance/check",
            json={
                "company_id": 1,
                "domains": ["employment_act"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "compliant"
        assert data["company_id"] == 1
        assert len(data["findings"]) >= 1
        # Provision count must come from real data, not hardcoded
        finding = data["findings"][0]
        assert finding["provisions_checked"] == 5
        assert finding["domain"] == "employment_act"

    @patch("hr_advisory.api.routers.compliance.search_provisions")
    def test_missing_non_critical_domain_returns_review_needed(self, mock_search, client):
        """Domains with no provisions that are not critical -> review_needed."""

        def side_effect(domain, limit=100):
            if domain == "wsh":
                return []
            return [_provision(domain)] * 3

        mock_search.side_effect = side_effect
        resp = client.post(
            "/compliance/check",
            json={
                "company_id": 1,
                "domains": ["employment_act", "wsh"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "review_needed"

    @patch("hr_advisory.api.routers.compliance.search_provisions")
    def test_missing_critical_domain_returns_non_compliant(self, mock_search, client):
        """When critical domains (employment_act, cpf) have no provisions -> non_compliant."""

        def side_effect(domain, limit=100):
            if domain == "employment_act":
                return []
            return [_provision(domain)] * 3

        mock_search.side_effect = side_effect
        resp = client.post(
            "/compliance/check",
            json={
                "company_id": 1,
                "domains": ["employment_act", "wsh"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "non_compliant"

    @patch("hr_advisory.api.routers.compliance.search_provisions")
    def test_missing_cpf_returns_non_compliant(self, mock_search, client):
        """CPF is critical -- missing provisions -> non_compliant."""

        def side_effect(domain, limit=100):
            if domain == "cpf":
                return []
            return [_provision(domain)] * 3

        mock_search.side_effect = side_effect
        resp = client.post(
            "/compliance/check",
            json={
                "company_id": 1,
                "domains": ["cpf", "wsh"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "non_compliant"

    @patch("hr_advisory.api.routers.compliance.search_provisions")
    def test_default_domains_when_none_requested(self, mock_search, client):
        """When no domains specified, all core domains are checked."""
        mock_search.return_value = [_provision("x")] * 2
        resp = client.post(
            "/compliance/check",
            json={
                "company_id": 1,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        # Should have checked the default set of core domains
        domains_checked = data["domains_checked"]
        assert "employment_act" in domains_checked
        assert "cpf" in domains_checked
        assert len(domains_checked) >= 5

    @patch("hr_advisory.api.routers.compliance.search_provisions")
    def test_findings_contain_domain_and_count(self, mock_search, client):
        """Each finding includes domain name, status, and provision count."""
        mock_search.return_value = [_provision("employment_act")] * 7
        resp = client.post(
            "/compliance/check",
            json={
                "company_id": 1,
                "domains": ["employment_act"],
            },
        )
        data = resp.json()
        finding = data["findings"][0]
        assert "domain" in finding
        assert "status" in finding
        assert "provisions_checked" in finding
        assert finding["provisions_checked"] == 7

    @patch("hr_advisory.api.routers.compliance.search_provisions")
    def test_recommendations_for_gaps(self, mock_search, client):
        """When gaps exist, recommendations list is non-empty."""

        def side_effect(domain, limit=100):
            if domain == "wsh":
                return []
            return [_provision(domain)] * 3

        mock_search.side_effect = side_effect
        resp = client.post(
            "/compliance/check",
            json={
                "company_id": 1,
                "domains": ["employment_act", "wsh"],
            },
        )
        data = resp.json()
        assert len(data["recommendations"]) > 0

    @patch("hr_advisory.api.routers.compliance.search_provisions")
    def test_no_recommendations_when_fully_compliant(self, mock_search, client):
        """When all domains are covered, recommendations should be empty."""
        mock_search.return_value = [_provision("employment_act")] * 5
        resp = client.post(
            "/compliance/check",
            json={
                "company_id": 1,
                "domains": ["employment_act"],
            },
        )
        data = resp.json()
        assert data["recommendations"] == []

    @patch("hr_advisory.api.routers.compliance.search_provisions")
    def test_timestamp_is_present(self, mock_search, client):
        """Response includes an ISO timestamp."""
        mock_search.return_value = [_provision("employment_act")]
        resp = client.post(
            "/compliance/check",
            json={
                "company_id": 1,
                "domains": ["employment_act"],
            },
        )
        data = resp.json()
        assert "timestamp" in data
        # Should be parseable as ISO datetime
        datetime.fromisoformat(data["timestamp"])

    @patch("hr_advisory.api.routers.compliance.search_provisions")
    def test_kb_unavailable_returns_error_status(self, mock_search, client):
        """When KB raises an exception, endpoint returns graceful error, not 500."""
        mock_search.side_effect = Exception("Database connection failed")
        resp = client.post(
            "/compliance/check",
            json={
                "company_id": 1,
                "domains": ["employment_act"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "non_compliant"
        assert "error" in data or len(data["recommendations"]) > 0

    @patch("hr_advisory.api.routers.compliance.search_provisions")
    def test_risk_tier_green_when_compliant(self, mock_search, client):
        """Risk tier is 'green' when fully compliant."""
        mock_search.return_value = [_provision("employment_act")] * 5
        resp = client.post(
            "/compliance/check",
            json={
                "company_id": 1,
                "domains": ["employment_act"],
            },
        )
        data = resp.json()
        assert data["risk_tier"] == "green"

    @patch("hr_advisory.api.routers.compliance.search_provisions")
    def test_risk_tier_red_when_non_compliant(self, mock_search, client):
        """Risk tier is 'red' when critical domains are missing."""
        mock_search.return_value = []
        resp = client.post(
            "/compliance/check",
            json={
                "company_id": 1,
                "domains": ["employment_act"],
            },
        )
        data = resp.json()
        assert data["risk_tier"] == "red"


# ---------------------------------------------------------------------------
# 2. GET /status/{company_id} -- compliance status
# ---------------------------------------------------------------------------


class TestComplianceStatus:
    """GET /compliance/status/{company_id} returns domain coverage summary."""

    @patch("hr_advisory.api.routers.compliance.get_kb_stats")
    @patch("hr_advisory.api.routers.compliance.search_provisions")
    def test_returns_domain_coverage(self, mock_search, mock_stats, client):
        """Status endpoint returns per-domain coverage information."""
        mock_stats.return_value = {"provisions": 50, "domains": 5, "acts": 10}
        mock_search.return_value = [_provision("x")] * 4
        resp = client.get("/compliance/status/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["company_id"] == 1
        assert "domains" in data
        assert "overall_status" in data
        assert "last_check" in data

    @patch("hr_advisory.api.routers.compliance.get_kb_stats")
    @patch("hr_advisory.api.routers.compliance.search_provisions")
    def test_includes_total_provisions(self, mock_search, mock_stats, client):
        """Status response includes total provision count from get_kb_stats."""
        mock_stats.return_value = {"provisions": 42, "domains": 5, "acts": 10}
        mock_search.return_value = [_provision("x")] * 3
        resp = client.get("/compliance/status/1")
        data = resp.json()
        assert data["total_provisions"] == 42

    @patch("hr_advisory.api.routers.compliance.get_kb_stats")
    @patch("hr_advisory.api.routers.compliance.search_provisions")
    def test_domains_have_status_per_domain(self, mock_search, mock_stats, client):
        """Each core domain in the response has a status field."""
        mock_stats.return_value = {"provisions": 50, "domains": 5, "acts": 10}

        def side_effect(domain, limit=100):
            if domain == "employment_act":
                return [_provision(domain)] * 10
            return [_provision(domain)] * 2

        mock_search.side_effect = side_effect
        resp = client.get("/compliance/status/1")
        data = resp.json()
        domains = data["domains"]
        assert "employment_act" in domains
        assert "status" in domains["employment_act"]
        assert "provisions_count" in domains["employment_act"]

    @patch("hr_advisory.api.routers.compliance.get_kb_stats")
    @patch("hr_advisory.api.routers.compliance.search_provisions")
    def test_kb_unavailable_returns_graceful_response(self, mock_search, mock_stats, client):
        """When KB is unavailable, returns a response instead of crashing."""
        mock_stats.side_effect = Exception("DB down")
        mock_search.side_effect = Exception("DB down")
        resp = client.get("/compliance/status/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["company_id"] == 1
        assert data["overall_status"] in ("unknown", "non_compliant")


# ---------------------------------------------------------------------------
# 3. POST /gap-analysis -- detailed gap analysis
# ---------------------------------------------------------------------------


class TestGapAnalysis:
    """POST /compliance/gap-analysis returns detailed gap information."""

    @patch("hr_advisory.api.routers.compliance.search_provisions")
    def test_no_gaps_when_all_domains_covered(self, mock_search, client):
        """When all domains have provisions, gaps list is empty."""
        mock_search.return_value = [_provision("x")] * 10
        resp = client.post(
            "/compliance/gap-analysis",
            json={
                "company_id": 1,
                "domains": ["employment_act", "cpf"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_gaps"] == 0
        assert data["critical_gaps"] == 0

    @patch("hr_advisory.api.routers.compliance.search_provisions")
    def test_critical_severity_for_employment_act_gap(self, mock_search, client):
        """Missing employment_act provisions -> severity 'critical'."""

        def side_effect(domain, limit=100):
            if domain == "employment_act":
                return []
            return [_provision(domain)] * 5

        mock_search.side_effect = side_effect
        resp = client.post(
            "/compliance/gap-analysis",
            json={
                "company_id": 1,
                "domains": ["employment_act", "wsh"],
            },
        )
        data = resp.json()
        assert data["total_gaps"] >= 1
        assert data["critical_gaps"] >= 1
        ea_gap = next(g for g in data["gaps"] if g["domain"] == "employment_act")
        assert ea_gap["severity"] == "critical"

    @patch("hr_advisory.api.routers.compliance.search_provisions")
    def test_critical_severity_for_cpf_gap(self, mock_search, client):
        """Missing CPF provisions -> severity 'critical'."""

        def side_effect(domain, limit=100):
            if domain == "cpf":
                return []
            return [_provision(domain)] * 5

        mock_search.side_effect = side_effect
        resp = client.post(
            "/compliance/gap-analysis",
            json={
                "company_id": 1,
                "domains": ["cpf", "wsh"],
            },
        )
        data = resp.json()
        cpf_gap = next(g for g in data["gaps"] if g["domain"] == "cpf")
        assert cpf_gap["severity"] == "critical"

    @patch("hr_advisory.api.routers.compliance.search_provisions")
    def test_high_severity_for_foreign_manpower_gap(self, mock_search, client):
        """Missing foreign_manpower provisions -> severity 'high'."""

        def side_effect(domain, limit=100):
            if domain == "foreign_manpower":
                return []
            return [_provision(domain)] * 5

        mock_search.side_effect = side_effect
        resp = client.post(
            "/compliance/gap-analysis",
            json={
                "company_id": 1,
                "domains": ["employment_act", "foreign_manpower"],
            },
        )
        data = resp.json()
        fm_gap = next(g for g in data["gaps"] if g["domain"] == "foreign_manpower")
        assert fm_gap["severity"] == "high"

    @patch("hr_advisory.api.routers.compliance.search_provisions")
    def test_medium_severity_for_other_domains(self, mock_search, client):
        """Missing provisions in non-critical domains -> severity 'medium'."""

        def side_effect(domain, limit=100):
            if domain == "tax":
                return []
            return [_provision(domain)] * 5

        mock_search.side_effect = side_effect
        resp = client.post(
            "/compliance/gap-analysis",
            json={
                "company_id": 1,
                "domains": ["employment_act", "tax"],
            },
        )
        data = resp.json()
        tax_gap = next(g for g in data["gaps"] if g["domain"] == "tax")
        assert tax_gap["severity"] == "medium"

    @patch("hr_advisory.api.routers.compliance.search_provisions")
    def test_gaps_include_remediation(self, mock_search, client):
        """Each gap entry includes a remediation recommendation."""
        mock_search.return_value = []
        resp = client.post(
            "/compliance/gap-analysis",
            json={
                "company_id": 1,
                "domains": ["employment_act"],
            },
        )
        data = resp.json()
        assert len(data["gaps"]) > 0
        gap = data["gaps"][0]
        assert "remediation" in gap
        assert len(gap["remediation"]) > 0

    @patch("hr_advisory.api.routers.compliance.search_provisions")
    def test_sparse_coverage_detected(self, mock_search, client):
        """A domain with very few provisions is flagged as a gap."""

        def side_effect(domain, limit=100):
            if domain == "wsh":
                return [_provision(domain)]  # Only 1 provision -- sparse
            return [_provision(domain)] * 10

        mock_search.side_effect = side_effect
        resp = client.post(
            "/compliance/gap-analysis",
            json={
                "company_id": 1,
                "domains": ["employment_act", "wsh"],
            },
        )
        data = resp.json()
        # wsh with only 1 provision should be flagged as sparse coverage
        wsh_gap = next((g for g in data["gaps"] if g["domain"] == "wsh"), None)
        assert wsh_gap is not None
        assert "sparse" in wsh_gap.get("reason", "").lower() or wsh_gap["provisions_found"] <= 2

    @patch("hr_advisory.api.routers.compliance.search_provisions")
    def test_default_domains_when_none_specified(self, mock_search, client):
        """When no domains specified, analysis covers all core domains."""
        mock_search.return_value = [_provision("x")] * 5
        resp = client.post(
            "/compliance/gap-analysis",
            json={
                "company_id": 1,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["company_id"] == 1
        # Should have analyzed core domains
        assert "domains_analyzed" in data
        assert len(data["domains_analyzed"]) >= 5

    @patch("hr_advisory.api.routers.compliance.search_provisions")
    def test_timestamp_present(self, mock_search, client):
        """Gap analysis response includes an ISO timestamp."""
        mock_search.return_value = [_provision("x")]
        resp = client.post(
            "/compliance/gap-analysis",
            json={
                "company_id": 1,
                "domains": ["employment_act"],
            },
        )
        data = resp.json()
        assert "timestamp" in data
        datetime.fromisoformat(data["timestamp"])

    @patch("hr_advisory.api.routers.compliance.search_provisions")
    def test_kb_unavailable_returns_graceful_response(self, mock_search, client):
        """When KB is unavailable, returns a response instead of crashing."""
        mock_search.side_effect = Exception("Database offline")
        resp = client.post(
            "/compliance/gap-analysis",
            json={
                "company_id": 1,
                "domains": ["employment_act"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_gaps"] >= 1
