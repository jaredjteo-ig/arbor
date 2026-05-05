"""Backfill: delete empty/abandoned payroll drafts.

Round-12 redteam M4: a $0.00 Jan 2026 Draft run was sitting in the
payroll dashboard alongside live runs. It was a stalled seed —
28 payslips all at zero. Empty drafts confuse the "next pay date"
heuristic and the audit trail.

This script deletes any draft run where every payslip has gross_pay = 0
(or there are no payslips). It does NOT touch approved/paid runs, even
if they have zero pay — those are intentional history.

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
                SELECT pr.id, pr.period_end,
                       COALESCE(SUM(ps.gross_pay), 0)::numeric(14,2) AS total_gross,
                       COUNT(ps.id) AS payslip_count
                  FROM payroll_runs pr
                  LEFT JOIN payslips ps ON ps.payroll_run_id = pr.id
                 WHERE pr.status = 'draft'
                 GROUP BY pr.id, pr.period_end
                HAVING COALESCE(SUM(ps.gross_pay), 0) = 0
                """
            )
            empty = cur.fetchall()
            if not empty:
                logger.info("No empty draft payroll runs found.")
                return

            for run_id, period_end, total, count in empty:
                logger.info(
                    "Deleting empty draft id=%s period_end=%s payslips=%s",
                    run_id,
                    period_end,
                    count,
                )

            ids = [r[0] for r in empty]
            cur.execute("DELETE FROM payslips WHERE payroll_run_id = ANY(%s)", (ids,))
            payslip_deletes = cur.rowcount
            cur.execute("DELETE FROM payroll_runs WHERE id = ANY(%s)", (ids,))
            run_deletes = cur.rowcount
            logger.info(
                "Deleted %d empty draft run(s) and %d associated payslip row(s).",
                run_deletes,
                payslip_deletes,
            )
    finally:
        conn.close()


if __name__ == "__main__":
    run()
    logger.info("Done.")
