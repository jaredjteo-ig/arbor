"""Backfill: collapse duplicate active onboarding templates per company.

Round-12 redteam H4: prod had three active templates named
'HR Technology / SaaS Onboarding'. Names are now uniqueness-checked at
the API layer (see _ensure_unique_template_name in onboarding.py), but
the existing rows still need to be deduped so admins see one canonical
template per name.

Strategy (per company_id, casefolded+whitespace-normalized name):
  - Pick the surviving template:
      1. is_default=true if present
      2. Otherwise the oldest (lowest id) WITHOUT a "(Copy)" suffix
      3. Otherwise the oldest by id
  - Soft-archive every other duplicate by setting is_active=false. We do
    NOT delete: prior assignments may still reference the row, and the
    archive_template endpoint guards against breaking those.

Idempotent. Reports per-company counts.
"""

from __future__ import annotations

import logging
import os
import re
import sys
from collections import defaultdict

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
        logger.error("DATABASE_URL is not set. Set it in .env or environment.")
        sys.exit(1)
    return url


_WS = re.compile(r"\s+")


def _normalize(name: str) -> str:
    return _WS.sub(" ", (name or "").strip()).casefold()


def _is_copy(name: str) -> bool:
    return "(copy" in (name or "").casefold()


def run() -> None:
    try:
        import psycopg2
    except ImportError:
        logger.error(
            "psycopg2 is required. Install with: pip install psycopg2-binary"
        )
        sys.exit(1)

    database_url = _get_database_url()
    logger.info("Connecting to database...")
    conn = psycopg2.connect(database_url)
    conn.autocommit = False

    archived_total = 0
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, company_id, name, is_default
                  FROM onboarding_templates
                 WHERE is_active = true
                 ORDER BY company_id, id
                """
            )
            rows = cur.fetchall()

            buckets: dict[tuple[int, str], list[tuple]] = defaultdict(list)
            for row in rows:
                _id, company_id, name, _is_default = row
                buckets[(company_id, _normalize(name))].append(row)

            duplicates = {k: v for k, v in buckets.items() if len(v) > 1}
            if not duplicates:
                logger.info("No duplicate active templates found.")
                return

            for (company_id, norm_name), group in duplicates.items():
                # Pick the survivor.
                defaults = [g for g in group if g[3]]
                if defaults:
                    survivor = min(defaults, key=lambda g: g[0])
                else:
                    non_copies = [g for g in group if not _is_copy(g[2])]
                    pool = non_copies or group
                    survivor = min(pool, key=lambda g: g[0])

                archive_ids = [g[0] for g in group if g[0] != survivor[0]]
                logger.info(
                    "company=%s name=%r: keep id=%s, archive ids=%s",
                    company_id,
                    survivor[2],
                    survivor[0],
                    archive_ids,
                )
                cur.execute(
                    """
                    UPDATE onboarding_templates
                       SET is_active = false,
                           updated_at = NOW()
                     WHERE id = ANY(%s)
                    """,
                    (archive_ids,),
                )
                archived_total += cur.rowcount

            logger.info("Archived %d duplicate template(s).", archived_total)
    finally:
        conn.close()


if __name__ == "__main__":
    run()
    logger.info("Done.")
