"""Backfill: default empty employee.pass_type to 'citizen'.

Round-12 redteam M1: an active employee with NULL/empty pass_type
surfaced as "Unknown 1" on the dashboard headcount tile — almost
always an admin/owner row that was created without immigration
metadata. Default missing values to 'citizen' (the SG-SME baseline).

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
            cur.execute(
                """
                UPDATE employees
                   SET pass_type = 'citizen',
                       nationality = COALESCE(NULLIF(nationality, ''), 'Singaporean')
                 WHERE is_active = true
                   AND (pass_type IS NULL OR pass_type = '')
                """
            )
            logger.info(
                "Defaulted %d active employee(s) with empty pass_type to citizen.",
                cur.rowcount,
            )
    finally:
        conn.close()


if __name__ == "__main__":
    run()
    logger.info("Done.")
