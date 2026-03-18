"""Unit tests for application settings.

Tests production safety guards and configuration loading.
"""

from __future__ import annotations

import os

import pytest

from hr_advisory.config.settings import get_settings


class TestProductionGuards:
    """Test that production mode enforces security requirements."""

    def test_production_rejects_default_jwt(self) -> None:
        """Production mode should refuse to start with default JWT secret."""
        # Clear the lru_cache so we get a fresh settings load
        get_settings.cache_clear()

        original_env = os.environ.get("APP_ENV")
        original_jwt = os.environ.get("JWT_SECRET_KEY")
        original_debug = os.environ.get("DEBUG")

        try:
            os.environ["APP_ENV"] = "production"
            os.environ["DEBUG"] = "false"
            # Remove JWT_SECRET_KEY so it falls back to default
            os.environ.pop("JWT_SECRET_KEY", None)

            with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
                get_settings()
        finally:
            # Restore original environment
            get_settings.cache_clear()
            if original_env is not None:
                os.environ["APP_ENV"] = original_env
            else:
                os.environ.pop("APP_ENV", None)
            if original_jwt is not None:
                os.environ["JWT_SECRET_KEY"] = original_jwt
            if original_debug is not None:
                os.environ["DEBUG"] = original_debug
            else:
                os.environ.pop("DEBUG", None)

    def test_development_allows_default_jwt(self) -> None:
        """Development mode should allow default JWT secret."""
        get_settings.cache_clear()

        original_env = os.environ.get("APP_ENV")
        original_jwt = os.environ.get("JWT_SECRET_KEY")

        try:
            os.environ["APP_ENV"] = "development"
            os.environ.pop("JWT_SECRET_KEY", None)

            settings = get_settings()
            assert settings.jwt_secret_key == "change-this-in-production"
        finally:
            get_settings.cache_clear()
            if original_env is not None:
                os.environ["APP_ENV"] = original_env
            else:
                os.environ.pop("APP_ENV", None)
            if original_jwt is not None:
                os.environ["JWT_SECRET_KEY"] = original_jwt

    def test_production_accepts_custom_jwt(self) -> None:
        """Production mode should start with a custom JWT secret and debug off."""
        get_settings.cache_clear()

        original_env = os.environ.get("APP_ENV")
        original_jwt = os.environ.get("JWT_SECRET_KEY")
        original_debug = os.environ.get("DEBUG")
        original_db_url = os.environ.get("DATABASE_URL")

        try:
            os.environ["APP_ENV"] = "production"
            os.environ["JWT_SECRET_KEY"] = "a-very-secure-custom-secret-key-here"
            os.environ["DEBUG"] = "false"
            os.environ["DATABASE_URL"] = "postgresql://produser:securepass@db.example.com:5432/arbor"

            settings = get_settings()
            assert settings.jwt_secret_key == "a-very-secure-custom-secret-key-here"
            assert settings.debug is False
        finally:
            get_settings.cache_clear()
            if original_env is not None:
                os.environ["APP_ENV"] = original_env
            else:
                os.environ.pop("APP_ENV", None)
            if original_jwt is not None:
                os.environ["JWT_SECRET_KEY"] = original_jwt
            else:
                os.environ.pop("JWT_SECRET_KEY", None)
            if original_debug is not None:
                os.environ["DEBUG"] = original_debug
            else:
                os.environ.pop("DEBUG", None)
            if original_db_url is not None:
                os.environ["DATABASE_URL"] = original_db_url
            else:
                os.environ.pop("DATABASE_URL", None)

    def test_production_rejects_debug_mode(self) -> None:
        """Production mode should refuse to start with debug enabled."""
        get_settings.cache_clear()

        original_env = os.environ.get("APP_ENV")
        original_jwt = os.environ.get("JWT_SECRET_KEY")
        original_debug = os.environ.get("DEBUG")
        original_db_url = os.environ.get("DATABASE_URL")

        try:
            os.environ["APP_ENV"] = "production"
            os.environ["JWT_SECRET_KEY"] = "a-very-secure-custom-secret-key-here"
            os.environ["DEBUG"] = "true"
            os.environ["DATABASE_URL"] = "postgresql://produser:securepass@db.example.com:5432/arbor"

            with pytest.raises(RuntimeError, match="DEBUG"):
                get_settings()
        finally:
            get_settings.cache_clear()
            if original_env is not None:
                os.environ["APP_ENV"] = original_env
            else:
                os.environ.pop("APP_ENV", None)
            if original_jwt is not None:
                os.environ["JWT_SECRET_KEY"] = original_jwt
            else:
                os.environ.pop("JWT_SECRET_KEY", None)
            if original_debug is not None:
                os.environ["DEBUG"] = original_debug
            else:
                os.environ.pop("DEBUG", None)
            if original_db_url is not None:
                os.environ["DATABASE_URL"] = original_db_url
            else:
                os.environ.pop("DATABASE_URL", None)

    def test_production_rejects_default_database_credentials(self) -> None:
        """Production mode should refuse to start with default DB credentials."""
        get_settings.cache_clear()

        original_env = os.environ.get("APP_ENV")
        original_jwt = os.environ.get("JWT_SECRET_KEY")
        original_debug = os.environ.get("DEBUG")
        original_db_url = os.environ.get("DATABASE_URL")

        try:
            os.environ["APP_ENV"] = "production"
            os.environ["JWT_SECRET_KEY"] = "a-very-secure-custom-secret-key-here"
            os.environ["DEBUG"] = "false"
            os.environ["DATABASE_URL"] = "postgresql://arbor:arbor@localhost:5432/arbor"

            with pytest.raises(RuntimeError, match="DATABASE_URL"):
                get_settings()
        finally:
            get_settings.cache_clear()
            if original_env is not None:
                os.environ["APP_ENV"] = original_env
            else:
                os.environ.pop("APP_ENV", None)
            if original_jwt is not None:
                os.environ["JWT_SECRET_KEY"] = original_jwt
            else:
                os.environ.pop("JWT_SECRET_KEY", None)
            if original_debug is not None:
                os.environ["DEBUG"] = original_debug
            else:
                os.environ.pop("DEBUG", None)
            if original_db_url is not None:
                os.environ["DATABASE_URL"] = original_db_url
            else:
                os.environ.pop("DATABASE_URL", None)
