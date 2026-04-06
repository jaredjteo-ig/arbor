"""DataFlow database instance — single source of truth.

All models are registered on this instance. Import `db` from here
to define models or build workflows.
"""

import os
from urllib.parse import quote_plus, urlparse, urlunparse
from dataflow import DataFlow, DataFlowConfig


def _encode_password_in_url(url: str) -> str:
    """URL-encode the password portion of a database URL.

    Auto-generated passwords (e.g. K8s secrets) may contain shell
    metacharacters that fail SDK security validation. Encoding the
    password prevents false positives.
    """
    if "://" not in url or url.startswith("sqlite"):
        return url
    parsed = urlparse(url)
    if not parsed.password:
        return url
    encoded_password = quote_plus(parsed.password)
    netloc = f"{parsed.username}:{encoded_password}@{parsed.hostname}"
    if parsed.port:
        netloc += f":{parsed.port}"
    return urlunparse(parsed._replace(netloc=netloc))


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
    return _encode_password_in_url(url)


_url = get_database_url()

db = DataFlow(
    database_url=_url,
    config=DataFlowConfig(
        database_url=_url,
        max_connections=20,
        min_connections=1,
        connect_timeout_secs=30,
        max_lifetime_secs=3600,
        auto_migrate=True,
    ),
)
