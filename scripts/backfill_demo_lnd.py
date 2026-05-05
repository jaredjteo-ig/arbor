"""Backfill: seed demo L&D data — training records, certs, mandatory rules.

Phase 2 P2-LD-7 (obayashi). Idempotent — skips if any TrainingRecord
or Certification or MandatoryTrainingRequirement already exists for
the target company.

Seed contents:
  - 3 training records (mix of internal / external / SkillsFuture)
  - 2 certifications (one expiring in ~21 days for the alert demo,
    one safely active)
  - 1 mandatory requirement (WSH First-Aider for Operations dept)
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


def _table_exists(cursor, table: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = %s",
        (table,),
    )
    return cursor.fetchone() is not None


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
            # Sanity — Phase 2 tables only exist after the model is deployed.
            for tbl in (
                "training_records",
                "certifications",
                "mandatory_training_requirements",
            ):
                if not _table_exists(cur, tbl):
                    logger.warning(
                        "Table %s does not exist yet — deploy the P2-LD "
                        "models first.",
                        tbl,
                    )
                    return

            # Idempotency: if any rows already exist for this company on any
            # of the three tables, skip the seed entirely.
            for tbl in (
                "training_records",
                "certifications",
                "mandatory_training_requirements",
            ):
                cur.execute(
                    f"SELECT 1 FROM {tbl} WHERE company_id = %s LIMIT 1",
                    (company_id,),
                )
                if cur.fetchone():
                    logger.info(
                        "%s already populated for company %s — skipping.",
                        tbl,
                        company_id,
                    )
                    return

            cur.execute(
                "SELECT id FROM employees WHERE company_id = %s "
                "AND is_active = true ORDER BY id LIMIT 5",
                (company_id,),
            )
            employees = [r[0] for r in cur.fetchall()]
            if len(employees) < 3:
                logger.warning(
                    "Need ≥3 active employees in company %s to seed L&D demo.",
                    company_id,
                )
                return

            # Training records — three rows.
            records = [
                (
                    employees[0],
                    "Effective Workplace Communication",
                    "NTUC LearningHub",
                    "external",
                    (today - timedelta(days=14)).isoformat(),
                    (today - timedelta(days=7)).isoformat(),
                    8.0,
                    420.0,
                    "skillsfuture_credit",
                ),
                (
                    employees[1],
                    "WSH Site Safety Supervisor",
                    "Singapore Polytechnic",
                    "skillsfuture",
                    (today - timedelta(days=30)).isoformat(),
                    (today - timedelta(days=15)).isoformat(),
                    16.0,
                    1100.0,
                    "skillsfuture_credit",
                ),
                (
                    employees[2],
                    "Singapore Employment Act 101",
                    "Internal HR",
                    "internal",
                    (today - timedelta(days=3)).isoformat(),
                    "",
                    2.0,
                    0.0,
                    "employer",
                ),
            ]
            for (
                emp_id,
                name,
                provider,
                ctype,
                start,
                done,
                hours,
                cost,
                funding,
            ) in records:
                cur.execute(
                    "INSERT INTO training_records "
                    "(company_id, employee_id, course_name, course_provider, "
                    " course_type, start_date, completion_date, hours, cost, "
                    " funding_source, certificate_url, notes, is_archived, "
                    " created_at, updated_at) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'','',false,%s,%s)",
                    (
                        company_id,
                        emp_id,
                        name,
                        provider,
                        ctype,
                        start,
                        done,
                        hours,
                        cost,
                        funding,
                        now,
                        now,
                    ),
                )
            logger.info("Seeded 3 training records.")

            # Certifications — one expiring in 21d, one safely active.
            certs = [
                (
                    employees[0],
                    "First Aid Certificate",
                    "Singapore Red Cross",
                    (today - timedelta(days=345)).isoformat(),
                    (today + timedelta(days=21)).isoformat(),
                    "FA-2025-001234",
                ),
                (
                    employees[1],
                    "WSH Site Safety Supervisor Cert",
                    "Singapore Polytechnic",
                    (today - timedelta(days=15)).isoformat(),
                    (today + timedelta(days=720)).isoformat(),
                    "WSH-SSS-2026-000789",
                ),
            ]
            for emp_id, name, body, issued, expires, num in certs:
                cur.execute(
                    "INSERT INTO certifications "
                    "(company_id, employee_id, certification_name, issuing_body, "
                    " issued_date, expires_at, cert_number, attachment_url, notes, "
                    " is_archived, created_at, updated_at) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,'','',false,%s,%s)",
                    (
                        company_id,
                        emp_id,
                        name,
                        body,
                        issued,
                        expires,
                        num,
                        now,
                        now,
                    ),
                )
            logger.info("Seeded 2 certifications (one expiring soon).")

            # 1 mandatory requirement.
            cur.execute(
                "INSERT INTO mandatory_training_requirements "
                "(company_id, requirement_name, applicable_to, "
                " required_certification_name, due_within_days_of_hire, "
                " is_active, notes, created_at, updated_at) "
                "VALUES (%s,%s,%s,%s,%s,true,'',%s,%s)",
                (
                    company_id,
                    "WSH First-Aider per workplace",
                    "department:Operations",
                    "First Aid Certificate",
                    90,
                    now,
                    now,
                ),
            )
            logger.info("Seeded 1 mandatory training requirement.")
    finally:
        conn.close()


if __name__ == "__main__":
    run()
    logger.info("Done.")
