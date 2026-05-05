"""Backfill: seed an active appraisal period with 3 in-flight reviews.

Round-12 redteam M5: the /appraisals page showed only the
"Annual Performance Review" template — no Periods, no in-flight
reviews. The whole stage looked dead.

This script creates one in-progress period plus three appraisal rows
(2 in draft, 1 submitted) so the page tells a complete demo story.
Idempotent — skips if a period already exists for the company.
"""

from __future__ import annotations

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
        logger.error("psycopg2 required. pip install psycopg2-binary")
        sys.exit(1)

    conn = psycopg2.connect(_get_database_url())
    conn.autocommit = False
    company_id = DEFAULT_COMPANY_ID

    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM appraisal_periods WHERE company_id = %s LIMIT 1",
                (company_id,),
            )
            if cur.fetchone():
                logger.info(
                    "Company %s already has an appraisal period — skipping.",
                    company_id,
                )
                return

            cur.execute(
                "SELECT id FROM appraisal_templates WHERE company_id = %s "
                "ORDER BY id LIMIT 1",
                (company_id,),
            )
            row = cur.fetchone()
            if not row:
                logger.warning(
                    "No appraisal template for company %s — cannot seed.",
                    company_id,
                )
                return
            template_id = row[0]

            cur.execute(
                "SELECT id FROM employees WHERE company_id = %s "
                "AND is_active = true "
                "AND designation NOT ILIKE '%%manager%%' "
                "AND designation NOT ILIKE '%%director%%' "
                "AND designation NOT ILIKE '%%founder%%' "
                "ORDER BY id LIMIT 3",
                (company_id,),
            )
            employees = [r[0] for r in cur.fetchall()]

            cur.execute(
                "SELECT id FROM employees WHERE company_id = %s "
                "AND is_active = true "
                "AND (designation ILIKE '%%manager%%' OR "
                "     designation ILIKE '%%director%%') "
                "ORDER BY id LIMIT 2",
                (company_id,),
            )
            managers = [r[0] for r in cur.fetchall()]

            if len(employees) < 3 or len(managers) < 1:
                logger.warning(
                    "Not enough employees/managers in company %s "
                    "(need 3+ ICs and 1+ manager).",
                    company_id,
                )
                return

            now = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
            cur.execute(
                "INSERT INTO appraisal_periods "
                "(company_id, template_id, name, start_date, end_date, "
                " status, created_at, updated_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (
                    company_id,
                    template_id,
                    "H1 2026 Performance Review",
                    "2026-01-01",
                    "2026-06-30",
                    "in_progress",
                    now,
                    now,
                ),
            )
            (period_id,) = cur.fetchone()
            logger.info(
                "Created period id=%s for company %s", period_id, company_id
            )

            mgr_a = managers[0]
            mgr_b = managers[-1]
            seeds = [
                (employees[0], mgr_a, "draft", "", "", None),
                (
                    employees[1],
                    mgr_a,
                    "submitted",
                    '{"q1": "Strong delivery on Q1 OKRs",'
                    ' "q2": "Initiative on cross-team work"}',
                    '{"delivery": 4, "collaboration": 5}',
                    4.5,
                ),
                (
                    employees[2],
                    mgr_b,
                    "draft",
                    '{"q1": "Reliable execution"}',
                    '{"delivery": 3}',
                    3.0,
                ),
            ]
            for emp_id, mgr_id, status, responses, scores, overall in seeds:
                cur.execute(
                    "INSERT INTO appraisals "
                    "(period_id, employee_id, reviewer_id, template_id, "
                    " company_id, status, responses, scores, overall_score, "
                    " reviewer_comments, employee_comments, submitted_at, "
                    " signed_off_at, created_at, updated_at) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (
                        period_id,
                        emp_id,
                        mgr_id,
                        template_id,
                        company_id,
                        status,
                        responses,
                        scores,
                        overall,
                        "",
                        "",
                        "",
                        "",
                        now,
                        now,
                    ),
                )
            logger.info("Seeded 3 in-flight appraisals.")
    finally:
        conn.close()


if __name__ == "__main__":
    run()
    logger.info("Done.")
