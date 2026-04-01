"""Web change detection engine for government pages.

Monitors configurable list of URLs (CPF Board news, IRAS newsroom,
TAFEP guidelines, eGazette) by fetching page content, computing
hashes, and detecting changes between runs.

T218: Web Change Detection Engine (R04)
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from difflib import unified_diff
from typing import Optional
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from hr_advisory.mcp_servers.resilience import get_circuit

logger = logging.getLogger(__name__)


@dataclass
class MonitoredPage:
    """Configuration for a single page to monitor."""

    url: str
    name: str
    css_selector: str  # Reserved for future HTML parsing; currently uses full body
    check_frequency: str  # "daily" or "weekly"
    category: str  # e.g. "cpf", "iras", "tafep", "mom", "gazette"


@dataclass
class PageSnapshot:
    """Stored snapshot of a monitored page."""

    url: str
    content_hash: str
    content_text: str  # Plain text extraction of the page body
    checked_at: datetime
    changed_at: Optional[datetime] = None
    previous_hash: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "content_hash": self.content_hash,
            "checked_at": self.checked_at.isoformat(),
            "changed_at": self.changed_at.isoformat() if self.changed_at else None,
            "content_length": len(self.content_text),
        }


@dataclass
class ChangeDetection:
    """Record of a detected change on a monitored page."""

    url: str
    page_name: str
    category: str
    old_hash: str
    new_hash: str
    diff_summary: str
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "page_name": self.page_name,
            "category": self.category,
            "old_hash": self.old_hash,
            "new_hash": self.new_hash,
            "diff_summary": self.diff_summary,
            "detected_at": self.detected_at.isoformat(),
        }


# Default pages to monitor — SG government regulatory sources
DEFAULT_MONITORED_PAGES: list[MonitoredPage] = [
    MonitoredPage(
        url="https://www.cpf.gov.sg/member/infohub/news/news-releases",
        name="CPF Board News Releases",
        css_selector="main",
        check_frequency="daily",
        category="cpf",
    ),
    MonitoredPage(
        url="https://www.iras.gov.sg/news-events/newsroom",
        name="IRAS Newsroom",
        css_selector="main",
        check_frequency="daily",
        category="iras",
    ),
    MonitoredPage(
        url="https://www.tal.sg/tafep/getting-started/fair/tripartite-guidelines",
        name="TAFEP Tripartite Guidelines",
        css_selector="main",
        check_frequency="weekly",
        category="tafep",
    ),
    MonitoredPage(
        url="https://www.mom.gov.sg/employment-practices/employment-act",
        name="MOM Employment Act Page",
        css_selector="main",
        check_frequency="weekly",
        category="mom",
    ),
    MonitoredPage(
        url="https://www.egazette.gov.sg/",
        name="eGazette Browse",
        css_selector="main",
        check_frequency="daily",
        category="gazette",
    ),
]


class ChangeDetectionEngine:
    """Web change detection engine for regulatory monitoring.

    Fetches web pages, extracts text content, computes content hashes,
    and detects changes between runs. Uses polite crawling practices:
    proper User-Agent, respects robots.txt, 1-second delay between requests.

    Usage::

        engine = ChangeDetectionEngine()
        changes = await engine.check_all_pages()
        for change in changes:
            print(f"Change detected: {change.page_name}")
    """

    def __init__(
        self,
        pages: Optional[list[MonitoredPage]] = None,
        crawl_delay: float = 1.0,
    ):
        self._pages = {p.url: p for p in (pages or DEFAULT_MONITORED_PAGES)}
        self._snapshots: dict[str, PageSnapshot] = {}
        self._changes: list[ChangeDetection] = []
        self._crawl_delay = crawl_delay
        self._robots_cache: dict[str, Optional[RobotFileParser]] = {}
        self._circuit = get_circuit("data_gov_sg")  # Shared gov circuit

    @property
    def monitored_pages(self) -> list[dict]:
        """Return list of all monitored pages."""
        return [
            {
                "url": p.url,
                "name": p.name,
                "category": p.category,
                "check_frequency": p.check_frequency,
                "has_snapshot": p.url in self._snapshots,
            }
            for p in self._pages.values()
        ]

    def add_page(self, page: MonitoredPage) -> None:
        """Add a page to the monitoring list."""
        self._pages[page.url] = page

    def remove_page(self, url: str) -> bool:
        """Remove a page from monitoring. Returns True if it existed."""
        if url in self._pages:
            del self._pages[url]
            return True
        return False

    async def check_all_pages(self) -> list[ChangeDetection]:
        """Check all monitored pages for changes.

        Fetches each page sequentially with a polite delay between
        requests. Returns list of detected changes.
        """
        changes: list[ChangeDetection] = []

        for url, page in self._pages.items():
            if not await self._is_allowed(url):
                logger.debug("Skipping %s — disallowed by robots.txt", url)
                continue

            try:
                change = await self._check_single_page(page)
                if change is not None:
                    changes.append(change)
                    self._changes.append(change)
            except Exception as exc:
                logger.warning(
                    "Failed to check %s: %s: %s",
                    page.name,
                    type(exc).__name__,
                    exc,
                )

            # Polite crawling delay between requests
            await asyncio.sleep(self._crawl_delay)

        if changes:
            logger.info("Detected %d page changes", len(changes))
        return changes

    async def check_single_page_by_url(self, url: str) -> Optional[ChangeDetection]:
        """Check a single page for changes by URL."""
        page = self._pages.get(url)
        if page is None:
            raise ValueError(f"URL not in monitored pages: {url}")
        return await self._check_single_page(page)

    async def _check_single_page(self, page: MonitoredPage) -> Optional[ChangeDetection]:
        """Fetch a page, compare against stored snapshot, return change if found."""
        content = await self._fetch_page(page.url)
        text = self._extract_text(content)
        new_hash = hashlib.sha256(text.encode()).hexdigest()
        now = datetime.now(timezone.utc)

        existing = self._snapshots.get(page.url)

        if existing is None:
            # First time seeing this page — store baseline, no change
            self._snapshots[page.url] = PageSnapshot(
                url=page.url,
                content_hash=new_hash,
                content_text=text,
                checked_at=now,
            )
            logger.debug("Baseline snapshot stored for %s", page.name)
            return None

        if new_hash == existing.content_hash:
            # No change — just update check time
            existing.checked_at = now
            return None

        # Change detected
        diff_summary = self._compute_diff_summary(existing.content_text, text, page.name)

        change = ChangeDetection(
            url=page.url,
            page_name=page.name,
            category=page.category,
            old_hash=existing.content_hash,
            new_hash=new_hash,
            diff_summary=diff_summary,
        )

        # Update snapshot
        self._snapshots[page.url] = PageSnapshot(
            url=page.url,
            content_hash=new_hash,
            content_text=text,
            checked_at=now,
            changed_at=now,
            previous_hash=existing.content_hash,
        )

        logger.info(
            "Change detected on %s (hash: %s -> %s)",
            page.name,
            existing.content_hash[:8],
            new_hash[:8],
        )
        return change

    async def _fetch_page(self, url: str) -> str:
        """Fetch page HTML through the circuit breaker."""

        async def _do_fetch() -> str:
            async with httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
            ) as client:
                resp = await client.get(url, headers=self._request_headers())
                resp.raise_for_status()
                return resp.text

        return await self._circuit.call(_do_fetch)

    @staticmethod
    def _request_headers() -> dict[str, str]:
        return {
            "User-Agent": (
                "Mozilla/5.0 (compatible; Arbor-Regulatory-Monitor/1.0; "
                "+https://central.kailash.ai; legal-compliance-monitoring)"
            ),
            "Accept": "text/html, application/xhtml+xml, */*",
            "Accept-Language": "en-SG,en;q=0.9",
        }

    @staticmethod
    def _extract_text(html: str) -> str:
        """Extract readable text from HTML, stripping tags and normalizing whitespace.

        This is a lightweight approach that avoids heavy dependencies
        like BeautifulSoup. It strips script/style blocks, HTML tags,
        and collapses whitespace.
        """
        # Remove script and style blocks
        text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
        # Remove HTML comments
        text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
        # Remove all HTML tags
        text = re.sub(r"<[^>]+>", " ", text)
        # Decode common HTML entities
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&nbsp;", " ")
        text = text.replace("&quot;", '"')
        text = text.replace("&#39;", "'")
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def _compute_diff_summary(old_text: str, new_text: str, page_name: str) -> str:
        """Compute a human-readable diff summary between two text snapshots.

        Returns a summary of added and removed lines, limited to a
        reasonable length for notification purposes.
        """
        old_lines = old_text.split(". ")
        new_lines = new_text.split(". ")

        diff = list(
            unified_diff(
                old_lines,
                new_lines,
                fromfile=f"{page_name} (previous)",
                tofile=f"{page_name} (current)",
                lineterm="",
                n=1,
            )
        )

        if not diff:
            return "Content changed but diff is empty (whitespace or formatting change)"

        # Count additions and removals
        added = [line[2:] for line in diff if line.startswith("+ ") and not line.startswith("+++")]
        removed = [
            line[2:] for line in diff if line.startswith("- ") and not line.startswith("---")
        ]

        summary_parts: list[str] = []
        if added:
            preview = "; ".join(added[:3])
            if len(preview) > 300:
                preview = preview[:300] + "..."
            summary_parts.append(f"Added ({len(added)} segments): {preview}")
        if removed:
            preview = "; ".join(removed[:3])
            if len(preview) > 300:
                preview = preview[:300] + "..."
            summary_parts.append(f"Removed ({len(removed)} segments): {preview}")

        return " | ".join(summary_parts) or "Minor content change detected"

    async def _is_allowed(self, url: str) -> bool:
        """Check robots.txt to see if crawling is allowed.

        Caches robots.txt per domain. Returns True if robots.txt
        cannot be fetched (fail open for monitoring).
        """
        parsed = urlparse(url)
        domain = f"{parsed.scheme}://{parsed.netloc}"

        if domain not in self._robots_cache:
            self._robots_cache[domain] = await self._fetch_robots(domain)

        rp = self._robots_cache[domain]
        if rp is None:
            return True  # No robots.txt or fetch failed — allow

        return rp.can_fetch("Arbor-Regulatory-Monitor", url)

    async def _fetch_robots(self, domain: str) -> Optional[RobotFileParser]:
        """Fetch and parse robots.txt for a domain."""
        robots_url = f"{domain}/robots.txt"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(robots_url, headers=self._request_headers())
                if resp.status_code != 200:
                    return None
                rp = RobotFileParser()
                rp.parse(resp.text.splitlines())
                return rp
        except Exception:
            logger.debug("Could not fetch robots.txt from %s", domain)
            return None

    def get_recent_changes(self, limit: int = 50) -> list[dict]:
        """Return recent change detections."""
        sorted_changes = sorted(self._changes, key=lambda c: c.detected_at, reverse=True)
        return [c.to_dict() for c in sorted_changes[:limit]]

    def get_snapshot(self, url: str) -> Optional[dict]:
        """Return the current snapshot for a URL."""
        snap = self._snapshots.get(url)
        return snap.to_dict() if snap else None

    def get_engine_status(self) -> dict:
        """Return overall engine status."""
        return {
            "total_pages_monitored": len(self._pages),
            "pages_with_snapshots": len(self._snapshots),
            "total_changes_detected": len(self._changes),
            "crawl_delay_seconds": self._crawl_delay,
            "pages": self.monitored_pages,
        }
