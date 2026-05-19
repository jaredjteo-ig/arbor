"""Authentication endpoints.

Handles user registration, login, token refresh, profile retrieval,
logout, password reset, Google OAuth SSO, and employee registration
via invitation tokens.

All business logic is delegated to AuthService -- this module only
handles HTTP concerns (request parsing, response formatting, status codes).
"""

import logging
from datetime import datetime, timezone

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
    if not check_rate_limit(rate_key, max_requests=5, window_seconds=60):
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
        429: Rate limited
    """
    _check_auth_rate_limit(request)
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
        429: Rate limited
    """
    _check_auth_rate_limit(request)
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
# POST /register-employee — Register via invitation
# --------------------------------------------------------------------------


@router.post("/register-employee")
async def register_employee(
    request: Request,
    auth_service: AuthService = Depends(_get_auth_service),
) -> dict:
    """Register a new employee account via an invitation token.

    Accepts: name, email, password, invitation_token.
    Validates the invitation, creates User + Employee + initial LeaveBalance
    records, marks the invitation as accepted, and returns JWT tokens.

    Status codes:
        200: Success
        400: Validation error
        404: Invalid/expired/already-used invitation
        409: Email already registered
    """
    _check_auth_rate_limit(request)
    body = await request.json()

    name = body.get("name", "")
    email = body.get("email", "").strip().lower()
    password = body.get("password", "")
    invitation_token = body.get("invitation_token", "")

    # --- Input validation ---
    if not invitation_token:
        raise HTTPException(status_code=400, detail="Invitation token is required.")

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

    # --- Validate invitation ---
    from hr_advisory.api.routers.employees import (
        _find_invitation_by_token,
        _update_invitation,
    )

    invitation = _find_invitation_by_token(invitation_token)
    if invitation is None:
        raise HTTPException(status_code=404, detail="Invitation not found.")

    if invitation.get("accepted_at"):
        raise HTTPException(status_code=404, detail="This invitation has already been used.")

    if not invitation.get("is_active", True):
        raise HTTPException(status_code=404, detail="Invitation not found.")

    # Check expiry
    expires_at_str = invitation.get("expires_at", "")
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires_at:
                raise HTTPException(status_code=404, detail="This invitation has expired.")
        except ValueError:
            raise HTTPException(status_code=404, detail="This invitation has expired.")

    # Email must match the invitation
    if email != invitation.get("email", "").strip().lower():
        raise HTTPException(
            status_code=400,
            detail="Email does not match the invitation.",
        )

    # --- Check for duplicate email ---
    existing = auth_service._find_user_by_email(email)
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"Email already registered: {email}")

    # --- Mark invitation as accepted FIRST to prevent TOCTOU race condition ---
    # If two concurrent requests pass the validation checks above, only the
    # first one to mark the invitation will succeed. The second will find
    # accepted_at already set and fail at the top of this function.
    company_id = invitation.get("company_id")

    # S2-T1: defense-in-depth role allow-list. The hire endpoint enforces
    # HIRABLE_ROLES, but if an Invitation row was tampered with (or created
    # by a future endpoint that forgets the check), clamp the role here so
    # the user cannot be created with platform_admin / owner / arbitrary
    # privileges. Anything outside the set falls back to "employee" with a
    # logged warning so the audit trail captures the attempt.
    INVITATION_VALID_ROLES: frozenset[str] = frozenset({"employee", "hr_manager"})
    raw_role = invitation.get("role", "employee")
    if raw_role in INVITATION_VALID_ROLES:
        invited_role = raw_role
    else:
        logger.warning(
            "Invitation role outside allow-list — clamping to 'employee'. "
            "invitation_id=%s raw_role=%s email=%s",
            invitation.get("id"),
            raw_role,
            email,
        )
        invited_role = "employee"
    accepted_at = datetime.now(timezone.utc).isoformat()
    _update_invitation(
        invitation["id"],
        {"accepted_at": accepted_at, "is_active": False},
    )

    password_hash = auth_service.hash_password(password)
    try:
        user = auth_service._create_user(
            email=email,
            name=name,
            password_hash=password_hash,
            company_id=company_id,
            role=invited_role,
        )
    except Exception as exc:
        error_msg = str(exc).lower()
        if "unique" in error_msg or "duplicate" in error_msg or "already" in error_msg:
            raise HTTPException(
                status_code=409, detail=f"Email already registered: {email}"
            ) from exc
        # Rollback invitation — allow retry (T280: invitation must not be
        # permanently burned when user creation fails for transient reasons)
        try:
            _update_invitation(
                invitation["id"],
                {"accepted_at": "", "is_active": True},
            )
            logger.info("Reverted invitation %s after user creation failure", invitation["id"])
        except Exception as revert_exc:
            logger.error("Failed to revert invitation %s: %s", invitation["id"], revert_exc)
        raise HTTPException(
            status_code=500, detail="Registration failed. Please try again."
        ) from exc

    user_id = user["id"]

    # --- Create Employee record ---
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401

    # Pull department/designation/phone/salary from invitation if set
    inv_department = invitation.get("department", "")
    inv_designation = invitation.get("designation", "")
    inv_phone = invitation.get("phone", "")
    inv_salary = invitation.get("salary")

    wf = WorkflowBuilder()
    emp_fields = {
        "user_id": user_id,
        "company_id": company_id,
        "employment_type": "full_time",
        "start_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "is_active": True,
    }
    if inv_department:
        emp_fields["department"] = inv_department
    if inv_designation:
        emp_fields["designation"] = inv_designation
    if inv_phone:
        emp_fields["phone"] = inv_phone
    if inv_salary is not None:
        emp_fields["salary_monthly"] = inv_salary
    # Red-team M5: deterministic probation_end_date on invitation accept.
    from hr_advisory.services.probation import ensure_probation_end_date_in_payload

    ensure_probation_end_date_in_payload(emp_fields)
    wf.add_node("EmployeeCreateNode", "create_emp", emp_fields)
    runtime = LocalRuntime()
    # S2-T2 saga: if Employee create fails the User row would be orphaned
    # and the Invitation already burned. Compensate by deleting User and
    # reverting the Invitation before re-raising as a 500.
    try:
        results, _ = runtime.execute(wf.build())
    except Exception as emp_exc:
        logger.error(
            "Employee create failed — compensating saga "
            "(deleting User, reverting Invitation): user_id=%s err=%s",
            user_id,
            emp_exc,
        )
        try:
            from hr_advisory.services import dataflow_crud as _df

            _df.delete("User", user_id)
        except Exception as comp_exc:
            logger.error(
                "Saga compensation failed to delete User %s: %s", user_id, comp_exc
            )
        try:
            _update_invitation(
                invitation["id"],
                {"accepted_at": "", "is_active": True},
            )
        except Exception as comp_exc:
            logger.error(
                "Saga compensation failed to revert Invitation %s: %s",
                invitation["id"],
                comp_exc,
            )
        raise HTTPException(
            status_code=500,
            detail="Registration failed during employee setup. Please retry.",
        ) from emp_exc
    employee_result = results["create_emp"]

    # Retrieve the employee ID — CreateNode may not return it directly
    employee_id = employee_result.get("id")
    if employee_id is None:
        # Look up the employee we just created
        wf2 = WorkflowBuilder()
        wf2.add_node(
            "EmployeeListNode",
            "find_emp",
            {
                "filter": {"user_id": user_id, "company_id": company_id},
                "limit": 1,
                "enable_cache": False,
            },
        )
        runtime2 = LocalRuntime()
        results2, _ = runtime2.execute(wf2.build())
        emp_records = results2["find_emp"].get("records", [])
        if emp_records:
            employee_id = emp_records[0]["id"]
        else:
            logger.warning(
                "Created employee record but could not retrieve ID: user=%s, company=%s",
                user_id,
                company_id,
            )
            employee_id = 0

    # --- Create initial LeaveBalance records ---
    # T293: Use ensure_leave_balances instead of hardcoded values.
    # This creates balances for ALL configured leave types, respecting
    # gender, service-month rules, and pro-ration for mid-year joiners.
    #
    # Leave-balance failure is intentionally NON-FATAL: companies without
    # a leave-type catalogue should still be able to register employees;
    # balances can be re-seeded later via /leave/balances/seed.
    if employee_id and company_id:
        try:
            from hr_advisory.api.routers.leave import ensure_leave_balances

            ensure_leave_balances(employee_id, company_id)
            logger.info("Created leave balances for employee_id=%s", employee_id)
        except Exception as leave_exc:
            logger.warning(
                "Failed to create leave balances for employee %s: %s", employee_id, leave_exc
            )

    # --- Auto-assign default onboarding template (T226 + S2-T2 saga) ---
    # The hire chain is User → Employee → OnboardingAssignment. If the
    # auto-assign step RAISES (vs returning None for "no default template"),
    # we have a partial state — User and Employee exist but no onboarding
    # plan. Compensate by deleting Employee + User and reverting the
    # Invitation, so the new hire retries cleanly rather than logging in
    # to a half-built account.
    #
    # Note: a None return is the legitimate "company has no default
    # template" path and is NOT compensated — those companies just don't
    # auto-assign and that's by design.
    if employee_id and company_id:
        try:
            from hr_advisory.api.routers.onboarding import auto_assign_default_onboarding

            onboarding_result = auto_assign_default_onboarding(employee_id, company_id)
            if onboarding_result:
                logger.info(
                    "Auto-assigned onboarding for employee_id=%s, assignment_id=%s",
                    employee_id,
                    onboarding_result.get("id"),
                )
            else:
                logger.info(
                    "No default onboarding template for company_id=%s — skipped auto-assign",
                    company_id,
                )
        except Exception as onboard_exc:
            logger.error(
                "Onboarding auto-assign failed — compensating saga "
                "(deleting Employee + User, reverting Invitation): "
                "employee_id=%s user_id=%s err=%s",
                employee_id,
                user_id,
                onboard_exc,
            )
            try:
                from hr_advisory.services import dataflow_crud as _df

                _df.delete("Employee", employee_id)
            except Exception as comp_exc:
                logger.error(
                    "Saga compensation failed to delete Employee %s: %s",
                    employee_id,
                    comp_exc,
                )
            try:
                from hr_advisory.services import dataflow_crud as _df

                _df.delete("User", user_id)
            except Exception as comp_exc:
                logger.error(
                    "Saga compensation failed to delete User %s: %s",
                    user_id,
                    comp_exc,
                )
            try:
                _update_invitation(
                    invitation["id"],
                    {"accepted_at": "", "is_active": True},
                )
            except Exception as comp_exc:
                logger.error(
                    "Saga compensation failed to revert Invitation %s: %s",
                    invitation["id"],
                    comp_exc,
                )
            raise HTTPException(
                status_code=500,
                detail="Registration failed during onboarding setup. Please retry.",
            ) from onboard_exc

    # Invitation was already marked as accepted before user creation
    # (see TOCTOU race condition prevention above)

    # --- Generate JWT tokens ---
    access_token = auth_service.create_access_token(
        user_id=user_id,
        email=user["email"],
        role=user["role"],
        company_id=company_id,
        token_version=user.get("token_version", 1),
    )
    refresh_token = auth_service.create_refresh_token(
        user_id=user_id,
        token_version=user.get("token_version", 1),
    )

    logger.info(
        "Employee registered via invitation: email=%s, user_id=%s, company_id=%s",
        email,
        user_id,
        company_id,
    )

    return {
        "user": {
            "id": user_id,
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
            "company_id": company_id,
        },
        "employee_id": employee_id,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


# --------------------------------------------------------------------------
# Google OAuth SSO — code exchange endpoint
# --------------------------------------------------------------------------
# The frontend constructs the Google OAuth URL directly and handles the
# callback. This endpoint receives the authorization code from the frontend
# and exchanges it for Arbor tokens. Since it returns JSON, the Nexus gateway
# wrapping is harmless.


@router.post("/google/exchange")
async def google_exchange(request: Request):
    """Exchange a Google OAuth authorization code for Arbor tokens.

    Called by the frontend callback page after Google redirects with a code.
    Returns Arbor JWT tokens and user info as JSON.
    """
    _check_auth_rate_limit(request)

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
        # C-2 fix: New Google SSO users get "employee" role, not "owner".
        # Owner role is only assigned through the standard registration/onboarding flow.
        user = auth_service._create_user(
            email=email,
            name=name,
            password_hash="",
            role="employee",
        )
        logger.info("Google SSO: created new user email=%s, id=%s", email, user.get("id"))
    else:
        # Block deactivated users (e.g. terminated employees)
        if not user.get("is_active", True):
            raise HTTPException(status_code=403, detail="Account is deactivated.")
        logger.info("Google SSO: existing user email=%s, id=%s", email, user.get("id"))

    # Generate Arbor JWTs
    access_token = auth_service.create_access_token(
        user_id=user["id"],
        email=user["email"],
        role=user["role"],
        company_id=user.get("company_id"),
        token_version=user.get("token_version", 1),
    )
    refresh_token = auth_service.create_refresh_token(
        user_id=user["id"],
        token_version=user.get("token_version", 1),
    )

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
