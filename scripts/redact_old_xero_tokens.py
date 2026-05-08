"""Redact disconnected Xero OAuth tokens older than 90 days.

PDPA data-minimization: once an integration is disconnected and the
short dispute-resolution window has closed, the encrypted token
material has no further purpose. Replace it with empty strings so a
DB compromise cannot recover historical OAuth grants.

The metadata (xero_tenant_id, connected_by, connected_at,
disconnected_at) is kept for audit. Hard-deletion of the entire row
happens at the 7-year mark via a separate deferred job — too new for
any rows to be eligible today.

Run via deploy cron monthly:
    0 3 1 * * cd /app && python scripts/redact_old_xero_tokens.py
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timedelta, timezone

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("xero-redact")


def _get_database_url() -> str:
    try:
        from dotenv import load_dotenv

        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        load_dotenv(env_path)
    except ImportError:
        pass
    url = os.environ.get("DATABASE_URL")
    if not url:
        logger.error("DATABASE_URL not set.")
        sys.exit(1)
    return url


def run() -> None:
    try:
        import psycopg2
    except ImportError:
        logger.error("psycopg2 required.")
        sys.exit(1)

    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    cutoff_iso = cutoff.isoformat()

    conn = psycopg2.connect(_get_database_url())
    conn.autocommit = False
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE integration_tokens "
                "SET access_token_encrypted = '', "
                "    refresh_token_encrypted = '' "
                "WHERE provider = 'xero' "
                "  AND disconnected_at != '' "
                "  AND disconnected_at < %s "
                "  AND (access_token_encrypted != '' "
                "       OR refresh_token_encrypted != '')",
                (cutoff_iso,),
            )
            n = cur.rowcount
            logger.info(
                "Redacted token material on %d disconnected Xero token row(s) "
                "older than %s",
                n,
                cutoff_iso,
            )
    finally:
        conn.close()


if __name__ == "__main__":
    run()
    logger.info("Done.")
