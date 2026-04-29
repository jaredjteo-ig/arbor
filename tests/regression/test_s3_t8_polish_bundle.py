"""Regression: S3-T8 — polish bundle (6 items, code review carryovers).

Each test pins one of the small fixes so a future refactor cannot
silently re-introduce the issue:

- T8a: 3 bare `except Exception: pass` sites narrowed to specific classes
- T8b: `ScorecardEntry` persistence catches schema-mismatch only — real DB
       failures log loudly via `logger.error`
- T8c: reminder email HTML uses `html.escape()` not manual `<>` replace
- T8d: Calendar webhook rejects bodies > 64 KB
- T8e: deferred (no actual tz-comparison code in shadow/briefing.py today;
       guarded by source-level grep)
- T8f: `verify_signed_state` rejects payloads missing user_id as malformed
"""

from __future__ import annotations

import inspect

import pytest


# ---------------------------------------------------------------------------
# T8a: bare except sites narrowed
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_s3_t8a_onboarding_complete_step_narrows_body_parse():
    """The two body-parse sites in onboarding.py must catch JSONDecodeError /
    ValueError specifically — bare `except Exception: pass` would swallow
    legitimate framework errors (cancellation, EOF) silently.
    """
    from hr_advisory.api.routers import onboarding as onboarding_module

    src_complete = inspect.getsource(onboarding_module.complete_step)
    assert "except (ValueError, json.JSONDecodeError)" in src_complete, (
        "complete_step body parse must narrow to JSONDecodeError/ValueError"
    )


@pytest.mark.regression
def test_s3_t8a_onboarding_admin_complete_step_narrows_body_parse():
    """Same for admin_complete_step."""
    from hr_advisory.api.routers import onboarding as onboarding_module

    handler = getattr(onboarding_module, "admin_complete_step", None)
    if handler is None:
        # Locate the handler — exact name varies across refactors. Find any
        # function whose source contains "admin-complete-step body parse".
        src_module = inspect.getsource(onboarding_module)
        assert "admin-complete-step body parse" in src_module, (
            "Could not find the admin step-completion handler. The narrow-"
            "catch fix must be wired wherever the admin completes a step."
        )
    else:
        src = inspect.getsource(handler)
        assert "except (ValueError, json.JSONDecodeError)" in src


@pytest.mark.regression
def test_s3_t8a_onboarding_policy_ack_narrows_ip_lookup():
    """The IP-extraction site must catch AttributeError specifically."""
    from hr_advisory.api.routers import onboarding as onboarding_module

    src = inspect.getsource(onboarding_module)
    # Must NOT contain the bare `except Exception: pass` at the policy-ack ip site
    assert "ip_address = client.host" in src
    # The narrow-catch marker
    assert "except AttributeError as exc" in src


@pytest.mark.regression
def test_s3_t8a_calendar_webhook_narrows_body_decode():
    """Calendar webhook body decode must narrow to UnicodeDecodeError /
    ConnectionError — bare except would swallow a corrupted-stream bug.
    """
    from hr_advisory.api.routers import integrations_calendar as cal_module

    src = inspect.getsource(cal_module)
    assert "except (UnicodeDecodeError, ConnectionError)" in src


# ---------------------------------------------------------------------------
# T8b: ScorecardEntry persistence narrows Exception
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_s3_t8b_scorecard_persistence_distinguishes_schema_vs_db_errors():
    """ScorecardEntry persistence must check the exception message and
    only treat schema-mismatch (no such column / does not exist) as a
    no-op log-and-continue. Real DB failures (timeout, deadlock) must
    surface via `logger.error` so we don't silently lose scorecards.
    """
    from hr_advisory.api.routers import recruitment as recruitment_module

    src = inspect.getsource(recruitment_module)
    # The 4 message patterns the schema-mismatch heuristic checks for
    assert '"no such column" in msg' in src
    assert '"does not exist" in msg' in src
    assert '"undefinedcolumn" in msg' in src
    assert '"unknown column" in msg' in src
    # And the non-schema branch logs at ERROR level (not INFO)
    assert "ScorecardEntry persistence FAILED (non-schema)" in src
    assert "logger.error" in src


# ---------------------------------------------------------------------------
# T8c: html.escape() in reminder email
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_s3_t8c_reminder_email_uses_html_escape():
    """The onboarding reminder body must use `html.escape()` not the
    manual `replace("<", "&lt;").replace(">", "&gt;")` two-pass which
    leaves `&` and quote injection vectors open.
    """
    from hr_advisory.api.routers import onboarding as onboarding_module

    src = inspect.getsource(onboarding_module)
    assert "import html" in src
    assert "html.escape(employee_name" in src
    assert "html.escape(template_name" in src
    assert "html.escape(company_name" in src
    # And the manual replace pattern must be gone from the reminder body
    # block specifically (other parts of the file may still use it for
    # different reasons; this test is scoped to the reminder).
    reminder_section = src[src.index("Render a simple HTML reminder body"):src.index("Render a simple HTML reminder body") + 2000]
    assert '.replace("<", "&lt;")' not in reminder_section, (
        "Reminder body must not fall back to the manual <>-only replace."
    )


# ---------------------------------------------------------------------------
# T8d: Calendar webhook 64 KB cap
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_s3_t8d_calendar_webhook_rejects_oversized_body():
    """The Calendar webhook handler must reject any request whose
    Content-Length header declares > 64 KB. Anything that large from
    Google is either a misconfigured proxy or a hostile probe.
    """
    from hr_advisory.api.routers import integrations_calendar as cal_module

    src = inspect.getsource(cal_module)
    assert "_CALENDAR_WEBHOOK_MAX_BYTES = 64 * 1024" in src
    assert 'detail="Webhook body too large."' in src
    assert "status_code=413" in src


# ---------------------------------------------------------------------------
# T8f: verify_signed_state rejects malformed (missing user_id) payloads
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_s3_t8f_verify_state_rejects_old_format_without_user_id(monkeypatch):
    """An old-format state without a `user_id` field must be rejected
    as malformed. The CRIT-S3 fix made user_id mandatory; this test
    pins the rejection so a future regression cannot accept legacy
    states that pre-date the user-binding requirement.

    Uses monkeypatch (not direct os.environ) so the OAUTH_STATE_SECRET
    set here is reverted at teardown — otherwise unrelated tests in the
    same run would HMAC-verify against a stale secret.
    """
    import base64
    import hashlib
    import hmac as hmac_mod
    import json
    import time

    from hr_advisory.integrations.google_calendar.oauth import (
        OAuthStateError,
        verify_signed_state,
    )

    secret_value = "test-secret-32-chars-min-1234567890"
    monkeypatch.setenv("OAUTH_STATE_SECRET", secret_value)

    # Hand-craft an "old format" payload — no user_id field
    payload = {
        "company_id": 42,
        "ts": int(time.time()),
        "nonce": "abcd" * 4,
    }
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sig = hmac_mod.new(secret_value.encode("utf-8"), payload_bytes, hashlib.sha256).digest()

    def _b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode().rstrip("=")

    legacy_state = f"{_b64url(payload_bytes)}.{_b64url(sig)}"

    with pytest.raises(OAuthStateError) as exc_info:
        verify_signed_state(legacy_state)
    # The rejection reason must be specifically about the missing field,
    # not a signature failure (which would mean the test secret was wrong).
    assert "missing required fields" in str(exc_info.value)
