"""Unit tests for recruitment email templates and automated stage transition emails.

Tests T-R017 (recruitment email templates) and T-R018 (automated email on stage
transitions) covering:

1. Template rendering: All 5 recruitment email templates render without errors
   when all placeholders are filled.
2. Template content: Subject and body contain expected variables and key phrases.
3. _send_recruitment_email helper:
   - Returns False when RESEND_API_KEY is not configured
   - Returns False for unknown template names
   - Handles adapter exceptions gracefully (never raises)
   - Returns True on successful send
4. Integration with add_candidate endpoint: application_received email is sent
   when a candidate is created with an email address.
"""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# T-R017: Template rendering tests
# ---------------------------------------------------------------------------


class TestRecruitmentTemplates:
    """Verify all recruitment email templates are well-formed and renderable."""

    def test_recruitment_templates_dict_exists(self):
        """RECRUITMENT_TEMPLATES dict exists and has all 5 templates."""
        from hr_advisory.templates.recruitment_emails import RECRUITMENT_TEMPLATES

        assert isinstance(RECRUITMENT_TEMPLATES, dict)
        expected_keys = {
            "application_received",
            "interview_invitation",
            "offer_sent",
            "rejection_notice",
            "feedback_reminder",
        }
        assert set(RECRUITMENT_TEMPLATES.keys()) == expected_keys

    def test_each_template_has_subject_and_html(self):
        """Each template entry must have 'subject' and 'html' keys."""
        from hr_advisory.templates.recruitment_emails import RECRUITMENT_TEMPLATES

        for name, template in RECRUITMENT_TEMPLATES.items():
            assert "subject" in template, f"Template '{name}' missing 'subject' key"
            assert "html" in template, f"Template '{name}' missing 'html' key"
            assert isinstance(template["subject"], str)
            assert isinstance(template["html"], str)

    # -- application_received --

    def test_application_received_renders(self):
        """application_received template renders with all placeholders filled."""
        from hr_advisory.templates.recruitment_emails import RECRUITMENT_TEMPLATES

        tpl = RECRUITMENT_TEMPLATES["application_received"]
        subject = tpl["subject"].format(
            candidate_name="Alice Tan",
            job_title="Software Engineer",
            company_name="Acme Pte Ltd",
        )
        html = tpl["html"].format(
            candidate_name="Alice Tan",
            job_title="Software Engineer",
            company_name="Acme Pte Ltd",
        )
        assert "Software Engineer" in subject
        assert "Acme Pte Ltd" in subject
        assert "Alice Tan" in html
        assert "Software Engineer" in html
        assert "Acme Pte Ltd" in html

    def test_application_received_subject_format(self):
        """application_received subject includes job title and company name."""
        from hr_advisory.templates.recruitment_emails import RECRUITMENT_TEMPLATES

        tpl = RECRUITMENT_TEMPLATES["application_received"]
        subject = tpl["subject"].format(
            candidate_name="Bob",
            job_title="Data Analyst",
            company_name="Test Corp",
        )
        assert "Data Analyst" in subject
        assert "Test Corp" in subject

    def test_application_received_html_is_valid_html(self):
        """application_received HTML body contains basic HTML structure."""
        from hr_advisory.templates.recruitment_emails import RECRUITMENT_TEMPLATES

        html = RECRUITMENT_TEMPLATES["application_received"]["html"]
        assert "<html" in html.lower()
        assert "</html>" in html.lower()
        assert "<body" in html.lower()

    def test_application_received_has_company_footer(self):
        """application_received includes company name in footer area."""
        from hr_advisory.templates.recruitment_emails import RECRUITMENT_TEMPLATES

        html = RECRUITMENT_TEMPLATES["application_received"]["html"].format(
            candidate_name="Alice",
            job_title="Engineer",
            company_name="Footer Corp",
        )
        # The company name should appear at least twice: in the body AND the footer
        assert html.count("Footer Corp") >= 2

    # -- interview_invitation --

    def test_interview_invitation_renders(self):
        """interview_invitation template renders with all placeholders filled."""
        from hr_advisory.templates.recruitment_emails import RECRUITMENT_TEMPLATES

        tpl = RECRUITMENT_TEMPLATES["interview_invitation"]
        subject = tpl["subject"].format(
            candidate_name="Charlie",
            job_title="Product Manager",
            company_name="Acme Pte Ltd",
            interview_date="15 April 2026",
            interview_time="10:00 AM",
            duration="60 minutes",
            interview_format="Video Call",
            location_or_link="https://meet.example.com/abc",
            interviewer_names="Dana Lee, Eric Ng",
        )
        html = tpl["html"].format(
            candidate_name="Charlie",
            job_title="Product Manager",
            company_name="Acme Pte Ltd",
            interview_date="15 April 2026",
            interview_time="10:00 AM",
            duration="60 minutes",
            interview_format="Video Call",
            location_or_link="https://meet.example.com/abc",
            interviewer_names="Dana Lee, Eric Ng",
        )
        assert "Product Manager" in subject
        assert "Acme Pte Ltd" in subject
        assert "Charlie" in html
        assert "15 April 2026" in html
        assert "10:00 AM" in html
        assert "Video Call" in html
        assert "Dana Lee, Eric Ng" in html

    # -- offer_sent --

    def test_offer_sent_renders(self):
        """offer_sent template renders with all placeholders filled."""
        from hr_advisory.templates.recruitment_emails import RECRUITMENT_TEMPLATES

        tpl = RECRUITMENT_TEMPLATES["offer_sent"]
        subject = tpl["subject"].format(
            candidate_name="Dana",
            position_title="Senior Developer",
            company_name="Acme Pte Ltd",
            salary="$8,000",
            start_date="1 May 2026",
            expiry_date="20 April 2026",
        )
        html = tpl["html"].format(
            candidate_name="Dana",
            position_title="Senior Developer",
            company_name="Acme Pte Ltd",
            salary="$8,000",
            start_date="1 May 2026",
            expiry_date="20 April 2026",
        )
        assert "Senior Developer" in subject
        assert "Acme Pte Ltd" in subject
        assert "Dana" in html
        assert "$8,000" in html
        assert "1 May 2026" in html
        assert "20 April 2026" in html

    # -- rejection_notice --

    def test_rejection_notice_renders(self):
        """rejection_notice template renders with all placeholders filled."""
        from hr_advisory.templates.recruitment_emails import RECRUITMENT_TEMPLATES

        tpl = RECRUITMENT_TEMPLATES["rejection_notice"]
        subject = tpl["subject"].format(
            candidate_name="Eve",
            job_title="Designer",
            company_name="Acme Pte Ltd",
        )
        html = tpl["html"].format(
            candidate_name="Eve",
            job_title="Designer",
            company_name="Acme Pte Ltd",
        )
        assert "Acme Pte Ltd" in subject
        assert "Eve" in html
        assert "Acme Pte Ltd" in html

    def test_rejection_notice_tone_is_professional(self):
        """rejection_notice should be professional and kind, not harsh."""
        from hr_advisory.templates.recruitment_emails import RECRUITMENT_TEMPLATES

        html = RECRUITMENT_TEMPLATES["rejection_notice"]["html"].format(
            candidate_name="Eve",
            job_title="Designer",
            company_name="Acme Pte Ltd",
        )
        html_lower = html.lower()
        # Should NOT contain harsh language
        assert "unfortunately" not in html_lower or "regret" not in html_lower  # at least one soft approach
        # Should contain positive/professional phrases
        assert "thank" in html_lower
        assert "wish" in html_lower or "best" in html_lower

    # -- feedback_reminder --

    def test_feedback_reminder_renders(self):
        """feedback_reminder template renders with all placeholders filled."""
        from hr_advisory.templates.recruitment_emails import RECRUITMENT_TEMPLATES

        tpl = RECRUITMENT_TEMPLATES["feedback_reminder"]
        subject = tpl["subject"].format(
            candidate_name="Frank",
            job_title="Backend Engineer",
            interview_date="10 April 2026",
        )
        html = tpl["html"].format(
            candidate_name="Frank",
            job_title="Backend Engineer",
            interview_date="10 April 2026",
        )
        assert "Frank" in subject
        assert "Frank" in html
        assert "Backend Engineer" in html
        assert "10 April 2026" in html

    def test_feedback_reminder_is_internal_tone(self):
        """feedback_reminder is for internal use — mentions feedback submission."""
        from hr_advisory.templates.recruitment_emails import RECRUITMENT_TEMPLATES

        html = RECRUITMENT_TEMPLATES["feedback_reminder"]["html"].format(
            candidate_name="Frank",
            job_title="Backend Engineer",
            interview_date="10 April 2026",
        )
        html_lower = html.lower()
        assert "feedback" in html_lower


