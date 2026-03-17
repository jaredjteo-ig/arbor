"""Microsoft Graph API adapter for Outlook Calendar sync.

Creates Out-of-Office events in Outlook Calendar when leave is
approved, syncs SG public holidays. Uses Microsoft Graph API v1.0
with OAuth 2.0 via Entra ID (formerly Azure AD).

Note: EWS is deprecated Oct 2026 — this adapter uses Graph API only.

T248: Microsoft Outlook Calendar Sync (C08)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

from hr_advisory.mcp_servers.auth.token_store import get_token_manager
from hr_advisory.mcp_servers.resilience import get_circuit

logger = logging.getLogger(__name__)

_GRAPH_API_BASE = "https://graph.microsoft.com/v1.0/"
_PROVIDER_NAME = "microsoft_graph"


class MicrosoftGraphError(Exception):
    """Raised when a Microsoft Graph API call fails."""

    def __init__(self, status_code: int, error_code: str, message: str):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        super().__init__(f"Microsoft Graph [{status_code}] {error_code}: {message}")


class MicrosoftGraphAdapter:
    """Adapter for Microsoft Graph API (Calendar).

    Manages Outlook Calendar events for leave sync and public holidays.
    Authenticates via OAuth 2.0 with Entra ID, supporting both
    delegated (per-user) and application-level access.

    Usage::

        adapter = MicrosoftGraphAdapter()
        result = await adapter.create_ooo_event(
            user_id="emp_456",
            start="2026-03-15",
            end="2026-03-17",
            summary="Annual Leave - John Tan",
            tenant_id="company_123",
        )
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        entra_tenant_id: Optional[str] = None,
    ):
        self._client_id = client_id or os.environ.get("MICROSOFT_CLIENT_ID", "")
        self._client_secret = client_secret or os.environ.get("MICROSOFT_CLIENT_SECRET", "")
        self._entra_tenant_id = entra_tenant_id or os.environ.get("MICROSOFT_TENANT_ID", "common")
        self._circuit = get_circuit("microsoft_graph")
        self._token_manager = get_token_manager()

    def _token_provider_key(self, user_id: str) -> str:
        return f"{_PROVIDER_NAME}:{user_id}"

    async def _get_access_token(self, tenant_id: str, user_id: str) -> str:
        """Get a valid access token for the user.

        Tries per-user delegated token first, then falls back to
        application-level token with user impersonation.
        """
        provider_key = self._token_provider_key(user_id)
        token = await self._token_manager.refresh_if_expired(tenant_id, provider_key)
        if token is None:
            token = self._token_manager.get_valid_token(tenant_id, provider_key)
        if token is None:
            raise MicrosoftGraphError(
                status_code=401,
                error_code="NoToken",
                message=(
                    f"No Microsoft Graph token for user {user_id}. "
                    "Employee must connect their Microsoft account in profile settings."
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
        """Make a Graph API call through the circuit breaker."""

        async def _do_call() -> dict:
            url = f"{_GRAPH_API_BASE}{path}"
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method == "GET":
                    resp = await client.get(url, headers=self._headers(access_token), params=params)
                elif method == "POST":
                    resp = await client.post(
                        url, json=json_body, headers=self._headers(access_token)
                    )
                elif method == "PATCH":
                    resp = await client.patch(
                        url, json=json_body, headers=self._headers(access_token)
                    )
                elif method == "DELETE":
                    resp = await client.delete(url, headers=self._headers(access_token))
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                if resp.status_code >= 400:
                    error_body = resp.json() if resp.content else {}
                    error_info = error_body.get("error", {})
                    raise MicrosoftGraphError(
                        status_code=resp.status_code,
                        error_code=error_info.get("code", "Unknown"),
                        message=error_info.get("message", resp.text[:500]),
                    )

                if resp.status_code == 204:
                    return {"status": "success"}
                return resp.json()

        return await self._circuit.call(_do_call)

    # ── OAuth flow ───────────────────────────────────────────────

    def get_authorization_url(
        self,
        redirect_uri: str,
        state: str,
    ) -> str:
        """Build the Entra ID OAuth 2.0 authorization URL.

        Args:
            redirect_uri: Callback URL after consent.
            state: Opaque state for CSRF protection (encode tenant + user).

        Returns:
            URL to redirect the employee to for Microsoft consent.
        """
        scopes = "Calendars.ReadWrite offline_access"
        return (
            f"https://login.microsoftonline.com/{self._entra_tenant_id}/oauth2/v2.0/authorize"
            f"?client_id={self._client_id}"
            f"&response_type=code"
            f"&redirect_uri={redirect_uri}"
            f"&scope={scopes}"
            f"&state={state}"
            f"&response_mode=query"
        )

    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
        tenant_id: str,
        user_id: str,
    ) -> dict:
        """Exchange authorization code for tokens and store them.

        Args:
            code: Authorization code from Entra ID callback.
            redirect_uri: Must match the auth URL redirect_uri.
            tenant_id: AITE tenant (company) ID.
            user_id: AITE employee ID.

        Returns:
            Token metadata dict.
        """
        token_url = f"https://login.microsoftonline.com/{self._entra_tenant_id}/oauth2/v2.0/token"

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                token_url,
                data={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                    "scope": "Calendars.ReadWrite offline_access",
                },
            )
            resp.raise_for_status()
            token_data = resp.json()

        provider_key = self._token_provider_key(user_id)
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

        self._token_manager.register_refresh_callback(provider_key, self._make_refresh_callback())

        logger.info(
            "Microsoft Graph connected for tenant=%s user=%s",
            tenant_id,
            user_id,
        )
        return {
            "status": "connected",
            "scopes": token_data.get("scope", "").split(),
            "expires_in": token_data.get("expires_in"),
        }

    def _make_refresh_callback(self):
        """Create a token refresh callback closure."""

        async def _refresh(tenant_id: str, refresh_token: str) -> dict:
            token_url = (
                f"https://login.microsoftonline.com/{self._entra_tenant_id}/oauth2/v2.0/token"
            )
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    token_url,
                    data={
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                        "scope": "Calendars.ReadWrite offline_access",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            return {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token", refresh_token),
                "expires_in": data.get("expires_in", 3600),
                "scope": data.get("scope", ""),
            }

        return _refresh

    # ── Calendar events ──────────────────────────────────────────

    async def create_ooo_event(
        self,
        user_id: str,
        start: str,
        end: str,
        summary: str,
        tenant_id: str = "system",
        description: Optional[str] = None,
    ) -> dict:
        """Create an Out-of-Office event on a user's Outlook Calendar.

        Uses the Graph API events endpoint. Sets showAs="oof" for
        Out-of-Office status and isAllDay=true for all-day events.

        Args:
            user_id: AITE employee ID (for token lookup). Uses "me"
                endpoint with delegated tokens.
            start: Start date (YYYY-MM-DD).
            end: End date (YYYY-MM-DD), inclusive.
            summary: Event subject line.
            tenant_id: AITE company ID.
            description: Optional event body text.

        Returns:
            Dict with event_id, web_link, status.
        """
        access_token = await self._get_access_token(tenant_id, user_id)

        # Graph API all-day events need dateTime with "0:00:00.0000000"
        # and the timeZone set. End date is exclusive (add 1 day).
        end_exclusive = self._next_day(end)

        event_body: dict[str, Any] = {
            "subject": summary,
            "isAllDay": True,
            "start": {
                "dateTime": f"{start}T00:00:00.0000000",
                "timeZone": "Singapore Standard Time",
            },
            "end": {
                "dateTime": f"{end_exclusive}T00:00:00.0000000",
                "timeZone": "Singapore Standard Time",
            },
            "showAs": "oof",
            "isReminderOn": False,
            "categories": ["AITE Leave"],
        }
        if description:
            event_body["body"] = {
                "contentType": "text",
                "content": description,
            }

        # Use transactional property to tag AITE-managed events
        event_body["singleValueExtendedProperties"] = [
            {
                "id": "String {66f5a359-4659-4830-9070-00047ec6ac6e} Name aite_managed",
                "value": "true",
            }
        ]

        result = await self._api_call(
            method="POST",
            path="me/events",
            access_token=access_token,
            json_body=event_body,
        )

        logger.info(
            "Created Outlook OOO event '%s' (%s to %s) for user %s",
            summary,
            start,
            end,
            user_id,
        )
        return {
            "event_id": result.get("id"),
            "web_link": result.get("webLink"),
            "status": "created",
        }

    async def sync_leave(
        self,
        user_id: str,
        leave_records: list[dict],
        tenant_id: str = "system",
    ) -> dict:
        """Batch-sync approved leave records to a user's Outlook Calendar.

        Creates OOO events for each leave record. Uses categories and
        extended properties to identify AITE-managed events and prevent
        duplicates.

        Args:
            user_id: AITE employee ID.
            leave_records: List of leave dicts with id, start_date,
                end_date, leave_type, employee_name.
            tenant_id: Company ID.

        Returns:
            Summary with created, skipped, failed counts.
        """
        access_token = await self._get_access_token(tenant_id, user_id)
        created = 0
        skipped = 0
        failed = 0
        errors: list[str] = []

        # Get existing AITE-managed events to check for duplicates
        existing_ids = await self._get_existing_aite_event_subjects(access_token)

        for leave in leave_records:
            leave_id = leave.get("id", "")
            # Use leave_id in subject for dedup
            leave_subject = f"{leave.get('leave_type', 'Leave').title()} - {leave.get('employee_name', 'Employee')} [{leave_id}]"

            if leave_subject in existing_ids:
                skipped += 1
                continue

            try:
                await self.create_ooo_event(
                    user_id=user_id,
                    start=leave["start_date"],
                    end=leave["end_date"],
                    summary=leave_subject,
                    tenant_id=tenant_id,
                )
                created += 1
            except Exception as e:
                failed += 1
                errors.append(f"Leave {leave_id}: {e}")
                logger.warning("Failed to sync leave %s to Outlook: %s", leave_id, e)

        logger.info(
            "Outlook leave sync complete: created=%d skipped=%d failed=%d",
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
        """Add Singapore public holidays to an Outlook Calendar.

        Args:
            calendar_id: Not used directly for Graph — uses "me" endpoint.
                Retained for interface compatibility with Google adapter.
            holidays: List of holiday dicts with "date", "day", "holiday".
            tenant_id: Company ID.
            user_id: Employee ID for token lookup.

        Returns:
            Summary with created and skipped counts.
        """
        access_token = await self._get_access_token(tenant_id, user_id)
        created = 0
        skipped = 0

        existing_subjects = await self._get_existing_aite_event_subjects(access_token)

        for holiday in holidays:
            subject = f"[SG] {holiday['holiday']}"
            if subject in existing_subjects:
                skipped += 1
                continue

            try:
                end_exclusive = self._next_day(holiday["date"])
                event_body: dict[str, Any] = {
                    "subject": subject,
                    "isAllDay": True,
                    "start": {
                        "dateTime": f"{holiday['date']}T00:00:00.0000000",
                        "timeZone": "Singapore Standard Time",
                    },
                    "end": {
                        "dateTime": f"{end_exclusive}T00:00:00.0000000",
                        "timeZone": "Singapore Standard Time",
                    },
                    "showAs": "free",
                    "isReminderOn": False,
                    "categories": ["AITE Holiday"],
                }

                await self._api_call(
                    method="POST",
                    path="me/events",
                    access_token=access_token,
                    json_body=event_body,
                )
                created += 1
            except Exception as e:
                logger.warning("Failed to sync holiday '%s': %s", holiday.get("holiday"), e)

        logger.info("Outlook holiday sync: created=%d skipped=%d", created, skipped)
        return {
            "created": created,
            "skipped": skipped,
            "total_holidays": len(holidays),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ── Internal helpers ─────────────────────────────────────────

    async def _get_existing_aite_event_subjects(
        self,
        access_token: str,
    ) -> set[str]:
        """Get subjects of events in AITE categories for dedup."""
        try:
            result = await self._api_call(
                method="GET",
                path="me/events",
                access_token=access_token,
                params={
                    "$filter": "categories/any(c:c eq 'AITE Leave' or c eq 'AITE Holiday')",
                    "$select": "subject",
                    "$top": "999",
                },
            )
            return {event.get("subject", "") for event in result.get("value", [])}
        except Exception:
            logger.warning("Could not fetch existing Outlook events for dedup")
            return set()

    @staticmethod
    def _next_day(date_str: str) -> str:
        """Return the next day in YYYY-MM-DD format."""
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return (dt + timedelta(days=1)).strftime("%Y-%m-%d")
