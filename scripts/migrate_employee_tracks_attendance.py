"""Migration: add Employee.tracks_attendance and backfill from existing fields.

Round-12 redteam H1: the Attendance page showed every active employee
as "Absent" because there was no concept of "this employee actually
clocks in". Added a per-employee `tracks_attendance` flag (default
false). The today-dashboard endpoint now filters on it so salaried
desk staff don't pollute the daily roster.

Backfill heuristics on existing rows:
  - tracks_attendance = true if salary_type='hourly' OR
                                working_hours_type='shift' OR
                                designation ILIKE any of:
                                  warehouse, driver, technician,
                                  cleaner, security, kitchen, server,
                                  delivery, packer, operator, cashier
  - false otherwise.

These match the SG-SME demo data (Central / Ricoh Thailand) where
warehouse + delivery + kitchen staff clock in but desk staff don't.

Idempotent: safe to re-run. Reports counts.
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
        logger.error("DATABASE_URL is not set. Set it in .env or environment.")
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
        logger.error(
            "psycopg2 is required. Install with: pip install psycopg2-binary"
        )
        sys.exit(1)

    database_url = _get_database_url()
    conn = psycopg2.connect(database_url)
    conn.autocommit = False

    try:
        with conn, conn.cursor() as cur:
            if not _column_exists(cur, "employees", "tracks_attendance"):
                logger.info("Adding employees.tracks_attendance (default false)")
                cur.execute(
                    "ALTER TABLE employees "
                    "ADD COLUMN tracks_attendance BOOLEAN NOT NULL DEFAULT false"
                )
            else:
                logger.info("employees.tracks_attendance already exists")

            # Backfill: set true for clearly hourly / shift / operations roles.
            cur.execute(
                """
                UPDATE employees
                   SET tracks_attendance = true
                 WHERE tracks_attendance = false
                   AND (
                        salary_type = 'hourly'
                     OR working_hours_type = 'shift'
                     OR designation ILIKE ANY(ARRAY[
                          '%warehouse%', '%driver%', '%technician%',
                          '%cleaner%', '%security%', '%kitchen%',
                          '%server%', '%delivery%', '%packer%',
                          '%operator%', '%cashier%', '%barista%',
                          '%housekeep%', '%production%', '%assembly%'
                        ])
                   )
                """
            )
            tracked = cur.rowcount
            logger.info("Marked %d employees as tracks_attendance=true", tracked)

            cur.execute(
                "SELECT COUNT(*) FROM employees WHERE tracks_attendance = true"
            )
            (total_tracked,) = cur.fetchone()
            cur.execute(
                "SELECT COUNT(*) FROM employees WHERE is_active = true"
            )
            (total_active,) = cur.fetchone()
            logger.info(
                "Active total=%d  tracks_attendance=%d (rest are salaried desk)",
                total_active,
                total_tracked,
            )
    finally:
        conn.close()


if __name__ == "__main__":
    run()
    logger.info("Done.")
