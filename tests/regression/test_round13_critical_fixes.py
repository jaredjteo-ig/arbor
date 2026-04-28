"""Regression tests for the 3 round-13 CRITICAL fixes + the related HIGHs.

Each test pins one of the post-round-13 invariants so a refactor cannot
silently re-open the security holes.

Maps:

- CRIT-S1: Multi-channel handler (`platform.py`) advisory + compliance
  handlers must NOT accept `company_id` from the caller.
- CRIT-S2: `ARBOR_API_URL` must be validated against an https-allowlist
  (or http://localhost in dev) before being registered as a webhook URL
  with Google.
- CRIT-S3: OAuth state binds to ``(company_id, user_id)``; the callback
  verifier rejects state issued for a different user.
- H1: OAuth access/refresh tokens are encrypted at rest (Fernet).
- H2: OAuth state HMAC refuses to sign with the default placeholder
  ``"change-this-in-production"`` — fail-fast.
- H3: Webhook handler verifies ``X-Goog-Resource-ID`` against the stored
  ``channel_resource_id``.
"""

from __future__ import annotations

import inspect
import re

import pytest


# ----------------------------------------------------------------------------
# CRIT-S1
# ----------------------------------------------------------------------------


@pytest.mark.regression
def test_crit_s1_advisory_query_handler_drops_company_id():
    """The CLI/MCP advisory handler must not accept a tenant id from the
    caller. The HTTP route handles tenant isolation via Depends(get_current_user);
    these handlers are unauthenticated and would otherwise let any caller
    pull policies for any company."""
    from hr_advisory.api import platform as platform_module

    src = inspect.getsource(platform_module._register_handlers)
    # The signature line that USED to be `company_id: int = 0` is gone.
    assert "advisory_query_handler(query: str)" in src, (
        "advisory_query_handler must accept ONLY the query parameter. "
        "Adding company_id back without a trusted-channel auth mechanism "
        "would re-open the round-13 CRIT-S1 tenant leak."
    )
    assert "compliance_check_handler(domains: str = \"\")" in src, (
        "compliance_check_handler must accept ONLY the domains parameter. "
        "Adding company_id back would re-open round-13 CRIT-S1."
    )


# ----------------------------------------------------------------------------
# CRIT-S2
# ----------------------------------------------------------------------------


class TestCritS2WebhookUrlValidation:
    """``_validate_webhook_base_url`` is the gatekeeper for the URL we
    register with Google. Failing it must raise ValueError so the caller
    skips webhook registration entirely rather than register a poisoned URL."""

    def _fn(self):
        from hr_advisory.api.routers.integrations_calendar import (
            _validate_webhook_base_url,
        )

        return _validate_webhook_base_url

    def test_https_terrene_foundation_allowed(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "production")
        assert (
            self._fn()("https://api.terrene.foundation/")
            == "https://api.terrene.foundation"
        )

    def test_https_terrene_dev_allowed(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "production")
        assert self._fn()("https://app.terrene.dev") == "https://app.terrene.dev"

    def test_attacker_https_host_rejected(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "production")
        with pytest.raises(ValueError, match="not on the webhook allowlist"):
            self._fn()("https://evil.example.com/")

    def test_http_in_production_rejected(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "production")
        with pytest.raises(ValueError, match="https"):
            self._fn()("http://api.terrene.foundation/")

    def test_localhost_allowed_in_dev(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "development")
        assert self._fn()("http://localhost:8001") == "http://localhost:8001"

    def test_localhost_rejected_in_production(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "production")
        with pytest.raises(ValueError, match="localhost"):
            self._fn()("http://localhost:8001")

    def test_empty_url_rejected(self):
        with pytest.raises(ValueError, match="must be set"):
            self._fn()("")


# ----------------------------------------------------------------------------
# CRIT-S3 + H2: covered by `tests/unit/test_google_calendar_sync.py`'s
# `test_default_secret_rejected` and `test_exchange_code_rejects_user_mismatch`.
# This file just confirms the source still binds user_id, so a refactor can't
# drop the parameter without tripping a regression first.
# ----------------------------------------------------------------------------


