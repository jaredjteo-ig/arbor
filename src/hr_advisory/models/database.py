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
        import sys

        if "pytest" in sys.modules:
            url = "sqlite:///:memory:"
        else:
            raise ValueError(
                "DATABASE_URL environment variable is required. "
                "Set it in .env or your deployment configuration."
            )
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