# ---------------------------------------------------------------------------
# T-R018: _send_recruitment_email helper tests
# ---------------------------------------------------------------------------


class TestSendRecruitmentEmail:
    """Verify _send_recruitment_email helper handles all edge cases."""

    def test_returns_false_when_no_api_key(self):
        """When RESEND_API_KEY is empty, email should be silently skipped."""
        from hr_advisory.api.routers.recruitment import _send_recruitment_email

        with patch.dict("os.environ", {"RESEND_API_KEY": ""}, clear=False):
            result = asyncio.get_event_loop().run_until_complete(
                _send_recruitment_email(
                    to="alice@example.com",
                    template_name="application_received",
                    variables={
                        "candidate_name": "Alice",
                        "job_title": "Engineer",
                        "company_name": "Acme",
                    },
                )
            )
        assert result is False

    def test_returns_false_when_api_key_not_set(self):
        """When RESEND_API_KEY is not in env at all, email should be silently skipped."""
        from hr_advisory.api.routers.recruitment import _send_recruitment_email

        env = {k: v for k, v in __import__("os").environ.items() if k != "RESEND_API_KEY"}
        with patch.dict("os.environ", env, clear=True):
            result = asyncio.get_event_loop().run_until_complete(
                _send_recruitment_email(
                    to="alice@example.com",
                    template_name="application_received",
                    variables={
                        "candidate_name": "Alice",
                        "job_title": "Engineer",
                        "company_name": "Acme",
                    },
                )
            )
        assert result is False

    def test_returns_false_for_unknown_template(self):
        """When template name is not recognized, should return False with a warning."""
        from hr_advisory.api.routers.recruitment import _send_recruitment_email

        with patch.dict("os.environ", {"RESEND_API_KEY": "re_test_key"}, clear=False):
            result = asyncio.get_event_loop().run_until_complete(
                _send_recruitment_email(
                    to="alice@example.com",
                    template_name="nonexistent_template",
                    variables={"candidate_name": "Alice"},
                )
            )
        assert result is False

    def test_returns_false_on_adapter_exception(self):
        """When adapter.send_email raises, should catch and return False."""
        from hr_advisory.api.routers.recruitment import _send_recruitment_email

        with (
            patch.dict("os.environ", {"RESEND_API_KEY": "re_test_key"}, clear=False),
            patch(
                "hr_advisory.api.routers.recruitment.ResendAdapter"
            ) as MockAdapter,
        ):
            mock_instance = AsyncMock()
            mock_instance.send_email.side_effect = RuntimeError("Network error")
            MockAdapter.return_value = mock_instance

            result = asyncio.get_event_loop().run_until_complete(
                _send_recruitment_email(
                    to="alice@example.com",
                    template_name="application_received",
                    variables={
                        "candidate_name": "Alice",
                        "job_title": "Engineer",
                        "company_name": "Acme",
                    },
                )
            )
        assert result is False

    def test_returns_true_on_success(self):
        """When adapter.send_email succeeds, should return True."""
        from hr_advisory.api.routers.recruitment import _send_recruitment_email

        with (
            patch.dict("os.environ", {"RESEND_API_KEY": "re_test_key"}, clear=False),
            patch(
                "hr_advisory.api.routers.recruitment.ResendAdapter"
            ) as MockAdapter,
        ):
            mock_instance = AsyncMock()
            mock_instance.send_email.return_value = {"id": "msg_123", "status": "sent"}
            MockAdapter.return_value = mock_instance

            result = asyncio.get_event_loop().run_until_complete(
                _send_recruitment_email(
                    to="alice@example.com",
                    template_name="application_received",
                    variables={
                        "candidate_name": "Alice",
                        "job_title": "Engineer",
                        "company_name": "Acme",
                    },
                )
            )
        assert result is True

    def test_sends_correct_subject_and_html(self):
        """Verify the adapter receives rendered subject and HTML from the template."""
        from hr_advisory.api.routers.recruitment import _send_recruitment_email

        with (
            patch.dict("os.environ", {"RESEND_API_KEY": "re_test_key"}, clear=False),
            patch(
                "hr_advisory.api.routers.recruitment.ResendAdapter"
            ) as MockAdapter,
        ):
            mock_instance = AsyncMock()
            mock_instance.send_email.return_value = {"id": "msg_456", "status": "sent"}
            MockAdapter.return_value = mock_instance

            asyncio.get_event_loop().run_until_complete(
                _send_recruitment_email(
                    to="bob@example.com",
                    template_name="application_received",
                    variables={
                        "candidate_name": "Bob Lee",
                        "job_title": "Data Analyst",
                        "company_name": "Test Corp",
                    },
                )
            )

            mock_instance.send_email.assert_called_once()
            call_kwargs = mock_instance.send_email.call_args
            # Check subject contains the job title and company
            subject = call_kwargs.kwargs.get("subject") or call_kwargs[1].get("subject", "")
            if not subject:
                # positional args: to, subject, html_body
                subject = call_kwargs[0][1] if len(call_kwargs[0]) > 1 else ""
            assert "Data Analyst" in subject
            assert "Test Corp" in subject

    def test_never_raises(self):
        """_send_recruitment_email must NEVER raise, even on unexpected errors."""
        from hr_advisory.api.routers.recruitment import _send_recruitment_email

        # Even with a completely broken import path, it should catch and return False
        with (
            patch.dict("os.environ", {"RESEND_API_KEY": "re_test_key"}, clear=False),
            patch(
                "hr_advisory.api.routers.recruitment.RECRUITMENT_TEMPLATES",
                side_effect=AttributeError("broken"),
            ),
        ):
            # This should NOT raise, it should return False
            result = asyncio.get_event_loop().run_until_complete(
                _send_recruitment_email(
                    to="alice@example.com",
                    template_name="application_received",
                    variables={"candidate_name": "Alice"},
                )
            )
            assert result is False


