"""Push Notification Service (T056).

Handles creation, targeting, and delivery of push notifications for
the AITE HR Advisory platform. Notification types include regulatory
updates, deadline reminders, compliance alerts, correction notices,
and system announcements.

Delivery channel: Firebase Cloud Messaging (FCM) in production.
User targeting resolves affected users by company, regulatory domain,
or specific provision IDs.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────


class NotificationType(str, Enum):
    """Categories of push notification."""

    REGULATORY_UPDATE = "regulatory_update"
    DEADLINE_REMINDER = "deadline_reminder"
    COMPLIANCE_ALERT = "compliance_alert"
    CORRECTION_NOTICE = "correction_notice"
    SYSTEM_ANNOUNCEMENT = "system_announcement"


class NotificationPriority(str, Enum):
    """Delivery priority — maps to FCM priority levels."""

    HIGH = "high"
    NORMAL = "normal"


class DeliveryStatus(str, Enum):
    """Status of a notification delivery attempt."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


# ── Data classes ─────────────────────────────────────────────


@dataclass(frozen=True)
class NotificationPayload:
    """Immutable notification content ready for delivery.

    Attributes:
        notification_id: Unique identifier (UUID).
        type: Category of notification.
        title: Short headline displayed in notification tray.
        body: Full notification text.
        deep_link: In-app navigation path (e.g. "/compliance/cpf-filing").
        data: Arbitrary key-value metadata for the client app.
        priority: FCM delivery priority.
        created_at: Timestamp of creation.
    """

    notification_id: str
    type: NotificationType
    title: str
    body: str
    deep_link: str
    data: dict = field(default_factory=dict)
    priority: NotificationPriority = NotificationPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class NotificationTarget:
    """A user to receive a notification.

    In production, FCM token and email are resolved from the DataFlow
    User model. Either fcm_token (for push) or email (for fallback
    email delivery) should be present.

    Attributes:
        user_id: Platform user ID.
        company_id: Company the user belongs to.
        fcm_token: Firebase Cloud Messaging device token (optional).
        email: Fallback email address (optional).
    """

    user_id: str
    company_id: str
    fcm_token: Optional[str] = None
    email: Optional[str] = None


@dataclass(frozen=True)
class NotificationResult:
    """Outcome of a send_notification call.

    Attributes:
        notification_id: The payload that was sent.
        total_targets: Number of users targeted.
        successful: Number of successful deliveries.
        failed: Number of failed deliveries.
        status: Overall delivery status.
        errors: Per-target error messages (keyed by user_id).
    """

    notification_id: str
    total_targets: int
    successful: int
    failed: int
    status: DeliveryStatus
    errors: dict = field(default_factory=dict)


# ── In-memory stores (production: DataFlow models) ──────────
#
# _notification_store: maps notification_id → NotificationPayload
# _user_notifications: maps user_id → list of notification_ids (delivery log)
# _user_registry: maps company_id → list of NotificationTarget
#    In production, this is replaced by DataFlow User queries filtered
#    by company_id. Kept here for local testing and development.
# _provision_subscriptions: maps provision_id → list of user_ids
#    In production, resolved by querying which companies have profiles
#    affected by the provision's domain, then resolving users.

_notification_store: dict[str, NotificationPayload] = {}
_user_notifications: dict[str, list[str]] = {}  # user_id → [notification_id, ...]
_user_registry: dict[str, list[NotificationTarget]] = {}  # company_id → [targets]
_provision_subscriptions: dict[str, list[str]] = {}  # provision_id → [user_id, ...]


# ── Notification creation ────────────────────────────────────


def create_notification(
    type: NotificationType,
    title: str,
    body: str,
    deep_link: str,
    data: Optional[dict] = None,
    priority: NotificationPriority = NotificationPriority.NORMAL,
) -> NotificationPayload:
    """Create a new notification payload.

    Generates a unique notification_id and timestamps the payload.
    The notification is stored in the notification store for history
    retrieval but is not yet delivered to any users.

    Args:
        type: Notification category.
        title: Short headline for the notification tray.
        body: Full notification text.
        deep_link: In-app navigation path.
        data: Optional key-value metadata for the client app.
        priority: Delivery priority (high or normal).

    Returns:
        The created NotificationPayload.
    """
    payload = NotificationPayload(
        notification_id=str(uuid.uuid4()),
        type=type,
        title=title,
        body=body,
        deep_link=deep_link,
        data=data or {},
        priority=priority,
    )
    _notification_store[payload.notification_id] = payload
    logger.info(
        "Notification created: id=%s type=%s title=%r",
        payload.notification_id,
        type.value,
        title,
    )
    return payload


