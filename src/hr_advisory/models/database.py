"""DataFlow database instance — single source of truth.

All models are registered on this instance. Import `db` from here
to define models or build workflows.
"""

import os
from dataflow import DataFlow, DataFlowConfig


def get_database_url() -> str:
    """Get database URL from environment, never hardcode."""
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://arbor:arbor@localhost:5432/arbor",
    )


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
