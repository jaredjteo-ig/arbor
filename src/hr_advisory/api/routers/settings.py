"""User settings endpoints.

Handles user preferences (notifications, display, language) and
password changes for authenticated users.

Settings are stored per-user in an in-memory dict for now (will migrate
to DataFlow UserSettings model in a future sprint).  Password change
delegates to AuthService for hash verification and update.
"""

import logging
from copy import deepcopy
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Request

from hr_advisory.api.middleware.auth_middleware import get_current_user
from hr_advisory.config.settings import get_settings
from hr_advisory.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter()

# ── In-memory settings store (keyed by user ID) ────────────────

_settings_lock = Lock()
_user_settings: dict[int, dict] = {}

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
            _user_settings[user_id] = deepcopy(_DEFAULT_SETTINGS)
        return deepcopy(_user_settings[user_id])


def _save_settings_for_user(user_id: int, settings: dict) -> dict:
    """Persist updated settings and return a copy."""
    with _settings_lock:
        _user_settings[user_id] = deepcopy(settings)
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

    # Update the password
    new_hash = auth_service.hash_password(new_password)
    auth_service._update_user(user_id, {"password_hash": new_hash})

    logger.info("Password changed for user_id=%s", user_id)
    return {"message": "Password changed successfully"}