# ── Targeting ────────────────────────────────────────────────


def target_by_company(
    company_id: str,
    affected_domains: Optional[list[str]] = None,
) -> list[NotificationTarget]:
    """Identify notification targets within a company.

    If affected_domains is provided, in production this would further
    filter to users whose role or preferences indicate interest in
    those domains (e.g. only HR managers for CPF domain notifications).
    In the current implementation, all registered users for the company
    are returned.

    Args:
        company_id: Company to target.
        affected_domains: Optional list of regulatory domains to narrow
            the audience (e.g. ["cpf", "employment_act"]).

    Returns:
        List of NotificationTarget for matching users.
    """
    targets = _user_registry.get(company_id, [])
    if not targets:
        logger.info(
            "No registered targets for company %s (domains=%s)",
            company_id,
            affected_domains,
        )
    else:
        logger.info(
            "Found %d targets for company %s (domains=%s)",
            len(targets),
            company_id,
            affected_domains,
        )
    # In production: further filter by domain preferences/roles
    _ = affected_domains
    return list(targets)


def target_by_provision(
    provision_ids: list[str],
) -> list[NotificationTarget]:
    """Find users whose profiles are affected by specific provisions.

    In production, this resolves provision_ids → domains → companies
    → users via DataFlow queries. Companies are matched when the
    provision's applicability rules match the company's profile
    (headcount, sector, worker types).

    Args:
        provision_ids: List of provision identifiers to match against.

    Returns:
        Deduplicated list of NotificationTarget for affected users.
    """
    seen_user_ids: set[str] = set()
    targets: list[NotificationTarget] = []

    for provision_id in provision_ids:
        user_ids = _provision_subscriptions.get(provision_id, [])
        for user_id in user_ids:
            if user_id in seen_user_ids:
                continue
            seen_user_ids.add(user_id)
            # Resolve the full target from the registry
            target = _resolve_target_by_user_id(user_id)
            if target is not None:
                targets.append(target)

    logger.info(
        "Resolved %d targets for %d provisions",
        len(targets),
        len(provision_ids),
    )
    return targets


def _resolve_target_by_user_id(user_id: str) -> Optional[NotificationTarget]:
    """Look up a NotificationTarget by user_id across all companies.

    In production, this is a single DataFlow User query by ID.
    """
    for company_targets in _user_registry.values():
        for target in company_targets:
            if target.user_id == user_id:
                return target
    return None


# ── Delivery ─────────────────────────────────────────────────


async def _send_via_fcm(
    payload: NotificationPayload,
    target: NotificationTarget,
) -> bool:
    """Send a single notification via Firebase Cloud Messaging.

    In production, this calls the FCM v1 HTTP API:
        POST https://fcm.googleapis.com/v1/projects/{project}/messages:send

    The current implementation logs the delivery and returns success.
    Replace with real FCM HTTP client when deploying.

    Args:
        payload: The notification content.
        target: The recipient.

    Returns:
        True if delivery succeeded, False otherwise.
    """
    import os

    fcm_credentials = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    if not fcm_credentials:
        logger.warning(
            "FCM delivery skipped — GOOGLE_APPLICATION_CREDENTIALS not configured. "
            "notification=%s user=%s title=%r. "
            "Set GOOGLE_APPLICATION_CREDENTIALS to enable push notification delivery.",
            payload.notification_id,
            target.user_id,
            payload.title,
        )
        return False

    if not target.fcm_token:
        logger.warning(
            "FCM delivery skipped — user %s has no FCM token registered. " "notification=%s",
            target.user_id,
            payload.notification_id,
        )
        return False

    logger.info(
        "FCM send: notification=%s user=%s token=%s title=%r",
        payload.notification_id,
        target.user_id,
        target.fcm_token[:8] + "...",
        payload.title,
    )
    # Production: async HTTP POST to FCM v1 API
    # POST https://fcm.googleapis.com/v1/projects/{project}/messages:send
    # with service account credentials from GOOGLE_APPLICATION_CREDENTIALS
    logger.warning(
        "FCM delivery not available — firebase-admin SDK not integrated. "
        "notification=%s user=%s. Install firebase-admin and implement "
        "the FCM HTTP call to enable push delivery.",
        payload.notification_id,
        target.user_id,
    )
    return False


