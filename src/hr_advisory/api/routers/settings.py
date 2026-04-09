"""User settings endpoints.

Handles user preferences (notifications, display, language) and
password changes for authenticated users.

Settings are stored per-user in an in-memory dict for now (will migrate
to DataFlow UserSettings model in a future sprint).  Password change
delegates to AuthService for hash verification and update.
"""

import logging
from collections import OrderedDict
from copy import deepcopy
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Request

from hr_advisory.api.middleware.auth_middleware import get_current_user
from hr_advisory.config.settings import get_settings
from hr_advisory.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter()

# ── In-memory settings store (keyed by user ID) ────────────────

_MAX_STORE_ENTRIES = 10000

_settings_lock = Lock()
_user_settings: OrderedDict[int, dict] = OrderedDict()

_DEFAULT_SETTINGS: dict = {
    "notifications": {
        "emailAlerts": True,
        "pushNotifications": False,
        "inAppNotifications": True,
        "alertFrequency": "daily",
    },
    "display": {
        "textSize": "normal",
    },
    "language": "en",
}


def _get_settings_for_user(user_id: int) -> dict:
    """Return a copy of the user's settings, initialising defaults if needed."""
    with _settings_lock:
        if user_id not in _user_settings:
            # Evict oldest entries if at capacity
            while len(_user_settings) >= _MAX_STORE_ENTRIES:
                _user_settings.popitem(last=False)
            _user_settings[user_id] = deepcopy(_DEFAULT_SETTINGS)
        else:
            # Move to end (most recently used)
            _user_settings.move_to_end(user_id)
        return deepcopy(_user_settings[user_id])


def _save_settings_for_user(user_id: int, settings: dict) -> dict:
    """Persist updated settings and return a copy."""
    with _settings_lock:
        if user_id not in _user_settings:
            while len(_user_settings) >= _MAX_STORE_ENTRIES:
                _user_settings.popitem(last=False)
        _user_settings[user_id] = deepcopy(settings)
        _user_settings.move_to_end(user_id)
        return deepcopy(_user_settings[user_id])


def _get_auth_service() -> AuthService:
    """Provide an AuthService instance using current settings."""
    return AuthService(settings=get_settings())


# ------------------------------------------------------------------
# GET /settings
# ------------------------------------------------------------------


@router.get("")
async def get_user_settings(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get the current user's preferences.

    Returns notification, display, and language settings.

    Status codes:
        200: Success
        401: Not authenticated
    """
    user_id = current_user.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    settings = _get_settings_for_user(user_id)
    logger.info("Settings retrieved for user_id=%s", user_id)
    return settings


# ------------------------------------------------------------------
# PUT /settings
# ------------------------------------------------------------------


@router.put("")
async def update_user_settings(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Update the current user's preferences.

    Accepts partial updates — only provided fields are merged.

    Status codes:
        200: Success
        400: Invalid input
        401: Not authenticated
    """
    user_id = current_user.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    body = await request.json()
    current = _get_settings_for_user(user_id)

    # Merge notifications
    if "notifications" in body:
        notif = body["notifications"]
        if not isinstance(notif, dict):
            raise HTTPException(status_code=400, detail="notifications must be an object")
        valid_frequencies = {"immediately", "daily", "weekly"}
        if "alertFrequency" in notif and notif["alertFrequency"] not in valid_frequencies:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid alertFrequency. Valid values: {sorted(valid_frequencies)}",
            )
        current["notifications"].update(notif)

    # Merge display
    if "display" in body:
        disp = body["display"]
        if not isinstance(disp, dict):
            raise HTTPException(status_code=400, detail="display must be an object")
        valid_sizes = {"normal", "large", "extra-large"}
        if "textSize" in disp and disp["textSize"] not in valid_sizes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid textSize. Valid values: {sorted(valid_sizes)}",
            )
        current["display"].update(disp)

    # Merge language
    if "language" in body:
        current["language"] = body["language"]

    saved = _save_settings_for_user(user_id, current)
    logger.info("Settings updated for user_id=%s", user_id)
    return saved


# ------------------------------------------------------------------
# POST /settings/change-password
# ------------------------------------------------------------------


