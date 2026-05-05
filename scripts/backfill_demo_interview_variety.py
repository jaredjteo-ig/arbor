"""Backfill: add Completed + Cancelled interview rows for demo variety.

Round-12 redteam M7: every visible interview was at "Scheduled" status,
which made the Recruitment ▸ Interviews tab read as flat history. The
funnel feels more real with at least one Completed (with notes) and one
Cancelled (with reason).

This script adds two lightweight candidates + their interviews. Skips
gracefully if it's already been run (presence check on email).

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


SEED_EMAILS = ("priya.s@example.com", "marcus.c@example.com")


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
                "SELECT email FROM candidates "
                "WHERE company_id = %s AND email = ANY(%s)",
                (company_id, list(SEED_EMAILS)),
            )
            if cur.fetchall():
                logger.info(
                    "Demo interview variety already seeded for company %s.",
                    company_id,
                )
                return

            cur.execute(
                "SELECT job_listing_id FROM candidates "
                "WHERE company_id = %s LIMIT 1",
                (company_id,),
            )
            row = cur.fetchone()
            if not row:
                logger.warning(
                    "Company %s has no candidates yet — skipping demo "
                    "interview seed.",
                    company_id,
                )
                return
            job_id = row[0]

            now = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)

            seeds = [
                (
                    "Priya Subramaniam",
                    "priya.s@example.com",
                    "interview",
                    "video",
                    (now - timedelta(days=5)).isoformat(sep="T"),
                    60,
                    "Google Meet",
                    "completed",
                    "Solid technical round, recommend next stage.",
                ),
                (
                    "Marcus Chen",
                    "marcus.c@example.com",
                    "rejected",
                    "in_person",
                    (now + timedelta(days=2)).isoformat(sep="T"),
                    45,
                    "60 Anson Rd",
                    "cancelled",
                    "Candidate withdrew before interview.",
                ),
            ]

            for (
                name,
                email,
                stage,
                interview_type,
                scheduled_at,
                duration,
                location,
                status,
                notes,
            ) in seeds:
                cur.execute(
                    "INSERT INTO candidates "
                    "(company_id, job_listing_id, name, email, stage, source, "
                    " pdpa_consent, pdpa_consent_date, created_at, updated_at) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                    (
                        company_id,
                        job_id,
                        name,
                        email,
                        stage,
                        "direct",
                        True,
                        "2026-03-01",
                        now,
                        now,
                    ),
                )
                (cid,) = cur.fetchone()

                cur.execute(
                    "INSERT INTO interview_schedules "
                    "(candidate_id, company_id, interview_type, scheduled_at, "
                    " duration_minutes, location, interviewers, status, notes, "
                    " created_at, updated_at) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (
                        cid,
                        company_id,
                        interview_type,
                        scheduled_at,
                        duration,
                        location,
                        "[]",
                        status,
                        notes,
                        now,
                        now,
                    ),
                )

            logger.info(
                "Seeded 2 candidates + 1 completed + 1 cancelled interview "
                "for company %s.",
                company_id,
            )
    finally:
        conn.close()


if __name__ == "__main__":
    run()
    logger.info("Done.")
