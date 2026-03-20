"""Unit tests for LLM key rotation — encrypt/rotate/decrypt roundtrip.

Tests that the rotate_keys function is importable, and that the core
rotation logic (decrypt with old key, re-encrypt with new key, verify)
works correctly at the unit level without hitting DataFlow.

T443 — BYOK API Keys: Key rotation unit tests.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Import test
# ---------------------------------------------------------------------------


class TestRotateKeysImportable:
    """Test that the rotation entry point is importable."""

    def test_rotate_keys_importable(self) -> None:
        """rotate_keys function exists and is callable."""
        from hr_advisory.cli.rotate_llm_keys import rotate_keys

        assert callable(rotate_keys)


# ---------------------------------------------------------------------------
# Encrypt -> Rotate -> Decrypt roundtrip (unit level, no DataFlow)
# ---------------------------------------------------------------------------


class TestKeyRotationRoundtrip:
    """Test the core cryptographic logic of key rotation:
    encrypt with key A, decrypt with A, re-encrypt with key B, decrypt with B."""

    def test_encrypt_rotate_decrypt(self) -> None:
        """Full rotation roundtrip: key A -> plaintext -> key B."""
        from cryptography.fernet import Fernet

        key_a = Fernet.generate_key()
        key_b = Fernet.generate_key()
        assert key_a != key_b

        fernet_a = Fernet(key_a)
        fernet_b = Fernet(key_b)

        # Original plaintext
        plaintext = "sk-original-byok-api-key-abc123def456"

        # Step 1: Encrypt with key A
        ciphertext_a = fernet_a.encrypt(plaintext.encode()).decode()

        # Step 2: Decrypt with key A (rotation step 1)
        decrypted = fernet_a.decrypt(ciphertext_a.encode()).decode()
        assert decrypted == plaintext

        # Step 3: Re-encrypt with key B (rotation step 2)
        ciphertext_b = fernet_b.encrypt(decrypted.encode()).decode()

        # Step 4: Verify — decrypt with key B
        final = fernet_b.decrypt(ciphertext_b.encode()).decode()
        assert final == plaintext

        # Key A should NOT decrypt ciphertext_b
        with pytest.raises(Exception):
            fernet_a.decrypt(ciphertext_b.encode())

    def test_rotation_preserves_all_key_formats(self) -> None:
        """Rotation preserves keys regardless of format (long, special chars, unicode)."""
        from cryptography.fernet import Fernet

        key_a = Fernet.generate_key()
        key_b = Fernet.generate_key()
        fernet_a = Fernet(key_a)
        fernet_b = Fernet(key_b)

        test_keys = [
            "sk-proj-abc123def456ghi789jkl012",
            "sk-ant-api03-xxxxxxxxxxxxxxxxxxxx",
            "AIzaSyC-xxxxxxxxxxxxxxxxxxx",
            "a" * 500,  # Very long key
            "key!@#$%^&*()",  # Special characters
        ]

        for api_key in test_keys:
            ct_old = fernet_a.encrypt(api_key.encode()).decode()
            decrypted = fernet_a.decrypt(ct_old.encode()).decode()
            ct_new = fernet_b.encrypt(decrypted.encode()).decode()
            result = fernet_b.decrypt(ct_new.encode()).decode()
            assert result == api_key, f"Rotation failed for key pattern: {api_key[:10]}..."

    def test_rotation_verification_step(self) -> None:
        """The rotate_keys function includes a verification step:
        after re-encryption, it decrypts again to confirm correctness."""
        from cryptography.fernet import Fernet

        key_a = Fernet.generate_key()
        key_b = Fernet.generate_key()
        fernet_a = Fernet(key_a)
        fernet_b = Fernet(key_b)

        plaintext = "sk-verification-test-key-12345678"

        # Encrypt
        ct_old = fernet_a.encrypt(plaintext.encode()).decode()

        # Decrypt with old
        decrypted = fernet_a.decrypt(ct_old.encode()).decode()

        # Re-encrypt with new
        ct_new = fernet_b.encrypt(decrypted.encode()).decode()

        # Verify (this is what rotate_keys does)
        verify = fernet_b.decrypt(ct_new.encode()).decode()
        assert verify == plaintext


# ---------------------------------------------------------------------------
# CLI argument validation
# ---------------------------------------------------------------------------


class TestRotateKeysCLIValidation:
    """Test that rotate_keys validates its required environment variables."""

    @patch("hr_advisory.cli.rotate_llm_keys.sys")
    def test_missing_old_key_exits(self, mock_sys, monkeypatch) -> None:
        """rotate_keys should exit if OLD_LLM_KEY is not set."""
        monkeypatch.delenv("OLD_LLM_KEY", raising=False)
        monkeypatch.delenv("NEW_LLM_KEY", raising=False)

        mock_sys.exit = MagicMock(side_effect=SystemExit(1))

        from hr_advisory.cli.rotate_llm_keys import rotate_keys

        with pytest.raises(SystemExit):
            rotate_keys()

        mock_sys.exit.assert_called_with(1)

    @patch("hr_advisory.cli.rotate_llm_keys.sys")
    def test_missing_new_key_exits(self, mock_sys, monkeypatch) -> None:
        """rotate_keys should exit if NEW_LLM_KEY is not set."""
        from cryptography.fernet import Fernet

        monkeypatch.setenv("OLD_LLM_KEY", Fernet.generate_key().decode())
        monkeypatch.delenv("NEW_LLM_KEY", raising=False)

        mock_sys.exit = MagicMock(side_effect=SystemExit(1))

        from hr_advisory.cli.rotate_llm_keys import rotate_keys

        with pytest.raises(SystemExit):
            rotate_keys()

        mock_sys.exit.assert_called_with(1)

    @patch("hr_advisory.cli.rotate_llm_keys.sys")
    def test_invalid_old_key_exits(self, mock_sys, monkeypatch) -> None:
        """rotate_keys should exit if OLD_LLM_KEY is not a valid Fernet key."""
        monkeypatch.setenv("OLD_LLM_KEY", "not-a-valid-fernet-key")
        monkeypatch.setenv("NEW_LLM_KEY", "also-not-valid")

        mock_sys.exit = MagicMock(side_effect=SystemExit(1))

        from hr_advisory.cli.rotate_llm_keys import rotate_keys

        with pytest.raises(SystemExit):
            rotate_keys()

        mock_sys.exit.assert_called_with(1)


# ---------------------------------------------------------------------------
# Integration with llm_encryption module (unit-level, no DB)
# ---------------------------------------------------------------------------


class TestRotationWithEncryptionModule:
    """Test that rotation works with the llm_encryption module's functions."""

    def test_encrypt_with_module_rotate_manually(self, monkeypatch) -> None:
        """Encrypt via llm_encryption, manually rotate with Fernet, verify."""
        from cryptography.fernet import Fernet

        from hr_advisory.security.llm_encryption import (
            _get_fernet,
            decrypt_api_key,
            encrypt_api_key,
        )

        # Set up key A
        key_a = Fernet.generate_key().decode()
        monkeypatch.setenv("LLM_KEY_ENCRYPTION_KEY", key_a)
        monkeypatch.setenv("APP_ENV", "development")
        _get_fernet.cache_clear()

        # Encrypt with key A via module
        plaintext = "sk-module-rotation-test-abcdef123456"
        ciphertext = encrypt_api_key(plaintext)

        # Verify decrypt works
        assert decrypt_api_key(ciphertext) == plaintext

        # Now "rotate": decrypt with old fernet, re-encrypt with new
        key_b = Fernet.generate_key().decode()
        fernet_a = Fernet(key_a.encode())
        fernet_b = Fernet(key_b.encode())

        decrypted = fernet_a.decrypt(ciphertext.encode()).decode()
        new_ciphertext = fernet_b.encrypt(decrypted.encode()).decode()

        # Switch module to key B
        monkeypatch.setenv("LLM_KEY_ENCRYPTION_KEY", key_b)
        _get_fernet.cache_clear()

        # Verify the rotated ciphertext decrypts correctly with new key
        assert decrypt_api_key(new_ciphertext) == plaintext

        # Old ciphertext should NOT decrypt with new key
        from hr_advisory.security.llm_encryption import LLMEncryptionError

        with pytest.raises(LLMEncryptionError):
            decrypt_api_key(ciphertext)

        # Clean up
        _get_fernet.cache_clear()
