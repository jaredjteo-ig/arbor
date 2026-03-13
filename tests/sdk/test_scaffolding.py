"""Verify project scaffolding is correct."""

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestProjectStructure:
    """Verify all required directories and files exist."""

    def test_backend_package_exists(self):
        assert (PROJECT_ROOT / "src" / "hr_advisory" / "__init__.py").exists()

    def test_backend_subpackages_exist(self):
        for pkg in ["config", "models", "agents", "workflows", "services", "api"]:
            assert (PROJECT_ROOT / "src" / "hr_advisory" / pkg / "__init__.py").exists()

    def test_web_app_exists(self):
        assert (PROJECT_ROOT / "apps" / "web" / "package.json").exists()

    def test_mobile_app_exists(self):
        assert (PROJECT_ROOT / "apps" / "mobile" / "pubspec.yaml").exists()

    def test_docker_compose_exists(self):
        assert (PROJECT_ROOT / "docker-compose.dev.yml").exists()

    def test_env_example_exists(self):
        assert (PROJECT_ROOT / ".env.example").exists()

    def test_conftest_exists(self):
        assert (PROJECT_ROOT / "conftest.py").exists()


class TestConfigSettings:
    """Verify settings load correctly from environment."""

    def test_settings_load(self):
        from hr_advisory.config import get_settings

        settings = get_settings()
        assert settings.app_env in ("development", "staging", "production")

    def test_settings_defaults(self):
        from hr_advisory.config import get_settings

        settings = get_settings()
        assert settings.jwt_algorithm == "HS256"
        assert settings.jwt_expiry_minutes == 60

    def test_package_version(self):
        from hr_advisory import __version__

        assert __version__ == "0.1.0"
