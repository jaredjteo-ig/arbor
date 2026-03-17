"""Telegram channel monitor for government regulatory posts.

Monitors public government Telegram channels (@sgministryofmanpower,
@CPFBoard, @govsg) for new posts relevant to HR and employment
regulations.

T219: Telegram Government Channel Monitor (R05)
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from hr_advisory.mcp_servers.resilience import get_circuit

logger = logging.getLogger(__name__)

_TELEGRAM_API_BASE = "https://api.telegram.org"

# Government channels to monitor
DEFAULT_CHANNELS: list[dict[str, str]] = [
    {"username": "sgministryofmanpower", "name": "MOM Singapore"},
    {"username": "CPFBoard", "name": "CPF Board"},
    {"username": "govsg", "name": "Gov.sg"},
]

# Keywords that indicate HR/employment relevance
_HR_KEYWORDS: set[str] = {
    # Employment terms
    "employment",
    "employer",
    "employee",
    "worker",
    "workforce",
    "manpower",
    "labour",
    "labor",
    # Specific Singapore employment topics
    "cpf",
    "central provident fund",
    "medisave",
    "ordinary account",
    "special account",
    "retirement account",
    "employment act",
    "efma",
    "foreign manpower",
    "work permit",
    "s pass",
    "employment pass",
    "work pass",
    "levy",
    "foreign worker levy",
    "minimum wage",
    "progressive wage",
    "wica",
    "work injury",
    "workplace safety",
    "wsha",
    "retrenchment",
    "redundancy",
    "termination",
    "maternity",
    "paternity",
    "childcare leave",
    "parental leave",
    "annual leave",
    "sick leave",
    "medical leave",
    "overtime",
    "working hours",
    "rest day",
    "salary",
    "wages",
    "payroll",
    "bonus",
    "aws",
    "ir8a",
    "iras",
    "income tax",
    "tripartite",
    "tafep",
    "fair employment",
    "sdl",
    "skills development levy",
    "skillsfuture",
    "retirement",
    "re-employment",
    "rra",
    "workplace fairness",
    # Regulatory
    "gazette",
    "amendment",
    "regulation",
    "legislation",
    "act",
    "budget",
    "parliament",
}

# Minimum keyword matches for a post to be considered relevant
_MIN_KEYWORD_MATCHES = 1


@dataclass
class ChannelPost:
    """A single message from a monitored Telegram channel."""

    message_id: int
    channel_username: str
    channel_name: str
    text: str
    date: datetime
    is_relevant: bool
    matched_keywords: list[str]
    has_media: bool
    url: str
    first_seen_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def id(self) -> str:
        return f"{self.channel_username}:{self.message_id}"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "message_id": self.message_id,
            "channel_username": self.channel_username,
            "channel_name": self.channel_name,
            "text": self.text[:500] if self.text else "",
            "date": self.date.isoformat(),
            "is_relevant": self.is_relevant,
            "matched_keywords": self.matched_keywords,
            "has_media": self.has_media,
            "url": self.url,
            "first_seen_at": self.first_seen_at.isoformat(),
        }


class TelegramChannelMonitor:
    """Monitor public Telegram channels for HR/employment-relevant posts.

    Uses the Telegram Bot API to read messages from public channels
    that the bot has been added to (or that are public). Filters
    messages for HR/employment relevance using keyword matching.

    Usage::

        monitor = TelegramChannelMonitor()
        new_posts = await monitor.check_channels()
        relevant = [p for p in new_posts if p.is_relevant]
    """

    def __init__(
        self,
        bot_token: Optional[str] = None,
        channels: Optional[list[dict[str, str]]] = None,
        keywords: Optional[set[str]] = None,
        min_keyword_matches: int = _MIN_KEYWORD_MATCHES,
    ):
        self._bot_token = bot_token or os.environ.get("TELEGRAM_MONITOR_BOT_TOKEN", "")
        self._channels = channels or DEFAULT_CHANNELS
        self._keywords = keywords or _HR_KEYWORDS
        self._min_keyword_matches = min_keyword_matches
        self._circuit = get_circuit("telegram")
        self._seen_posts: dict[str, ChannelPost] = {}  # id -> post
        self._last_message_id: dict[str, int] = {}  # channel_username -> last msg id

    @property
    def _api_base(self) -> str:
        return f"{_TELEGRAM_API_BASE}/bot{self._bot_token}"

    def _validate_token(self) -> None:
        if not self._bot_token:
            raise ValueError(
                "TELEGRAM_MONITOR_BOT_TOKEN not configured. "
                "Set the environment variable or pass bot_token to constructor."
            )

    async def check_channels(self) -> list[ChannelPost]:
        """Check all monitored channels for new posts.

        Returns posts not previously seen. Each post is classified
        for HR/employment relevance using keyword matching.
        """
        self._validate_token()
        all_new: list[ChannelPost] = []

        for channel in self._channels:
            new_posts = await self._check_single_channel(channel["username"], channel["name"])
            all_new.extend(new_posts)

        if all_new:
            relevant_count = sum(1 for p in all_new if p.is_relevant)
            logger.info(
                "Found %d new Telegram posts (%d relevant)",
                len(all_new),
                relevant_count,
            )

        return all_new

    async def get_relevant_posts(self, limit: int = 50) -> list[dict]:
        """Return stored posts that were classified as relevant."""
        relevant = [p for p in self._seen_posts.values() if p.is_relevant]
        relevant.sort(key=lambda p: p.date, reverse=True)
        return [p.to_dict() for p in relevant[:limit]]

    async def _check_single_channel(
        self,
        channel_username: str,
        channel_name: str,
    ) -> list[ChannelPost]:
        """Fetch new messages from a single channel."""
        try:
            updates = await self._get_channel_messages(channel_username)
        except Exception as exc:
            logger.warning(
                "Failed to fetch messages from @%s: %s: %s",
                channel_username,
                type(exc).__name__,
                exc,
            )
            return []

        new_posts: list[ChannelPost] = []
        for msg in updates:
            post = self._parse_message(msg, channel_username, channel_name)
            if post is None:
                continue
            if post.id in self._seen_posts:
                continue
            self._seen_posts[post.id] = post
            new_posts.append(post)

            # Track highest message ID for this channel
            current_max = self._last_message_id.get(channel_username, 0)
            if post.message_id > current_max:
                self._last_message_id[channel_username] = post.message_id

        return new_posts

    async def _get_channel_messages(self, channel_username: str) -> list[dict]:
        """Fetch recent messages from a public channel via Telegram Bot API.

        Uses getUpdates with the channel chat_id (@username format).
        For public channels, the bot needs to be added as an admin,
        or we use the forwarded message approach.

        The Telegram Bot API approach for reading channel messages is
        to use getUpdates if the bot is a channel admin, or to use
        the getChat + getChatHistory-equivalent endpoints.

        Since the official Bot API does not have getChatHistory,
        we use the channel forwarding approach: the bot receives
        forwarded messages from channels it monitors.

        Alternative: Use getUpdates with offset to get new channel_post updates.
        """

        async def _do_fetch() -> list[dict]:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Use getUpdates to get channel_post updates
                params: dict[str, Any] = {
                    "allowed_updates": '["channel_post"]',
                    "timeout": 5,
                }

                # Use offset to only get new messages
                last_id = self._last_message_id.get(channel_username, 0)
                if last_id > 0:
                    params["offset"] = last_id + 1

                resp = await client.get(
                    f"{self._api_base}/getUpdates",
                    params=params,
                )
                resp.raise_for_status()
                data = resp.json()

                if not data.get("ok"):
                    logger.warning(
                        "Telegram API returned ok=false: %s",
                        data.get("description", "unknown"),
                    )
                    return []

                # Extract channel_post updates matching our channel
                messages: list[dict] = []
                for update in data.get("result", []):
                    channel_post = update.get("channel_post", {})
                    chat = channel_post.get("chat", {})
                    chat_username = (chat.get("username") or "").lower()
                    if chat_username == channel_username.lower():
                        messages.append(channel_post)

                return messages

        return await self._circuit.call(_do_fetch)

    def _parse_message(
        self,
        msg: dict,
        channel_username: str,
        channel_name: str,
    ) -> Optional[ChannelPost]:
        """Parse a Telegram message dict into a ChannelPost."""
        message_id = msg.get("message_id")
        if message_id is None:
            return None

        text = msg.get("text") or msg.get("caption") or ""
        date_unix = msg.get("date", 0)
        has_media = any(
            msg.get(media_type) is not None
            for media_type in ("photo", "document", "video", "audio")
        )

        # Parse date
        msg_date = (
            datetime.fromtimestamp(date_unix, tz=timezone.utc)
            if date_unix
            else datetime.now(timezone.utc)
        )

        # Classify relevance
        matched = self._find_keyword_matches(text)
        is_relevant = len(matched) >= self._min_keyword_matches

        # Build public URL
        url = f"https://t.me/{channel_username}/{message_id}"

        return ChannelPost(
            message_id=message_id,
            channel_username=channel_username,
            channel_name=channel_name,
            text=text,
            date=msg_date,
            is_relevant=is_relevant,
            matched_keywords=matched,
            has_media=has_media,
            url=url,
        )

    def _find_keyword_matches(self, text: str) -> list[str]:
        """Find HR/employment keywords in a text string.

        Uses case-insensitive word-boundary matching to avoid
        false positives from partial matches.
        """
        if not text:
            return []

        text_lower = text.lower()
        matched: list[str] = []

        for keyword in self._keywords:
            # Use word boundary matching for single words, substring for phrases
            if " " in keyword:
                # Multi-word phrase: simple substring check
                if keyword in text_lower:
                    matched.append(keyword)
            else:
                # Single word: use word boundary regex
                pattern = rf"\b{re.escape(keyword)}\b"
                if re.search(pattern, text_lower):
                    matched.append(keyword)

        return sorted(set(matched))

    def get_monitor_status(self) -> dict:
        """Return current monitoring status."""
        return {
            "bot_configured": bool(self._bot_token),
            "channels_monitored": len(self._channels),
            "channels": [
                {
                    "username": c["username"],
                    "name": c["name"],
                    "last_message_id": self._last_message_id.get(c["username"]),
                    "posts_seen": sum(
                        1 for p in self._seen_posts.values() if p.channel_username == c["username"]
                    ),
                    "relevant_posts": sum(
                        1
                        for p in self._seen_posts.values()
                        if p.channel_username == c["username"] and p.is_relevant
                    ),
                }
                for c in self._channels
            ],
            "total_posts_stored": len(self._seen_posts),
            "total_relevant": sum(1 for p in self._seen_posts.values() if p.is_relevant),
        }
