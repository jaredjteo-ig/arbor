"""External API adapters for MCP integration servers.

Each adapter wraps a single external API (or file format generator)
with a standardized interface. Adapters handle authentication,
rate limiting, error handling, and response normalization.

M29 adapters (Regulatory Intelligence + Communications + Quick Wins):

- DataGovSGAdapter: Public holidays, CPF rates from data.gov.sg
- SSORSSAdapter: Legislative RSS feeds from Singapore Statutes Online
- MOMSitemapAdapter: MOM newsroom sitemap monitoring
- ChangeDetectionEngine: Web page change detection for gov sites
- TelegramChannelMonitor: Government Telegram channel monitoring
- RegulatoryChangeClassifier: Deterministic change classification
- ResendAdapter: Transactional email via Resend
- TelegramBotAdapter: Notifications and files via Telegram Bot
- S3StorageAdapter: Document storage on AWS S3
"""

from hr_advisory.mcp_servers.adapters.data_gov_sg import DataGovSGAdapter
from hr_advisory.mcp_servers.adapters.sso_rss import SSORSSAdapter
from hr_advisory.mcp_servers.adapters.mom_sitemap import MOMSitemapAdapter
from hr_advisory.mcp_servers.adapters.change_detector import ChangeDetectionEngine
from hr_advisory.mcp_servers.adapters.telegram_monitor import TelegramChannelMonitor
from hr_advisory.mcp_servers.adapters.regulatory_classifier import (
    RegulatoryChangeClassifier,
    ClassificationInput,
    ClassificationResult,
)
from hr_advisory.mcp_servers.adapters.resend_email import ResendAdapter
from hr_advisory.mcp_servers.adapters.telegram_bot import TelegramBotAdapter
from hr_advisory.mcp_servers.adapters.s3_storage import S3StorageAdapter

__all__ = [
    "DataGovSGAdapter",
    "SSORSSAdapter",
    "MOMSitemapAdapter",
    "ChangeDetectionEngine",
    "TelegramChannelMonitor",
    "RegulatoryChangeClassifier",
    "ClassificationInput",
    "ClassificationResult",
    "ResendAdapter",
    "TelegramBotAdapter",
    "S3StorageAdapter",
]
