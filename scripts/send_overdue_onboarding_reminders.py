#!/usr/bin/env python3
"""S4-T4 cron — daily overdue onboarding reminder dispatch.

Iterates EVERY company that has at least one OnboardingAssignment, then
calls the existing per-company reminder helper (which itself debounces
via OnboardingAssignment.last_reminder_sent_at — 24h window). Designed
to run inside the arbor-backend container at 09:00 SGT (01:00 UTC).

Usage (inside the backend container):
    python /app/scripts/send_overdue_onboarding_reminders.py

Recommended cron line:
    0 1 * * * /opt/arbor/cron/send_overdue_onboarding_reminders.sh

Exit code:
    0  -> ran cleanly (any combination of sent/skipped/errored counted)
    1  -> infrastructure failure (DB unreachable, RESEND_API_KEY missing)
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

# Path setup for `docker exec`
sys.path.insert(0, "/app/src")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("send_overdue_onboarding_reminders")


async def _main_async() -> int:
    if not os.environ.get("RESEND_API_KEY"):
        logger.error(
            "RESEND_API_KEY not set in arbor-backend env — emails would no-op. "
            "Set it in deploy/.env.prod and rebuild the container."
        )
        return 1

    from hr_advisory.api.routers.onboarding import _send_overdue_reminders_for_company  # noqa: E402
    from hr_advisory.services import dataflow_crud  # noqa: E402

    # Pull the distinct company_ids that have at least one assignment.
    try:
        rows = dataflow_crud.list_records("OnboardingAssignment", {})
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to list OnboardingAssignment rows: %s", exc, exc_info=True)
        return 1

    if not rows:
        logger.info("No OnboardingAssignment rows — nothing to remind.")
        return 0

    company_ids = sorted({int(r.get("company_id", 0)) for r in rows if r.get("company_id")})
    logger.info("Daily reminder cron: scanning %s companies", len(company_ids))

    totals = {
        "companies_processed": 0,
        "assignments_scanned": 0,
        "overdue_assignments": 0,
        "emails_sent": 0,
        "skipped": 0,
        "errors": 0,
    }

    for company_id in company_ids:
        try:
            summary = await _send_overdue_reminders_for_company(company_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Reminder dispatch raised for company_id=%s: %s",
                company_id,
                exc,
            )
            totals["errors"] += 1
            continue

        totals["companies_processed"] += 1
        for key in ("assignments_scanned", "overdue_assignments", "emails_sent", "skipped"):
            totals[key] += int(summary.get(key, 0) or 0)
        totals["errors"] += int(summary.get("errors", 0) or 0)

    logger.info(
        "Daily reminder cron complete: %s ts=%s",
        totals,
        datetime.now(timezone.utc).isoformat(),
    )
    return 0


def main() -> int:
    return asyncio.run(_main_async())


if __name__ == "__main__":
    sys.exit(main())
