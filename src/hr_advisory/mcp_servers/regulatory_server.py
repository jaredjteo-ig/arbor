"""aite-regulatory MCP server.

Provides regulatory intelligence tools for the shadow agent:
- Real-time government data (public holidays, CPF rates)
- Legislative amendment monitoring (SSO RSS, MOM sitemap)
- Web change detection (CPF Board, IRAS, TAFEP, eGazette)
- Telegram government channel monitoring
- Regulatory change classification and summarization

T213: aite-regulatory MCP Server Shell
T214-T220: Individual connector implementations
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from hr_advisory.mcp_servers.base import AiteMCPServer, TenantContext
from hr_advisory.mcp_servers.adapters.data_gov_sg import DataGovSGAdapter
from hr_advisory.mcp_servers.adapters.sso_rss import SSORSSAdapter
from hr_advisory.mcp_servers.adapters.mom_sitemap import MOMSitemapAdapter
from hr_advisory.mcp_servers.adapters.change_detector import ChangeDetectionEngine
from hr_advisory.mcp_servers.adapters.telegram_monitor import TelegramChannelMonitor
from hr_advisory.mcp_servers.adapters.regulatory_classifier import (
    RegulatoryChangeClassifier,
    ClassificationInput,
)
from hr_advisory.workflows.regulatory_updates import (
    list_updates,
    get_staleness_summary,
)

logger = logging.getLogger(__name__)

# ── Singleton adapter instances ───────────────────────────────
# Created once at server init, reused across all tool invocations.
# This preserves in-memory caches and seen-entry tracking.

_data_gov: DataGovSGAdapter | None = None
_sso_rss: SSORSSAdapter | None = None
_mom_sitemap: MOMSitemapAdapter | None = None
_change_detector: ChangeDetectionEngine | None = None
_telegram_monitor: TelegramChannelMonitor | None = None
_classifier: RegulatoryChangeClassifier | None = None


def _get_data_gov() -> DataGovSGAdapter:
    global _data_gov
    if _data_gov is None:
        _data_gov = DataGovSGAdapter()
    return _data_gov


def _get_sso_rss() -> SSORSSAdapter:
    global _sso_rss
    if _sso_rss is None:
        _sso_rss = SSORSSAdapter()
    return _sso_rss


def _get_mom_sitemap() -> MOMSitemapAdapter:
    global _mom_sitemap
    if _mom_sitemap is None:
        _mom_sitemap = MOMSitemapAdapter()
    return _mom_sitemap


def _get_change_detector() -> ChangeDetectionEngine:
    global _change_detector
    if _change_detector is None:
        _change_detector = ChangeDetectionEngine()
    return _change_detector


def _get_telegram_monitor() -> TelegramChannelMonitor:
    global _telegram_monitor
    if _telegram_monitor is None:
        _telegram_monitor = TelegramChannelMonitor()
    return _telegram_monitor


def _get_classifier() -> RegulatoryChangeClassifier:
    global _classifier
    if _classifier is None:
        _classifier = RegulatoryChangeClassifier()
    return _classifier


# ── MCP Server ────────────────────────────────────────────────

server = AiteMCPServer(
    name="aite-regulatory",
    description=(
        "Regulatory intelligence: live government data, legislative monitoring, "
        "web change detection, and regulatory change classification."
    ),
    version="1.0.0",
)


# ── MCP Resources ────────────────────────────────────────────
# Read-only data accessible by the shadow agent without tool invocation.


@server.resource(
    uri="regulatory://public-holidays/{year}",
    name="SG Public Holidays",
    description="Gazetted Singapore public holidays for the given year, sourced from data.gov.sg.",
)
def resource_public_holidays() -> dict:
    """Returns a reference to the public holidays resource.

    Actual data is fetched via the government_get_public_holidays tool.
    This resource registration makes it discoverable via MCP resource listing.
    """
    return {
        "description": "Use government_get_public_holidays tool to fetch holiday data",
        "source": "data.gov.sg",
        "resource_id": "d_149b61ad0a22f61c09dc80f2df5bbec8",
    }


@server.resource(
    uri="regulatory://cpf/rates/{year}",
    name="CPF Contribution Rates",
    description="CPF contribution rate tables from data.gov.sg, cached with 7-day TTL.",
)
def resource_cpf_rates() -> dict:
    return {
        "description": "Use regulatory_check_cpf_rates tool to fetch and compare rates",
        "source": "data.gov.sg",
        "resource_id": "d_98ffa142ae0dec40391f78f81d26aca9",
    }


@server.resource(
    uri="regulatory://sdl/rates",
    name="SDL Rates",
    description="Skills Development Levy rates. Currently hardcoded: 0.25% of gross, min $2, max $11.25.",
)
def resource_sdl_rates() -> dict:
    return {
        "rate_percent": 0.25,
        "minimum": 2.00,
        "maximum": 11.25,
        "currency": "SGD",
        "source": "Skills Development Levy Act",
        "note": "Rate has been stable since 2008. Monitor via change detection.",
    }


@server.resource(
    uri="regulatory://fwl/rates",
    name="Foreign Worker Levy Rates",
    description="Foreign Worker Levy rates by pass type and sector.",
)
def resource_fwl_rates() -> dict:
    return {
        "work_permit_base": 300,
        "s_pass_base": 450,
        "currency": "SGD",
        "note": "Rates vary by sector, dependency ratio ceiling, and tier. "
        "See MOM website for full rate tables.",
        "source": "MOM",
    }


@server.resource(
    uri="regulatory://updates/feed",
    name="Regulatory Updates Feed",
    description="Recent regulatory updates detected by all monitoring sources.",
)
def resource_updates_feed() -> dict:
    updates = list_updates()
    return {
        "total_updates": len(updates),
        "recent": [
            {
                "id": u.id,
                "title": u.title,
                "source": u.source,
                "urgency": u.urgency.value,
                "status": u.status.value,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in updates[:10]
        ],
        "staleness": get_staleness_summary(),
    }


# ── MCP Tools: Data.gov.sg (G08, G09) ────────────────────────


@server.tool(
    name="government_get_public_holidays",
    description=(
        "Fetch gazetted Singapore public holidays for a given year from data.gov.sg. "
        "Returns date, day of week, and holiday name. Cached for 24 hours."
    ),
)
async def tool_get_public_holidays(ctx: TenantContext, year: int = 2026) -> dict:
    adapter = _get_data_gov()
    holidays = await adapter.fetch_public_holidays(year)
    return {
        "year": year,
        "total": len(holidays),
        "holidays": holidays,
        "source": "data.gov.sg",
        "cached": adapter.get_cache_stats()["active_entries"] > 0,
    }


@server.tool(
    name="regulatory_check_cpf_rates",
    description=(
        "Fetch CPF contribution rates from data.gov.sg and compare against "
        "hardcoded rates in the payroll calculator. Flags any discrepancies."
    ),
)
async def tool_check_cpf_rates(
    ctx: TenantContext,
    hardcoded_rates: dict | None = None,
) -> dict:
    adapter = _get_data_gov()
    rates = await adapter.fetch_cpf_rates()

    result: dict[str, Any] = {
        "total_records": len(rates),
        "source": "data.gov.sg",
    }

    if hardcoded_rates:
        discrepancies = await adapter.check_cpf_rate_discrepancies(hardcoded_rates)
        result["discrepancies"] = discrepancies
        result["has_discrepancies"] = len(discrepancies) > 0
    else:
        result["rates"] = rates[:20]  # Return first 20 records
        result["note"] = "Pass hardcoded_rates to compare against payroll calculator values"

    return result


# ── MCP Tools: SSO RSS Monitor (R01) ─────────────────────────


@server.tool(
    name="regulatory_get_act_amendments",
    description=(
        "Fetch recent RSS entries for a specific Singapore Act from SSO. "
        "Acts: employment_act, cpf_act, efma, wica, wsha, ita, eca, cdcsa, wfa, rra."
    ),
)
async def tool_get_act_amendments(ctx: TenantContext, act_key: str) -> dict:
    adapter = _get_sso_rss()
    entries = await adapter.get_act_amendments(act_key)
    return {
        "act_key": act_key,
        "total": len(entries),
        "entries": entries,
        "source": "Singapore Statutes Online RSS",
    }


@server.tool(
    name="regulatory_check_updates",
    description=(
        "Poll ALL regulatory monitoring sources for new changes: "
        "SSO RSS feeds, MOM sitemap, web change detection, and Telegram channels. "
        "Returns only new entries not seen in previous checks. "
        "Automatically classifies each change for relevance and urgency."
    ),
)
async def tool_check_updates(ctx: TenantContext) -> dict:
    results: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sources": {},
        "all_new_changes": [],
        "classified": [],
    }

    # 1. SSO RSS
    sso = _get_sso_rss()
    try:
        sso_entries = await sso.check_for_updates()
        results["sources"]["sso_rss"] = {
            "new_entries": len(sso_entries),
            "entries": [e.to_dict() for e in sso_entries[:10]],
        }
        for entry in sso_entries:
            results["all_new_changes"].append(
                {
                    "source": "sso_rss",
                    "title": entry.title,
                    "url": entry.link,
                }
            )
    except Exception as exc:
        results["sources"]["sso_rss"] = {"error": str(exc)}

    # 2. MOM Sitemap
    mom = _get_mom_sitemap()
    try:
        mom_entries = await mom.check_for_new_entries()
        results["sources"]["mom_sitemap"] = {
            "new_entries": len(mom_entries),
            "entries": [e.to_dict() for e in mom_entries[:10]],
        }
        for entry in mom_entries:
            results["all_new_changes"].append(
                {
                    "source": "mom_sitemap",
                    "title": entry.url,
                    "url": entry.url,
                }
            )
    except Exception as exc:
        results["sources"]["mom_sitemap"] = {"error": str(exc)}

    # 3. Web Change Detection
    detector = _get_change_detector()
    try:
        changes = await detector.check_all_pages()
        results["sources"]["change_detection"] = {
            "changes_detected": len(changes),
            "changes": [c.to_dict() for c in changes[:10]],
        }
        for change in changes:
            results["all_new_changes"].append(
                {
                    "source": "change_detection",
                    "title": change.page_name,
                    "url": change.url,
                    "diff_summary": change.diff_summary,
                }
            )
    except Exception as exc:
        results["sources"]["change_detection"] = {"error": str(exc)}

    # 4. Telegram Channels
    tg = _get_telegram_monitor()
    try:
        posts = await tg.check_channels()
        relevant = [p for p in posts if p.is_relevant]
        results["sources"]["telegram"] = {
            "new_posts": len(posts),
            "relevant_posts": len(relevant),
            "posts": [p.to_dict() for p in relevant[:10]],
        }
        for post in relevant:
            results["all_new_changes"].append(
                {
                    "source": "telegram",
                    "title": post.text[:100] if post.text else "",
                    "url": post.url,
                }
            )
    except Exception as exc:
        results["sources"]["telegram"] = {"error": str(exc)}

    # 5. Classify all detected changes
    classifier = _get_classifier()
    for change_item in results["all_new_changes"]:
        classification = classifier.classify(
            ClassificationInput(
                title=change_item.get("title", ""),
                url=change_item.get("url", ""),
                source=change_item.get("source", "unknown"),
                diff_text=change_item.get("diff_summary", ""),
            )
        )
        if classification.is_relevant:
            results["classified"].append(classification.to_dict())

    results["summary"] = {
        "total_new_changes": len(results["all_new_changes"]),
        "relevant_classified": len(results["classified"]),
    }

    return results


# ── MCP Tools: Regulatory Classifier (R06) ───────────────────


@server.tool(
    name="regulatory_classify_change",
    description=(
        "Classify a regulatory change for HR relevance, affected domains, "
        "and urgency. Uses deterministic keyword matching."
    ),
)
async def tool_classify_change(
    ctx: TenantContext,
    title: str,
    url: str,
    source: str = "manual",
    description: str = "",
    diff_text: str = "",
) -> dict:
    classifier = _get_classifier()
    result = classifier.classify(
        ClassificationInput(
            title=title,
            url=url,
            source=source,
            description=description,
            diff_text=diff_text,
        )
    )
    return result.to_dict()


@server.tool(
    name="regulatory_get_monitor_status",
    description=(
        "Get the status of all regulatory monitoring sources: "
        "which feeds are being tracked, when they were last checked, "
        "how many entries have been seen."
    ),
)
async def tool_get_monitor_status(ctx: TenantContext) -> dict:
    return {
        "sso_rss": _get_sso_rss().get_check_status(),
        "mom_sitemap": _get_mom_sitemap().get_monitor_status(),
        "change_detection": _get_change_detector().get_engine_status(),
        "telegram": _get_telegram_monitor().get_monitor_status(),
        "classifier": _get_classifier().get_classification_stats(),
        "data_gov_sg_cache": _get_data_gov().get_cache_stats(),
    }


@server.tool(
    name="regulatory_get_recent_classifications",
    description="Get recent regulatory change classifications with domains and urgency.",
)
async def tool_get_recent_classifications(
    ctx: TenantContext,
    limit: int = 20,
) -> dict:
    classifier = _get_classifier()
    return {
        "classifications": classifier.get_recent_classifications(limit),
        "stats": classifier.get_classification_stats(),
    }


@server.tool(
    name="regulatory_get_recent_changes",
    description="Get recent web page changes detected by the change detection engine.",
)
async def tool_get_recent_changes(
    ctx: TenantContext,
    limit: int = 20,
) -> dict:
    detector = _get_change_detector()
    return {
        "changes": detector.get_recent_changes(limit),
        "status": detector.get_engine_status(),
    }
