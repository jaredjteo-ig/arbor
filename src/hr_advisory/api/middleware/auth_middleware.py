"""FastAPI dependencies for authentication and role-based access control.

These are injected into route handlers via ``Depends()``.
The middleware never accesses the database directly -- it delegates
to AuthService for token decoding and the token blocklist for revocation checks.
"""

import logging
from typing import Callable

from fastapi import Depends, HTTPException, Request

from hr_advisory.api.middleware.token_blocklist import get_blocklist
from hr_advisory.config.settings import get_settings
from hr_advisory.services.auth_service import AuthService

logger = logging.getLogger(__name__)


def _get_auth_service() -> AuthService:
    """Provide an AuthService instance using current settings."""
    return AuthService(settings=get_settings())


async def get_current_user(
    request: Request,
    auth_service: AuthService = Depends(_get_auth_service),
) -> dict:
    """Extract and validate JWT from the Authorization header.

    Returns the decoded user payload dict on success.
    Raises 401 if the token is missing, malformed, invalid, or revoked.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        logger.warning("Missing Authorization header on %s %s", request.method, request.url.path)
        raise HTTPException(status_code=401, detail="Missing authorization header")

    parts = auth_header.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        logger.warning("Malformed Authorization header: scheme=%s", parts[0] if parts else "empty")
        raise HTTPException(
            status_code=401, detail="Invalid authorization scheme — expected 'Bearer <token>'"
        )

    token = parts[1]
    try:
        payload = auth_service.decode_token(token)
    except Exception as exc:
        logger.warning("Token validation failed: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc

    # Check if the token has been revoked (server-side blocklist)
    jti = payload.get("jti")
    if jti:
        blocklist = get_blocklist()
        if blocklist.is_revoked(jti):
            logger.warning(
                "Revoked token used: jti=%s, user=%s, path=%s",
                jti,
                payload.get("sub"),
                request.url.path,
            )
            raise HTTPException(status_code=401, detail="Token has been revoked")

    # Check token version — instant invalidation on termination/password change
    tv = payload.get("tv")
    user_id_str = payload.get("sub")
    if tv is not None and user_id_str is not None:
        try:
            uid = int(user_id_str) if isinstance(user_id_str, str) else user_id_str
            from hr_advisory.api.middleware.token_version_cache import get_token_version_cache

            cache = get_token_version_cache()
            current_tv = cache.get_or_fetch(uid)
            if tv != current_tv:
                logger.warning(
                    "Token version mismatch: token tv=%s, current tv=%s, user=%s, path=%s",
                    tv,
                    current_tv,
                    uid,
                    request.url.path,
                )
                raise HTTPException(status_code=401, detail="Token has been invalidated")
        except (ValueError, TypeError):
            pass  # Non-integer user_id, skip version check

    return payload


async def get_current_user_optional(
    request: Request,
    auth_service: AuthService = Depends(_get_auth_service),
) -> dict | None:
    """Like get_current_user but returns None for unauthenticated requests.

    Used by routes that change behaviour based on role but still serve a
    sensible default to anonymous callers (e.g. role-aware help content).
    Any token-validation failure is also treated as anonymous rather than
    401 so the endpoint stays public.
    """
    if not request.headers.get("Authorization"):
        return None
    try:
        return await get_current_user(request, auth_service=auth_service)
    except HTTPException:
        return None


def require_role(*allowed_roles: str) -> Callable:
    """Role-based access control dependency factory.

    Usage in a route::

        @router.get("/admin-only")
        async def admin_view(user: dict = Depends(require_role("owner", "hr_manager"))):
            ...

    Returns 403 if the user's role is not in *allowed_roles*.
    """

    async def _role_checker(
        current_user: dict = Depends(get_current_user),
    ) -> dict:
        user_role = current_user.get("role")
        if user_role not in allowed_roles:
            logger.warning(
                "Access denied: user role=%s, required one of %s",
                user_role,
                allowed_roles,
            )
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions to access this resource.",
            )
        return current_user

    return _role_checker
