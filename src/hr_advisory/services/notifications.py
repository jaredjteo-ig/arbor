"""In-app notification service (T06 / Z10).

Round-3 product revision: engagement-survey launches fan out via
in-app notifications instead of email (engagement is in-app only at
v1). This service is the only writer to the `Notification` table.

Used by:
- M3 T30 — engagement launch creates one notification per response.
- M3 T31 — submit handler marks the related notification resolved.
- M3 T37 — accepting an action with a linked goal owned by a manager
  fans out an `engagement_action_accepted` notification to that manager.
- M8 T86 — reminder send creates `engagement_reminder` rows.

Email send (used by exit interviews, M8 reminder) is a separate
concern — see future EmailDeliveryJob module.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from hr_advisory.services import dataflow_crud

logger = logging.getLogger(__name__)

__all__ = [
    "create_notification",
    "bulk_create_engagement_pending",
    "list_user_notifications",
    "mark_resolved",
    "mark_resolved_by_link",
    "ENGAGEMENT_PENDING",
    "ENGAGEMENT_REMINDER",
    "ENGAGEMENT_ACTION_ACCEPTED",
]

ENGAGEMENT_PENDING = "engagement_pending"
ENGAGEMENT_REMINDER = "engagement_reminder"
ENGAGEMENT_ACTION_ACCEPTED = "engagement_action_accepted"


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def create_notification(
    *,
    user_id: int,
    company_id: int,
    kind: str,
    title: str,
    body: str = "",
    link: str = "",
    actor_user_id: int = 0,
    metadata: dict | None = None,
) -> dict:
    """Create one notification row.

    Returns the created record.
    """
    if user_id <= 0:
        raise ValueError("user_id must be > 0.")
    if company_id <= 0:
        raise ValueError("company_id must be > 0.")
    if not kind:
        raise ValueError("kind must be a non-empty string.")
    if not title:
        raise ValueError("title must be non-empty.")

    now = _now()
    record = dataflow_crud.create(
        "Notification",
        {
            "user_id": int(user_id),
            "company_id": int(company_id),
            "kind": str(kind),
            "title": str(title)[:200],
            "body": str(body)[:1000],
            "link": str(link)[:500],
            "actor_user_id": int(actor_user_id),
            "is_resolved": False,
            "resolved_at": None,
            "is_archived": False,
            "metadata_json": json.dumps(metadata) if metadata else "",
            "created_at": now,
            "updated_at": now,
        },
    )
    return record


def bulk_create_engagement_pending(
    *,
    company_id: int,
    actor_user_id: int,
    survey_name: str,
    closes_at_iso: str,
    response_user_pairs: list[tuple[int, int]],
) -> int:
    """Fan out engagement-pending notifications for a survey launch.

    `response_user_pairs` is a list of `(response_id, user_id)` tuples.
    One notification per pair; link points at the in-app form.

    Returns the count of notifications created. Failures on individual
    rows are logged but do not abort the batch — partial fanout state
    is reflected on the survey detail page (round-3 saga shape Z09).
    """
    created = 0
    title = f"Pulse open: {survey_name}"
    body = f"Closes {closes_at_iso}. Takes about 90 seconds."
    for response_id, user_id in response_user_pairs:
        try:
            create_notification(
                user_id=user_id,
                company_id=company_id,
                kind=ENGAGEMENT_PENDING,
                title=title,
                body=body,
                link=f"/my-engagement-surveys/{int(response_id)}/respond",
                actor_user_id=actor_user_id,
                metadata={"response_id": int(response_id)},
            )
            created += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "engagement_pending_notification_failed",
                extra={
                    "response_id": response_id,
                    "user_id": user_id,
                    "error": str(exc),
                },
            )
    logger.info(
        "engagement_pending_notifications_fanned_out",
        extra={
            "company_id": company_id,
            "created": created,
            "target": len(response_user_pairs),
        },
    )
    return created


def list_user_notifications(
    user_id: int,
    *,
    kind: str | None = None,
    only_unresolved: bool = True,
) -> list[dict]:
    """List notifications for a user, optionally filtered by kind."""
    where: dict[str, Any] = {"user_id": int(user_id), "is_archived": False}
    if kind is not None:
        where["kind"] = str(kind)
    if only_unresolved:
        where["is_resolved"] = False

    rows = dataflow_crud.list_records("Notification", where, cache_ttl=0)
    rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return rows


def mark_resolved(notification_id: int, user_id: int) -> bool:
    """Mark a notification resolved. Returns True on success.

    Verifies user_id matches the notification owner so a malicious
    user can't resolve another user's notifications.
    """
    rows = dataflow_crud.list_records(
        "Notification",
        {"id": int(notification_id)},
        cache_ttl=0,
    )
    if not rows:
        return False
    row = rows[0]
    if int(row.get("user_id") or 0) != int(user_id):
        logger.warning(
            "notification_resolve_user_mismatch",
            extra={
                "notification_id": notification_id,
                "owner_user_id": row.get("user_id"),
                "claimed_user_id": user_id,
            },
        )
        return False
    if row.get("is_resolved"):
        return True
    now = _now()
    dataflow_crud.update(
        "Notification",
        int(notification_id),
        {"is_resolved": True, "resolved_at": now, "updated_at": now},
    )
    return True


def mark_resolved_by_link(user_id: int, link: str) -> int:
    """Mark all of a user's notifications matching `link` as resolved.

    Used by the engagement submit handler — when the form submits, any
    notification pointing at this response's link is auto-resolved so
    the dashboard pending card disappears immediately. Returns count.
    """
    rows = dataflow_crud.list_records(
        "Notification",
        {"user_id": int(user_id), "link": str(link), "is_resolved": False},
        cache_ttl=0,
    )
    count = 0
    now = _now()
    for r in rows:
        try:
            dataflow_crud.update(
                "Notification",
                int(r["id"]),
                {"is_resolved": True, "resolved_at": now, "updated_at": now},
            )
            count += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "notification_resolve_by_link_failed",
                extra={"id": r.get("id"), "error": str(exc)},
            )
    return count
