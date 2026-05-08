"""Migration: add ``xero_force_counter`` column to ``payroll_runs``.

Powers stable Idempotency-Key headers on Xero POST ManualJournals.
Idempotent.
"""

from __future__ import annotations

import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


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


def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = %s AND column_name = %s",
        (table, column),
    )
    return cursor.fetchone() is not None


def run() -> None:
    try:
        import psycopg2
    except ImportError:
        logger.error("psycopg2 required.")
        sys.exit(1)

    conn = psycopg2.connect(_get_database_url())
    conn.autocommit = False
    try:
        with conn, conn.cursor() as cur:
            if _column_exists(cur, "payroll_runs", "xero_force_counter"):
                logger.info(
                    "payroll_runs.xero_force_counter exists — skipping"
                )
                return
            logger.info("Adding payroll_runs.xero_force_counter")
            cur.execute(
                "ALTER TABLE payroll_runs ADD COLUMN "
                "xero_force_counter INTEGER NOT NULL DEFAULT 0"
            )
    finally:
        conn.close()


if __name__ == "__main__":
    run()
    logger.info("Done.")
