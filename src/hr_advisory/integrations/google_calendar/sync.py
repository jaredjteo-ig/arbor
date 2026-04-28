"""Google Calendar event sync service (T-R055).

Wraps the Google Calendar v3 API so that interview schedule changes in Arbor
flow to Google Calendar.  All public functions are best-effort: on any Google
API failure they log and return ``None`` (or ``False``) so that an outage in
Google Calendar does not break Arbor's interview UX.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional

from hr_advisory.integrations.google_calendar import oauth

logger = logging.getLogger(__name__)

__all__ = [
    "build_event_body",
    "create_event",
    "update_event",
    "delete_event",
    "fetch_event",
    "watch_events",
]


def _arbor_base_url() -> str:
    return os.environ.get("ARBOR_PUBLIC_URL", "http://localhost:3001")


def _build_service(company_id: int):
    """Build a Google Calendar service, returning ``None`` if not connected.

    Lazy import so unit tests can patch ``googleapiclient.discovery.build``.
    """

    creds = oauth.get_credentials(company_id)
    if creds is None:
        logger.debug("No Google Calendar credentials for company %s", company_id)
        return None

    try:
        from googleapiclient.discovery import build  # type: ignore

        return build("calendar", "v3", credentials=creds, cache_discovery=False)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to build Google Calendar client for company %s: %s", company_id, exc)
        return None


def _coerce_attendee_emails(value: Any) -> list[str]:
    """Accept either ``["a@x"]`` or ``[{"email": "a@x"}]`` and produce a flat list."""

    if value is None:
        return []
    if isinstance(value, str):
        # A JSON-encoded list (the model stores ``interviewers`` as a JSON string)
        try:
            value = json.loads(value)
        except Exception:
            return [v.strip() for v in value.split(",") if v.strip() and "@" in v]
    if not isinstance(value, Iterable):
        return []

    emails: list[str] = []
    for item in value:
        if isinstance(item, str) and "@" in item:
            emails.append(item)
        elif isinstance(item, dict):
            email = item.get("email") or item.get("user_email") or item.get("mail")
            if isinstance(email, str) and "@" in email:
                emails.append(email)
    return emails


def _parse_scheduled_at(scheduled_at: str) -> Optional[datetime]:
    if not scheduled_at:
        return None
    try:
        dt = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def build_event_body(interview: dict[str, Any]) -> dict[str, Any]:
    """Build the Google Calendar event payload from an interview dict.

    Expected keys (all optional except ``scheduled_at``):
        - ``id`` — Arbor interview id (used for description back-link)
        - ``scheduled_at`` — ISO timestamp
        - ``duration_minutes`` — int (default 60)
        - ``location`` — free-form
        - ``interviewers`` — list of emails or list of {email}
        - ``candidate_email`` — string
        - ``candidate_name`` — string
        - ``job_title`` — string
        - ``status`` — ``"cancelled"`` flips event status to ``cancelled``
    """

    candidate_name = interview.get("candidate_name") or "Candidate"
    job_title = interview.get("job_title") or "Position"
    summary = f"Interview: {candidate_name} for {job_title}"

    start_dt = _parse_scheduled_at(interview.get("scheduled_at", ""))
    duration = int(interview.get("duration_minutes") or 60)
    if start_dt is None:
        # Without a start time the Google API will reject the request, but we
        # still emit a best-guess body so the caller can see what was missing.
        end_dt = None
    else:
        end_dt = start_dt + timedelta(minutes=duration)

    attendees: list[dict[str, str]] = []
    seen: set[str] = set()
    for email in _coerce_attendee_emails(interview.get("interviewers")):
        if email.lower() not in seen:
            attendees.append({"email": email})
            seen.add(email.lower())
    candidate_email = (interview.get("candidate_email") or "").strip()
    if candidate_email and candidate_email.lower() not in seen:
        attendees.append({"email": candidate_email, "responseStatus": "needsAction"})

    interview_id = interview.get("id") or interview.get("interview_id")
    description_lines = [
        f"Interview scheduled via Arbor for {candidate_name}.",
    ]
    if job_title:
        description_lines.append(f"Role: {job_title}")
    notes = interview.get("notes")
    if notes:
        description_lines.append("")
        description_lines.append(str(notes))
    if interview_id is not None:
        description_lines.append("")
        description_lines.append(
            f"View in Arbor: {_arbor_base_url()}/recruitment/interviews/{interview_id}",
        )
    description = "\n".join(description_lines)

    body: dict[str, Any] = {
        "summary": summary,
        "description": description,
        "location": interview.get("location") or "",
        "attendees": attendees,
        "reminders": {"useDefault": True},
    }
    if start_dt is not None and end_dt is not None:
        body["start"] = {"dateTime": start_dt.isoformat()}
        body["end"] = {"dateTime": end_dt.isoformat()}

    if interview.get("status") == "cancelled":
        body["status"] = "cancelled"

    return body


def _calendar_id() -> str:
    """Calendar to write to.  ``primary`` is the user's main calendar."""

    return os.environ.get("GOOGLE_CALENDAR_ID", "primary")