async def send_notification(
    payload: NotificationPayload,
    targets: list[NotificationTarget],
) -> NotificationResult:
    """Deliver a notification to a list of targets via FCM.

    Attempts delivery to each target. Records the notification in
    each user's history for later retrieval via get_notification_history.

    Args:
        payload: The notification to send.
        targets: List of recipients.

    Returns:
        NotificationResult with delivery counts and any errors.
    """
    if not targets:
        logger.warning(
            "send_notification called with no targets: notification=%s",
            payload.notification_id,
        )
        return NotificationResult(
            notification_id=payload.notification_id,
            total_targets=0,
            successful=0,
            failed=0,
            status=DeliveryStatus.SENT,
        )

    successful = 0
    failed = 0
    errors: dict[str, str] = {}

    for target in targets:
        try:
            ok = await _send_via_fcm(payload, target)
            if ok:
                successful += 1
                # Record in user's notification history
                history = _user_notifications.setdefault(target.user_id, [])
                history.append(payload.notification_id)
            else:
                failed += 1
                errors[target.user_id] = "FCM delivery returned failure"
        except Exception as exc:
            failed += 1
            errors[target.user_id] = str(exc)
            logger.exception(
                "FCM delivery failed: notification=%s user=%s",
                payload.notification_id,
                target.user_id,
            )

    overall_status = DeliveryStatus.SENT if failed == 0 else DeliveryStatus.FAILED
    if successful > 0 and failed > 0:
        # Partial success — still mark as sent but include errors
        overall_status = DeliveryStatus.SENT

    result = NotificationResult(
        notification_id=payload.notification_id,
        total_targets=len(targets),
        successful=successful,
        failed=failed,
        status=overall_status,
        errors=errors,
    )

    logger.info(
        "Notification delivered: id=%s total=%d ok=%d fail=%d",
        payload.notification_id,
        result.total_targets,
        result.successful,
        result.failed,
    )
    return result


# ── Deadline reminders ───────────────────────────────────────


