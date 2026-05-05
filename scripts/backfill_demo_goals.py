"""Backfill: seed demo Goals + check-ins.

Phase 2 P2-GO-5 (obayashi). 3 employees × 2 goals each, 4 check-ins
spread across the 6 goals so the timeline isn't flat.

Idempotent.
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
    today = now.date()

    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name = 'goals'"
            )
            if not cur.fetchone():
                logger.warning("goals table does not exist yet.")
                return

            cur.execute(
                "SELECT 1 FROM goals WHERE company_id = %s LIMIT 1",
                (company_id,),
            )
            if cur.fetchone():
                logger.info(
                    "Goals already seeded for company %s — skipping.",
                    company_id,
                )
                return

            cur.execute(
                "SELECT id, user_id FROM employees WHERE company_id = %s "
                "AND is_active = true ORDER BY id LIMIT 6",
                (company_id,),
            )
            employees = cur.fetchall()
            if len(employees) < 3:
                logger.warning("Need ≥3 active employees in company %s.", company_id)
                return

            seeds = [
                # employee_idx, title, metric, status, progress, due_offset_days
                (
                    0,
                    "Reduce time-to-hire by 30% this half",
                    "Avg days to offer ≤ 17 (from 24)",
                    "active",
                    45,
                    60,
                ),
                (
                    0,
                    "Roll out structured interview rubric",
                    "100% panels using rubric on the next 5 hires",
                    "active",
                    20,
                    45,
                ),
                (
                    1,
                    "Launch Q2 customer training programme",
                    "≥40 sessions, ≥85% CSAT",
                    "at_risk",
                    25,
                    30,
                ),
                (
                    1,
                    "Reduce open critical bugs to 0",
                    "0 bugs at sev=critical at month-end",
                    "done",
                    100,
                    -2,
                ),
                (
                    2,
                    "Pass WSH supervisor cert by EOM",
                    "Cert issued",
                    "active",
                    60,
                    14,
                ),
                (
                    2,
                    "Document on-call runbook",
                    "Runbook published in /docs",
                    "draft",
                    0,
                    21,
                ),
            ]
            goal_ids: list[int] = []
            for emp_idx, title, metric, status, progress, due_off in seeds:
                emp_id, _ = employees[emp_idx]
                due = (today + timedelta(days=due_off)).isoformat()
                start = (today - timedelta(days=14)).isoformat()
                cur.execute(
                    "INSERT INTO goals "
                    "(company_id, employee_id, manager_id, period_id, title, "
                    " description, metric, target_value, start_date, due_date, "
                    " status, progress_pct, is_archived, created_at, updated_at) "
                    "VALUES (%s,%s,0,0,%s,'',%s,'',%s,%s,%s,%s,false,%s,%s) RETURNING id",
                    (
                        company_id,
                        emp_id,
                        title,
                        metric,
                        start,
                        due,
                        status,
                        progress,
                        now,
                        now,
                    ),
                )
                (gid,) = cur.fetchone()
                goal_ids.append(gid)
            logger.info("Seeded %d goals.", len(goal_ids))

            # 4 check-ins spread across the goals.
            checkins = [
                (goal_ids[0], 25, "Backfilled the talent pool with 8 fresh contacts.", 7),
                (goal_ids[0], 45, "Two offers shipped this week.", 2),
                (goal_ids[2], 25, "First two pilot sessions wrapped — early CSAT 78%.", 10),
                (goal_ids[3], 100, "All sev=critical bugs closed and verified.", 1),
            ]
            for goal_id, pct, note, days_ago in checkins:
                created = now - timedelta(days=days_ago)
                cur.execute(
                    "INSERT INTO goal_check_ins "
                    "(goal_id, company_id, actor_user_id, progress_pct, note, created_at) "
                    "VALUES (%s,%s,0,%s,%s,%s)",
                    (goal_id, company_id, pct, note, created),
                )
            logger.info("Seeded %d check-ins.", len(checkins))
    finally:
        conn.close()


if __name__ == "__main__":
    run()
    logger.info("Done.")
