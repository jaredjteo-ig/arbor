# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""Encryption for LLM API keys — separate from salary/PII encryption.

Uses a dedicated LLM_KEY_ENCRYPTION_KEY to avoid single-point-of-compromise
with SALARY_ENCRYPTION_KEY.  NO plaintext fallback in any environment.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache

logger = logging.getLogger(__name__)

__all__ = [
    "encrypt_api_key",
    "decrypt_api_key",
    "mask_api_key",
]


class LLMEncryptionError(Exception):
    """Raised when LLM key encryption/decryption fails."""


@lru_cache(maxsize=1)
def _get_fernet():
    """Get Fernet instance for LLM key encryption.

    Uses LLM_KEY_ENCRYPTION_KEY (primary) or derives a fallback from
    JWT_SECRET_KEY in development mode only.  Never returns None — raises
    if no key is available.

    NOTE: The Fernet instance is cached for the process lifetime.  After
    rotating LLM_KEY_ENCRYPTION_KEY, restart the application process.
    Call ``_get_fernet.cache_clear()`` if you need to force a refresh
    (e.g., in the key rotation CLI).
    """
    from cryptography.fernet import Fernet

    key = os.environ.get("LLM_KEY_ENCRYPTION_KEY", "")

    if key:
        try:
            return Fernet(key.encode() if isinstance(key, str) else key)
        except Exception as e:
            raise LLMEncryptionError(
                f"Invalid LLM_KEY_ENCRYPTION_KEY: {e}.  "
                "Generate one with: python -c "
                '"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
            ) from e

    # No dedicated key — check environment
    app_env = os.environ.get("APP_ENV", "development")
    if app_env == "production":
        raise LLMEncryptionError(
            "FATAL: LLM_KEY_ENCRYPTION_KEY must be set in production.  "
            "Generate one with: python -c "
            '"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )

    # Development fallback: derive from JWT_SECRET_KEY (deterministic)
    import base64
    import hashlib

    jwt_secret = os.environ.get("JWT_SECRET_KEY", "change-this-in-production")
    derived = hashlib.sha256(f"llm-key-encryption:{jwt_secret}".encode()).digest()
    fernet_key = base64.urlsafe_b64encode(derived)
    logger.warning(
        "LLM_KEY_ENCRYPTION_KEY not set — using key derived from JWT_SECRET_KEY "
        "(development only, DO NOT use in production)"
    )
    return Fernet(fernet_key)


def encrypt_api_key(plaintext: str) -> str:
    """Encrypt an API key.  Returns base64-encoded ciphertext.

    Raises LLMEncryptionError if encryption is not configured.
    """
    if not plaintext:
        raise ValueError("Cannot encrypt empty API key")
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_api_key(ciphertext: str) -> str:
    """Decrypt an API key.

    Raises LLMEncryptionError on failure (wrong key, corrupt data).
    """
    if not ciphertext:
        raise ValueError("Cannot decrypt empty ciphertext")
    f = _get_fernet()
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except Exception as e:
        raise LLMEncryptionError(
            f"Failed to decrypt API key — wrong encryption key or corrupt data: {e}"
        ) from e


def mask_api_key(key: str) -> str:
    """Mask API key for display: show first 3 + last 4 chars."""
    if not key:
        return ""
    if len(key) <= 8:
        return "****"
    return key[:3] + "..." + key[-4:]
