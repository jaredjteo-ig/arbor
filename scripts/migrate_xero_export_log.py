"""Migration: ``xero_export_logs`` table — append-only audit trail for
every Xero ManualJournal export attempt (success or failure).

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
        logger.error("DATABASE_URL is not set.")
        sys.exit(1)
    return url


def _table_exists(cursor, table: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = %s",
        (table,),
    )
    return cursor.fetchone() is not None


_DDL = """
CREATE TABLE xero_export_logs (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL,
    payroll_run_id INTEGER NOT NULL,
    journal_id TEXT NOT NULL DEFAULT '',
    posted_at TEXT NOT NULL DEFAULT '',
    actor_id INTEGER NOT NULL DEFAULT 0,
    line_count INTEGER NOT NULL DEFAULT 0,
    payload_hash TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT '',
    error_message TEXT NOT NULL DEFAULT '',
    bonus_total DOUBLE PRECISION NOT NULL DEFAULT 0,
    forced_reexport BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_xerolog_company_run
    ON xero_export_logs(company_id, payroll_run_id);
CREATE INDEX idx_xerolog_journal ON xero_export_logs(journal_id);
"""


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
            if _table_exists(cur, "xero_export_logs"):
                logger.info("xero_export_logs already exists — skipping")
                return
            logger.info("Creating xero_export_logs table")
            cur.execute(_DDL)
            logger.info("Created xero_export_logs table.")
    finally:
        conn.close()


if __name__ == "__main__":
    run()
    logger.info("Done.")
