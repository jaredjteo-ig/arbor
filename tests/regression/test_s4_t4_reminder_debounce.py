"""Regression: S4-T4 — daily reminder debounce.

The new daily cron will call `_send_overdue_reminders_for_company` for
every company every day. Without 24h debounce, every overdue employee
would receive the same digest email every day. This test pins:

  1. OnboardingAssignment has a `last_reminder_sent_at` field
  2. The reminder helper skips assignments whose stamp is < 24h old
  3. The reminder helper writes the stamp on successful send
"""

from __future__ import annotations

import inspect

import pytest


@pytest.mark.regression
def test_s4_t4_assignment_has_last_reminder_field():
    """Without the column, the cron has no debounce key.
    """
    from hr_advisory.models.company_user import OnboardingAssignment

    assert "last_reminder_sent_at" in OnboardingAssignment.__annotations__


@pytest.mark.regression
def test_s4_t4_reminder_helper_implements_debounce():
    """`_send_overdue_reminders_for_company` MUST check
    last_reminder_sent_at and skip if < 24h old.
    """
    from hr_advisory.api.routers import onboarding as onboarding_module

    src = inspect.getsource(onboarding_module._send_overdue_reminders_for_company)
    # Source-level guards
    assert "last_reminder_sent_at" in src, (
        "Reminder helper must read last_reminder_sent_at for debounce."
    )
    assert "timedelta(hours=24)" in src, (
        "Debounce window must be 24h. Without this constant the cron "
        "would re-email every employee every day."
    )
    # And on a successful send, it must stamp the field
    assert 'dataflow_crud.update(' in src
    assert '"OnboardingAssignment"' in src
    assert '"last_reminder_sent_at": now_dt' in src or '"last_reminder_sent_at"' in src


@pytest.mark.regression
def test_s4_t4_cron_script_exists_and_is_async():
    """The cron script must exist and be runnable by `python scripts/...`.
    """
    import os
    import pathlib

    repo_root = pathlib.Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "send_overdue_onboarding_reminders.py"

    assert script.exists(), "Daily reminder cron script must exist."
    assert os.access(script, os.X_OK), "Script must be executable."

    src = script.read_text()
    assert "async def _main_async" in src, "Cron must use an async main."
    assert "_send_overdue_reminders_for_company" in src
    assert "RESEND_API_KEY" in src, "Cron must guard on RESEND_API_KEY."


@pytest.mark.regression
def test_s4_t4_cron_skips_when_no_assignments():
    """No OnboardingAssignment rows → cron returns 0 cleanly without
    even attempting to load the email adapter. Keeps the daily job quiet
    on empty stacks.
    """
    import asyncio
    import os
    from unittest.mock import patch

    # Provide RESEND_API_KEY so the early guard passes; the empty rows
    # will short-circuit before any actual email send.
    with patch.dict(os.environ, {"RESEND_API_KEY": "test-key"}, clear=False):
        # Stub list_records to return empty
        import sys
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "send_overdue_onboarding_reminders",
            "/Users/jaredteo/Documents/GitHub/arbor/scripts/send_overdue_onboarding_reminders.py",
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules["send_overdue_onboarding_reminders"] = module
        spec.loader.exec_module(module)

        with patch("hr_advisory.services.dataflow_crud.list_records", return_value=[]):
            exit_code = asyncio.run(module._main_async())

    assert exit_code == 0
