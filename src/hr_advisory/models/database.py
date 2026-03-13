"""DataFlow database instance — single source of truth.

All models are registered on this instance. Import `db` from here
to define models or build workflows.
"""

import os
from dataflow import DataFlow


def get_database_url() -> str:
    """Get database URL from environment, never hardcode."""
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://aite:aite@localhost:5432/aite",
    )


db = DataFlow(
    database_url=get_database_url(),
    auto_migrate=True,
    pool_size=20,
    pool_max_overflow=30,
    pool_recycle=3600,
    echo=False,
    monitoring=True,
)
