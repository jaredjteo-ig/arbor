"""Authentication service with password hashing and JWT tokens.

Pure service layer -- NO framework imports (no FastAPI, no request objects).
Uses DataFlow workflow nodes for user CRUD operations.
Uses bcrypt for password hashing and PyJWT for token management.

All secrets are read from Settings; nothing is hardcoded.
"""

import logging
import re
import time
import uuid
from datetime import datetime, timezone

import bcrypt
import jwt

from hr_advisory.config.settings import Settings, get_settings

logger = logging.getLogger(__name__)

# Pre-compiled email regex (RFC 5322 simplified)
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

# Minimum password length
_MIN_PASSWORD_LENGTH = 8

# Refresh token expiry: 7 days in minutes
_REFRESH_TOKEN_EXPIRY_MINUTES = 7 * 24 * 60


class AuthService:
    """Authentication service with password hashing and JWT tokens.

    All user persistence goes through DataFlow workflow nodes so that
    the service never touches SQL directly.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    # ------------------------------------------------------------------
    # Password hashing
    # ------------------------------------------------------------------

    def hash_password(self, password: str) -> str:
        """Hash a plaintext password using bcrypt.

        Raises:
            ValueError: If password is empty.
        """
        if not password:
            raise ValueError("Password must not be empty")
        password_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode("utf-8")

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a plaintext password against a bcrypt hash.

        Returns True if they match, False otherwise.
        """
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"),
                hashed.encode("utf-8"),
            )
        except Exception:
            return False

    # ------------------------------------------------------------------
    # JWT tokens
    # ------------------------------------------------------------------

    def create_access_token(
        self,
        user_id: int,
        email: str,
        role: str,
        company_id: int | None = None,
        token_version: int = 1,
    ) -> str:
        """Create an access JWT containing user identity.

        Token payload:
            sub: str(user_id)  -- JWT spec requires sub to be a string
            email: user email
            role: user role
            company_id: (optional) the user's company for tenant isolation
            tv: token version (for instant invalidation on termination/password change)
            exp: expiry timestamp (settings.jwt_expiry_minutes from now)

        Note: sub is stored as a string per JWT spec. decode_token converts
        it back to int for access tokens.
        """
        now = int(time.time())
        payload = {
            "sub": str(user_id),
            "email": email,
            "role": role,
            "jti": str(uuid.uuid4()),
            "tv": token_version,
            "iat": now,
            "exp": now + (self._settings.jwt_expiry_minutes * 60),
        }
        if company_id is not None:
            payload["company_id"] = company_id
        return jwt.encode(
            payload,
            self._settings.jwt_secret_key,
            algorithm=self._settings.jwt_algorithm,
        )

    def create_refresh_token(self, user_id: int, token_version: int = 1) -> str:
        """Create a refresh JWT (7-day expiry).

        Token payload:
            sub: str(user_id)
            type: "refresh"
            tv: token version (for instant invalidation on termination/password change)
            exp: 7 days from now
        """
        now = int(time.time())
        payload = {
            "sub": str(user_id),
            "type": "refresh",
            "tv": token_version,
            "jti": str(uuid.uuid4()),
            "iat": now,
            "exp": now + (_REFRESH_TOKEN_EXPIRY_MINUTES * 60),
        }
        return jwt.encode(
            payload,
            self._settings.jwt_secret_key,
            algorithm=self._settings.jwt_algorithm,
        )

    def create_password_reset_token(self, email: str) -> str:
        """Create a password-reset JWT (1-hour expiry).

        Token payload:
            sub: email
            type: "password_reset"
            jti: unique ID (for single-use invalidation)
            exp: 1 hour from now
        """
        now = int(time.time())
        payload = {
            "sub": email,
            "type": "password_reset",
            "jti": str(uuid.uuid4()),
            "iat": now,
            "exp": now + 3600,
        }
        return jwt.encode(
            payload,
            self._settings.jwt_secret_key,
            algorithm=self._settings.jwt_algorithm,
        )

    def decode_token(self, token: str) -> dict:
        """Decode and validate a JWT.

        Returns the decoded payload dict. The ``sub`` claim is automatically
        converted back to ``int`` when it represents a numeric user ID
        (access and refresh tokens). Password-reset tokens keep ``sub`` as
        a string (the email address).

        Raises:
            jwt.ExpiredSignatureError: Token has expired.
            jwt.InvalidTokenError: Token is malformed or signature invalid.
        """
        payload = jwt.decode(
            token,
            self._settings.jwt_secret_key,
            algorithms=[self._settings.jwt_algorithm],
        )
        # Convert sub back to int for user-ID based tokens
        sub = payload.get("sub")
        if sub is not None and isinstance(sub, str):
            try:
                payload["sub"] = int(sub)
            except ValueError:
                # sub is not numeric (e.g. email in password_reset tokens) -- keep as string
                pass
        return payload

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def validate_email(email: str) -> None:
        """Validate email format.

        Raises:
            ValueError: If email is empty or malformed.
        """
        if not email or not _EMAIL_RE.match(email):
            raise ValueError("Invalid email format")

    @staticmethod
    def validate_password(password: str) -> None:
        """Validate password meets length requirements.

        bcrypt silently truncates at 72 bytes, so we cap at 72 characters
        to prevent users from relying on password content beyond that limit.

        Raises:
            ValueError: If password is too short or too long.
        """
        if not password or len(password) < _MIN_PASSWORD_LENGTH:
            raise ValueError(f"Password must be at least {_MIN_PASSWORD_LENGTH} characters")
        if len(password) > 72:
            raise ValueError("Password must be at most 72 characters")

    @staticmethod
    def validate_name(name: str) -> None:
        """Validate user name is present.

        Raises:
            ValueError: If name is empty or blank.
        """
        if not name or not name.strip():
            raise ValueError("Name is required")

    # ------------------------------------------------------------------
    # User lookup via DataFlow
    # ------------------------------------------------------------------

    def _find_user_by_email(self, email: str) -> dict | None:
        """Look up a user record by email using DataFlow UserListNode.

        Returns the user dict if found, or None.
        Cache is disabled to ensure fresh lookups (critical for
        duplicate-email checks during registration).
        """
        from kailash.runtime import LocalRuntime
        from kailash.workflow.builder import WorkflowBuilder

        # Ensure models are registered
        import hr_advisory.models  # noqa: F401

        wf = WorkflowBuilder()
        wf.add_node(
            "UserListNode",
            "find",
            {"filter": {"email": email}, "limit": 1, "enable_cache": False},
        )
        runtime = LocalRuntime()
        results, _ = runtime.execute(wf.build())
        records = results["find"].get("records", [])
        if records:
            return records[0]
        return None

    def _find_user_by_id(self, user_id: int) -> dict | None:
        """Look up a user record by ID using DataFlow UserReadNode.

        Returns the user dict if found, or None.
        """
        from kailash.runtime import LocalRuntime
        from kailash.workflow.builder import WorkflowBuilder

        import hr_advisory.models  # noqa: F401

        wf = WorkflowBuilder()
        wf.add_node("UserReadNode", "read", {"id": user_id})
        runtime = LocalRuntime()
        results, _ = runtime.execute(wf.build())
        result = results.get("read", {})
        if result.get("error") or result.get("failed"):
            return None
        return result

    def _create_user(
        self,
        email: str,
        name: str,
        password_hash: str,
        company_id: int | None = None,
        role: str = "owner",
    ) -> dict:
        """Create a new user via DataFlow UserCreateNode.

        Returns the created user dict including the database-generated id.

        Note: DataFlow's CreateNode returns only the input params and
        rows_affected -- it does NOT return the auto-generated primary key.
        We therefore follow up with a ListNode lookup by email to retrieve
        the full record including the id.
        """
        from kailash.runtime import LocalRuntime
        from kailash.workflow.builder import WorkflowBuilder

        import hr_advisory.models  # noqa: F401

        params: dict = {
            "email": email,
            "name": name,
            "password_hash": password_hash,
            "role": role,
            "is_active": True,
        }
        if company_id is not None:
            params["company_id"] = company_id

        wf = WorkflowBuilder()
        wf.add_node("UserCreateNode", "create", params)
        runtime = LocalRuntime()
        results, _ = runtime.execute(wf.build())
        create_result = results["create"]

        # CreateNode doesn't return the auto-generated id, so fetch it.
        if "id" not in create_result:
            user = self._find_user_by_email(email)
            if user is not None:
                return user
            # Fallback: return create result as-is (should not happen)
            logger.warning("Created user but could not retrieve record by email=%s", email)
        return create_result

    def _update_user(self, user_id: int, updates: dict) -> dict:
        """Update a user record via DataFlow UserUpdateNode.

        Uses the v0.6 API: filter + fields.
        Returns the updated user dict.
        """
        from kailash.runtime import LocalRuntime
        from kailash.workflow.builder import WorkflowBuilder

        import hr_advisory.models  # noqa: F401

        wf = WorkflowBuilder()
        wf.add_node(
            "UserUpdateNode",
            "update",
            {"filter": {"id": user_id}, "fields": updates},
        )
        runtime = LocalRuntime()
        results, _ = runtime.execute(wf.build())
        return results["update"]

    # ------------------------------------------------------------------
    # High-level auth operations
    # ------------------------------------------------------------------

    def register_user(
        self,
        email: str,
        password: str,
        name: str,
        company_id: int | None = None,
    ) -> dict:
        """Register a new user.

        Returns:
            dict with "user", "access_token", "refresh_token", "token_type".

        Raises:
            ValueError: If input validation fails or email is already registered.
        """
        self.validate_email(email)
        self.validate_password(password)
        self.validate_name(name)

        # Check for duplicate email
        existing = self._find_user_by_email(email)
        if existing is not None:
            raise ValueError(f"Email already registered: {email}")

        password_hash = self.hash_password(password)
        user = self._create_user(
            email=email,
            name=name,
            password_hash=password_hash,
            company_id=company_id,
        )

        access_token = self.create_access_token(
            user_id=user["id"],
            email=user["email"],
            role=user["role"],
            company_id=user.get("company_id"),
            token_version=user.get("token_version", 1),
        )
        refresh_token = self.create_refresh_token(
            user_id=user["id"],
            token_version=user.get("token_version", 1),
        )

        logger.info("User registered: email=%s, id=%s", email, user["id"])

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

    def authenticate(self, email: str, password: str) -> dict:
        """Authenticate a user with email + password.

        Returns:
            dict with "user", "access_token", "refresh_token", "token_type".

        Raises:
            ValueError: If credentials are invalid.
        """
        user = self._find_user_by_email(email)
        if user is None:
            logger.warning("Login attempt for nonexistent email: %s", email)
            raise ValueError("Invalid email or password")

        if not user.get("password_hash"):
            logger.warning("Login attempt for user without password_hash: email=%s", email)
            raise ValueError("Invalid email or password")

        if not self.verify_password(password, user["password_hash"]):
            logger.warning("Failed login attempt: email=%s", email)
            raise ValueError("Invalid email or password")

        if not user.get("is_active", True):
            logger.warning("Login attempt for deactivated account: email=%s", email)
            raise ValueError("Account is deactivated")

        # Update last_login_at (strip tzinfo to match naive DB column)
        try:
            self._update_user(
                user["id"],
                {"last_login_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()},
            )
        except Exception:
            logger.warning(
                "Failed to update last_login_at for user %s",
                user["id"],
                exc_info=True,
            )

        access_token = self.create_access_token(
            user_id=user["id"],
            email=user["email"],
            role=user["role"],
            company_id=user.get("company_id"),
            token_version=user.get("token_version", 1),
        )
        refresh_token = self.create_refresh_token(
            user_id=user["id"],
            token_version=user.get("token_version", 1),
        )

        logger.info("User authenticated: email=%s, id=%s", email, user["id"])

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

    def refresh(self, refresh_token: str) -> dict:
        """Exchange a valid refresh token for a new access token.

        Returns:
            dict with "access_token", "token_type".

        Raises:
            ValueError: If the token is invalid, expired, or not a refresh token.
        """
        try:
            payload = self.decode_token(refresh_token)
        except Exception as exc:
            logger.warning("Refresh token decode failed: %s", exc)
            raise ValueError("Invalid or expired refresh token") from exc

        if payload.get("type") != "refresh":
            logger.warning("Non-refresh token used for refresh: type=%s", payload.get("type"))
            raise ValueError("Token is not a refresh token")

        # Check if the refresh token has been revoked (e.g. by logout)
        jti = payload.get("jti")
        if jti:
            from hr_advisory.api.middleware.token_blocklist import get_blocklist

            if get_blocklist().is_revoked(jti):
                logger.warning("Revoked refresh token used: jti=%s", jti)
                raise ValueError("Refresh token has been revoked")

        user_id = payload["sub"]
        user = self._find_user_by_id(user_id)
        if user is None:
            logger.warning("Refresh token references nonexistent user: id=%s", user_id)
            raise ValueError("User not found")

        if not user.get("is_active", True):
            logger.warning("Refresh attempt for deactivated account: id=%s", user_id)
            raise ValueError("Account is deactivated")

        # Check token version — reject refresh if token_version was bumped
        # (e.g. after termination or password reset)
        refresh_tv = payload.get("tv")
        current_tv = user.get("token_version", 1)
        if refresh_tv is not None and refresh_tv != current_tv:
            logger.warning(
                "Refresh token version mismatch: token tv=%s, user tv=%s, user_id=%s",
                refresh_tv,
                current_tv,
                user_id,
            )
            raise ValueError("Token has been invalidated")

        access_token = self.create_access_token(
            user_id=user["id"],
            email=user["email"],
            role=user["role"],
            company_id=user.get("company_id"),
            token_version=current_tv,
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
        }

    def get_user_by_id(self, user_id: int) -> dict | None:
        """Retrieve a user by ID.

        Returns the user dict or None.
        """
        return self._find_user_by_id(user_id)

    def reset_password(self, token: str, new_password: str) -> dict:
        """Reset a user's password using a password-reset token.

        The token is invalidated after use (single-use) by adding its
        JTI to the token blocklist.

        Returns:
            dict with "message".

        Raises:
            ValueError: If token is invalid/expired or password is too short.
        """
        self.validate_password(new_password)

        try:
            payload = self.decode_token(token)
        except Exception as exc:
            logger.warning("Password reset token decode failed: %s", exc)
            raise ValueError("Invalid or expired reset token") from exc

        if payload.get("type") != "password_reset":
            raise ValueError("Token is not a password reset token")

        # Check if the reset token has already been used
        from hr_advisory.api.middleware.token_blocklist import get_blocklist

        jti = payload.get("jti")
        blocklist = get_blocklist()
        if jti and blocklist.is_revoked(jti):
            raise ValueError("This password reset link has already been used")

        email = payload["sub"]
        user = self._find_user_by_email(email)
        if user is None:
            logger.warning("Password reset for nonexistent email: %s", email)
            raise ValueError("User not found")

        new_hash = self.hash_password(new_password)

        # Increment token_version to invalidate all existing sessions
        current_tv = user.get("token_version", 1)
        new_tv = current_tv + 1
        self._update_user(user["id"], {"password_hash": new_hash, "token_version": new_tv})

        # Invalidate the token version cache so the middleware picks up the change
        from hr_advisory.api.middleware.token_version_cache import get_token_version_cache

        get_token_version_cache().invalidate(user["id"])
        logger.info(
            "Password reset: incremented token_version %s->%s for user %s",
            current_tv,
            new_tv,
            user["id"],
        )

        # Invalidate the reset token so it cannot be reused
        if jti:
            exp = payload.get("exp", int(time.time()) + 3600)
            blocklist.revoke_token(jti, exp)
            logger.info("Password reset token invalidated: jti=%s", jti)

        logger.info("Password reset completed for email=%s", email)
        return {"message": "Password has been reset successfully"}
