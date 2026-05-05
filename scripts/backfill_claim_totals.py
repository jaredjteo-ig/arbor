"""Backfill: recompute claims.total_amount = SUM(claim_items.amount).

Round-12 redteam B3: prod claims show last-item amount instead of the
sum because the list cache returned stale rows during item-add. The
fix lives in claims.py (`_recalculate_claim_total` now passes
`cache_ttl=0`), but already-seeded prod rows still have the wrong
totals. This script recomputes them in one SQL statement.

Idempotent: safe to run multiple times. Reports how many rows changed.
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
        logger.error("DATABASE_URL is not set. Set it in .env or environment.")
        sys.exit(1)
    return url


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

    try:
        with conn, conn.cursor() as cur:
            # Snapshot mismatched rows BEFORE the update for reporting.
            cur.execute(
                """
                SELECT c.id, c.total_amount,
                       COALESCE(SUM(ci.amount), 0)::numeric(12,2) AS true_total
                  FROM claims c
                  LEFT JOIN claim_items ci ON ci.claim_id = c.id
                 GROUP BY c.id, c.total_amount
                HAVING c.total_amount IS DISTINCT FROM
                       COALESCE(SUM(ci.amount), 0)::numeric(12,2)
                """
            )
            mismatched = cur.fetchall()
            if not mismatched:
                logger.info("All claim totals already correct — nothing to do.")
                return

            logger.info("Found %d claims with stale totals:", len(mismatched))
            for cid, current, true_total in mismatched[:20]:
                logger.info("  claim %s: %s -> %s", cid, current, true_total)
            if len(mismatched) > 20:
                logger.info("  ... and %d more", len(mismatched) - 20)

            # Single atomic UPDATE — recompute every claim.
            cur.execute(
                """
                UPDATE claims c
                   SET total_amount = sub.true_total
                  FROM (
                       SELECT cl.id,
                              COALESCE(SUM(ci.amount), 0)::numeric(12,2)
                                AS true_total
                         FROM claims cl
                         LEFT JOIN claim_items ci ON ci.claim_id = cl.id
                        GROUP BY cl.id
                       ) sub
                 WHERE c.id = sub.id
                   AND c.total_amount IS DISTINCT FROM sub.true_total
                """
            )
            logger.info("Updated %d claim rows.", cur.rowcount)
    finally:
        conn.close()


if __name__ == "__main__":
    run()
    logger.info("Done.")
