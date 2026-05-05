"""Migration: add employer-brand fields to companies table.

Phase 1 P1-7 (obayashi). Adds six TEXT NOT NULL DEFAULT '' columns:
  mission, tagline, benefits_summary, culture_pillars,
  team_photos_url, glassdoor_url.

These are read by the Lifecycle Dashboard's Attract stage and surfaced
on the public careers page. Empty defaults so the brand-new-company
state stays clean.

Idempotent: each ALTER guarded by a column-exists check.
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


def _column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = %s AND column_name = %s",
        (table, column),
    )
    return cursor.fetchone() is not None


_FIELDS = [
    "mission",
    "tagline",
    "benefits_summary",
    "culture_pillars",
    "team_photos_url",
    "glassdoor_url",
]


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
            added = 0
            for field in _FIELDS:
                if _column_exists(cur, "companies", field):
                    logger.info("companies.%s already exists — skipping", field)
                    continue
                logger.info(
                    "Adding companies.%s (TEXT NOT NULL DEFAULT '')", field
                )
                cur.execute(
                    f"ALTER TABLE companies ADD COLUMN {field} "
                    "TEXT NOT NULL DEFAULT ''"
                )
                added += 1
            logger.info(
                "Added %d employer-brand column(s) to companies.", added
            )
    finally:
        conn.close()


if __name__ == "__main__":
    run()
    logger.info("Done.")
