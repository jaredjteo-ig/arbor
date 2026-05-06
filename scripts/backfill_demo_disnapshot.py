"""Backfill: bring DiSnapshot completeness to 100% for the demo persona.

Round-2 redteam L finding: gender 96% complete, DOB 96% complete. The
single uncovered employee is the demo admin (Founder & CEO row created
implicitly during sign-up). Filling those two fields keeps the lifecycle
DiSnapshot tile reading 100% across the board for screenshot-quality
demos.

Idempotent: only writes rows where the field is currently empty.
"""

from __future__ import annotations

import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_COMPANY_ID = int(os.environ.get("ARBOR_DEMO_COMPANY_ID", "1"))


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
        logger.error("psycopg2 required.")
        sys.exit(1)

    conn = psycopg2.connect(_get_database_url())
    conn.autocommit = False
    company_id = DEFAULT_COMPANY_ID

    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE employees
                   SET gender = COALESCE(NULLIF(gender, ''), 'female'),
                       date_of_birth = COALESCE(
                         NULLIF(date_of_birth, ''),
                         '1985-06-15'
                       )
                 WHERE company_id = %s
                   AND is_active = true
                   AND (
                        (gender IS NULL OR gender = '')
                     OR (date_of_birth IS NULL OR date_of_birth = '')
                   )
                """,
                (company_id,),
            )
            logger.info(
                "Backfilled %d employee row(s) with default gender + DOB.",
                cur.rowcount,
            )
    finally:
        conn.close()


if __name__ == "__main__":
    run()
    logger.info("Done.")