def create_event(company_id: int, interview: dict[str, Any]) -> Optional[str]:
    """Create a Google Calendar event for the given interview.

    Returns the new ``google_event_id`` or ``None`` on any failure.
    """

    service = _build_service(company_id)
    if service is None:
        return None

    body = build_event_body(interview)
    if "start" not in body:
        logger.info("Skipping create_event: scheduled_at missing/invalid for interview %s", interview.get("id"))
        return None

    try:
        event = (
            service.events()
            .insert(
                calendarId=_calendar_id(),
                body=body,
                sendUpdates="all",
            )
            .execute()
        )
        return event.get("id")
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Google Calendar create_event failed for company %s interview %s: %s",
            company_id,
            interview.get("id"),
            exc,
        )
        return None


def update_event(
    company_id: int,
    google_event_id: str,
    interview: dict[str, Any],
) -> Optional[str]:
    """Patch a previously created Google Calendar event.  Returns event id or None."""

    if not google_event_id:
        return None
    service = _build_service(company_id)
    if service is None:
        return None

    body = build_event_body(interview)
    try:
        event = (
            service.events()
            .patch(
                calendarId=_calendar_id(),
                eventId=google_event_id,
                body=body,
                sendUpdates="all",
            )
            .execute()
        )
        return event.get("id")
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Google Calendar update_event failed for company %s event %s: %s",
            company_id,
            google_event_id,
            exc,
        )
        return None


def delete_event(company_id: int, google_event_id: str) -> bool:
    """Delete (cancel) a previously created Google Calendar event."""

    if not google_event_id:
        return False
    service = _build_service(company_id)
    if service is None:
        return False

    try:
        service.events().delete(
            calendarId=_calendar_id(),
            eventId=google_event_id,
            sendUpdates="all",
        ).execute()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Google Calendar delete_event failed for company %s event %s: %s",
            company_id,
            google_event_id,
            exc,
        )
        return False


def fetch_event(company_id: int, google_event_id: str) -> Optional[dict[str, Any]]:
    """Fetch a single event by id (used by the webhook handler)."""

    if not google_event_id:
        return None
    service = _build_service(company_id)
    if service is None:
        return None
    try:
        return (
            service.events()
            .get(calendarId=_calendar_id(), eventId=google_event_id)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Google Calendar fetch_event failed for company %s event %s: %s",
            company_id,
            google_event_id,
            exc,
        )
        return None


def watch_events(company_id: int, channel_id: str, channel_token: str, webhook_url: str) -> Optional[dict[str, Any]]:
    """Subscribe to push notifications for the configured calendar.

    Returns Google's ``channel`` resource (with ``resourceId`` and ``expiration``)
    or ``None`` on failure.  Persisting these values is the caller's job.
    """

    service = _build_service(company_id)
    if service is None:
        return None

    body = {
        "id": channel_id,
        "type": "web_hook",
        "address": webhook_url,
        "token": channel_token,
    }
    try:
        return (
            service.events()
            .watch(calendarId=_calendar_id(), body=body)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Google Calendar watch_events failed for company %s: %s",
            company_id,
            exc,
        )
        return None