@pytest.mark.regression
def test_crit_s3_state_signature_includes_user_id():
    """The signature of `build_signed_state` MUST include user_id."""
    from hr_advisory.integrations.google_calendar import oauth

    sig = inspect.signature(oauth.build_signed_state)
    params = list(sig.parameters.keys())
    assert "company_id" in params
    assert "user_id" in params, (
        "build_signed_state must bind state to user_id (round-13 CRIT-S3). "
        "Without this, an attacker who steals a state from one user can "
        "redeem it as another user."
    )


@pytest.mark.regression
def test_crit_s3_callback_requires_authentication():
    """The /callback handler must use Depends to require authentication."""
    from hr_advisory.api.routers import integrations_calendar

    src = inspect.getsource(integrations_calendar.google_calendar_callback)
    assert "Depends(require_role(" in src, (
        "google_calendar_callback must require authentication via Depends. "
        "Without this, an unauthenticated attacker can complete an OAuth "
        "flow they did not initiate (round-13 CRIT-S3)."
    )


# ----------------------------------------------------------------------------
# H1
# ----------------------------------------------------------------------------


@pytest.mark.regression
def test_h1_oauth_tokens_encrypted_at_rest(monkeypatch):
    """When SALARY_ENCRYPTION_KEY is set, ``_credentials_to_record`` must
    return a record where access_token / refresh_token are NOT the raw
    values — i.e. they are Fernet-encrypted ciphertext."""
    # Generate a fresh Fernet key for this test
    from cryptography.fernet import Fernet

    monkeypatch.setenv("OAUTH_STATE_SECRET", "regtest-state-secret-32chars-ABCDEF")
    monkeypatch.setenv("SALARY_ENCRYPTION_KEY", Fernet.generate_key().decode())

    # Bust the lru_cache that would otherwise hold the OLD (no-key) Fernet
    from hr_advisory.security.encryption import _get_fernet

    _get_fernet.cache_clear()

    from unittest.mock import MagicMock

    from hr_advisory.integrations.google_calendar import oauth

    fake_creds = MagicMock()
    fake_creds.token = "RAW-ACCESS-TOKEN-abc123"
    fake_creds.refresh_token = "RAW-REFRESH-TOKEN-def456"
    fake_creds.scopes = [oauth.GOOGLE_CALENDAR_SCOPE]
    fake_creds.token_uri = "https://oauth2.googleapis.com/token"
    fake_creds.expiry = None

    record = oauth._credentials_to_record(
        fake_creds, company_id=42, connected_by=7
    )

    assert record["access_token"] != "RAW-ACCESS-TOKEN-abc123", (
        "access_token in the persisted record must be encrypted ciphertext, "
        "not the raw bearer token (round-13 H1)."
    )
    assert record["refresh_token"] != "RAW-REFRESH-TOKEN-def456"
    # Round-trip via _record_to_credentials must recover the originals.
    creds = oauth._record_to_credentials(record)
    assert creds.token == "RAW-ACCESS-TOKEN-abc123"
    assert creds.refresh_token == "RAW-REFRESH-TOKEN-def456"


# ----------------------------------------------------------------------------
# H3
# ----------------------------------------------------------------------------


@pytest.mark.regression
def test_h3_webhook_verifies_resource_id():
    """Source-level pin: the webhook handler must compare X-Goog-Resource-ID
    against the stored channel_resource_id with constant-time compare."""
    from hr_advisory.api.routers import integrations_calendar

    src = inspect.getsource(integrations_calendar.google_calendar_webhook)
    assert re.search(r"channel_resource_id.*resource_id|resource_id.*channel_resource_id", src), (
        "Webhook handler must verify X-Goog-Resource-ID against the stored "
        "channel_resource_id (round-13 H3)."
    )
    assert "compare_digest" in src, (
        "Resource-id comparison must be constant-time."
    )
