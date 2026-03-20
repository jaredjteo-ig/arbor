"""Unit tests for LLM API key encryption — encrypt, decrypt, mask.

Tests Fernet encrypt/decrypt roundtrip, ciphertext uniqueness (due to
timestamped tokens), decryption with wrong key, empty-input guards,
and mask_api_key display formatting.

T426 — BYOK API Keys: Encryption unit tests.
"""

from __future__ import annotations

import os

import pytest

from hr_advisory.security.llm_encryption import (
    LLMEncryptionError,
    _get_fernet,
    decrypt_api_key,
    encrypt_api_key,
    mask_api_key,
)


@pytest.fixture(autouse=True)
def _clear_fernet_cache():
    """Clear the lru_cache on _get_fernet before and after each test
    so environment variable changes take effect."""
    _get_fernet.cache_clear()
    yield
    _get_fernet.cache_clear()


@pytest.fixture()
def _dev_encryption_env(monkeypatch):
    """Ensure development encryption environment (no dedicated key,
    uses JWT_SECRET_KEY derivation)."""
    monkeypatch.delenv("LLM_KEY_ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-for-encryption")


@pytest.fixture()
def _dedicated_key_env(monkeypatch):
    """Set up a dedicated LLM_KEY_ENCRYPTION_KEY."""
    from cryptography.fernet import Fernet

    key = Fernet.generate_key().decode()
    monkeypatch.setenv("LLM_KEY_ENCRYPTION_KEY", key)
    monkeypatch.setenv("APP_ENV", "development")
    return key


class TestEncryptDecryptRoundtrip:
    """Test that encrypting then decrypting returns the original plaintext."""

    def test_roundtrip_with_dev_fallback(self, _dev_encryption_env) -> None:
        """Encrypt/decrypt cycle works using the JWT-derived fallback key."""
        plaintext = "sk-proj-abc123def456ghi789jkl012mno345pqr678"
        ciphertext = encrypt_api_key(plaintext)
        assert ciphertext != plaintext
        decrypted = decrypt_api_key(ciphertext)
        assert decrypted == plaintext

    def test_roundtrip_with_dedicated_key(self, _dedicated_key_env) -> None:
        """Encrypt/decrypt cycle works using a dedicated encryption key."""
        plaintext = "anthropic-sk-ant-test-key-value-here-1234"
        ciphertext = encrypt_api_key(plaintext)
        decrypted = decrypt_api_key(ciphertext)
        assert decrypted == plaintext

    def test_roundtrip_various_key_formats(self, _dev_encryption_env) -> None:
        """Various real-world key formats all survive encrypt/decrypt."""
        keys = [
            "sk-proj-abc123",  # OpenAI project key
            "sk-ant-api03-xxxxxxxxxxxxxxxxxxxx",  # Anthropic
            "AIzaSyC-xxxxxxxxxxxxxxxxxxx",  # Gemini
            "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",  # DeepSeek
            "a" * 200,  # Long key
            "key-with-special-chars!@#$%^&*()",  # Special chars
            "unicode-key-\u00e9\u00e8\u00ea",  # Unicode
        ]
        for key in keys:
            ct = encrypt_api_key(key)
            assert decrypt_api_key(ct) == key


class TestCiphertextUniqueness:
    """Test that Fernet produces unique ciphertexts (timestamped tokens)."""

    def test_same_plaintext_different_ciphertext(self, _dev_encryption_env) -> None:
        """Encrypting the same plaintext twice should produce different ciphertext.
        Fernet includes a timestamp, so this is expected."""
        plaintext = "sk-test-unique-cipher-1234567890ab"
        ct1 = encrypt_api_key(plaintext)
        ct2 = encrypt_api_key(plaintext)
        assert ct1 != ct2
        # Both should decrypt to the same thing
        assert decrypt_api_key(ct1) == plaintext
        assert decrypt_api_key(ct2) == plaintext


class TestDecryptionWithWrongKey:
    """Test that decryption fails safely with the wrong key."""

    def test_wrong_key_raises_encryption_error(self, monkeypatch) -> None:
        """Decrypting with a different key should raise LLMEncryptionError."""
        from cryptography.fernet import Fernet

        # Encrypt with key A
        key_a = Fernet.generate_key().decode()
        monkeypatch.setenv("LLM_KEY_ENCRYPTION_KEY", key_a)
        monkeypatch.setenv("APP_ENV", "development")
        _get_fernet.cache_clear()

        ciphertext = encrypt_api_key("sk-secret-key-for-wrong-key-test")

        # Switch to key B
        key_b = Fernet.generate_key().decode()
        monkeypatch.setenv("LLM_KEY_ENCRYPTION_KEY", key_b)
        _get_fernet.cache_clear()

        with pytest.raises(LLMEncryptionError, match="Failed to decrypt"):
            decrypt_api_key(ciphertext)

    def test_corrupt_ciphertext_raises_encryption_error(self, _dev_encryption_env) -> None:
        """Garbage ciphertext raises LLMEncryptionError."""
        with pytest.raises(LLMEncryptionError, match="Failed to decrypt"):
            decrypt_api_key("definitely-not-valid-ciphertext-at-all")


class TestEmptyInputGuards:
    """Test that empty/blank inputs are rejected."""

    def test_encrypt_empty_string_raises(self, _dev_encryption_env) -> None:
        """encrypt_api_key('') should raise ValueError."""
        with pytest.raises(ValueError, match="Cannot encrypt empty"):
            encrypt_api_key("")

    def test_decrypt_empty_string_raises(self, _dev_encryption_env) -> None:
        """decrypt_api_key('') should raise ValueError."""
        with pytest.raises(ValueError, match="Cannot decrypt empty"):
            decrypt_api_key("")


class TestProductionRequiresKey:
    """Test that production mode refuses to work without LLM_KEY_ENCRYPTION_KEY."""

    def test_production_without_key_raises(self, monkeypatch) -> None:
        """Production mode with no LLM_KEY_ENCRYPTION_KEY raises LLMEncryptionError."""
        monkeypatch.delenv("LLM_KEY_ENCRYPTION_KEY", raising=False)
        monkeypatch.setenv("APP_ENV", "production")
        _get_fernet.cache_clear()

        with pytest.raises(LLMEncryptionError, match="must be set in production"):
            encrypt_api_key("sk-will-never-encrypt")


class TestMaskApiKey:
    """Test mask_api_key() display formatting."""

    def test_mask_long_key(self) -> None:
        """Keys > 8 chars show first 3 + '...' + last 4."""
        assert mask_api_key("sk-proj-abc123def456") == "sk-...f456"

    def test_mask_exactly_9_chars(self) -> None:
        """Edge case: 9-char key (just above threshold)."""
        assert mask_api_key("123456789") == "123...6789"

    def test_mask_8_char_key(self) -> None:
        """Keys <= 8 chars show '****'."""
        assert mask_api_key("12345678") == "****"

    def test_mask_short_key(self) -> None:
        """Very short key shows '****'."""
        assert mask_api_key("abc") == "****"

    def test_mask_single_char(self) -> None:
        """Single character key shows '****'."""
        assert mask_api_key("x") == "****"

    def test_mask_empty_string(self) -> None:
        """Empty string returns empty string."""
        assert mask_api_key("") == ""

    def test_mask_real_openai_format(self) -> None:
        """Realistic OpenAI key format."""
        key = "sk-proj-abc123def456ghi789jkl012mno345pqr678stu901"
        masked = mask_api_key(key)
        assert masked.startswith("sk-")
        assert masked.endswith("901")
        assert "..." in masked
        assert len(masked) == 10  # 3 + 3 + 4