def schedule_deadline_reminders(
    company_id: str,
) -> list[NotificationPayload]:
    """Generate deadline reminder notifications for a company.

    Produces reminders for recurring Singapore HR compliance deadlines:
    - CPF contribution filing (14th of each month)
    - Work pass renewal (90 days before expiry)
    - Annual IR8A submission (1 March each year)
    - SDL payment (monthly with CPF)

    In production, the actual deadline dates are resolved from the
    company's DataFlow records (work pass expiry dates, filing history).
    This implementation generates reminders relative to today's date.

    Args:
        company_id: Company to generate reminders for.

    Returns:
        List of created NotificationPayload objects.
    """
    today = date.today()
    reminders: list[NotificationPayload] = []

    # ── CPF filing reminder (due 14th of each month) ────────
    cpf_due = date(today.year, today.month, 14)
    if cpf_due < today:
        # Already past this month's deadline — look at next month
        if today.month == 12:
            cpf_due = date(today.year + 1, 1, 14)
        else:
            cpf_due = date(today.year, today.month + 1, 14)

    days_until_cpf = (cpf_due - today).days
    if days_until_cpf <= 7:
        reminders.append(
            create_notification(
                type=NotificationType.DEADLINE_REMINDER,
                title="CPF contributions due soon",
                body=(
                    f"CPF contributions for your employees are due on "
                    f"{cpf_due.strftime('%d %B %Y')}. Late submissions incur "
                    f"interest charges of 1.5% per month."
                ),
                deep_link="/compliance/cpf-filing",
                data={
                    "company_id": company_id,
                    "deadline_type": "cpf_filing",
                    "due_date": cpf_due.isoformat(),
                    "days_remaining": days_until_cpf,
                },
                priority=NotificationPriority.HIGH,
            )
        )

    # ── Work pass renewal reminder (90 days before expiry) ──
    # In production: query DataFlow for employees with work passes
    # expiring within 90 days. Generate one reminder per expiring pass.
    # Placeholder creates a generic reminder for the company.
    work_pass_check_date = today + timedelta(days=90)
    reminders.append(
        create_notification(
            type=NotificationType.DEADLINE_REMINDER,
            title="Review upcoming work pass renewals",
            body=(
                "Check if any employee work passes expire within the next "
                "90 days. Work pass renewal applications should be submitted "
                "at least 2 months before expiry to avoid disruption."
            ),
            deep_link="/compliance/work-passes",
            data={
                "company_id": company_id,
                "deadline_type": "work_pass_renewal",
                "check_horizon_date": work_pass_check_date.isoformat(),
            },
        )
    )

    # ── IR8A annual submission (due 1 March) ────────────────
    ir8a_due = date(today.year, 3, 1)
    if ir8a_due < today:
        ir8a_due = date(today.year + 1, 3, 1)

    days_until_ir8a = (ir8a_due - today).days
    if days_until_ir8a <= 30:
        reminders.append(
            create_notification(
                type=NotificationType.DEADLINE_REMINDER,
                title="IR8A submission deadline approaching",
                body=(
                    f"Annual IR8A employee income forms must be submitted to "
                    f"IRAS by {ir8a_due.strftime('%d %B %Y')}. Ensure all "
                    f"employee earnings data is accurate and complete."
                ),
                deep_link="/compliance/ir8a-submission",
                data={
                    "company_id": company_id,
                    "deadline_type": "ir8a_submission",
                    "due_date": ir8a_due.isoformat(),
                    "days_remaining": days_until_ir8a,
                },
                priority=NotificationPriority.HIGH,
            )
        )

    # ── SDL payment reminder (monthly with CPF) ────────────
    # Skills Development Levy is submitted together with CPF.
    # Only add a separate reminder if the company has 2+ employees.
    sdl_due = cpf_due  # same deadline
    if days_until_cpf <= 7:
        reminders.append(
            create_notification(
                type=NotificationType.DEADLINE_REMINDER,
                title="SDL payment due with CPF",
                body=(
                    f"Skills Development Levy (SDL) is due on "
                    f"{sdl_due.strftime('%d %B %Y')} together with CPF "
                    f"contributions. SDL applies to all employees earning "
                    f"$800+ per month."
                ),
                deep_link="/compliance/sdl-payment",
                data={
                    "company_id": company_id,
                    "deadline_type": "sdl_payment",
                    "due_date": sdl_due.isoformat(),
                },
            )
        )

    logger.info(
        "Generated %d deadline reminders for company %s",
        len(reminders),
        company_id,
    )
    return reminders


# ── History ──────────────────────────────────────────────────


def get_notification_history(
    user_id: str,
    limit: int = 50,
) -> list[NotificationPayload]:
    """Retrieve a user's notification history, most recent first.

    In production, this queries the DataFlow notification delivery log
    joined with the notification payloads table.

    Args:
        user_id: The user whose history to retrieve.
        limit: Maximum number of notifications to return.

    Returns:
        List of NotificationPayload ordered by created_at descending.
    """
    notification_ids = _user_notifications.get(user_id, [])
    # Most recent first
    recent_ids = list(reversed(notification_ids))[:limit]
    payloads: list[NotificationPayload] = []
    for nid in recent_ids:
        payload = _notification_store.get(nid)
        if payload is not None:
            payloads.append(payload)
    return payloads


# ── Test helpers ─────────────────────────────────────────────


def register_target(target: NotificationTarget) -> None:
    """Register a notification target in the in-memory store.

    Used during testing and development. In production, targets are
    resolved dynamically from the DataFlow User model.
    """
    company_targets = _user_registry.setdefault(target.company_id, [])
    # Avoid duplicates
    if not any(t.user_id == target.user_id for t in company_targets):
        company_targets.append(target)


def subscribe_to_provision(user_id: str, provision_id: str) -> None:
    """Subscribe a user to notifications for a specific provision.

    Used during testing. In production, subscriptions are derived from
    the company profile's applicability against provision rules.
    """
    subscribers = _provision_subscriptions.setdefault(provision_id, [])
    if user_id not in subscribers:
        subscribers.append(user_id)


def clear_stores() -> None:
    """Reset all in-memory stores. For testing only."""
    _notification_store.clear()
    _user_notifications.clear()
    _user_registry.clear()
    _provision_subscriptions.clear()
