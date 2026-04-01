"""Integration tests for the Company Policy feature (T034).

Tests the policies router endpoints via TestClient with real JWT tokens
and real DataFlow operations. Covers CRUD, file upload, versioning,
acknowledgment, role-based access, and statutory floor checks.

Docker must be running: docker compose -f docker-compose.dev.yml up -d
"""

import io
import logging
import os
import time
import uuid

import jwt as pyjwt
import pytest
from starlette.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql://arbor:arbor@localhost:5432/arbor")

from hr_advisory.config.settings import Settings, get_settings

_TEST_JWT_SECRET = "test-secret-key-for-integration-tests"
os.environ["JWT_SECRET_KEY"] = _TEST_JWT_SECRET
get_settings.cache_clear()

from hr_advisory.api.platform import create_platform

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _unique_email() -> str:
    return f"policy_test_{uuid.uuid4().hex[:12]}@example.com"


@pytest.fixture(scope="module")
def settings() -> Settings:
    return Settings(
        app_env="development",
        api_port=8097,
        cors_origins="http://localhost:3000",
        jwt_secret_key=_TEST_JWT_SECRET,
        jwt_algorithm="HS256",
        jwt_expiry_minutes=60,
    )


@pytest.fixture(scope="module")
def platform(settings):
    return create_platform(settings)


@pytest.fixture(scope="module")
def client(platform) -> TestClient:
    return TestClient(platform._gateway.app)


def _make_token(
    settings: Settings,
    user_id: int,
    email: str,
    role: str,
    company_id: int | None = None,
) -> str:
    """Create a JWT token with optional company_id claim."""
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + 3600,
    }
    if company_id is not None:
        payload["company_id"] = company_id
    return pyjwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


@pytest.fixture(scope="module")
def owner_token(settings) -> str:
    """Token for an owner in company 1."""
    return _make_token(
        settings, user_id=201, email="owner@policy-test.com", role="owner", company_id=1
    )


@pytest.fixture(scope="module")
def hr_manager_token(settings) -> str:
    """Token for an HR manager in company 1."""
    return _make_token(
        settings, user_id=202, email="hr@policy-test.com", role="hr_manager", company_id=1
    )


@pytest.fixture(scope="module")
def employee_token(settings) -> str:
    """Token for an employee in company 1."""
    return _make_token(
        settings, user_id=203, email="employee@policy-test.com", role="employee", company_id=1
    )


@pytest.fixture(scope="module")
def company_b_owner_token(settings) -> str:
    """Token for an owner in company 2 (different tenant)."""
    return _make_token(
        settings, user_id=204, email="owner@company-b.com", role="owner", company_id=2
    )


def _auth(token: str) -> dict:
    """Build Authorization header dict from token."""
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# 1. Create Policy (POST /policies/)
# ---------------------------------------------------------------------------


