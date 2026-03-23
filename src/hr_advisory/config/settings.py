"""Application settings — single source of truth for all configuration.

All API keys, model names, and URLs come from environment variables.
Never hardcode secrets or model strings.
"""

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

# Load .env file so that OPENAI_API_KEY and other secrets are available
# even when the server is started without a shell that sources .env.
# override=False means existing env vars take precedence over .env values.
load_dotenv(override=False)


@dataclass(frozen=True)
class Settings:
    """Application configuration loaded from environment variables."""

    # Application
    app_env: str = "development"
    debug: bool = True
    log_level: str = "INFO"

    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000"  # Comma-separated list

    # Database
    database_url: str = "postgresql://arbor:arbor@localhost:5432/arbor"
    redis_url: str = "redis://localhost:6379/0"

    # LLM
    openai_api_key: str = ""
    openai_prod_model: str = "gpt-4o"
    openai_dev_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    default_llm_model: str = "gpt-4o"

    # Ollama (local LLM fallback)
    ollama_model: str = ""  # e.g. "qwen2.5:32b-instruct-q8_0"
    ollama_base_url: str = "http://localhost:11434"

    # Authentication
    jwt_secret_key: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    google_oauth_redirect_uri: str = ""

    # Email
    sendgrid_api_key: str = ""
    from_email: str = "noreply@arbor.sg"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def cors_origins_list(self) -> list:
        """Parse comma-separated CORS origins into a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load settings from environment variables. Cached after first call."""
    app_env = os.environ.get("APP_ENV", "development")
    jwt_secret = os.environ.get("JWT_SECRET_KEY", "change-this-in-production")

    # SECURITY: Block startup if production uses the default JWT secret
    if app_env == "production" and jwt_secret == "change-this-in-production":
        raise RuntimeError(
            "FATAL: JWT_SECRET_KEY must be set to a secure value in production. "
            'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(64))"'
        )

    # SECURITY: Block startup if production uses the default database credentials
    database_url = os.environ.get("DATABASE_URL", "postgresql://arbor:arbor@localhost:5432/arbor")
    if app_env == "production" and "arbor:arbor" in database_url:
        raise RuntimeError(
            "FATAL: DATABASE_URL must not use default credentials (arbor:arbor) in production. "
            "Set DATABASE_URL to a connection string with secure credentials."
        )

    debug = os.environ.get("DEBUG", "true").lower() == "true"

    # SECURITY: Block startup if production runs in debug mode
    if app_env == "production" and debug:
        raise RuntimeError(
            "FATAL: DEBUG must be set to 'false' in production. "
            "Set DEBUG=false in your environment."
        )

    return Settings(
        app_env=app_env,
        debug=debug,
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
        api_host=os.environ.get("API_HOST", "0.0.0.0"),
        api_port=int(os.environ.get("API_PORT", "8000")),
        cors_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000"),
        database_url=database_url,
        redis_url=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
        openai_prod_model=os.environ.get("OPENAI_PROD_MODEL", "gpt-5-mini-2025-08-07"),
        openai_dev_model=os.environ.get("OPENAI_DEV_MODEL", "gpt-5-mini-2025-08-07"),
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        default_llm_model=os.environ.get("DEFAULT_LLM_MODEL", "gpt-5-mini-2025-08-07"),
        ollama_model=os.environ.get("OLLAMA_MODEL", ""),
        ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        jwt_secret_key=jwt_secret,
        jwt_algorithm=os.environ.get("JWT_ALGORITHM", "HS256"),
        jwt_expiry_minutes=int(os.environ.get("JWT_EXPIRY_MINUTES", "60")),
        google_oauth_client_id=os.environ.get("GOOGLE_OAUTH_CLIENT_ID", ""),
        google_oauth_client_secret=os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", ""),
        google_oauth_redirect_uri=os.environ.get("GOOGLE_OAUTH_REDIRECT_URI", ""),
        sendgrid_api_key=os.environ.get("SENDGRID_API_KEY", ""),
        from_email=os.environ.get("FROM_EMAIL", "noreply@arbor.sg"),
    )
