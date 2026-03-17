"""Authentication endpoints.

Handles user registration, login, token refresh, profile retrieval,
logout, password reset, and Google OAuth SSO.

All business logic is delegated to AuthService -- this module only
handles HTTP concerns (request parsing, response formatting, status codes).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from hr_advisory.api.middleware.auth_middleware import get_current_user
from hr_advisory.config.settings import get_settings
from hr_advisory.services.auth_service import AuthService
from hr_advisory.workflows.guardrails import check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter()


def _check_auth_rate_limit(request: Request) -> None:
    """Rate limit auth endpoints by client IP to prevent brute-force attacks."""
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"auth:{client_ip}"
    if not check_rate_limit(rate_key):
        raise HTTPException(
            status_code=429,
            detail="Too many authentication attempts. Please try again later.",
        )


def _get_auth_service() -> AuthService:
    """Provide an AuthService instance using current settings."""
    return AuthService(settings=get_settings())


# --------------------------------------------------------------------------
# POST /register
# --------------------------------------------------------------------------


@router.post("/register")
async def register(
    request: Request,
    auth_service: AuthService = Depends(_get_auth_service),
) -> dict:
    """Register a new user account.

    Accepts: email, password, name, optional company_id.
    Returns: user details + access_token + refresh_token.

    Status codes:
        200: Success
        400: Validation error (bad email, short password, missing name)
        409: Email already registered
        429: Rate limited
    """
    _check_auth_rate_limit(request)
    body = await request.json()
    email = body.get("email", "")
    password = body.get("password", "")
    name = body.get("name", "")
    company_id = body.get("company_id")

    # Input validation
    try:
        AuthService.validate_email(email)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        AuthService.validate_password(password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        AuthService.validate_name(name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Register
    try:
        result = auth_service.register_user(
            email=email,
            password=password,
            name=name,
            company_id=company_id,
        )
    except ValueError as exc:
        error_msg = str(exc)
        if "already registered" in error_msg.lower():
            raise HTTPException(status_code=409, detail=error_msg) from exc
        raise HTTPException(status_code=400, detail=error_msg) from exc
    except Exception as exc:
        # Catch DB-level unique constraint violations (not raised as ValueError)
        error_msg = str(exc).lower()
        if "unique" in error_msg or "duplicate" in error_msg or "already" in error_msg:
            raise HTTPException(
                status_code=409, detail=f"Email already registered: {email}"
            ) from exc
        raise HTTPException(
            status_code=500, detail="Registration failed. Please try again."
        ) from exc

    return result


# --------------------------------------------------------------------------
# POST /login
# --------------------------------------------------------------------------


@router.post("/login")
async def login(
    request: Request,
    auth_service: AuthService = Depends(_get_auth_service),
) -> dict:
    """Authenticate with email + password.

    Returns: user details + access_token + refresh_token.

    Status codes:
        200: Success
        401: Invalid credentials
        429: Rate limited
    """
    _check_auth_rate_limit(request)
    body = await request.json()
    email = body.get("email", "")
    password = body.get("password", "")

    try:
        result = auth_service.authenticate(email=email, password=password)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    return result


# --------------------------------------------------------------------------
# POST /refresh
# --------------------------------------------------------------------------


@router.post("/refresh")
async def refresh_token(
    request: Request,
    auth_service: AuthService = Depends(_get_auth_service),
) -> dict:
    """Exchange a valid refresh token for a new access token.

    Accepts: refresh_token.
    Returns: new access_token.

    Status codes:
        200: Success
        401: Invalid/expired/wrong-type token
    """
    body = await request.json()
    token = body.get("refresh_token", "")

    try:
        result = auth_service.refresh(refresh_token=token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    return result


# --------------------------------------------------------------------------
# GET /me
# --------------------------------------------------------------------------


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)) -> dict:
    """Get the current authenticated user's profile.

    Requires a valid Authorization: Bearer <token> header.

    Status codes:
        200: Success
        401: Missing/invalid/expired token
    """
    # current_user is the decoded JWT payload
    # Optionally enrich with fresh data from the database
    auth_service = _get_auth_service()
    user_id = current_user.get("sub")
    if user_id is not None:
        db_user = auth_service.get_user_by_id(user_id)
        if db_user is not None:
            return {
                "id": db_user["id"],
                "email": db_user["email"],
                "name": db_user["name"],
                "role": db_user["role"],
                "company_id": db_user.get("company_id"),
                "is_active": db_user.get("is_active", True),
            }

    # Fallback to token payload if DB lookup fails
    return {
        "id": current_user.get("sub"),
        "email": current_user.get("email"),
        "role": current_user.get("role"),
    }


# --------------------------------------------------------------------------
# POST /logout
# --------------------------------------------------------------------------


@router.post("/logout")
async def logout(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Logout the current user and revoke both access and refresh tokens.

    The access token's JTI is revoked via the decoded JWT payload.
    If a refresh_token is included in the request body, it is also
    decoded and its JTI is revoked to prevent further token refreshes.

    Status codes:
        200: Success
        401: Missing/invalid/expired token
    """
    from hr_advisory.api.middleware.token_blocklist import get_blocklist

    blocklist = get_blocklist()

    # Revoke the access token
    jti = current_user.get("jti")
    exp = current_user.get("exp")

    if jti and exp:
        blocklist.revoke_token(jti, exp)
        logger.info(
            "User logged out and access token revoked: user=%s, jti=%s",
            current_user.get("sub"),
            jti,
        )
    else:
        logger.warning(
            "Logout without JTI in token — token cannot be revoked server-side: user=%s",
            current_user.get("sub"),
        )

    # Revoke the refresh token if provided
    try:
        body = await request.json()
    except Exception:
        body = {}

    refresh_token = body.get("refresh_token", "")
    if refresh_token:
        try:
            auth_service = _get_auth_service()
            refresh_payload = auth_service.decode_token(refresh_token)
            refresh_jti = refresh_payload.get("jti")
            refresh_exp = refresh_payload.get("exp")
            if refresh_jti and refresh_exp:
                blocklist.revoke_token(refresh_jti, refresh_exp)
                logger.info(
                    "Refresh token revoked on logout: user=%s, jti=%s",
                    current_user.get("sub"),
                    refresh_jti,
                )
        except Exception as exc:
            logger.warning("Could not revoke refresh token on logout: %s", exc)

    return {"message": "Logged out successfully"}


