"""MOM (Ministry of Manpower) XML sitemap monitor.

Parses the MOM newsroom sitemap to detect new press releases and
announcements relevant to employment regulations.

T217: MOM Sitemap Monitor (R03)
"""

from __future__ import annotations

import hashlib
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import httpx

from hr_advisory.mcp_servers.resilience import get_circuit

logger = logging.getLogger(__name__)

_MOM_SITEMAP_URL = "https://www.mom.gov.sg/newsroom.xml"

# Sitemap XML namespace
_SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"

# URL path patterns that indicate press releases or announcements
_RELEVANT_PATTERNS = [
    "/newsroom/press-releases/",
    "/newsroom/parliament-questions-and-replies/",
    "/newsroom/speeches/",
    "/employment-practices/",
    "/passes-and-permits/",
    "/workplace-safety-and-health/",
]


@dataclass
class SitemapEntry:
    """A single URL entry from the MOM sitemap."""

    url: str
    lastmod: Optional[datetime]
    changefreq: str
    priority: float
    entry_type: str  # "press_release", "announcement", "policy", "other"
    first_seen_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def id(self) -> str:
        return hashlib.sha256(self.url.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "url": self.url,
            "lastmod": self.lastmod.isoformat() if self.lastmod else None,
            "changefreq": self.changefreq,
            "priority": self.priority,
            "entry_type": self.entry_type,
            "first_seen_at": self.first_seen_at.isoformat(),
        }


