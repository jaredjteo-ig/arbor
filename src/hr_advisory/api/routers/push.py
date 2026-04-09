"""Web Push subscription management endpoints.

Handles browser push notification subscriptions using the VAPID protocol.
Users subscribe via the browser PushManager API and send the subscription
details to these endpoints. The backend stores subscriptions and uses them
to deliver push notifications (e.g. regulatory alerts).

All endpoints require authentication.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from hr_advisory.api.middleware.rate_limit import check_rate_limit
from hr_advisory.api.middleware.tenant_isolation import get_current_company_id
from pydantic import BaseModel, field_validator

from hr_advisory.api.middleware.auth_middleware import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Request/Response models ──────────────────────────────────


class SubscriptionKeys(BaseModel):
    """Browser push subscription encryption keys."""

    p256dh: str
    auth: str

    @field_validator("p256dh", "auth")
    @classmethod
    def must_be_nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Key must not be empty")
        return v.strip()


class SubscribeRequest(BaseModel):
    """Push subscription from the browser PushManager API."""

    endpoint: str
    keys: SubscriptionKeys

    @field_validator("endpoint")
    @classmethod
    def must_be_https_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith("https://"):
            raise ValueError("Push endpoint must be an HTTPS URL")
        if len(v) > 2048:
            raise ValueError("Push endpoint URL too long (max 2048 characters)")
        return v


class UnsubscribeRequest(BaseModel):
    """Request to remove a push subscription."""

    endpoint: str

    @field_validator("endpoint")
    @classmethod
    def must_be_nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Endpoint must not be empty")
        return v.strip()


class VapidKeyResponse(BaseModel):
    """Public VAPID key for the frontend to use when subscribing."""

    public_key: str | None
    configured: bool


class SubscribeResponse(BaseModel):
    """Response after subscribing to push notifications."""

    message: str
    subscription_id: int | None = None


class UnsubscribeResponse(BaseModel):
    """Response after unsubscribing from push notifications."""

    message: str
    removed: bool


# ── Endpoints ────────────────────────────────────────────────


@router.get("/vapid-key", response_model=VapidKeyResponse)
async def get_vapid_key() -> VapidKeyResponse:
    """Return the public VAPID key for browser push subscription.

    The frontend uses this key with PushManager.subscribe() to register
    for push notifications. This endpoint does not require authentication
    because the key is public.
    """
    from hr_advisory.notifications.web_push import get_vapid_public_key

    public_key = get_vapid_public_key()
    return VapidKeyResponse(
        public_key=public_key,
        configured=public_key is not None,
    )


@router.post("/subscribe", response_model=SubscribeResponse)
async def subscribe_push(
    req: SubscribeRequest,
    user: dict = Depends(get_current_user),
) -> SubscribeResponse:
    """Register a browser push subscription for the current user.

    The frontend calls this after a successful PushManager.subscribe() call,
    passing the subscription endpoint and encryption keys.
    """
    from hr_advisory.notifications.web_push import store_subscription

    user_id = int(user.get("sub", 0))
    company_id = get_current_company_id(user) or 0

    check_rate_limit(
        f"push_subscribe:{user_id}",
        max_requests=10,
        window_seconds=60,
        action_name="push subscribe",
    )

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user identity")

    result = store_subscription(
        user_id=user_id,
        company_id=company_id,
        endpoint=req.endpoint,
        p256dh=req.keys.p256dh,
        auth=req.keys.auth,
    )

    subscription_id = result.get("id") if isinstance(result, dict) else None

    logger.info(
        "Push subscription registered: user=%d endpoint=%s",
        user_id,
        req.endpoint[:60],
    )
    return SubscribeResponse(
        message="Push subscription registered successfully.",
        subscription_id=subscription_id,
    )


@router.post("/unsubscribe", response_model=UnsubscribeResponse)
async def unsubscribe_push(
    req: UnsubscribeRequest,
    user: dict = Depends(get_current_user),
) -> UnsubscribeResponse:
    """Remove a push subscription for the current user.

    Called when the user disables push notifications or the service worker
    subscription is revoked.
    """
    from hr_advisory.notifications.web_push import remove_subscription

    user_id = int(user.get("sub", 0))
    check_rate_limit(
        f"push_unsubscribe:{user_id}",
        max_requests=10,
        window_seconds=60,
        action_name="push unsubscribe",
    )

    user_id = int(user.get("sub", 0))
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid user identity")

    removed = remove_subscription(user_id=user_id, endpoint=req.endpoint)

    if removed:
        logger.info(
            "Push subscription removed: user=%d endpoint=%s",
            user_id,
            req.endpoint[:60],
        )
    else:
        logger.info(
            "Push subscription not found for removal: user=%d endpoint=%s",
            user_id,
            req.endpoint[:60],
        )

    return UnsubscribeResponse(
        message="Push subscription removed." if removed else "No matching subscription found.",
        removed=removed,
    )
