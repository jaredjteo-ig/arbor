"""Singapore Statutes Online (SSO) RSS feed adapter.

Monitors RSS feeds for amendments to Singapore employment-related
Acts: Employment Act, CPF Act, EFMA, WICA, WSHA, ITA, ECA, CDCSA,
WFA, RRA.

T216: SSO Per-Act RSS Monitor (R01)
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

# SSO base URL for legislation RSS feeds.
# Each Act has a unique title slug used in the feed URL.
_SSO_BASE = "https://sso.agc.gov.sg"

# Map of Act short names to their SSO Act identifiers.
# These are used to construct the RSS feed URL for each Act.
_ACT_FEEDS: dict[str, dict[str, str]] = {
    "employment_act": {
        "name": "Employment Act 1968",
        "feed_path": "/RSS/CurrentVersionRss?TransactionDate=&ViewType=Sl&PageIndex=0&CurrentPage=0&ActTitle=Employment+Act+1968",
    },
    "cpf_act": {
        "name": "Central Provident Fund Act 1953",
        "feed_path": "/RSS/CurrentVersionRss?TransactionDate=&ViewType=Sl&PageIndex=0&CurrentPage=0&ActTitle=Central+Provident+Fund+Act+1953",
    },
    "efma": {
        "name": "Employment of Foreign Manpower Act 1990",
        "feed_path": "/RSS/CurrentVersionRss?TransactionDate=&ViewType=Sl&PageIndex=0&CurrentPage=0&ActTitle=Employment+of+Foreign+Manpower+Act+1990",
    },
    "wica": {
        "name": "Work Injury Compensation Act 2019",
        "feed_path": "/RSS/CurrentVersionRss?TransactionDate=&ViewType=Sl&PageIndex=0&CurrentPage=0&ActTitle=Work+Injury+Compensation+Act+2019",
    },
    "wsha": {
        "name": "Workplace Safety and Health Act 2006",
        "feed_path": "/RSS/CurrentVersionRss?TransactionDate=&ViewType=Sl&PageIndex=0&CurrentPage=0&ActTitle=Workplace+Safety+and+Health+Act+2006",
    },
    "ita": {
        "name": "Income Tax Act 1947",
        "feed_path": "/RSS/CurrentVersionRss?TransactionDate=&ViewType=Sl&PageIndex=0&CurrentPage=0&ActTitle=Income+Tax+Act+1947",
    },
    "eca": {
        "name": "Employment Claims Act 2016",
        "feed_path": "/RSS/CurrentVersionRss?TransactionDate=&ViewType=Sl&PageIndex=0&CurrentPage=0&ActTitle=Employment+Claims+Act+2016",
    },
    "cdcsa": {
        "name": "Child Development Co-Savings Act 2001",
        "feed_path": "/RSS/CurrentVersionRss?TransactionDate=&ViewType=Sl&PageIndex=0&CurrentPage=0&ActTitle=Child+Development+Co-Savings+Act+2001",
    },
    "wfa": {
        "name": "Workplace Fairness Act 2025",
        "feed_path": "/RSS/CurrentVersionRss?TransactionDate=&ViewType=Sl&PageIndex=0&CurrentPage=0&ActTitle=Workplace+Fairness+Act+2025",
    },
    "rra": {
        "name": "Retirement and Re-employment Act 1993",
        "feed_path": "/RSS/CurrentVersionRss?TransactionDate=&ViewType=Sl&PageIndex=0&CurrentPage=0&ActTitle=Retirement+and+Re-employment+Act+1993",
    },
}

# Common RSS XML namespace prefixes
_RSS_NAMESPACES = {
    "atom": "http://www.w3.org/2005/Atom",
    "dc": "http://purl.org/dc/elements/1.1/",
}


@dataclass
class FeedEntry:
    """A single RSS feed entry representing a legislative change."""

    id: str
    act_key: str
    act_name: str
    title: str
    link: str
    published: Optional[datetime]
    description: str
    first_seen_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "act_key": self.act_key,
            "act_name": self.act_name,
            "title": self.title,
            "link": self.link,
            "published": self.published.isoformat() if self.published else None,
            "description": self.description,
            "first_seen_at": self.first_seen_at.isoformat(),
        }


class SSORSSAdapter:
    """Adapter for Singapore Statutes Online RSS feeds.

    Monitors legislative RSS feeds for employment-related Acts.
    Tracks previously seen entries to detect new amendments.

    Usage::

        adapter = SSORSSAdapter()
        new_entries = await adapter.check_for_updates()
        amendments = await adapter.get_act_amendments("employment_act")
    """

    def __init__(self):
        self._circuit = get_circuit("mom")  # SSO shares gov circuit
        self._seen_entries: dict[str, FeedEntry] = {}  # id -> FeedEntry
        self._last_check: dict[str, datetime] = {}  # act_key -> last check time

    @property
    def tracked_acts(self) -> list[dict[str, str]]:
        """Return list of all tracked Acts with their names."""
        return [{"key": k, "name": v["name"]} for k, v in _ACT_FEEDS.items()]

    async def check_for_updates(self) -> list[FeedEntry]:
        """Poll all RSS feeds and return new entries not previously seen.

        Returns only entries that were not in the store from the last check.
        New entries are automatically stored for future comparison.
        """
        all_new: list[FeedEntry] = []
        for act_key in _ACT_FEEDS:
            new_entries = await self._check_single_feed(act_key)
            all_new.extend(new_entries)

        if all_new:
            logger.info(
                "Found %d new legislative entries across %d Acts",
                len(all_new),
                len({e.act_key for e in all_new}),
            )
        else:
            logger.debug("No new legislative entries found")

        return all_new

    async def get_act_amendments(self, act_key: str) -> list[dict]:
        """Fetch current RSS entries for a specific Act.

        Args:
            act_key: Short key for the Act (e.g. "employment_act", "cpf_act").

        Returns:
            List of entry dicts with title, link, published date, description.
        """
        if act_key not in _ACT_FEEDS:
            available = ", ".join(sorted(_ACT_FEEDS.keys()))
            raise ValueError(f"Unknown act key '{act_key}'. Available: {available}")

        entries = await self._fetch_feed(act_key)
        return [e.to_dict() for e in entries]

    async def get_all_stored_entries(self) -> list[dict]:
        """Return all stored entries across all Acts, sorted by published date."""
        entries = sorted(
            self._seen_entries.values(),
            key=lambda e: e.published or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        return [e.to_dict() for e in entries]

    async def _check_single_feed(self, act_key: str) -> list[FeedEntry]:
        """Check a single Act's RSS feed for new entries."""
        try:
            entries = await self._fetch_feed(act_key)
        except Exception as exc:
            logger.warning(
                "Failed to fetch RSS feed for %s: %s",
                act_key,
                type(exc).__name__,
            )
            return []

        new_entries: list[FeedEntry] = []
        for entry in entries:
            if entry.id not in self._seen_entries:
                self._seen_entries[entry.id] = entry
                new_entries.append(entry)

        self._last_check[act_key] = datetime.now(timezone.utc)
        return new_entries

    async def _fetch_feed(self, act_key: str) -> list[FeedEntry]:
        """Fetch and parse an RSS feed for a specific Act."""
        act_info = _ACT_FEEDS[act_key]
        url = _SSO_BASE + act_info["feed_path"]

        async def _do_fetch() -> str:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, headers=self._request_headers())
                resp.raise_for_status()
                return resp.text

        xml_text = await self._circuit.call(_do_fetch)
        return self._parse_rss(xml_text, act_key, act_info["name"])

    @staticmethod
    def _request_headers() -> dict[str, str]:
        """Return headers that SSO accepts.

        SSO is known to return 403 to some automated fetchers,
        so we use a browser-like User-Agent.
        """
        return {
            "User-Agent": (
                "Mozilla/5.0 (compatible; Arbor-Regulatory-Monitor/1.0; "
                "+https://central.kailash.ai; legal-compliance-monitoring)"
            ),
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
            "Accept-Language": "en-SG,en;q=0.9",
        }

    def _parse_rss(
        self,
        xml_text: str,
        act_key: str,
        act_name: str,
    ) -> list[FeedEntry]:
        """Parse RSS XML into FeedEntry objects.

        Handles both RSS 2.0 and Atom feed formats since SSO
        may serve either depending on the endpoint.
        """
        entries: list[FeedEntry] = []

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            logger.warning("Failed to parse RSS XML for %s: %s", act_key, exc)
            return entries

        # Try RSS 2.0 format first
        items = root.findall(".//item")
        if items:
            for item in items:
                entry = self._parse_rss_item(item, act_key, act_name)
                if entry:
                    entries.append(entry)
            return entries

        # Fall back to Atom format
        atom_entries = root.findall(".//atom:entry", _RSS_NAMESPACES) or root.findall(
            ".//{http://www.w3.org/2005/Atom}entry"
        )
        for atom_entry in atom_entries:
            entry = self._parse_atom_entry(atom_entry, act_key, act_name)
            if entry:
                entries.append(entry)

        return entries

    def _parse_rss_item(
        self,
        item: ET.Element,
        act_key: str,
        act_name: str,
    ) -> Optional[FeedEntry]:
        """Parse a single RSS 2.0 <item> element."""
        title = self._get_text(item, "title") or ""
        link = self._get_text(item, "link") or ""
        description = self._get_text(item, "description") or ""
        pub_date_str = self._get_text(item, "pubDate") or ""
        guid = self._get_text(item, "guid") or ""

        if not title and not link:
            return None

        # Generate stable ID from guid or link+title hash
        entry_id = guid or self._generate_id(act_key, link, title)
        published = self._parse_rss_date(pub_date_str) if pub_date_str else None

        return FeedEntry(
            id=entry_id,
            act_key=act_key,
            act_name=act_name,
            title=title.strip(),
            link=link.strip(),
            published=published,
            description=description.strip(),
        )

    def _parse_atom_entry(
        self,
        entry_el: ET.Element,
        act_key: str,
        act_name: str,
    ) -> Optional[FeedEntry]:
        """Parse a single Atom <entry> element."""
        ns = "{http://www.w3.org/2005/Atom}"

        title_el = entry_el.find(f"{ns}title")
        title = (title_el.text or "").strip() if title_el is not None else ""

        link_el = entry_el.find(f"{ns}link")
        link = link_el.get("href", "") if link_el is not None else ""

        summary_el = entry_el.find(f"{ns}summary") or entry_el.find(f"{ns}content")
        description = (summary_el.text or "").strip() if summary_el is not None else ""

        updated_el = entry_el.find(f"{ns}updated") or entry_el.find(f"{ns}published")
        pub_str = (updated_el.text or "").strip() if updated_el is not None else ""

        id_el = entry_el.find(f"{ns}id")
        entry_id = (id_el.text or "").strip() if id_el is not None else ""

        if not title and not link:
            return None

        entry_id = entry_id or self._generate_id(act_key, link, title)
        published = self._parse_iso_date(pub_str) if pub_str else None

        return FeedEntry(
            id=entry_id,
            act_key=act_key,
            act_name=act_name,
            title=title,
            link=link,
            published=published,
            description=description,
        )

    @staticmethod
    def _get_text(parent: ET.Element, tag: str) -> Optional[str]:
        """Safely get text content of a child element."""
        child = parent.find(tag)
        if child is not None and child.text:
            return child.text
        return None

    @staticmethod
    def _generate_id(act_key: str, link: str, title: str) -> str:
        """Generate a stable ID from act key, link, and title."""
        raw = f"{act_key}:{link}:{title}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    @staticmethod
    def _parse_rss_date(date_str: str) -> Optional[datetime]:
        """Parse an RSS 2.0 date (RFC 822 format)."""
        # Common RSS date formats
        formats = [
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S %Z",
            "%d %b %Y %H:%M:%S %z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        logger.debug("Could not parse RSS date: %s", date_str)
        return None

    @staticmethod
    def _parse_iso_date(date_str: str) -> Optional[datetime]:
        """Parse an ISO 8601 date string."""
        try:
            # Handle both Z suffix and +00:00
            cleaned = date_str.replace("Z", "+00:00")
            return datetime.fromisoformat(cleaned)
        except ValueError:
            logger.debug("Could not parse ISO date: %s", date_str)
            return None

    def get_check_status(self) -> dict:
        """Return the current monitoring status."""
        return {
            "tracked_acts": len(_ACT_FEEDS),
            "stored_entries": len(self._seen_entries),
            "last_checks": {k: v.isoformat() for k, v in self._last_check.items()},
            "acts": [
                {
                    "key": k,
                    "name": v["name"],
                    "last_checked": (
                        self._last_check[k].isoformat() if k in self._last_check else None
                    ),
                    "entries_seen": sum(1 for e in self._seen_entries.values() if e.act_key == k),
                }
                for k, v in _ACT_FEEDS.items()
            ],
        }