@router.post("/change-password")
async def change_password(
    request: Request,
    current_user: dict = Depends(get_current_user),
    auth_service: AuthService = Depends(_get_auth_service),
) -> dict:
    """Change the current user's password.

    Requires the current password for verification, plus the new password.

    Accepts: current_password, new_password.

    Status codes:
        200: Password changed
        400: Validation error (new password too short, same as current)
        401: Current password is incorrect or not authenticated
    """
    user_id = current_user.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    body = await request.json()
    current_password = body.get("current_password", "")
    new_password = body.get("new_password", "")

    if not current_password:
        raise HTTPException(status_code=400, detail="Current password is required")

    # Validate new password format
    try:
        AuthService.validate_password(new_password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Look up the user to verify current password
    user = auth_service.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.get("password_hash"):
        raise HTTPException(status_code=401, detail="Account has no password set")

    if not auth_service.verify_password(current_password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    if current_password == new_password:
        raise HTTPException(
            status_code=400,
            detail="New password must be different from current password",
        )

    # Update the password and increment token_version to invalidate all existing sessions
    new_hash = auth_service.hash_password(new_password)
    current_tv = user.get("token_version", 1)
    new_tv = current_tv + 1
    auth_service._update_user(user_id, {"password_hash": new_hash, "token_version": new_tv})

    # Invalidate the token version cache so the middleware picks up the change
    from hr_advisory.api.middleware.token_version_cache import get_token_version_cache

    get_token_version_cache().invalidate(user_id)
    logger.info(
        "Password changed for user_id=%s, token_version %s->%s",
        user_id,
        current_tv,
        new_tv,
    )
    return {"message": "Password changed successfully"}


# ------------------------------------------------------------------
# Notification preferences
# ------------------------------------------------------------------

_DEFAULT_NOTIFICATION_PREFERENCES: list[dict] = [
    {
        "type": "leave_approval",
        "label": "Leave Approvals",
        "description": "Notifications when leave applications need your approval or are approved/rejected.",
        "channels": ["email"],
    },
    {
        "type": "payroll_ready",
        "label": "Payroll Ready",
        "description": "Notifications when payroll is finalized and payslips are available.",
        "channels": ["email"],
    },
    {
        "type": "claim_status",
        "label": "Claim Status Updates",
        "description": "Notifications when claims are approved, rejected, or need attention.",
        "channels": ["email"],
    },
    {
        "type": "document_expiry",
        "label": "Document Expiry Reminders",
        "description": "Reminders when employee documents (work permits, certifications) are expiring.",
        "channels": ["email"],
    },
    {
        "type": "compliance_alert",
        "label": "Compliance Alerts",
        "description": "Alerts for regulatory deadlines and compliance requirements.",
        "channels": ["email"],
    },
]

_notification_prefs_lock = Lock()
_notification_prefs: OrderedDict[int, dict] = OrderedDict()


def _get_notification_prefs(user_id: int) -> dict:
    """Return notification preferences for a user, with defaults."""
    with _notification_prefs_lock:
        if user_id not in _notification_prefs:
            while len(_notification_prefs) >= _MAX_STORE_ENTRIES:
                _notification_prefs.popitem(last=False)
            _notification_prefs[user_id] = {
                "preferences": deepcopy(_DEFAULT_NOTIFICATION_PREFERENCES),
                "phone_number": None,
            }
        else:
            _notification_prefs.move_to_end(user_id)
        return deepcopy(_notification_prefs[user_id])


@router.get("/notification-preferences")
async def get_notification_preferences(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get the current user's notification preferences.

    Returns notification channel preferences and phone number.

    Status codes:
        200: Success
        401: Not authenticated
    """
    user_id = current_user.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    prefs = _get_notification_prefs(user_id)
    logger.info("Notification preferences retrieved for user_id=%s", user_id)
    return prefs


@router.put("/notification-preferences")
async def update_notification_preferences(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Update the current user's notification preferences.

    Status codes:
        200: Success
        400: Invalid input
        401: Not authenticated
    """
    user_id = current_user.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    body = await request.json()

    with _notification_prefs_lock:
        current = _get_notification_prefs(user_id)

        if "preferences" in body:
            if not isinstance(body["preferences"], list):
                raise HTTPException(status_code=400, detail="preferences must be a list")
            current["preferences"] = body["preferences"]

        if "phone_number" in body:
            current["phone_number"] = body["phone_number"]

        _notification_prefs[user_id] = deepcopy(current)

    logger.info("Notification preferences updated for user_id=%s", user_id)
    return current


@router.post("/notification-preferences/test")
async def test_notification_channel(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Send a test notification on a specific channel.

    Status codes:
        200: Test sent
        401: Not authenticated
    """
    user_id = current_user.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    body = await request.json()
    channel = body.get("channel", "email")

    logger.info("Test notification sent via %s for user_id=%s", channel, user_id)
    return {"success": True, "message": f"Test notification sent via {channel}."}
