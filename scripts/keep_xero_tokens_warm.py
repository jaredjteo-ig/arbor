"""Refresh Xero OAuth tokens that are within 7 days of idle expiry.

Xero refresh tokens become invalid after 60 days of disuse. Customers
who run payroll once a month can hit the cliff after two missed
months. This script — run daily via cron — proactively rotates tokens
that are nearing expiry so the customer never sees an
``invalid_grant`` mid-export.

Behaviour:
- Read all active ``IntegrationToken`` rows where ``provider='xero'``
  and ``expires_at`` is within ``WARM_WINDOW_SEC`` of now.
- For each, call ``XeroAdapter.refresh_if_expired`` which posts a
  refresh-grant to Xero and stores the new access+refresh pair.
- On ``invalid_grant``, the adapter will hard-disconnect the row and
  raise ``XeroReauthRequired``; we count and log but don't re-raise.
- Log a structured summary at the end.

Run via deploy cron:
    0 2 * * * cd /app && python scripts/keep_xero_tokens_warm.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("xero-keepalive")

# Refresh anything expiring within 7 days. Xero access tokens live 30
# minutes; the practical effect is "any token whose access expires
# within 7 days" which is functionally "every Xero connection, every
# day" — but the no-op cost is a single /connections call per token
# (cheap), so this is OK.
WARM_WINDOW_SEC = 7 * 24 * 3600


def _load_env() -> None:
    try:
        from dotenv import load_dotenv

        env_path = Path(__file__).parent.parent / ".env"
        load_dotenv(env_path)
    except ImportError:
        pass


async def run() -> None:
    _load_env()

    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from hr_advisory.mcp_servers.adapters.xero import (
        XeroReauthRequired,
        get_xero_adapter,
    )
    from hr_advisory.services import dataflow_crud

    adapter = get_xero_adapter()  # registers refresh callback
    _ = adapter

    rows = dataflow_crud.list_records(
        "IntegrationToken",
        {"provider": "xero", "disconnected_at": ""},
        cache_ttl=0,
    )

    now = time.time()
    candidates = [
        r
        for r in rows
        if float(r.get("expires_at") or 0) - now < WARM_WINDOW_SEC
    ]

    refreshed = 0
    invalidated = 0
    errors = 0

    from hr_advisory.mcp_servers.auth.token_store import get_token_manager

    manager = get_token_manager()

    for row in candidates:
        tenant_id = str(row.get("tenant_id", ""))
        if not tenant_id:
            continue
        try:
            token = await manager.refresh_if_expired(tenant_id, "xero")
            if token:
                refreshed += 1
                logger.info(
                    "Refreshed Xero token for tenant=%s", tenant_id
                )
            else:
                # No refresh needed (token still fresh) or no refresh
                # token recorded — both benign.
                pass
        except XeroReauthRequired:
            invalidated += 1
            logger.warning(
                "Xero token for tenant=%s invalidated — user must reconnect.",
                tenant_id,
            )
        except Exception:
            errors += 1
            logger.exception(
                "Unexpected error refreshing Xero token for tenant=%s",
                tenant_id,
            )

    logger.info(
        "xero-keepalive done: candidates=%d, refreshed=%d, invalidated=%d, errors=%d",
        len(candidates),
        refreshed,
        invalidated,
        errors,
    )


if __name__ == "__main__":
    asyncio.run(run())
