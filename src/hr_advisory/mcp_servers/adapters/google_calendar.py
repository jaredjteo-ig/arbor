"""Google Calendar API adapter for leave sync and public holidays.

Creates Out-of-Office calendar events when leave is approved, syncs
SG public holidays, and batch-syncs leave records. Uses Google
Calendar API v3 with per-employee OAuth 2.0 tokens.

T247: Google Calendar Sync (C07)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from hr_advisory.mcp_servers.auth.token_store import get_token_manager
from hr_advisory.mcp_servers.resilience import get_circuit

logger = logging.getLogger(__name__)

_CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3/"
_PROVIDER_NAME = "google_calendar"


class GoogleCalendarError(Exception):
    """Raised when a Google Calendar API call fails."""

    def __init__(self, status_code: int, error: str, detail: str = ""):
        self.status_code = status_code
        self.error = error
        self.detail = detail
        super().__init__(f"Google Calendar API [{status_code}]: {error} — {detail}")


class GoogleCalendarAdapter:
    """Adapter for Google Calendar API v3.

    Manages Out-of-Office events for approved leave and syncs SG public
    holidays into employee or team calendars.

    Each employee authenticates via OAuth 2.0 (Google consent screen).
    Tokens are stored per-tenant per-employee via ExternalTokenManager.

    Usage::

        adapter = GoogleCalendarAdapter()
        result = await adapter.create_ooo_event(
            calendar_id="primary",
            start="2026-03-15",
            end="2026-03-17",
            summary="Annual Leave - John Tan",
            tenant_id="company_123",
            user_id="emp_456",
        )
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        self._client_id = client_id or os.environ.get("GOOGLE_CLIENT_ID", "")
        self._client_secret = client_secret or os.environ.get("GOOGLE_CLIENT_SECRET", "")
        self._circuit = get_circuit("google_calendar")
        self._token_manager = get_token_manager()

    def _token_provider_key(self, tenant_id: str, user_id: str) -> str:
        """Build the provider key for per-employee token storage."""
        return f"{_PROVIDER_NAME}:{user_id}"

    async def _get_access_token(self, tenant_id: str, user_id: str) -> str:
        """Get a valid access token for the employee, refreshing if needed.

        Raises:
            GoogleCalendarError: If no token or refresh fails.
        """
        provider_key = self._token_provider_key(tenant_id, user_id)
        token = await self._token_manager.refresh_if_expired(tenant_id, provider_key)
        if token is None:
            token = self._token_manager.get_valid_token(tenant_id, provider_key)
        if token is None:
            raise GoogleCalendarError(
                status_code=401,
                error="no_token",
                detail=(
                    f"No Google Calendar token for user {user_id}. "
                    "Employee must connect Google Calendar in their profile settings."
                ),
            )
        return token

    def _headers(self, access_token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    async def _api_call(
        self,
        method: str,
        path: str,
        access_token: str,
        json_body: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> dict:
        """Make a Google Calendar API call through the circuit breaker."""

        async def _do_call() -> dict:
            url = f"{_CALENDAR_API_BASE}{path}"
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method == "GET":
                    resp = await client.get(url, headers=self._headers(access_token), params=params)
                elif method == "POST":
                    resp = await client.post(
                        url, json=json_body, headers=self._headers(access_token), params=params
                    )
                elif method == "DELETE":
                    resp = await client.delete(url, headers=self._headers(access_token))
                elif method == "PATCH":
                    resp = await client.patch(
                        url, json=json_body, headers=self._headers(access_token), params=params
                    )
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                if resp.status_code >= 400:
                    error_body = resp.json() if resp.content else {}
                    error_info = error_body.get("error", {})
                    raise GoogleCalendarError(
                        status_code=resp.status_code,
                        error=error_info.get("message", "unknown"),
                        detail=str(error_info.get("errors", "")),
                    )

                if resp.status_code == 204:
                    return {"status": "success"}
                return resp.json()

        return await self._circuit.call(_do_call)

    # ── OAuth flow helpers ───────────────────────────────────────

    def get_authorization_url(
        self,
        redirect_uri: str,
        state: str,
    ) -> str:
        """Build the Google OAuth 2.0 authorization URL.

        Args:
            redirect_uri: Where Google redirects after consent.
            state: Opaque state parameter (encode tenant_id + user_id).

        Returns:
            URL to redirect the employee to for Google consent.
        """
        scopes = "https://www.googleapis.com/auth/calendar.events"
        return (
            "https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={self._client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&response_type=code"
            f"&scope={scopes}"
            f"&access_type=offline"
            f"&prompt=consent"
            f"&state={state}"
        )

    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
        tenant_id: str,
        user_id: str,
    ) -> dict:
        """Exchange an authorization code for access + refresh tokens.

        Stores the tokens in the ExternalTokenManager for future use.

        Args:
            code: Authorization code from Google callback.
            redirect_uri: Must match the one used in the auth URL.
            tenant_id: Company/tenant ID.
            user_id: Employee ID.

        Returns:
            Token metadata (scopes, expiry).
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            resp.raise_for_status()
            token_data = resp.json()

        provider_key = self._token_provider_key(tenant_id, user_id)
        self._token_manager.store_token(
            tenant_id,
            provider_key,
            {
                "access_token": token_data["access_token"],
                "refresh_token": token_data.get("refresh_token"),
                "expires_in": token_data.get("expires_in", 3600),
                "scope": token_data.get("scope", ""),
            },
        )

        # Register refresh callback for this provider
        self._token_manager.register_refresh_callback(provider_key, self._refresh_token_callback)

        logger.info(
            "Google Calendar connected for tenant=%s user=%s",
            tenant_id,
            user_id,
        )
        return {
            "status": "connected",
            "scopes": token_data.get("scope", "").split(),
            "expires_in": token_data.get("expires_in"),
        }

    async def _refresh_token_callback(
        self,
        tenant_id: str,
        refresh_token: str,
    ) -> dict:
        """Refresh an expired Google OAuth token."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        return {
            "access_token": data["access_token"],
            "refresh_token": refresh_token,  # Google doesn't always return a new one
            "expires_in": data.get("expires_in", 3600),
            "scope": data.get("scope", ""),
        }

    # ── Calendar events ──────────────────────────────────────────

    async def create_ooo_event(
        self,
        calendar_id: str,
        start: str,
        end: str,
        summary: str,
        tenant_id: str = "system",
        user_id: str = "system",
        description: Optional[str] = None,
    ) -> dict:
        """Create an Out-of-Office event on an employee's calendar.

        Creates an all-day event with the "outOfOffice" event type
        (supported by Google Workspace). For personal Google accounts
        it falls back to a regular all-day event.

        Args:
            calendar_id: Calendar ID — "primary" for the employee's
                default calendar.
            start: Start date in ISO format (YYYY-MM-DD).
            end: End date in ISO format (YYYY-MM-DD). Note: Google uses
                exclusive end dates, so the adapter adds one day.
            summary: Event title (e.g. "Annual Leave - John Tan").
            tenant_id: Company/tenant ID.
            user_id: Employee ID (for token lookup).
            description: Optional event description.

        Returns:
            Dict with event_id, link, and status.
        """
        access_token = await self._get_access_token(tenant_id, user_id)

        # Google Calendar uses exclusive end dates for all-day events.
        # If someone is on leave Mar 15-17, the end date should be Mar 18.
        end_exclusive = self._next_day(end)

        event_body: dict[str, Any] = {
            "summary": summary,
            "start": {"date": start},
            "end": {"date": end_exclusive},
            "eventType": "outOfOffice",
            "transparency": "opaque",
            "status": "confirmed",
        }
        if description:
            event_body["description"] = description

        result = await self._api_call(
            method="POST",
            path=f"calendars/{calendar_id}/events",
            access_token=access_token,
            json_body=event_body,
        )

        logger.info(
            "Created OOO event '%s' (%s to %s) on calendar %s",
            summary,
            start,
            end,
            calendar_id,
        )
        return {
            "event_id": result.get("id"),
            "html_link": result.get("htmlLink"),
            "status": "created",
            "calendar_id": calendar_id,
        }

    async def sync_leave(
        self,
        employee_calendar_id: str,
        leave_records: list[dict],
        tenant_id: str = "system",
        user_id: str = "system",
    ) -> dict:
        """Batch-sync approved leave records to an employee's calendar.

        Creates OOO events for each approved leave record that doesn't
        already have a calendar event. Uses the leave record ID as an
        extended property to prevent duplicates.

        Args:
            employee_calendar_id: Calendar ID (usually "primary").
            leave_records: List of leave dicts, each with:
                - id: Unique leave record ID.
                - start_date: ISO date string.
                - end_date: ISO date string.
                - leave_type: e.g., "annual", "medical".
                - employee_name: For the event title.
            tenant_id: Company ID.
            user_id: Employee ID.

        Returns:
            Summary dict with created, skipped, and failed counts.
        """
        access_token = await self._get_access_token(tenant_id, user_id)
        created = 0
        skipped = 0
        failed = 0
        errors: list[str] = []

        # Fetch existing events to check for duplicates
        existing_event_ids = await self._get_existing_leave_event_ids(
            employee_calendar_id, access_token
        )

        for leave in leave_records:
            leave_id = leave.get("id", "")
            if leave_id in existing_event_ids:
                skipped += 1
                continue

            try:
                summary = f"{leave.get('leave_type', 'Leave').title()} - {leave.get('employee_name', 'Employee')}"
                event_body: dict[str, Any] = {
                    "summary": summary,
                    "start": {"date": leave["start_date"]},
                    "end": {"date": self._next_day(leave["end_date"])},
                    "eventType": "outOfOffice",
                    "transparency": "opaque",
                    "extendedProperties": {
                        "private": {"aite_leave_id": leave_id},
                    },
                }

                await self._api_call(
                    method="POST",
                    path=f"calendars/{employee_calendar_id}/events",
                    access_token=access_token,
                    json_body=event_body,
                )
                created += 1
            except Exception as e:
                failed += 1
                errors.append(f"Leave {leave_id}: {e}")
                logger.warning("Failed to sync leave %s: %s", leave_id, e)

        logger.info(
            "Leave sync complete: created=%d skipped=%d failed=%d",
            created,
            skipped,
            failed,
        )
        return {
            "created": created,
            "skipped": skipped,
            "failed": failed,
            "errors": errors,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def sync_public_holidays(
        self,
        calendar_id: str,
        holidays: list[dict],
        tenant_id: str = "system",
        user_id: str = "system",
    ) -> dict:
        """Add Singapore public holidays to a calendar.

        Creates all-day events for each public holiday. Uses extended
        properties to prevent duplicates on repeat sync.

        Args:
            calendar_id: Target calendar ID.
            holidays: List of holiday dicts from data.gov.sg adapter,
                each with "date", "day", "holiday" keys.
            tenant_id: Company ID.
            user_id: User ID for token lookup.

        Returns:
            Summary with created and skipped counts.
        """
        access_token = await self._get_access_token(tenant_id, user_id)
        created = 0
        skipped = 0

        for holiday in holidays:
            holiday_key = f"sg_ph_{holiday['date']}"
            try:
                # Check if already exists via extended property search
                existing = await self._api_call(
                    method="GET",
                    path=f"calendars/{calendar_id}/events",
                    access_token=access_token,
                    params={
                        "privateExtendedProperty": f"aite_holiday_id={holiday_key}",
                        "maxResults": 1,
                    },
                )
                if existing.get("items"):
                    skipped += 1
                    continue

                event_body: dict[str, Any] = {
                    "summary": f"[SG] {holiday['holiday']}",
                    "start": {"date": holiday["date"]},
                    "end": {"date": self._next_day(holiday["date"])},
                    "transparency": "transparent",
                    "extendedProperties": {
                        "private": {"aite_holiday_id": holiday_key},
                    },
                }

                await self._api_call(
                    method="POST",
                    path=f"calendars/{calendar_id}/events",
                    access_token=access_token,
                    json_body=event_body,
                )
                created += 1
            except Exception as e:
                logger.warning("Failed to sync holiday %s: %s", holiday.get("holiday"), e)

        logger.info("Public holidays synced: created=%d skipped=%d", created, skipped)
        return {
            "created": created,
            "skipped": skipped,
            "total_holidays": len(holidays),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ── Internal helpers ─────────────────────────────────────────

    async def _get_existing_leave_event_ids(
        self,
        calendar_id: str,
        access_token: str,
    ) -> set[str]:
        """Retrieve IDs of leave events already synced by AITE."""
        try:
            result = await self._api_call(
                method="GET",
                path=f"calendars/{calendar_id}/events",
                access_token=access_token,
                params={
                    "privateExtendedProperty": "aite_leave_id",
                    "maxResults": 2500,
                    "singleEvents": "true",
                },
            )
            ids: set[str] = set()
            for event in result.get("items", []):
                ext = event.get("extendedProperties", {}).get("private", {})
                leave_id = ext.get("aite_leave_id")
                if leave_id:
                    ids.add(leave_id)
            return ids
        except Exception:
            logger.warning("Could not fetch existing leave events for dedup")
            return set()

    @staticmethod
    def _next_day(date_str: str) -> str:
        """Return the next day in YYYY-MM-DD format.

        Google Calendar all-day events use an exclusive end date.
        """
        from datetime import timedelta

        dt = datetime.strptime(date_str, "%Y-%m-%d")
        next_dt = dt + timedelta(days=1)
        return next_dt.strftime("%Y-%m-%d")
