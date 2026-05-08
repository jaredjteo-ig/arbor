"""Migration: ``integration_tokens`` table for persisted OAuth tokens.

Replaces the in-memory ``ExternalTokenManager`` storage with a
DataFlow-backed table. Tokens encrypted with Fernet using
``INTEGRATION_ENCRYPTION_KEY``. Survives restart, shared across
multi-worker uvicorn deployments.

Idempotent: skip if the table or any individual column already exists.
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


def _table_exists(cursor, table: str) -> bool:
    cursor.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_name = %s",
        (table,),
    )
    return cursor.fetchone() is not None


_DDL = """
CREATE TABLE integration_tokens (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL DEFAULT '',
    provider TEXT NOT NULL DEFAULT '',
    access_token_encrypted TEXT NOT NULL DEFAULT '',
    refresh_token_encrypted TEXT NOT NULL DEFAULT '',
    expires_at DOUBLE PRECISION NOT NULL DEFAULT 0,
    scopes TEXT NOT NULL DEFAULT '',
    xero_tenant_id TEXT NOT NULL DEFAULT '',
    xero_tenant_name TEXT NOT NULL DEFAULT '',
    connected_by INTEGER NOT NULL DEFAULT 0,
    connected_at TEXT NOT NULL DEFAULT '',
    disconnected_at TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_inttok_tenant_provider
    ON integration_tokens(tenant_id, provider);
CREATE UNIQUE INDEX idx_inttok_unique_active
    ON integration_tokens(tenant_id, provider)
    WHERE disconnected_at = '';
"""


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
            if _table_exists(cur, "integration_tokens"):
                logger.info(
                    "integration_tokens table already exists — skipping"
                )
                return
            logger.info("Creating integration_tokens table")
            cur.execute(_DDL)
            logger.info("Created integration_tokens table.")
    finally:
        conn.close()


if __name__ == "__main__":
    run()
    logger.info("Done.")
