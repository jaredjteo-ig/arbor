"""Web Push notification service using VAPID.

Sends browser push notifications via the Web Push protocol.
No Firebase or third-party push service required -- only standard
VAPID-authenticated Web Push (RFC 8291 / RFC 8292).

VAPID keys must be configured via environment variables:
  - VAPID_PUBLIC_KEY  (base64url-encoded P-256 public key)
  - VAPID_PRIVATE_KEY (base64url-encoded P-256 private key)
  - VAPID_SUBJECT     (e.g. mailto:admin@example.com)

If pywebpush is installed, actual push delivery is used.
Otherwise, delivery is logged but skipped.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Detect pywebpush at import time (optional dependency)
try:
    from pywebpush import webpush, WebPushException  # type: ignore[import-untyped]

    HAS_WEBPUSH = True
except ImportError:
    HAS_WEBPUSH = False
    logger.info(
        "pywebpush not installed -- Web Push delivery will be logged but not sent. "
        "Install with: pip install pywebpush"
    )


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------


def get_vapid_public_key() -> str | None:
    """Return the VAPID public key from environment, or None if not configured."""
    return os.environ.get("VAPID_PUBLIC_KEY")


def get_vapid_private_key() -> str | None:
    """Return the VAPID private key from environment, or None if not configured."""
    return os.environ.get("VAPID_PRIVATE_KEY")


def get_vapid_subject() -> str:
    """Return the VAPID subject claim (mailto: or https: URL)."""
    return os.environ.get("VAPID_SUBJECT", "mailto:admin@arbor.example.com")


def is_web_push_configured() -> bool:
    """Return True if VAPID keys are present and pywebpush is available."""
    return bool(get_vapid_public_key() and get_vapid_private_key() and HAS_WEBPUSH)


# ---------------------------------------------------------------------------
# Subscription management (via DataFlow)
# ---------------------------------------------------------------------------


def store_subscription(
    user_id: int,
    company_id: int,
    endpoint: str,
    p256dh: str,
    auth: str,
) -> dict[str, Any]:
    """Persist a push subscription for a user.

    If a subscription with the same endpoint already exists for this user,
    it is updated rather than duplicated.
    """
    from hr_advisory.services import dataflow_crud

    # Check for existing subscription with same endpoint
    existing = dataflow_crud.list_records(
        "PushSubscription",
        {"user_id": user_id, "endpoint": endpoint},
    )

    if existing:
        # Update the existing subscription (keys may have rotated)
        record = existing[0]
        return dataflow_crud.update(
            "PushSubscription",
            record["id"],
            {"p256dh": p256dh, "auth": auth, "is_active": True},
        )

    # Create new subscription
    return dataflow_crud.create(
        "PushSubscription",
        {
            "user_id": user_id,
            "company_id": company_id,
            "endpoint": endpoint,
            "p256dh": p256dh,
            "auth": auth,
            "is_active": True,
        },
    )


def remove_subscription(user_id: int, endpoint: str) -> bool:
    """Deactivate a push subscription by endpoint.

    Returns True if a subscription was found and deactivated.
    """
    from hr_advisory.services import dataflow_crud

    existing = dataflow_crud.list_records(
        "PushSubscription",
        {"user_id": user_id, "endpoint": endpoint},
    )

    if not existing:
        return False

    for record in existing:
        dataflow_crud.update("PushSubscription", record["id"], {"is_active": False})

    return True


def get_active_subscriptions(
    company_id: int | None = None,
    user_ids: list[int] | None = None,
) -> list[dict[str, Any]]:
    """Retrieve active push subscriptions, optionally filtered.

    Args:
        company_id: If set, return subscriptions for this company only.
        user_ids: If set, return subscriptions for these specific users.

    Returns:
        List of PushSubscription dicts with endpoint, p256dh, auth, etc.
    """
    from hr_advisory.services import dataflow_crud

    filter_dict: dict[str, Any] = {"is_active": True}
    if company_id is not None:
        filter_dict["company_id"] = company_id

    all_subs = dataflow_crud.list_records("PushSubscription", filter_dict)

    if user_ids is not None:
        user_id_set = set(user_ids)
        all_subs = [s for s in all_subs if s.get("user_id") in user_id_set]

    return all_subs


# ---------------------------------------------------------------------------
# Push delivery
# ---------------------------------------------------------------------------


def _send_single_push(
    subscription_info: dict[str, Any],
    payload: dict[str, Any],
) -> bool:
    """Send a single Web Push notification.

    Args:
        subscription_info: Dict with 'endpoint' and 'keys' (p256dh, auth).
        payload: JSON-serialisable notification payload.

    Returns:
        True if delivery succeeded, False otherwise.
    """
    if not HAS_WEBPUSH:
        logger.info(
            "Web Push delivery skipped (pywebpush not installed): endpoint=%s",
            subscription_info.get("endpoint", "?")[:60],
        )
        return False

    private_key = get_vapid_private_key()
    if not private_key:
        logger.warning("VAPID_PRIVATE_KEY not configured -- cannot send push")
        return False

    vapid_claims = {
        "sub": get_vapid_subject(),
    }

    try:
        webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload),
            vapid_private_key=private_key,
            vapid_claims=vapid_claims,
            timeout=10,
        )
        logger.info(
            "Web Push sent: endpoint=%s title=%r",
            subscription_info.get("endpoint", "?")[:60],
            payload.get("title", "?"),
        )
        return True
    except WebPushException as exc:
        status_code = getattr(exc, "response", None)
        if status_code is not None:
            status_code = getattr(status_code, "status_code", None)

        if status_code == 410:
            # 410 Gone -- subscription expired, mark inactive
            logger.info(
                "Push subscription expired (410 Gone): endpoint=%s",
                subscription_info.get("endpoint", "?")[:60],
            )
            _deactivate_subscription_by_endpoint(
                subscription_info.get("endpoint", "")
            )
            return False

        logger.warning(
            "Web Push delivery failed: endpoint=%s status=%s error=%s",
            subscription_info.get("endpoint", "?")[:60],
            status_code,
            exc,
        )
        return False
    except Exception as exc:
        logger.warning(
            "Web Push delivery error: endpoint=%s error=%s",
            subscription_info.get("endpoint", "?")[:60],
            exc,
        )
        return False


def _deactivate_subscription_by_endpoint(endpoint: str) -> None:
    """Mark all subscriptions with the given endpoint as inactive."""
    from hr_advisory.services import dataflow_crud

    subs = dataflow_crud.list_records(
        "PushSubscription",
        {"endpoint": endpoint, "is_active": True},
    )
    for sub in subs:
        dataflow_crud.update("PushSubscription", sub["id"], {"is_active": False})


def send_push_to_company(
    company_id: int,
    title: str,
    body: str,
    url: str = "/alerts",
    data: dict[str, Any] | None = None,
) -> dict[str, int]:
    """Send a push notification to all subscribed users in a company.

    Args:
        company_id: Target company.
        title: Notification title.
        body: Notification body text.
        url: Deep link URL to open on click.
        data: Additional JSON data for the notification.

    Returns:
        Dict with 'total', 'sent', 'failed' counts.
    """
    subscriptions = get_active_subscriptions(company_id=company_id)

    if not subscriptions:
        logger.info(
            "No active push subscriptions for company %d -- skipping",
            company_id,
        )
        return {"total": 0, "sent": 0, "failed": 0}

    payload = {
        "title": title,
        "body": body,
        "url": url,
        **(data or {}),
    }

    sent = 0
    failed = 0

    for sub in subscriptions:
        subscription_info = {
            "endpoint": sub["endpoint"],
            "keys": {
                "p256dh": sub["p256dh"],
                "auth": sub["auth"],
            },
        }
        if _send_single_push(subscription_info, payload):
            sent += 1
        else:
            failed += 1

    logger.info(
        "Web Push batch for company %d: total=%d sent=%d failed=%d",
        company_id,
        len(subscriptions),
        sent,
        failed,
    )
    return {"total": len(subscriptions), "sent": sent, "failed": failed}


def send_push_to_all_companies(
    title: str,
    body: str,
    url: str = "/alerts",
    data: dict[str, Any] | None = None,
) -> dict[str, int]:
    """Send a push notification to all subscribed users across all companies.

    Used for platform-wide announcements (e.g. regulatory updates).

    Returns:
        Aggregate dict with 'total', 'sent', 'failed' counts.
    """
    subscriptions = get_active_subscriptions()

    if not subscriptions:
        logger.info("No active push subscriptions -- skipping broadcast")
        return {"total": 0, "sent": 0, "failed": 0}

    payload = {
        "title": title,
        "body": body,
        "url": url,
        **(data or {}),
    }

    sent = 0
    failed = 0

    for sub in subscriptions:
        subscription_info = {
            "endpoint": sub["endpoint"],
            "keys": {
                "p256dh": sub["p256dh"],
                "auth": sub["auth"],
            },
        }
        if _send_single_push(subscription_info, payload):
            sent += 1
        else:
            failed += 1

    logger.info(
        "Web Push broadcast: total=%d sent=%d failed=%d",
        len(subscriptions),
        sent,
        failed,
    )
    return {"total": len(subscriptions), "sent": sent, "failed": failed}
