"""Backfill: seed Phase 3 demo data — workforce plan, skills, succession.

P3 obayashi. Seeds enough data so the Strategy hub renders cleanly.
Idempotent.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone

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

    try:
        with conn, conn.cursor() as cur:
            for tbl in ("workforce_plans", "skills_inventory_entries", "succession_plans"):
                cur.execute(
                    "SELECT 1 FROM information_schema.tables WHERE table_name = %s",
                    (tbl,),
                )
                if not cur.fetchone():
                    logger.warning(
                        "%s table not present yet — bootstrap via the API first.",
                        tbl,
                    )
                    return

            # WorkforcePlan
            cur.execute(
                "SELECT 1 FROM workforce_plans WHERE company_id = %s LIMIT 1",
                (company_id,),
            )
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO workforce_plans "
                    "(company_id, period_start, period_end, name, status, "
                    " headcount_targets, skills_priorities, retention_focus, "
                    " narrative, created_by, approved_by, approved_at, "
                    " created_at, updated_at) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,0,0,%s,%s,%s)",
                    (
                        company_id,
                        "2026-01-01",
                        "2026-06-30",
                        "FY2026 H1 Workforce Plan",
                        "published",
                        json.dumps({"local": 20, "ep": 3, "sp": 3, "wp": 2}),
                        json.dumps(["Cloud architecture", "SG payroll", "Customer success"]),
                        json.dumps(["First-90-day mentorship", "Mid-cycle stay-interviews"]),
                        "Hold local share at >=70%. Two new hires in Engineering. "
                        "Stay-interview every employee passing 18 months tenure.",
                        now,
                        now,
                        now,
                    ),
                )
                logger.info("Seeded 1 workforce plan.")
            else:
                logger.info("Workforce plan already seeded — skipping.")

            # Skills inventory — sample a few employees
            cur.execute(
                "SELECT 1 FROM skills_inventory_entries WHERE company_id = %s LIMIT 1",
                (company_id,),
            )
            if not cur.fetchone():
                cur.execute(
                    "SELECT id FROM employees WHERE company_id = %s "
                    "AND is_active = true ORDER BY id LIMIT 5",
                    (company_id,),
                )
                emp_ids = [r[0] for r in cur.fetchall()]
                if len(emp_ids) >= 3:
                    seeds = [
                        (emp_ids[0], "TypeScript", 5, 8.0),
                        (emp_ids[0], "PostgreSQL", 4, 6.0),
                        (emp_ids[1], "Singapore Payroll", 5, 5.5),
                        (emp_ids[1], "CPF / IRAS Filing", 5, 5.0),
                        (emp_ids[2], "Customer Success", 4, 4.0),
                        (emp_ids[2], "Account Management", 4, 4.0),
                    ]
                    for emp_id, skill, prof, years in seeds:
                        cur.execute(
                            "INSERT INTO skills_inventory_entries "
                            "(company_id, employee_id, skill_name, proficiency, "
                            " years_experience, last_used_date, verified_by_user_id, "
                            " notes, is_archived, created_at, updated_at) "
                            "VALUES (%s,%s,%s,%s,%s,%s,0,'',false,%s,%s)",
                            (
                                company_id,
                                emp_id,
                                skill,
                                prof,
                                years,
                                "2026-04-01",
                                now,
                                now,
                            ),
                        )
                    logger.info("Seeded %d skill entries.", len(seeds))
            else:
                logger.info("Skills inventory already seeded — skipping.")

            # SuccessionPlan
            cur.execute(
                "SELECT 1 FROM succession_plans WHERE company_id = %s LIMIT 1",
                (company_id,),
            )
            if not cur.fetchone():
                cur.execute(
                    "SELECT id FROM employees WHERE company_id = %s "
                    "AND is_active = true ORDER BY id LIMIT 4",
                    (company_id,),
                )
                emp_ids = [r[0] for r in cur.fetchall()]
                if len(emp_ids) >= 2:
                    seeds = [
                        (
                            "Engineering Manager",
                            emp_ids[0],
                            "high",
                            json.dumps(
                                [
                                    {
                                        "employee_id": emp_ids[1],
                                        "readiness_months": 12,
                                        "gaps": ["People management"],
                                    }
                                ]
                            ),
                            "Critical for delivery; one identified successor 12 months out.",
                        ),
                        (
                            "Finance Lead",
                            emp_ids[1] if len(emp_ids) > 1 else emp_ids[0],
                            "medium",
                            json.dumps([]),
                            "No identified successor yet — flagged in workforce plan.",
                        ),
                    ]
                    for role, incumbent, crit, succs, notes in seeds:
                        cur.execute(
                            "INSERT INTO succession_plans "
                            "(company_id, role_title, incumbent_employee_id, "
                            " criticality, successors, notes, last_reviewed_at, "
                            " is_archived, created_at, updated_at) "
                            "VALUES (%s,%s,%s,%s,%s,%s,%s,false,%s,%s)",
                            (
                                company_id,
                                role,
                                incumbent,
                                crit,
                                succs,
                                notes,
                                now,
                                now,
                                now,
                            ),
                        )
                    logger.info("Seeded %d succession plans.", len(seeds))
            else:
                logger.info("Succession plans already seeded — skipping.")
    finally:
        conn.close()


if __name__ == "__main__":
    run()
    logger.info("Done.")
