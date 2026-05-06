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
            already_seeded = cur.fetchone() is not None

            # Fix-up branch (R2-M finding): even if the row count is
            # already non-zero, an earlier seed may have written
            # manager_id=0 / period_id=0 (orphan reads). Repair those
            # in place before short-circuiting. Safe to run repeatedly.
            if already_seeded:
                cur.execute(
                    "SELECT id FROM appraisal_periods WHERE company_id = %s "
                    "AND name = 'H1 2026 Performance Review' LIMIT 1",
                    (company_id,),
                )
                period_row = cur.fetchone()
                period_id_fix = period_row[0] if period_row else 0
                if period_id_fix:
                    cur.execute(
                        "UPDATE goals SET period_id = %s "
                        "WHERE company_id = %s AND period_id = 0",
                        (period_id_fix, company_id),
                    )
                    logger.info(
                        "Fix-up: rewired %d goal(s) to period_id=%s.",
                        cur.rowcount,
                        period_id_fix,
                    )
                # Resolve manager_id: prefer reporting_manager_id; fall
                # back to the company's demo admin (Founder) so the
                # field is never 0 in the buyer-facing UI.
                cur.execute(
                    "SELECT e.id FROM employees e JOIN users u ON u.id = e.user_id "
                    "WHERE e.company_id = %s AND u.email = 'demo@central.kailash.ai' "
                    "ORDER BY e.id LIMIT 1",
                    (company_id,),
                )
                admin_row = cur.fetchone()
                admin_emp_id = admin_row[0] if admin_row else 0
                cur.execute(
                    "UPDATE goals g SET manager_id = "
                    "  COALESCE("
                    "    NULLIF((SELECT e.reporting_manager_id FROM employees e "
                    "            WHERE e.id = g.employee_id), 0),"
                    "    %s"
                    "  ) "
                    "WHERE g.company_id = %s "
                    "  AND (g.manager_id IS NULL OR g.manager_id = 0)"
                    "  AND g.employee_id != %s",
                    (admin_emp_id, company_id, admin_emp_id),
                )
                logger.info(
                    "Fix-up: rewired %d goal(s) to manager (reporting line "
                    "or demo admin fallback id=%s).",
                    cur.rowcount,
                    admin_emp_id,
                )
                logger.info(
                    "Goals already seeded for company %s — fix-up done.",
                    company_id,
                )
                return

            cur.execute(
                "SELECT id, user_id, reporting_manager_id FROM employees "
                "WHERE company_id = %s AND is_active = true ORDER BY id LIMIT 6",
                (company_id,),
            )
            employees = cur.fetchall()
            if len(employees) < 3:
                logger.warning("Need ≥3 active employees in company %s.", company_id)
                return

            # R2-M finding: goals had manager_id=0, period_id=0 — orphan
            # reads. Wire each goal to its employee's reporting manager
            # and to a real AppraisalPeriod row for FY2026 H1.
            cur.execute(
                "SELECT id FROM appraisal_periods WHERE company_id = %s "
                "AND name = 'H1 2026 Performance Review' LIMIT 1",
                (company_id,),
            )
            period_row = cur.fetchone()
            period_id = period_row[0] if period_row else 0

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
                emp_id, _user_id, manager_id = employees[emp_idx]
                manager_id = manager_id or 0  # may be NULL for top-of-org rows
                due = (today + timedelta(days=due_off)).isoformat()
                start = (today - timedelta(days=14)).isoformat()
                cur.execute(
                    "INSERT INTO goals "
                    "(company_id, employee_id, manager_id, period_id, title, "
                    " description, metric, target_value, start_date, due_date, "
                    " status, progress_pct, is_archived, created_at, updated_at) "
                    "VALUES (%s,%s,%s,%s,%s,'',%s,'',%s,%s,%s,%s,false,%s,%s) RETURNING id",
                    (
                        company_id,
                        emp_id,
                        manager_id,
                        period_id,
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
            logger.info(
                "Seeded %d goals (period_id=%s, manager_ids wired from "
                "employees.reporting_manager_id).",
                len(goal_ids),
                period_id,
            )

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
