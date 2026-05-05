"""Backfill: seed demo recognition + peer nominations.

Phase 2 P2-RC-5 (obayashi). 6 kudos across 4 employees, 1 private,
plus 2 peer nominations for the current month.

Idempotent: skips if either table already has rows for the company.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timedelta, timezone

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
    now = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
    period = now.strftime("%Y-%m")

    try:
        with conn, conn.cursor() as cur:
            # Sanity: Phase 2 tables exist.
            cur.execute(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'recognitions'"
            )
            if not cur.fetchone():
                logger.warning(
                    "recognitions table does not exist yet — deploy P2-RC first."
                )
                return

            cur.execute(
                "SELECT 1 FROM recognitions WHERE company_id = %s LIMIT 1",
                (company_id,),
            )
            if cur.fetchone():
                logger.info(
                    "Recognition already seeded for company %s — skipping.",
                    company_id,
                )
                return

            cur.execute(
                "SELECT id, user_id FROM employees WHERE company_id = %s "
                "AND is_active = true ORDER BY id LIMIT 8",
                (company_id,),
            )
            employees = cur.fetchall()
            if len(employees) < 4:
                logger.warning(
                    "Need ≥4 active employees in company %s.", company_id
                )
                return

            # Six recognitions, four recipients, mix of categories + 1 private.
            seeds = [
                (
                    employees[0][1],
                    employees[1][0],
                    "above_and_beyond",
                    "Stayed late to debug the prod payroll issue. Saved us a costly delay.",
                    True,
                    1,
                ),
                (
                    employees[1][1],
                    employees[2][0],
                    "teamwork",
                    "Pairs beautifully on the recruitment kanban — every candidate gets a touch within 2 days.",
                    True,
                    2,
                ),
                (
                    employees[2][1],
                    employees[3][0],
                    "customer",
                    "Turned a tough Ricoh demo question into a confident close.",
                    True,
                    3,
                ),
                (
                    employees[0][1],
                    employees[3][0],
                    "values",
                    "Quietly mentored two new hires through their probation. Living the values.",
                    True,
                    5,
                ),
                (
                    employees[3][1],
                    employees[0][0],
                    "innovation",
                    "Proposed the cache-bypass-on-recalc pattern that closed B3.",
                    True,
                    6,
                ),
                (
                    employees[1][1],
                    employees[3][0],
                    "values",
                    "Hand-written private note: thanks for picking up that compliance review last week.",
                    False,  # private
                    8,
                ),
            ]
            for from_user, to_emp, category, msg, public, days_ago in seeds:
                created = now - timedelta(days=days_ago)
                cur.execute(
                    "INSERT INTO recognitions "
                    "(company_id, from_user_id, to_employee_id, category, "
                    " message, is_public, is_archived, created_at, updated_at) "
                    "VALUES (%s,%s,%s,%s,%s,%s,false,%s,%s)",
                    (
                        company_id,
                        from_user,
                        to_emp,
                        category,
                        msg,
                        public,
                        created,
                        created,
                    ),
                )
            logger.info("Seeded 6 recognitions across 4 employees.")

            # Peer nominations.
            cur.execute(
                "INSERT INTO peer_nominations "
                "(company_id, nominator_user_id, nominee_employee_id, "
                " period, category, rationale, is_archived, created_at, updated_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,false,%s,%s)",
                (
                    company_id,
                    employees[0][1],
                    employees[3][0],
                    period,
                    "above_and_beyond",
                    "Consistently goes the extra mile.",
                    now,
                    now,
                ),
            )
            cur.execute(
                "INSERT INTO peer_nominations "
                "(company_id, nominator_user_id, nominee_employee_id, "
                " period, category, rationale, is_archived, created_at, updated_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,false,%s,%s)",
                (
                    company_id,
                    employees[2][1],
                    employees[1][0],
                    period,
                    "teamwork",
                    "Cross-team project coordination has been a force multiplier.",
                    now,
                    now,
                ),
            )
            logger.info("Seeded 2 peer nominations for period %s.", period)
    finally:
        conn.close()


if __name__ == "__main__":
    run()
    logger.info("Done.")
