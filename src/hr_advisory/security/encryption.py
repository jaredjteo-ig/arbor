"""Field-level encryption for PII data using Fernet symmetric encryption.

Encryption key is loaded from SALARY_ENCRYPTION_KEY environment variable.
If not set, a warning is logged and data is stored in plaintext (development only).
"""

import logging
import os
from functools import lru_cache

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_fernet():
    """Get or create a Fernet instance. Returns None if no key configured."""
    key = os.environ.get("SALARY_ENCRYPTION_KEY", "")
    if not key:
        logger.warning("SALARY_ENCRYPTION_KEY not set — PII stored in PLAINTEXT (dev mode only)")
        return None
    try:
        from cryptography.fernet import Fernet

        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as e:
        logger.error("Failed to initialize Fernet encryption: %s", e)
        return None


def encrypt_field(value: str) -> str:
    """Encrypt a string value. Returns original if encryption not configured."""
    if not value:
        return value
    f = _get_fernet()
    if f is None:
        return value
    return f.encrypt(value.encode()).decode()


def decrypt_field(value: str) -> str:
    """Decrypt a string value. Returns original if not encrypted or no key."""
    if not value:
        return value
    f = _get_fernet()
    if f is None:
        return value
    try:
        return f.decrypt(value.encode()).decode()
    except Exception:
        # Value might not be encrypted (migration scenario) — return as-is
        return value


def mask_nric(nric: str) -> str:
    """Mask NRIC showing only first and last 4 characters: S****567D"""
    if not nric or len(nric) < 5:
        return "****"
    return nric[0] + "*" * (len(nric) - 5) + nric[-4:]


def mask_bank_account(account: str) -> str:
    """Mask bank account showing only last 4 digits: ****1234"""
    if not account or len(account) <= 4:
        return "****"
    return "*" * (len(account) - 4) + account[-4:]