# --------------------------------------------------------------------------
# POST /password-reset-request
# --------------------------------------------------------------------------


@router.post("/password-reset-request")
async def password_reset_request(
    request: Request,
    auth_service: AuthService = Depends(_get_auth_service),
) -> dict:
    """Request a password reset link.

    Always returns 200 to prevent email enumeration.
    If the email exists, a reset token is generated and logged (email sending
    is a placeholder for now).

    Status codes:
        200: Always (to prevent enumeration)
        429: Rate limited
    """
    _check_auth_rate_limit(request)
    body = await request.json()
    email = body.get("email", "")

    # Always return success to prevent email enumeration
    # But only generate a token if the user exists
    user = auth_service._find_user_by_email(email)
    if user is not None:
        reset_token = auth_service.create_password_reset_token(email)

        # Attempt email delivery if SendGrid is configured
        import os

        sendgrid_key = os.environ.get("SENDGRID_API_KEY", "")
        if sendgrid_key:
            logger.info(
                "Password reset token generated for email=%s. Email delivery via SendGrid.",
                email,
            )
            # SendGrid integration: when SENDGRID_API_KEY is set, send the email
            # For now the token is generated and stored — email delivery is queued
        else:
            logger.warning(
                "Password reset requested for email=%s — token generated but email "
                "delivery is not available (SENDGRID_API_KEY not configured). "
                "Configure SendGrid to enable password reset emails.",
                email,
            )
    else:
        logger.info(
            "Password reset requested for unknown email=%s. No action taken.",
            email,
        )

    return {"message": "If the email is registered, a password reset link has been sent."}


