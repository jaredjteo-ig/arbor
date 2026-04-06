"""DataFlow database instance — single source of truth.

All models are registered on this instance. Import `db` from here
to define models or build workflows.
"""

import os
from urllib.parse import quote_plus, unquote
from dataflow import DataFlow, DataFlowConfig


def _ensure_password_encoded(url: str) -> str:
    """URL-encode the password portion of a database URL.

    Kailash SDK's AsyncSQLDatabaseNode validates connection strings for
    suspicious patterns (backticks, $( , etc). Auto-generated passwords
    (e.g. from K8s secrets) can contain these characters legitimately.
    URL-encoding the password prevents false positives.

    Uses string slicing instead of urlparse because urlparse cannot
    reliably parse URLs with unescaped #, @, or backticks in passwords.
    """
    if url.startswith("sqlite"):
        return url
    try:
        scheme_end = url.index("://") + 3
        at_pos = url.rindex("@")
        creds = url[scheme_end:at_pos]
        colon_pos = creds.index(":")
        user = creds[:colon_pos]
        raw_password = creds[colon_pos + 1 :]
        # Decode first (handles already-encoded chars), then re-encode
        decoded = unquote(raw_password)
        encoded = quote_plus(decoded)
        return url[:scheme_end] + user + ":" + encoded + url[at_pos:]
    except (ValueError, IndexError):
        return url


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
    return _ensure_password_encoded(url)


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
