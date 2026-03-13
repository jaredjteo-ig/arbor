# T056 — Push Notifications

**Status**: Completed
**Date**: 2026-03-12

## What was built

**Notification Taxonomy**:

- `NotificationType` enum (REGULATORY_UPDATE, DEADLINE_REMINDER, COMPLIANCE_ALERT, ADVISORY_FOLLOWUP, SYSTEM_UPDATE)

**Data Models**:

- `NotificationPayload` dataclass with notification type, title, body, data payload, priority, and scheduling metadata
- `NotificationTarget` dataclass for targeting by company, user, or topic subscription
- `NotificationResult` dataclass with delivery status, success/failure counts, and error details

**Public API**:

- `create_notification()` — constructs a notification payload with type-specific defaults
- `target_by_company()` — creates a notification target for all users within a company
- `send_notification()` — dispatches notification to targets via FCM integration placeholder
- `schedule_deadline_reminders()` — schedules recurring reminders for CPF submission deadlines (14th of month) and work pass renewal windows (60 days before expiry)

**FCM Integration**:

- Firebase Cloud Messaging integration placeholder with proper async signature for production deployment

## Files

- `src/hr_advisory/notifications/push_service.py` — push notification service module
- `src/hr_advisory/notifications/__init__.py` — package init