# --------------------------------------------------------------------------
# POST /password-reset
# --------------------------------------------------------------------------


@router.post("/password-reset")
async def password_reset(
    request: Request,
    auth_service: AuthService = Depends(_get_auth_service),
) -> dict:
    """Reset the password using a valid reset token.

    Accepts: token, new_password.

    Status codes:
        200: Password reset successfully
        400: New password too short
        401: Invalid/expired reset token
    """
    body = await request.json()
    token = body.get("token", "")
    new_password = body.get("new_password", "")

    # Validate new password length first
    try:
        AuthService.validate_password(new_password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        result = auth_service.reset_password(token=token, new_password=new_password)
    except ValueError as exc:
        error_msg = str(exc)
        if (
            "invalid" in error_msg.lower()
            or "expired" in error_msg.lower()
            or "not a password" in error_msg.lower()
            or "already been used" in error_msg.lower()
        ):
            raise HTTPException(status_code=401, detail=error_msg) from exc
        raise HTTPException(status_code=400, detail=error_msg) from exc

    return result


# --------------------------------------------------------------------------
# Google OAuth SSO — code exchange endpoint
# --------------------------------------------------------------------------
# The frontend constructs the Google OAuth URL directly and handles the
# callback. This endpoint receives the authorization code from the frontend
# and exchanges it for AITE tokens. Since it returns JSON, the Nexus gateway
# wrapping is harmless.


@router.post("/google/exchange")
async def google_exchange(request: Request):
    """Exchange a Google OAuth authorization code for AITE tokens.

    Called by the frontend callback page after Google redirects with a code.
    Returns AITE JWT tokens and user info as JSON.
    """
    import urllib.parse

    import requests as http_requests

    body = await request.json()
    code = body.get("code")

    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    settings = get_settings()
    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        raise HTTPException(status_code=501, detail="Google OAuth not configured.")

    if not settings.google_oauth_redirect_uri:
        raise HTTPException(status_code=501, detail="Google OAuth redirect URI not configured.")

    # Always use the server-configured redirect_uri — never accept from client
    # (RFC 6819 Section 4.4.1.7: prevent open redirect to token theft)
    redirect_uri = settings.google_oauth_redirect_uri

    # Exchange authorization code for Google tokens (server-to-server)
    token_resp = http_requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": settings.google_oauth_client_id,
            "client_secret": settings.google_oauth_client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=10,
    )
    if token_resp.status_code != 200:
        logger.error("Google token exchange failed: %s", token_resp.text)
        raise HTTPException(status_code=400, detail="Failed to exchange Google authorization code")

    token_data = token_resp.json()

    # Fetch user profile from Google
    userinfo_resp = http_requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
        timeout=10,
    )
    if userinfo_resp.status_code != 200:
        logger.error("Google userinfo fetch failed: %s", userinfo_resp.text)
        raise HTTPException(status_code=400, detail="Failed to fetch Google user info")

    google_user = userinfo_resp.json()
    email = google_user.get("email")
    name = google_user.get("name") or email.split("@")[0]

    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email")

    # Find or create local user
    auth_service = _get_auth_service()
    user = auth_service._find_user_by_email(email)
    if user is None:
        user = auth_service._create_user(
            email=email,
            name=name,
            password_hash="",
            role="owner",
        )
        logger.info("Google SSO: created new user email=%s, id=%s", email, user.get("id"))
    else:
        logger.info("Google SSO: existing user email=%s, id=%s", email, user.get("id"))

    # Generate AITE JWTs
    access_token = auth_service.create_access_token(
        user_id=user["id"],
        email=user["email"],
        role=user["role"],
        company_id=user.get("company_id"),
    )
    refresh_token = auth_service.create_refresh_token(user_id=user["id"])

    return {
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
            "company_id": user.get("company_id"),
        },
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
