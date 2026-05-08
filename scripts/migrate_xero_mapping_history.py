"""Migration: ``xero_account_mapping_history`` table — append-only
log of mapping field changes per company (M3-T03)."""

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


def _table_exists(cursor, table: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = %s",
        (table,),
    )
    return cursor.fetchone() is not None


_DDL = """
CREATE TABLE xero_account_mapping_histories (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL,
    field_name TEXT NOT NULL DEFAULT '',
    previous_code TEXT NOT NULL DEFAULT '',
    new_code TEXT NOT NULL DEFAULT '',
    changed_by INTEGER NOT NULL DEFAULT 0,
    changed_at TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_xerohist_company
    ON xero_account_mapping_histories(company_id);
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
            if _table_exists(cur, "xero_account_mapping_histories"):
                logger.info(
                    "xero_account_mapping_histories already exists — skipping"
                )
                return
            logger.info("Creating xero_account_mapping_histories table")
            cur.execute(_DDL)
            logger.info("Created.")
    finally:
        conn.close()


if __name__ == "__main__":
    run()
    logger.info("Done.")
