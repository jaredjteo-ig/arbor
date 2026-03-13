"""Push Notification System for AITE HR Advisory (T056).

Delivers proactive notifications to users about regulatory updates,
compliance deadlines, correction notices, and system announcements.

Notification delivery uses FCM (Firebase Cloud Messaging) in production.
User targeting resolves affected users by company, domain, or provision.
"""

from hr_advisory.notifications.push_service import (
    NotificationPriority,
    NotificationType,
    NotificationPayload,
    NotificationResult,
    NotificationTarget,
    create_notification,
    get_notification_history,
    schedule_deadline_reminders,
    send_notification,
    target_by_company,
    target_by_provision,
)

__all__ = [
    "NotificationPriority",
    "NotificationType",
    "NotificationPayload",
    "NotificationResult",
    "NotificationTarget",
    "create_notification",
    "get_notification_history",
    "schedule_deadline_reminders",
    "send_notification",
    "target_by_company",
    "target_by_provision",
]