# ---------------------------------------------------------------------------
# T-R018: Endpoint integration — add_candidate sends email
# ---------------------------------------------------------------------------


class TestAddCandidateSendsEmail:
    """Verify add_candidate endpoint triggers application_received email."""

    def _make_app_with_auth(self):
        """Build FastAPI app with auth dependency overridden (established codebase pattern)."""
        from fastapi import FastAPI
        from hr_advisory.api.routers.recruitment import router
        from hr_advisory.api.middleware.auth_middleware import get_current_user

        app = FastAPI()
        app.include_router(router, prefix="/recruitment")
        app.dependency_overrides[get_current_user] = lambda: {
            "sub": 10,
            "email": "hr@example.com",
            "role": "owner",
            "company_id": 1,
        }
        return app

    @patch("hr_advisory.api.routers.recruitment._send_recruitment_email", new_callable=AsyncMock)
    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    @patch("hr_advisory.api.routers.recruitment.get_current_company_id", return_value=1)
    def test_add_candidate_sends_application_received_email(
        self, mock_company_id, mock_crud, mock_send_email
    ):
        """When a candidate is added with an email, application_received email is sent."""
        from fastapi.testclient import TestClient

        mock_crud.list_records.return_value = []  # No duplicate
        mock_crud.create.return_value = {
            "id": 42,
            "name": "Alice Tan",
            "email": "alice@example.com",
            "stage": "applied",
        }
        mock_crud.read.side_effect = lambda model, id: {
            "JobListing": {
                "id": 1,
                "company_id": 1,
                "title": "Software Engineer",
            },
            "Company": {
                "id": 1,
                "name": "Acme Pte Ltd",
            },
        }.get(model, {})

        mock_send_email.return_value = True

        app = self._make_app_with_auth()
        client = TestClient(app)
        resp = client.post(
            "/recruitment/jobs/1/candidates",
            json={"name": "Alice Tan", "email": "alice@example.com"},
        )
        assert resp.status_code == 200

        mock_send_email.assert_called_once()
        call_kwargs = mock_send_email.call_args
        assert call_kwargs.kwargs["to"] == "alice@example.com"
        assert call_kwargs.kwargs["template_name"] == "application_received"
        assert "Alice Tan" in call_kwargs.kwargs["variables"]["candidate_name"]
        assert "Software Engineer" in call_kwargs.kwargs["variables"]["job_title"]

    @patch("hr_advisory.api.routers.recruitment._send_recruitment_email", new_callable=AsyncMock)
    @patch("hr_advisory.api.routers.recruitment.dataflow_crud")
    @patch("hr_advisory.api.routers.recruitment.get_current_company_id", return_value=1)
    def test_add_candidate_email_failure_does_not_block_creation(
        self, mock_company_id, mock_crud, mock_send_email
    ):
        """Even if email sending fails, the candidate is still created successfully."""
        from fastapi.testclient import TestClient

        mock_crud.list_records.return_value = []
        mock_crud.create.return_value = {
            "id": 43,
            "name": "Bob",
            "email": "bob@example.com",
            "stage": "applied",
        }
        mock_crud.read.side_effect = lambda model, id: {
            "JobListing": {
                "id": 1,
                "company_id": 1,
                "title": "Designer",
            },
            "Company": {
                "id": 1,
                "name": "Test Corp",
            },
        }.get(model, {})

        mock_send_email.return_value = False  # Email fails

        app = self._make_app_with_auth()
        client = TestClient(app)
        resp = client.post(
            "/recruitment/jobs/1/candidates",
            json={"name": "Bob", "email": "bob@example.com"},
        )
        assert resp.status_code == 200
        assert resp.json()["candidate"]["id"] == 43
