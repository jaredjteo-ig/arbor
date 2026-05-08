"""Migration: Xero payroll-journal export columns + table.

Adds:
  - payroll_runs.xero_journal_id (TEXT NOT NULL DEFAULT '')
  - payroll_runs.xero_exported_at (TEXT NOT NULL DEFAULT '')
  - xero_account_mappings table — one row per company holding the six
    bucket → Xero account-code mappings used by the journal builder.

Idempotent: each ALTER and CREATE is guarded.
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


def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = %s AND column_name = %s",
        (table, column),
    )
    return cursor.fetchone() is not None


def _table_exists(cursor, table: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_name = %s",
        (table,),
    )
    return cursor.fetchone() is not None


_PAYROLL_RUN_COLUMNS = [
    ("xero_journal_id", "TEXT NOT NULL DEFAULT ''"),
    ("xero_exported_at", "TEXT NOT NULL DEFAULT ''"),
]


_XERO_MAPPING_DDL = """
CREATE TABLE xero_account_mappings (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL,
    salary_expense_code TEXT NOT NULL DEFAULT '',
    bonus_expense_code TEXT NOT NULL DEFAULT '',
    employer_cpf_expense_code TEXT NOT NULL DEFAULT '',
    sdl_expense_code TEXT NOT NULL DEFAULT '',
    cpf_payable_code TEXT NOT NULL DEFAULT '',
    net_pay_payable_code TEXT NOT NULL DEFAULT '',
    last_updated_by INTEGER NOT NULL DEFAULT 0,
    last_updated_at TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_xeromap_company ON xero_account_mappings(company_id);
"""


def run() -> None:
    try:
        import psycopg2
    except ImportError:
        logger.error("psycopg2 required. pip install psycopg2-binary")
        sys.exit(1)

    conn = psycopg2.connect(_get_database_url())
    conn.autocommit = False

    try:
        with conn, conn.cursor() as cur:
            # 1. Add columns to payroll_runs
            added_cols = 0
            for column, ddl in _PAYROLL_RUN_COLUMNS:
                if _column_exists(cur, "payroll_runs", column):
                    logger.info(
                        "payroll_runs.%s already exists — skipping", column
                    )
                    continue
                logger.info("Adding payroll_runs.%s (%s)", column, ddl)
                cur.execute(
                    f"ALTER TABLE payroll_runs ADD COLUMN {column} {ddl}"
                )
                added_cols += 1
            logger.info(
                "Added %d Xero column(s) to payroll_runs.", added_cols
            )

            # 2. Create xero_account_mappings table
            if _table_exists(cur, "xero_account_mappings"):
                logger.info(
                    "xero_account_mappings table already exists — skipping"
                )
            else:
                logger.info("Creating xero_account_mappings table")
                cur.execute(_XERO_MAPPING_DDL)
                logger.info("Created xero_account_mappings table.")
    finally:
        conn.close()


if __name__ == "__main__":
    run()
    logger.info("Done.")
