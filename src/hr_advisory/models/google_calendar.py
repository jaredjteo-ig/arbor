"""DataFlow model for Google Calendar OAuth connections per company (T-R055).

Stores per-company Google OAuth tokens and webhook channel metadata so that
interview schedule changes in Arbor sync to Google Calendar (and vice versa).
"""

from __future__ import annotations

from hr_advisory.models.database import db


@db.model
class GoogleCalendarConnection:
    """Google Calendar OAuth connection scoped to a single company (T-R055).

    Tokens are encrypted at rest by DataFlow's standard column encryption
    (the values stored here are passed straight from Google's OAuth response).
    """

    company_id: int
    access_token: str = ""
    refresh_token: str = ""
    expires_at: str = ""  # ISO timestamp; empty = unknown
    scope: str = ""
    token_uri: str = "https://oauth2.googleapis.com/token"
    channel_id: str = ""
    channel_token: str = ""
    channel_resource_id: str = ""
    channel_expiration: str = ""  # ISO timestamp
    last_synced_at: str = ""
    connected_by: int = 0  # user_id who connected
    status: str = "connected"  # connected | disconnected | error
    # S3-T1: Google Calendar incremental sync token. Persisted from
    # `events.list(syncToken=...)` after every webhook-driven diff fetch.
    # On 410-Gone the token is reset to "" and the next webhook performs
    # a full re-sync (fetching all upcoming events).
    sync_token: str = ""

    __dataflow__ = {
        "indexes": [
            {"name": "idx_gcal_company", "fields": ["company_id"], "unique": True},
            {"name": "idx_gcal_channel", "fields": ["channel_id"]},
        ],
    }
