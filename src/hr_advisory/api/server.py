"""Server entrypoint for the HR Advisory Nexus platform.

Starts the Nexus server with configuration from environment variables.
Can be run directly: ``python -m hr_advisory.api.server``
"""

import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root before any settings are read
_project_root = Path(__file__).resolve().parents[3]
load_dotenv(_project_root / ".env")

from hr_advisory.api.platform import create_platform
from hr_advisory.config.settings import get_settings


def main() -> None:
    """Configure logging and start the Nexus platform."""
    settings = get_settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logger = logging.getLogger(__name__)

    logger.info(
        "Starting HR Advisory API (env=%s, host=%s, port=%d)",
        settings.app_env,
        settings.api_host,
        settings.api_port,
    )

    app = create_platform(settings)

    # app.start() is blocking (runs uvicorn under the hood)
    app.start()


if __name__ == "__main__":
    main()
