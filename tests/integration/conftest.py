"""Integration test configuration.

Provides automatic PostgreSQL availability detection. Tests in modules that
require PostgreSQL are automatically skipped when the database is unreachable,
producing a clear skip message instead of cryptic connection errors.

Usage in test modules:
    import pytest
    pytestmark = pytest.mark.requires_postgres
"""

import socket

import pytest

# ---------------------------------------------------------------------------
# PostgreSQL availability check (cached at import time)
# ---------------------------------------------------------------------------

_PG_HOST = "localhost"
_PG_PORT = 5432


def _postgres_is_reachable(host: str = _PG_HOST, port: int = _PG_PORT) -> bool:
    """Check if PostgreSQL is accepting TCP connections."""
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except (OSError, ConnectionRefusedError, TimeoutError):
        return False


_POSTGRES_AVAILABLE = _postgres_is_reachable()


def pytest_collection_modifyitems(config, items):
    """Auto-skip tests marked with requires_postgres when DB is unavailable."""
    if _POSTGRES_AVAILABLE:
        return

    skip_pg = pytest.mark.skip(reason=f"PostgreSQL not reachable at {_PG_HOST}:{_PG_PORT}")
    for item in items:
        if "requires_postgres" in item.keywords:
            item.add_marker(skip_pg)
