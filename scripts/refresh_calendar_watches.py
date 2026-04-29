#!/usr/bin/env python3
"""S3-T2 cron — refresh Google Calendar webhook channels close to expiry.

Iterates EVERY GoogleCalendarConnection (across all tenants), re-watches
any whose channel_expiration is within 24 hours, and persists the new
channel_id / channel_token / channel_resource_id / channel_expiration.

Designed to run inside the arbor-backend container via:
    docker exec arbor-backend python /app/scripts/refresh_calendar_watches.py

Recommended schedule: every 6 hours. Idempotent — running more often
just produces "skipped" rows for connections that aren't yet near expiry.

Exit code:
    0  -> success (any combination of refreshed/skipped/failed counted)
    1  -> infrastructure failure (DB unreachable, ARBOR_API_URL invalid)
"""

from __future__ import annotations

import logging
import os
import secrets
import sys
from datetime import datetime, timezone

# Ensure src/ is on the path when run via docker exec
sys.path.insert(0, "/app/src")

from hr_advisory.api.routers.integrations_calendar import (  # noqa: E402
    _channel_expires_within,
    _validate_webhook_base_url,
)
from hr_advisory.integrations.google_calendar import sync  # noqa: E402
from hr_advisory.services import dataflow_crud  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("refresh_calendar_watches")


def main() -> int:
    raw_webhook_base = os.environ.get("ARBOR_API_URL", "")
    if not raw_webhook_base:
        logger.error("ARBOR_API_URL is not set — cannot register webhook URLs.")
        return 1

    try:
        webhook_base = _validate_webhook_base_url(raw_webhook_base)
    except ValueError as exc:
        logger.error("ARBOR_API_URL invalid: %s — aborting.", exc)
        return 1

    webhook_url = f"{webhook_base}/integrations/google-calendar/webhook"

    try:
        rows = dataflow_crud.list_records("GoogleCalendarConnection", {})
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to list GoogleCalendarConnection rows: %s", exc, exc_info=True)
        return 1

    refreshed = 0
    skipped = 0
    failed = 0

    for row in rows:
        company_id = row.get("company_id")
        connection_id = row.get("id")
        if not _channel_expires_within(row):
            skipped += 1
            continue

        new_channel_id = secrets.token_urlsafe(24)
        new_channel_token = secrets.token_urlsafe(32)
        try:
            watch_result = sync.watch_events(
                company_id=int(company_id),
                channel_id=new_channel_id,
                channel_token=new_channel_token,
                webhook_url=webhook_url,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "watch_events raised for connection_id=%s company_id=%s: %s",
                connection_id,
                company_id,
                exc,
            )
            failed += 1
            continue

        if not watch_result:
            failed += 1
            logger.warning(
                "watch_events returned None for connection_id=%s company_id=%s",
                connection_id,
                company_id,
            )
            continue

        try:
            dataflow_crud.update(
                "GoogleCalendarConnection",
                connection_id,
                {
                    "channel_id": new_channel_id,
                    "channel_token": new_channel_token,
                    "channel_resource_id": watch_result.get("resourceId", ""),
                    "channel_expiration": watch_result.get("expiration", ""),
                },
            )
            refreshed += 1
            logger.info(
                "Refreshed connection_id=%s company_id=%s new_expiration=%s",
                connection_id,
                company_id,
                watch_result.get("expiration", ""),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Persistence failed for connection_id=%s: %s",
                connection_id,
                exc,
            )
            failed += 1

    logger.info(
        "Calendar watch refresh complete: refreshed=%s skipped=%s failed=%s total=%s ts=%s",
        refreshed,
        skipped,
        failed,
        len(rows),
        datetime.now(timezone.utc).isoformat(),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
