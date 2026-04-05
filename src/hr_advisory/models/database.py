"""DataFlow database instance — single source of truth.

All models are registered on this instance. Import `db` from here
to define models or build workflows.
"""

import os
from dataflow import DataFlow, DataFlowConfig


def get_database_url() -> str:
    """Get database URL from environment, never hardcode."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        import logging
        import sys

        if "pytest" in sys.modules:
            url = "sqlite:///:memory:"
        else:
            logging.getLogger(__name__).warning(
                "DATABASE_URL not set — using sqlite://:memory: (data will not persist). "
                "Set DATABASE_URL in .env for PostgreSQL."
            )
            url = "sqlite:///:memory:"
    return url


_url = get_database_url()

db = DataFlow(
    database_url=_url,
    pool_size=int(os.environ.get("DATAFLOW_MAX_CONNECTIONS", "10")),
    auto_migrate=True,
    config=DataFlowConfig(
        database_url=_url,
        connect_timeout_secs=5,
        max_lifetime_secs=3600,
    ),
)