class MOMSitemapAdapter:
    """Adapter for monitoring MOM's XML sitemap for new content.

    Fetches and parses the MOM newsroom sitemap, comparing against
    previously stored URLs to detect new press releases and policy
    announcements.

    Usage::

        adapter = MOMSitemapAdapter()
        new_urls = await adapter.check_for_new_entries()
        all_entries = adapter.get_all_entries()
    """

    def __init__(self, sitemap_url: str = _MOM_SITEMAP_URL):
        self._sitemap_url = sitemap_url
        self._circuit = get_circuit("mom")
        self._known_urls: dict[str, SitemapEntry] = {}  # url -> entry
        self._last_check: Optional[datetime] = None

    async def check_for_new_entries(self) -> list[SitemapEntry]:
        """Fetch the sitemap and return entries not previously seen.

        New entries are automatically stored for future comparison.
        Also detects entries whose lastmod has changed since last seen.
        """
        entries = await self._fetch_and_parse()
        new_entries: list[SitemapEntry] = []
        updated_entries: list[SitemapEntry] = []

        for entry in entries:
            existing = self._known_urls.get(entry.url)
            if existing is None:
                self._known_urls[entry.url] = entry
                new_entries.append(entry)
            elif (
                entry.lastmod is not None
                and existing.lastmod is not None
                and entry.lastmod > existing.lastmod
            ):
                # URL exists but content was updated
                self._known_urls[entry.url] = entry
                updated_entries.append(entry)

        self._last_check = datetime.now(timezone.utc)

        if new_entries or updated_entries:
            logger.info(
                "MOM sitemap: %d new URLs, %d updated URLs",
                len(new_entries),
                len(updated_entries),
            )
        else:
            logger.debug("MOM sitemap: no changes detected")

        # Return both new and updated entries — both indicate potential
        # regulatory changes worth classifying
        return new_entries + updated_entries

    async def get_press_releases(self) -> list[dict]:
        """Return all known press release entries."""
        return [
            e.to_dict()
            for e in sorted(
                self._known_urls.values(),
                key=lambda e: e.lastmod or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True,
            )
            if e.entry_type == "press_release"
        ]

    async def get_announcements(self) -> list[dict]:
        """Return all known announcement/policy entries."""
        return [
            e.to_dict()
            for e in sorted(
                self._known_urls.values(),
                key=lambda e: e.lastmod or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True,
            )
            if e.entry_type in ("announcement", "policy")
        ]

    def get_all_entries(self) -> list[dict]:
        """Return all stored sitemap entries."""
        return [
            e.to_dict()
            for e in sorted(
                self._known_urls.values(),
                key=lambda e: e.lastmod or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True,
            )
        ]

    async def _fetch_and_parse(self) -> list[SitemapEntry]:
        """Fetch the sitemap XML and parse it into entries."""

        async def _do_fetch() -> str:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    self._sitemap_url,
                    headers=self._request_headers(),
                )
                resp.raise_for_status()
                return resp.text

        xml_text = await self._circuit.call(_do_fetch)
        return self._parse_sitemap(xml_text)

    @staticmethod
    def _request_headers() -> dict[str, str]:
        return {
            "User-Agent": (
                "Mozilla/5.0 (compatible; AITE-Regulatory-Monitor/1.0; "
                "+https://aite.sg; legal-compliance-monitoring)"
            ),
            "Accept": "application/xml, text/xml, */*",
        }

    def _parse_sitemap(self, xml_text: str) -> list[SitemapEntry]:
        """Parse sitemap XML into SitemapEntry objects.

        Handles both standard sitemaps (with <url> entries) and
        sitemap index files (with <sitemap> entries pointing to
        sub-sitemaps).
        """
        entries: list[SitemapEntry] = []

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            logger.warning("Failed to parse MOM sitemap XML: %s", exc)
            return entries

        # Standard sitemap: <urlset> containing <url> elements
        for url_el in root.findall(f"{_SITEMAP_NS}url"):
            entry = self._parse_url_element(url_el)
            if entry is not None:
                entries.append(entry)

        # If no <url> elements found, check for sitemap index
        if not entries:
            for sitemap_el in root.findall(f"{_SITEMAP_NS}sitemap"):
                loc_el = sitemap_el.find(f"{_SITEMAP_NS}loc")
                if loc_el is not None and loc_el.text:
                    logger.debug("Found sub-sitemap: %s", loc_el.text)
                    # Store the sub-sitemap URL as an entry for tracking
                    # (actual fetching of sub-sitemaps would require recursion)

        return entries

    def _parse_url_element(self, url_el: ET.Element) -> Optional[SitemapEntry]:
        """Parse a single <url> element from the sitemap."""
        loc_el = url_el.find(f"{_SITEMAP_NS}loc")
        if loc_el is None or not loc_el.text:
            return None

        url = loc_el.text.strip()

        # Parse lastmod
        lastmod_el = url_el.find(f"{_SITEMAP_NS}lastmod")
        lastmod = None
        if lastmod_el is not None and lastmod_el.text:
            lastmod = self._parse_lastmod(lastmod_el.text.strip())

        # Parse changefreq
        changefreq_el = url_el.find(f"{_SITEMAP_NS}changefreq")
        changefreq = ""
        if changefreq_el is not None and changefreq_el.text:
            changefreq = changefreq_el.text.strip()

        # Parse priority
        priority_el = url_el.find(f"{_SITEMAP_NS}priority")
        priority = 0.5
        if priority_el is not None and priority_el.text:
            try:
                priority = float(priority_el.text.strip())
            except ValueError:
                pass

        # Classify the URL type based on path
        entry_type = self._classify_url(url)

        return SitemapEntry(
            url=url,
            lastmod=lastmod,
            changefreq=changefreq,
            priority=priority,
            entry_type=entry_type,
        )

    @staticmethod
    def _classify_url(url: str) -> str:
        """Classify a URL into a content type based on its path."""
        lower_url = url.lower()
        if "/press-releases/" in lower_url or "/press-release/" in lower_url:
            return "press_release"
        if "/parliament-questions" in lower_url or "/speeches/" in lower_url:
            return "announcement"
        if "/employment-practices/" in lower_url or "/passes-and-permits/" in lower_url:
            return "policy"
        if "/workplace-safety" in lower_url:
            return "policy"
        return "other"

    @staticmethod
    def _parse_lastmod(date_str: str) -> Optional[datetime]:
        """Parse a sitemap lastmod date.

        Supports full ISO 8601 and date-only formats:
        - 2026-03-15T10:30:00+08:00
        - 2026-03-15
        """
        # Try full ISO 8601
        try:
            cleaned = date_str.replace("Z", "+00:00")
            return datetime.fromisoformat(cleaned)
        except ValueError:
            pass

        # Try date-only
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass

        logger.debug("Could not parse lastmod date: %s", date_str)
        return None

    def get_monitor_status(self) -> dict:
        """Return current monitoring status."""
        by_type: dict[str, int] = {}
        for entry in self._known_urls.values():
            by_type[entry.entry_type] = by_type.get(entry.entry_type, 0) + 1

        return {
            "sitemap_url": self._sitemap_url,
            "total_urls_tracked": len(self._known_urls),
            "urls_by_type": by_type,
            "last_check": self._last_check.isoformat() if self._last_check else None,
        }
