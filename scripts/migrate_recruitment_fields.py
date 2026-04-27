"""Migration: Align recruitment model fields with router (T-R068).

Renames columns and drops deprecated fields to match the actual
field names used by the recruitment router and frontend.

Changes:
  - JobListing: position_title -> title, add status column, backfill from is_published
  - InterviewSchedule: location_or_link -> location, interviewer_ids -> interviewers
  - Candidate: drop nric_fin, date_of_birth, race, gender (PDPC pre-hire)
  - Company: add slug column, backfill from name (for public careers page)

Idempotent: safe to run multiple times.
"""

import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _get_database_url() -> str:
    """Read DATABASE_URL from .env or environment."""
    # Load .env if available
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
    """Check if a column exists in a PostgreSQL table."""
    cursor.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = %s AND column_name = %s",
        (table, column),
    )
    return cursor.fetchone() is not None


def run_migration():
    """Execute the recruitment field alignment migration."""
    try:
        import psycopg2
    except ImportError:
        logger.error(
            "psycopg2 is required for this migration. "
            "Install with: pip install psycopg2-binary"
        )
        sys.exit(1)

    database_url = _get_database_url()
    logger.info("Connecting to database...")

    conn = psycopg2.connect(database_url)
    conn.autocommit = False
    cursor = conn.cursor()

    try:
        # ------------------------------------------------------------------
        # JobListing: rename position_title -> title
        # ------------------------------------------------------------------
        if _column_exists(cursor, "job_listings", "position_title"):
            if _column_exists(cursor, "job_listings", "title"):
                logger.info("job_listings.title already exists, dropping position_title")
                cursor.execute("ALTER TABLE job_listings DROP COLUMN position_title")
            else:
                logger.info("Renaming job_listings.position_title -> title")
                cursor.execute(
                    "ALTER TABLE job_listings RENAME COLUMN position_title TO title"
                )
        else:
            logger.info("job_listings.position_title already renamed or absent -- skipping")

        # JobListing: add status column and backfill from is_published
        if not _column_exists(cursor, "job_listings", "status"):
            logger.info("Adding job_listings.status column")
            cursor.execute(
                "ALTER TABLE job_listings ADD COLUMN status VARCHAR(20) DEFAULT 'draft'"
            )
            # Backfill from is_published if that column still exists
            if _column_exists(cursor, "job_listings", "is_published"):
                logger.info("Backfilling status from is_published")
                cursor.execute(
                    "UPDATE job_listings SET status = CASE "
                    "WHEN is_published = true THEN 'open' ELSE 'draft' END"
                )
        else:
            logger.info("job_listings.status already exists -- skipping")

        # Drop is_published now that status is in place
        if _column_exists(cursor, "job_listings", "is_published"):
            logger.info("Dropping job_listings.is_published (replaced by status)")
            cursor.execute("ALTER TABLE job_listings DROP COLUMN is_published")

        # ------------------------------------------------------------------
        # InterviewSchedule: rename columns
        # ------------------------------------------------------------------
        if _column_exists(cursor, "interview_schedules", "location_or_link"):
            if _column_exists(cursor, "interview_schedules", "location"):
                logger.info(
                    "interview_schedules.location already exists, "
                    "dropping location_or_link"
                )
                cursor.execute(
                    "ALTER TABLE interview_schedules DROP COLUMN location_or_link"
                )
            else:
                logger.info("Renaming interview_schedules.location_or_link -> location")
                cursor.execute(
                    "ALTER TABLE interview_schedules "
                    "RENAME COLUMN location_or_link TO location"
                )
        else:
            logger.info(
                "interview_schedules.location_or_link already renamed or absent -- skipping"
            )

        if _column_exists(cursor, "interview_schedules", "interviewer_ids"):
            if _column_exists(cursor, "interview_schedules", "interviewers"):
                logger.info(
                    "interview_schedules.interviewers already exists, "
                    "dropping interviewer_ids"
                )
                cursor.execute(
                    "ALTER TABLE interview_schedules DROP COLUMN interviewer_ids"
                )
            else:
                logger.info(
                    "Renaming interview_schedules.interviewer_ids -> interviewers"
                )
                cursor.execute(
                    "ALTER TABLE interview_schedules "
                    "RENAME COLUMN interviewer_ids TO interviewers"
                )
        else:
            logger.info(
                "interview_schedules.interviewer_ids already renamed or absent -- skipping"
            )

        # ------------------------------------------------------------------
        # Company: add slug column for public careers page
        # ------------------------------------------------------------------
        if not _column_exists(cursor, "companies", "slug"):
            logger.info("Adding companies.slug column")
            cursor.execute(
                "ALTER TABLE companies ADD COLUMN slug VARCHAR(255) DEFAULT ''"
            )
            # Backfill slug from company name
            logger.info("Backfilling slugs from company names")
            cursor.execute(
                "UPDATE companies SET slug = LOWER(REGEXP_REPLACE("
                "TRIM(name), '[^a-zA-Z0-9]+', '-', 'g'))"
            )
            # Trim leading/trailing dashes
            cursor.execute(
                "UPDATE companies SET slug = TRIM(BOTH '-' FROM slug)"
            )
        else:
            logger.info("companies.slug already exists -- skipping")

        # ------------------------------------------------------------------
        # Candidate: drop NRIC and demographic fields (PDPC pre-hire)
        # ------------------------------------------------------------------
        for col in ("nric_fin", "date_of_birth", "race", "gender"):
            if _column_exists(cursor, "candidates", col):
                logger.info(f"Dropping candidates.{col}")
                cursor.execute(f"ALTER TABLE candidates DROP COLUMN {col}")
            else:
                logger.info(f"candidates.{col} already absent -- skipping")

        # ------------------------------------------------------------------
        # T-RX08: composite index on (job_listing_id, email) for fast
        # duplicate-application lookups.
        # ------------------------------------------------------------------
        logger.info("Ensuring composite index idx_candidate_job_email exists")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_candidate_job_email "
            "ON candidates (job_listing_id, email)"
        )

        # ------------------------------------------------------------------
        # T-R030: PDPA pre-purge warning column on candidates.
        # ------------------------------------------------------------------
        if not _column_exists(cursor, "candidates", "pdpa_purge_warned_at"):
            logger.info("Adding candidates.pdpa_purge_warned_at column")
            cursor.execute(
                "ALTER TABLE candidates "
                "ADD COLUMN pdpa_purge_warned_at TIMESTAMP NULL"
            )
        else:
            logger.info(
                "candidates.pdpa_purge_warned_at already exists -- skipping"
            )

        conn.commit()
        logger.info("Migration completed successfully.")

    except Exception:
        conn.rollback()
        logger.exception("Migration failed -- rolled back.")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    run_migration()
