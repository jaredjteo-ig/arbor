"""Purge legacy guardrail-fallback advisory turns from prod.

Red-team P5-AD-1 origin: workspaces/obayashi/04-validate/
13-redteam-comprehensive-2026-05-19.md finding O3 / C9. The live walk
turned up 2 conversations in the History sidebar with
"(earlier reply unavailable)" placeholder text. They are real
persisted conversations whose assistant turn was a degraded-state
phrase (e.g. "I'm having trouble processing your question right
now…"). The frontend rewrites that into the placeholder via
`cleanPreview` — but the underlying rows still exist, and a buyer
reads them as "things this platform lost".

Round-3 already fixed the engine's pre-classifier so new turns
shouldn't degrade into that text. Round P5-AD-1 also adds a
persistence-boundary filter (`short_term._is_legacy_fallback_reply`)
so the row never gets written in the first place. This script
cleans up legacy rows that landed before either fix shipped.

Idempotent. Safe to re-run after deploys.

Acceptance:
  - `SELECT COUNT(*) FROM conversation_messages WHERE sender='agent'
     AND text LIKE 'I''m having trouble%'` returns 0 after run.
  - Orphan threads (no agent reply) are deleted along with their
    user-side messages.
  - Owner / HR / IC see ZERO "(earlier reply unavailable)" entries
    in /advisory History sidebar after deploy.

Usage:
  ADMIN_PASSWORD=... DATABASE_URL=... \\
    python scripts/maintenance/purge_legacy_advisory.py [--dry-run]

The script refuses to run against non-localhost URLs when the
default ADMIN_PASSWORD env var is unset (mirrors the safety guard
in `scripts/seed_demo_data.py`).
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# Legacy-fallback phrases anchored at the start of the agent text.
# Must stay in sync with `short_term._LEGACY_FALLBACK_PATTERNS` so the
# database purge and the persistence-boundary filter agree on what
# counts as "degraded".
_LEGACY_LIKE_PATTERNS: tuple[str, ...] = (
    "I'm having trouble processing your question%",
    "I was unable to fully process your query%",
)


def _get_database_url() -> str:
    try:
        from dotenv import load_dotenv

        env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
        load_dotenv(env_path)
    except ImportError:
        pass

    url = os.environ.get("DATABASE_URL")
    if not url:
        logger.error("DATABASE_URL is not set. Set it in .env or environment.")
        sys.exit(1)
    return url


def _prod_safety_check(url: str) -> None:
    """Refuse to run against non-localhost without explicit ADMIN_PASSWORD."""
    is_local = ("localhost" in url) or ("127.0.0.1" in url)
    if is_local:
        return
    if not os.environ.get("ADMIN_PASSWORD"):
        logger.error(
            "Refusing to run against non-localhost without ADMIN_PASSWORD env "
            "var set. Set ADMIN_PASSWORD to confirm prod execution."
        )
        sys.exit(2)


def run(dry_run: bool = False) -> None:
    try:
        import psycopg2
    except ImportError:
        logger.error(
            "psycopg2 is required. Install with: pip install psycopg2-binary"
        )
        sys.exit(1)

    database_url = _get_database_url()
    _prod_safety_check(database_url)

    logger.info("Connecting to database (dry_run=%s)...", dry_run)
    conn = psycopg2.connect(database_url)
    conn.autocommit = False

    where_clause = " OR ".join(
        ["text LIKE %s" for _ in _LEGACY_LIKE_PATTERNS]
    )
    params = list(_LEGACY_LIKE_PATTERNS)

    try:
        with conn, conn.cursor() as cur:
            # 1. Count + sample the agent rows that match.
            cur.execute(
                f"""
                SELECT id, thread_id, LEFT(text, 80)
                  FROM conversation_messages
                 WHERE sender = 'agent' AND ({where_clause})
                 ORDER BY id DESC
                """,
                params,
            )
            agent_matches = cur.fetchall()
            if not agent_matches:
                logger.info(
                    "No legacy-fallback agent rows found. Nothing to purge."
                )
                return

            logger.info(
                "Found %d legacy-fallback agent message(s). Samples:",
                len(agent_matches),
            )
            for mid, tid, sample in agent_matches[:10]:
                logger.info("  msg %s (thread %s) -- %r", mid, tid, sample)
            if len(agent_matches) > 10:
                logger.info("  ... and %d more", len(agent_matches) - 10)

            # 2. Identify threads that will be orphaned (no remaining
            #    agent messages after the purge). Use the message IDs
            #    we found above to filter, since we haven't deleted yet.
            offending_msg_ids = [m[0] for m in agent_matches]
            cur.execute(
                """
                SELECT DISTINCT thread_id
                  FROM conversation_messages
                 WHERE id = ANY(%s::int[])
                """,
                (offending_msg_ids,),
            )
            candidate_thread_ids = [row[0] for row in cur.fetchall()]

            # A thread is orphaned iff EVERY agent message in it is in
            # the offending set (i.e. no other agent reply will remain).
            orphan_thread_ids: list[int] = []
            for tid in candidate_thread_ids:
                cur.execute(
                    """
                    SELECT COUNT(*)
                      FROM conversation_messages
                     WHERE thread_id = %s AND sender = 'agent'
                       AND NOT (id = ANY(%s::int[]))
                    """,
                    (tid, offending_msg_ids),
                )
                remaining_agent_count = cur.fetchone()[0]
                if remaining_agent_count == 0:
                    orphan_thread_ids.append(tid)

            logger.info(
                "Threads with no remaining agent reply: %d", len(orphan_thread_ids)
            )

            if dry_run:
                logger.info(
                    "DRY-RUN: would delete %d message(s) and %d thread(s). "
                    "No changes committed.",
                    len(offending_msg_ids),
                    len(orphan_thread_ids),
                )
                conn.rollback()
                return

            # 3. Delete the matching agent messages.
            cur.execute(
                """
                DELETE FROM conversation_messages
                 WHERE id = ANY(%s::int[])
                """,
                (offending_msg_ids,),
            )
            logger.info("Deleted %d agent message row(s).", cur.rowcount)

            # 4. Delete every message in the orphan threads (sweeping
            #    user-side messages too), then the threads themselves.
            if orphan_thread_ids:
                cur.execute(
                    """
                    DELETE FROM conversation_messages
                     WHERE thread_id = ANY(%s::int[])
                    """,
                    (orphan_thread_ids,),
                )
                logger.info(
                    "Deleted %d remaining user-side message(s) in orphan threads.",
                    cur.rowcount,
                )

                cur.execute(
                    """
                    DELETE FROM conversation_threads
                     WHERE id = ANY(%s::int[])
                    """,
                    (orphan_thread_ids,),
                )
                logger.info("Deleted %d thread(s).", cur.rowcount)
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Purge legacy guardrail-fallback advisory turns."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be deleted without committing.",
    )
    args = parser.parse_args()
    run(dry_run=args.dry_run)
    logger.info("Done.")


if __name__ == "__main__":
    main()