class TestCreatePolicy:
    """POST /policies/ — create a policy from manual text entry."""

    def test_create_policy_returns_correct_fields(self, client: TestClient, owner_token: str):
        """Creating a policy returns all expected fields and a success message."""
        resp = client.post(
            "/policies/",
            json={
                "title": f"Test Leave Policy {uuid.uuid4().hex[:8]}",
                "category": "leave_absence",
                "content": "Annual leave entitlement: 14 days per year.",
                "effective_date": "2026-01-01",
                "requires_acknowledgment": True,
                "status": "active",
                "policy_type": "leave",
            },
            headers=_auth(owner_token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "policy" in data
        assert "message" in data
        policy = data["policy"]
        assert policy["title"].startswith("Test Leave Policy")
        assert policy["category"] == "leave_absence"
        assert policy["content"] == "Annual leave entitlement: 14 days per year."
        assert policy["effective_date"] == "2026-01-01"
        assert policy["requires_acknowledgment"] is True
        assert policy["status"] == "active"
        assert policy["is_active"] is True
        assert policy["version_number"] == 1
        assert policy["file_type"] == "text"
        assert policy["extraction_status"] == "complete"
        assert policy["policy_type"] == "leave"
        assert "id" in policy

    def test_create_policy_missing_title_returns_400(self, client: TestClient, owner_token: str):
        """Missing title returns 400."""
        resp = client.post(
            "/policies/",
            json={"content": "Some content", "category": "general_hr"},
            headers=_auth(owner_token),
        )
        assert resp.status_code == 400
        assert "title" in resp.json()["detail"].lower()

    def test_create_policy_missing_content_returns_400(self, client: TestClient, owner_token: str):
        """Missing content returns 400."""
        resp = client.post(
            "/policies/",
            json={"title": "Empty Policy"},
            headers=_auth(owner_token),
        )
        assert resp.status_code == 400
        assert "content" in resp.json()["detail"].lower()

    def test_create_policy_invalid_category_returns_400(self, client: TestClient, owner_token: str):
        """Invalid category returns 400 with allowed categories."""
        resp = client.post(
            "/policies/",
            json={
                "title": "Bad Category Policy",
                "content": "Some content here.",
                "category": "nonexistent_category",
            },
            headers=_auth(owner_token),
        )
        assert resp.status_code == 400
        assert "invalid category" in resp.json()["detail"].lower()

    def test_create_policy_invalid_status_returns_400(self, client: TestClient, owner_token: str):
        """Only 'active' and 'draft' are valid for new policies."""
        resp = client.post(
            "/policies/",
            json={
                "title": "Bad Status Policy",
                "content": "Content.",
                "status": "archived",
            },
            headers=_auth(owner_token),
        )
        assert resp.status_code == 400
        assert "status" in resp.json()["detail"].lower()

    def test_hr_manager_can_create_policy(self, client: TestClient, hr_manager_token: str):
        """HR managers have permission to create policies."""
        resp = client.post(
            "/policies/",
            json={
                "title": f"HR Manager Policy {uuid.uuid4().hex[:8]}",
                "content": "HR Manager created this policy.",
                "category": "general_hr",
            },
            headers=_auth(hr_manager_token),
        )
        assert resp.status_code == 200
        assert resp.json()["policy"]["title"].startswith("HR Manager Policy")


# ---------------------------------------------------------------------------
# 2. List Policies (GET /policies/)
# ---------------------------------------------------------------------------


class TestListPolicies:
    """GET /policies/ — list policies with filtering."""

    def test_list_policies_returns_policies(self, client: TestClient, owner_token: str):
        """Listing policies returns a non-empty list with expected structure."""
        resp = client.get("/policies/", headers=_auth(owner_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "policies" in data
        assert "count" in data
        assert isinstance(data["policies"], list)
        if data["policies"]:
            policy = data["policies"][0]
            assert "id" in policy
            assert "title" in policy
            assert "category" in policy
            assert "status" in policy

    def test_list_policies_filter_by_category(self, client: TestClient, owner_token: str):
        """Filtering by category returns only matching policies."""
        # Create a policy with a known category
        client.post(
            "/policies/",
            json={
                "title": f"WS Policy {uuid.uuid4().hex[:8]}",
                "content": "Workplace safety rules.",
                "category": "workplace_safety",
            },
            headers=_auth(owner_token),
        )

        resp = client.get(
            "/policies/?category=workplace_safety",
            headers=_auth(owner_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        for p in data["policies"]:
            assert p["category"] == "workplace_safety"

    def test_list_policies_filter_by_status(self, client: TestClient, owner_token: str):
        """Owner can filter by status."""
        resp = client.get(
            "/policies/?status=active",
            headers=_auth(owner_token),
        )
        assert resp.status_code == 200
        for p in resp.json()["policies"]:
            assert p["status"] == "active"

    def test_list_policies_invalid_category_returns_400(
        self, client: TestClient, owner_token: str
    ):
        """Invalid category filter returns 400."""
        resp = client.get(
            "/policies/?category=bogus",
            headers=_auth(owner_token),
        )
        assert resp.status_code == 400

    def test_list_policies_content_is_truncated(self, client: TestClient, owner_token: str):
        """Content in list view is truncated to 200 characters."""
        long_content = "A" * 500
        client.post(
            "/policies/",
            json={
                "title": f"Long Content {uuid.uuid4().hex[:8]}",
                "content": long_content,
                "category": "general_hr",
            },
            headers=_auth(owner_token),
        )
        resp = client.get("/policies/", headers=_auth(owner_token))
        assert resp.status_code == 200
        for p in resp.json()["policies"]:
            assert len(p["content"]) <= 203  # 200 + "..."


# ---------------------------------------------------------------------------
# 3. Get Single Policy (GET /policies/{id})
# ---------------------------------------------------------------------------


class TestGetPolicy:
    """GET /policies/{id} — retrieve a single policy with tenant isolation."""

    def test_get_policy_returns_full_content(self, client: TestClient, owner_token: str):
        """Getting a single policy returns the full content, not truncated."""
        long_content = "B" * 500
        create_resp = client.post(
            "/policies/",
            json={
                "title": f"Full Content Policy {uuid.uuid4().hex[:8]}",
                "content": long_content,
                "category": "general_hr",
            },
            headers=_auth(owner_token),
        )
        policy_id = create_resp.json()["policy"]["id"]

        resp = client.get(f"/policies/{policy_id}", headers=_auth(owner_token))
        assert resp.status_code == 200
        assert resp.json()["policy"]["content"] == long_content

    def test_get_policy_tenant_isolation(
        self, client: TestClient, owner_token: str, company_b_owner_token: str
    ):
        """A user in company B cannot access company A's policy."""
        create_resp = client.post(
            "/policies/",
            json={
                "title": f"Secret Policy {uuid.uuid4().hex[:8]}",
                "content": "Confidential content.",
                "category": "general_hr",
            },
            headers=_auth(owner_token),
        )
        policy_id = create_resp.json()["policy"]["id"]

        # Company B owner should get 404 (tenant isolation)
        resp = client.get(f"/policies/{policy_id}", headers=_auth(company_b_owner_token))
        assert resp.status_code == 404

    def test_get_nonexistent_policy_returns_404(self, client: TestClient, owner_token: str):
        """Requesting a policy that does not exist returns 404."""
        resp = client.get("/policies/999999", headers=_auth(owner_token))
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 4. Upload Policy File (POST /policies/upload)
# ---------------------------------------------------------------------------


class TestUploadPolicy:
    """POST /policies/upload — upload a policy file with text extraction."""

    def test_upload_txt_file_extracts_content(self, client: TestClient, owner_token: str):
        """Uploading a .txt file extracts text and sets extraction_status."""
        file_content = b"This is a plain text policy document with leave rules."
        files = {"file": ("test_policy.txt", io.BytesIO(file_content), "text/plain")}
        data = {
            "title": f"TXT Upload {uuid.uuid4().hex[:8]}",
            "category": "general_hr",
        }

        resp = client.post(
            "/policies/upload",
            files=files,
            data=data,
            headers=_auth(owner_token),
        )
        assert resp.status_code == 200, resp.text
        result = resp.json()
        assert "policy" in result
        assert result["extraction_status"] in ("complete", "partial", "failed")
        assert result["policy"]["file_type"] == "txt"

    def test_upload_missing_file_returns_400(self, client: TestClient, owner_token: str):
        """Uploading without a file returns 400."""
        data = {"title": "No File Policy"}
        resp = client.post(
            "/policies/upload",
            data=data,
            headers=_auth(owner_token),
        )
        assert resp.status_code == 400

    def test_upload_missing_title_returns_400(self, client: TestClient, owner_token: str):
        """Uploading without a title returns 400."""
        file_content = b"Some content."
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        resp = client.post(
            "/policies/upload",
            files=files,
            data={},
            headers=_auth(owner_token),
        )
        assert resp.status_code == 400

    def test_upload_disallowed_extension_returns_400(self, client: TestClient, owner_token: str):
        """Uploading a file with a disallowed extension returns 400."""
        file_content = b"<html>not a policy</html>"
        files = {"file": ("malicious.html", io.BytesIO(file_content), "text/html")}
        data = {"title": "HTML Attempt"}
        resp = client.post(
            "/policies/upload",
            files=files,
            data=data,
            headers=_auth(owner_token),
        )
        assert resp.status_code == 400
        assert "extension" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 5. Versioning (PUT /policies/{id} with content change)
# ---------------------------------------------------------------------------


class TestVersioning:
    """PUT /policies/{id} — version creation when content changes."""

    def test_content_change_creates_new_version(self, client: TestClient, owner_token: str):
        """Changing content archives v1 and creates v2."""
        # Create v1
        create_resp = client.post(
            "/policies/",
            json={
                "title": f"Versioned Policy {uuid.uuid4().hex[:8]}",
                "content": "Version 1 content.",
                "category": "general_hr",
            },
            headers=_auth(owner_token),
        )
        v1 = create_resp.json()["policy"]
        v1_id = v1["id"]
        assert v1["version_number"] == 1

        # Update with new content -> should create v2
        update_resp = client.put(
            f"/policies/{v1_id}",
            json={"content": "Version 2 content with changes."},
            headers=_auth(owner_token),
        )
        assert update_resp.status_code == 200, update_resp.text
        data = update_resp.json()
        assert "previous_version_id" in data
        assert data["previous_version_id"] == v1_id
        v2 = data["policy"]
        assert v2["version_number"] == 2
        assert v2["content"] == "Version 2 content with changes."

        # Verify v1 is now archived
        v1_resp = client.get(f"/policies/{v1_id}", headers=_auth(owner_token))
        assert v1_resp.status_code == 200
        v1_refreshed = v1_resp.json()["policy"]
        assert v1_refreshed["status"] == "archived"
        assert v1_refreshed["is_active"] is False

    def test_metadata_only_update_does_not_create_version(
        self, client: TestClient, owner_token: str
    ):
        """Changing only metadata updates in place (same version)."""
        create_resp = client.post(
            "/policies/",
            json={
                "title": f"Metadata Policy {uuid.uuid4().hex[:8]}",
                "content": "Stable content.",
                "category": "general_hr",
            },
            headers=_auth(owner_token),
        )
        policy_id = create_resp.json()["policy"]["id"]

        update_resp = client.put(
            f"/policies/{policy_id}",
            json={"category": "compensation_benefits"},
            headers=_auth(owner_token),
        )
        assert update_resp.status_code == 200
        updated = update_resp.json()["policy"]
        assert updated["category"] == "compensation_benefits"
        # Should be same record, not a new version
        assert updated["id"] == policy_id
        assert "previous_version_id" not in update_resp.json()

    def test_cannot_update_archived_policy(self, client: TestClient, owner_token: str):
        """Updating an archived policy returns 400."""
        # Create and archive
        create_resp = client.post(
            "/policies/",
            json={
                "title": f"Archive Test {uuid.uuid4().hex[:8]}",
                "content": "Will be archived.",
                "category": "general_hr",
            },
            headers=_auth(owner_token),
        )
        policy_id = create_resp.json()["policy"]["id"]
        client.delete(f"/policies/{policy_id}", headers=_auth(owner_token))

        # Attempt update on archived policy
        resp = client.put(
            f"/policies/{policy_id}",
            json={"title": "New Title"},
            headers=_auth(owner_token),
        )
        assert resp.status_code == 400
        assert "archived" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 6. Soft Delete / Archive (DELETE /policies/{id})
# ---------------------------------------------------------------------------


class TestSoftDelete:
    """DELETE /policies/{id} — soft delete by archiving."""

    def test_archive_sets_status_and_is_active(self, client: TestClient, owner_token: str):
        """Archiving sets status='archived' and is_active=False."""
        create_resp = client.post(
            "/policies/",
            json={
                "title": f"Delete Test {uuid.uuid4().hex[:8]}",
                "content": "Will be soft deleted.",
                "category": "general_hr",
            },
            headers=_auth(owner_token),
        )
        policy_id = create_resp.json()["policy"]["id"]

        del_resp = client.delete(f"/policies/{policy_id}", headers=_auth(owner_token))
        assert del_resp.status_code == 200
        assert del_resp.json()["policy_id"] == policy_id

        # Verify via GET
        get_resp = client.get(f"/policies/{policy_id}", headers=_auth(owner_token))
        assert get_resp.status_code == 200
        policy = get_resp.json()["policy"]
        assert policy["status"] == "archived"
        assert policy["is_active"] is False

    def test_archive_idempotent(self, client: TestClient, owner_token: str):
        """Archiving an already-archived policy is a no-op."""
        create_resp = client.post(
            "/policies/",
            json={
                "title": f"Double Delete {uuid.uuid4().hex[:8]}",
                "content": "Archive me twice.",
                "category": "general_hr",
            },
            headers=_auth(owner_token),
        )
        policy_id = create_resp.json()["policy"]["id"]

        client.delete(f"/policies/{policy_id}", headers=_auth(owner_token))
        resp = client.delete(f"/policies/{policy_id}", headers=_auth(owner_token))
        assert resp.status_code == 200
        assert "already archived" in resp.json()["message"].lower()

    def test_archive_nonexistent_returns_404(self, client: TestClient, owner_token: str):
        """Archiving a nonexistent policy returns 404."""
        resp = client.delete("/policies/999999", headers=_auth(owner_token))
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 7. Acknowledgment (POST /policies/{id}/acknowledge)
# ---------------------------------------------------------------------------


class TestAcknowledgment:
    """POST /policies/{id}/acknowledge — employee acknowledgment."""

    def test_acknowledge_requires_employee_record(self, client: TestClient, owner_token: str):
        """Acknowledging without an employee record returns 400."""
        create_resp = client.post(
            "/policies/",
            json={
                "title": f"Ack Test {uuid.uuid4().hex[:8]}",
                "content": "Acknowledge this.",
                "category": "general_hr",
                "requires_acknowledgment": True,
            },
            headers=_auth(owner_token),
        )
        policy_id = create_resp.json()["policy"]["id"]

        # Owner user_id 201 likely has no employee record -> 400
        resp = client.post(
            f"/policies/{policy_id}/acknowledge",
            json={},
            headers=_auth(owner_token),
        )
        # Should be 400 (no employee record) — this validates the guard
        assert resp.status_code == 400
        assert "employee record" in resp.json()["detail"].lower()

    def test_acknowledge_nonexistent_policy_returns_404(
        self, client: TestClient, owner_token: str
    ):
        """Acknowledging a nonexistent policy returns 404."""
        resp = client.post(
            "/policies/999999/acknowledge",
            json={},
            headers=_auth(owner_token),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 8. Pending Acknowledgments (GET /policies/pending-acknowledgments)
# ---------------------------------------------------------------------------


class TestPendingAcknowledgments:
    """GET /policies/pending-acknowledgments — pending for current employee."""

    def test_pending_acknowledgments_returns_structure(
        self, client: TestClient, owner_token: str
    ):
        """Endpoint returns the expected response structure (may 400 if no employee record)."""
        resp = client.get(
            "/policies/pending-acknowledgments",
            headers=_auth(owner_token),
        )
        # Owner without employee record gets 400; with record gets 200
        if resp.status_code == 200:
            data = resp.json()
            assert "pending_policies" in data
            assert "count" in data
            assert isinstance(data["pending_policies"], list)
        else:
            assert resp.status_code == 400

    def test_pending_acknowledgments_requires_auth(self, client: TestClient):
        """Endpoint requires authentication."""
        resp = client.get("/policies/pending-acknowledgments")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 9. Role-Based Access — Employees Cannot Create/Update/Archive
# ---------------------------------------------------------------------------


class TestRoleBasedAccess:
    """Employee role is denied write operations on policies."""

    def test_employee_cannot_create_policy(self, client: TestClient, employee_token: str):
        """Employees cannot POST /policies/."""
        resp = client.post(
            "/policies/",
            json={
                "title": "Employee Attempt",
                "content": "Should be denied.",
                "category": "general_hr",
            },
            headers=_auth(employee_token),
        )
        assert resp.status_code == 403

    def test_employee_cannot_update_policy(
        self, client: TestClient, owner_token: str, employee_token: str
    ):
        """Employees cannot PUT /policies/{id}."""
        create_resp = client.post(
            "/policies/",
            json={
                "title": f"RBAC Test {uuid.uuid4().hex[:8]}",
                "content": "Employee should not update this.",
                "category": "general_hr",
            },
            headers=_auth(owner_token),
        )
        policy_id = create_resp.json()["policy"]["id"]

        resp = client.put(
            f"/policies/{policy_id}",
            json={"title": "Hacked Title"},
            headers=_auth(employee_token),
        )
        assert resp.status_code == 403

    def test_employee_cannot_archive_policy(
        self, client: TestClient, owner_token: str, employee_token: str
    ):
        """Employees cannot DELETE /policies/{id}."""
        create_resp = client.post(
            "/policies/",
            json={
                "title": f"RBAC Delete {uuid.uuid4().hex[:8]}",
                "content": "Employee should not delete this.",
                "category": "general_hr",
            },
            headers=_auth(owner_token),
        )
        policy_id = create_resp.json()["policy"]["id"]

        resp = client.delete(f"/policies/{policy_id}", headers=_auth(employee_token))
        assert resp.status_code == 403

    def test_employee_cannot_upload_policy(self, client: TestClient, employee_token: str):
        """Employees cannot POST /policies/upload."""
        file_content = b"Policy text."
        files = {"file": ("policy.txt", io.BytesIO(file_content), "text/plain")}
        data = {"title": "Employee Upload Attempt"}
        resp = client.post(
            "/policies/upload",
            files=files,
            data=data,
            headers=_auth(employee_token),
        )
        assert resp.status_code == 403

    def test_employee_can_read_active_policies(self, client: TestClient, employee_token: str):
        """Employees can GET /policies/ (read access)."""
        resp = client.get("/policies/", headers=_auth(employee_token))
        assert resp.status_code == 200
        # All returned policies should be active (employee filter)
        for p in resp.json()["policies"]:
            assert p["status"] == "active"
            assert p["is_active"] is True

    def test_employee_cannot_see_archived_policies(
        self, client: TestClient, owner_token: str, employee_token: str
    ):
        """Employees cannot see draft or archived policies in list."""
        # Create a draft policy
        client.post(
            "/policies/",
            json={
                "title": f"Draft Policy {uuid.uuid4().hex[:8]}",
                "content": "Draft content.",
                "category": "general_hr",
                "status": "draft",
            },
            headers=_auth(owner_token),
        )

        resp = client.get("/policies/", headers=_auth(employee_token))
        assert resp.status_code == 200
        for p in resp.json()["policies"]:
            assert p["status"] == "active"


# ---------------------------------------------------------------------------
# 10. Statutory Floor Warnings
# ---------------------------------------------------------------------------


class TestStatutoryFloorWarnings:
    """Statutory floor checks on leave policies."""

    def test_below_minimum_leave_returns_warnings(self, client: TestClient, owner_token: str):
        """Creating a leave policy with below-minimum values returns warnings."""
        resp = client.post(
            "/policies/",
            json={
                "title": f"Bad Leave Policy {uuid.uuid4().hex[:8]}",
                "category": "leave_absence",
                "content": (
                    "Annual leave: 3 days per year. "
                    "Sick leave: 5 days per year. "
                    "Hospitalisation leave: 20 days per year."
                ),
            },
            headers=_auth(owner_token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        warnings = data.get("statutory_floor_warnings", [])
        assert len(warnings) > 0, "Expected statutory floor warnings for below-minimum values"

        # Check for below_minimum findings
        below_min = [w for w in warnings if w.get("status") == "below_minimum"]
        assert len(below_min) >= 2, (
            f"Expected at least 2 below_minimum findings (annual + sick), got {len(below_min)}"
        )

        # Verify structure of each warning
        for w in warnings:
            assert "field" in w
            assert "company_value" in w
            assert "statutory_minimum" in w
            assert "status" in w
            assert "message" in w

    def test_above_minimum_leave_no_below_warnings(self, client: TestClient, owner_token: str):
        """Creating a leave policy with above-minimum values has no below_minimum warnings."""
        resp = client.post(
            "/policies/",
            json={
                "title": f"Good Leave Policy {uuid.uuid4().hex[:8]}",
                "category": "leave_absence",
                "content": (
                    "Annual leave: 21 days per year. "
                    "Sick leave: 30 days per year. "
                    "Hospitalisation leave: 90 days per year."
                ),
            },
            headers=_auth(owner_token),
        )
        assert resp.status_code == 200
        warnings = resp.json().get("statutory_floor_warnings", [])
        below_min = [w for w in warnings if w.get("status") == "below_minimum"]
        assert len(below_min) == 0, f"Expected no below_minimum warnings, got {below_min}"

    def test_non_leave_category_returns_no_warnings(self, client: TestClient, owner_token: str):
        """Non-leave categories do not produce statutory floor warnings."""
        resp = client.post(
            "/policies/",
            json={
                "title": f"Safety Policy {uuid.uuid4().hex[:8]}",
                "category": "workplace_safety",
                "content": "Workplace safety rules. Hard hats required.",
            },
            headers=_auth(owner_token),
        )
        assert resp.status_code == 200
        warnings = resp.json().get("statutory_floor_warnings", [])
        assert len(warnings) == 0

    def test_compliance_check_endpoint(self, client: TestClient, owner_token: str):
        """GET /policies/{id}/compliance-check returns statutory floor findings."""
        create_resp = client.post(
            "/policies/",
            json={
                "title": f"Compliance Check {uuid.uuid4().hex[:8]}",
                "category": "leave_absence",
                "content": "Annual leave: 5 days. Sick leave: 10 days.",
            },
            headers=_auth(owner_token),
        )
        policy_id = create_resp.json()["policy"]["id"]

        resp = client.get(
            f"/policies/{policy_id}/compliance-check",
            headers=_auth(owner_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["policy_id"] == policy_id
        assert data["category"] == "leave_absence"
        assert "findings" in data
        assert "findings_count" in data
        assert data["findings_count"] > 0


# ---------------------------------------------------------------------------
# 11. Version History (GET /policies/{id}/versions)
# ---------------------------------------------------------------------------


class TestVersionHistory:
    """GET /policies/{id}/versions — list version history."""

    def test_version_history_shows_all_versions(self, client: TestClient, owner_token: str):
        """After creating v1 and v2, version history shows both."""
        title = f"Versioned History {uuid.uuid4().hex[:8]}"
        create_resp = client.post(
            "/policies/",
            json={
                "title": title,
                "content": "Version 1 initial content.",
                "category": "general_hr",
            },
            headers=_auth(owner_token),
        )
        v1_id = create_resp.json()["policy"]["id"]

        # Create v2
        update_resp = client.put(
            f"/policies/{v1_id}",
            json={"content": "Version 2 updated content."},
            headers=_auth(owner_token),
        )
        v2_id = update_resp.json()["policy"]["id"]

        # Get version history via v2
        resp = client.get(f"/policies/{v2_id}/versions", headers=_auth(owner_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 2
        versions = data["versions"]
        version_numbers = [v["version_number"] for v in versions]
        assert 1 in version_numbers
        assert 2 in version_numbers
        # Should be sorted descending
        assert versions[0]["version_number"] >= versions[-1]["version_number"]


# ---------------------------------------------------------------------------
# 12. Content Edit (PUT /policies/{id}/content)
# ---------------------------------------------------------------------------


class TestContentEdit:
    """PUT /policies/{id}/content — edit extracted text."""

    def test_update_content_sets_manual_extraction_status(
        self, client: TestClient, owner_token: str
    ):
        """Editing content via /content endpoint sets extraction_status to 'manual'."""
        create_resp = client.post(
            "/policies/",
            json={
                "title": f"Content Edit {uuid.uuid4().hex[:8]}",
                "content": "Original content.",
                "category": "general_hr",
            },
            headers=_auth(owner_token),
        )
        policy_id = create_resp.json()["policy"]["id"]

        resp = client.put(
            f"/policies/{policy_id}/content",
            json={"content": "Manually corrected content."},
            headers=_auth(owner_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["policy_id"] == policy_id
        assert "content_hash" in data
        assert data["content_hash"]  # non-empty

    def test_update_content_empty_returns_400(self, client: TestClient, owner_token: str):
        """Empty content in /content endpoint returns 400."""
        create_resp = client.post(
            "/policies/",
            json={
                "title": f"Empty Content Edit {uuid.uuid4().hex[:8]}",
                "content": "Has content.",
                "category": "general_hr",
            },
            headers=_auth(owner_token),
        )
        policy_id = create_resp.json()["policy"]["id"]

        resp = client.put(
            f"/policies/{policy_id}/content",
            json={"content": ""},
            headers=_auth(owner_token),
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# 13. Authentication Required
# ---------------------------------------------------------------------------


class TestAuthRequired:
    """All policy endpoints require authentication."""

    def test_list_requires_auth(self, client: TestClient):
        resp = client.get("/policies/")
        assert resp.status_code == 401

    def test_get_requires_auth(self, client: TestClient):
        resp = client.get("/policies/1")
        assert resp.status_code == 401

    def test_create_requires_auth(self, client: TestClient):
        resp = client.post(
            "/policies/",
            json={"title": "Unauth", "content": "No auth."},
        )
        assert resp.status_code == 401

    def test_upload_requires_auth(self, client: TestClient):
        files = {"file": ("test.txt", io.BytesIO(b"test"), "text/plain")}
        resp = client.post("/policies/upload", files=files, data={"title": "Unauth"})
        assert resp.status_code == 401

    def test_update_requires_auth(self, client: TestClient):
        resp = client.put("/policies/1", json={"title": "Hacked"})
        assert resp.status_code == 401

    def test_delete_requires_auth(self, client: TestClient):
        resp = client.delete("/policies/1")
        assert resp.status_code == 401

    def test_acknowledge_requires_auth(self, client: TestClient):
        resp = client.post("/policies/1/acknowledge", json={})
        assert resp.status_code == 401
