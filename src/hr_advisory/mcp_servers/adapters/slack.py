"""Slack Bot adapter for notifications and interactive messages.

Posts messages, interactive button prompts, and handles slash command
registration via the Slack Web API. OAuth bot token from env var.

T245: Slack Bot Connector (C05)
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Callable, Optional

import httpx

from hr_advisory.mcp_servers.resilience import get_circuit

logger = logging.getLogger(__name__)

_SLACK_API_BASE = "https://slack.com/api/"


class SlackAPIError(Exception):
    """Raised when a Slack API call returns ok=false."""

    def __init__(self, method: str, error: str, detail: str = ""):
        self.method = method
        self.error = error
        self.detail = detail
        super().__init__(f"Slack API {method} failed: {error}{' — ' + detail if detail else ''}")


class SlackAdapter:
    """Adapter for the Slack Web API (Bot token mode).

    Supports:
    - Posting plain and rich-formatted messages to channels/DMs
    - Interactive messages with approve/reject buttons
    - Slash command handler registration (for routing inbound commands)
    - Webhook signature verification for inbound events

    Usage::

        adapter = SlackAdapter()
        result = await adapter.post_message(
            channel="#hr-notifications",
            text="March payroll is ready for review.",
        )
    """

    def __init__(
        self,
        bot_token: Optional[str] = None,
        signing_secret: Optional[str] = None,
    ):
        self._bot_token = bot_token or os.environ.get("SLACK_BOT_TOKEN", "")
        self._signing_secret = signing_secret or os.environ.get("SLACK_SIGNING_SECRET", "")
        self._circuit = get_circuit("slack")
        self._slash_commands: dict[str, Callable] = {}

        if not self._bot_token:
            logger.warning("SLACK_BOT_TOKEN not set — Slack adapter will fail on API calls")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._bot_token}",
            "Content-Type": "application/json; charset=utf-8",
        }

    async def _call_api(self, method: str, payload: dict) -> dict:
        """Call a Slack Web API method through the circuit breaker.

        Args:
            method: Slack API method name (e.g. "chat.postMessage").
            payload: JSON payload for the method.

        Returns:
            The parsed response body on success.

        Raises:
            SlackAPIError: If Slack returns ok=false.
            ExternalAPIUnavailable: If circuit breaker is open.
        """

        async def _do_call() -> dict:
            url = f"{_SLACK_API_BASE}{method}"
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload, headers=self._headers())
                body = resp.json()

                if not body.get("ok"):
                    raise SlackAPIError(
                        method=method,
                        error=body.get("error", "unknown_error"),
                        detail=(
                            body.get("response_metadata", {}).get("messages", [""])[0]
                            if body.get("response_metadata")
                            else ""
                        ),
                    )
                return body

        return await self._circuit.call(_do_call)

    # ── Message sending ─────────────────────────────────────────

    async def post_message(
        self,
        channel: str,
        text: str,
        blocks: Optional[list[dict]] = None,
        thread_ts: Optional[str] = None,
        unfurl_links: bool = False,
    ) -> dict:
        """Post a message to a Slack channel or DM.

        Args:
            channel: Channel ID, channel name (e.g. "#hr-updates"), or
                user ID for DM.
            text: Plain text fallback (shown in notifications and if
                blocks fail to render).
            blocks: Optional Block Kit blocks for rich formatting. See
                https://api.slack.com/block-kit
            thread_ts: If set, posts as a reply in a thread.
            unfurl_links: Whether to unfurl URL previews (default False
                for cleaner notification messages).

        Returns:
            Dict with ts (message timestamp/ID), channel.
        """
        payload: dict[str, Any] = {
            "channel": channel,
            "text": text,
            "unfurl_links": unfurl_links,
        }
        if blocks:
            payload["blocks"] = blocks
        if thread_ts:
            payload["thread_ts"] = thread_ts

        result = await self._call_api("chat.postMessage", payload)
        logger.info(
            "Slack message posted to %s (ts=%s)",
            channel,
            result.get("ts", "unknown"),
        )
        return {
            "ts": result.get("ts"),
            "channel": result.get("channel"),
            "status": "sent",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def send_interactive(
        self,
        channel: str,
        text: str,
        actions: list[dict[str, str]],
        callback_id: Optional[str] = None,
    ) -> dict:
        """Send an interactive message with action buttons.

        Buttons are rendered as a Slack actions block. When a user
        clicks a button, Slack sends an interaction payload to the
        configured request URL.

        Args:
            channel: Channel or user ID.
            text: Message text providing context for the action.
            actions: List of action button dicts. Each must have:
                - "action_id": Unique identifier for the action.
                - "text": Button label (max ~75 chars).
                - "style" (optional): "primary" (green) or "danger" (red).
                - "value" (optional): Payload value sent on click.
            callback_id: Optional identifier for the entire interaction
                (useful for routing responses).

        Returns:
            Dict with ts and channel.
        """
        button_elements = []
        for action in actions:
            element: dict[str, Any] = {
                "type": "button",
                "text": {"type": "plain_text", "text": action["text"]},
                "action_id": action["action_id"],
            }
            if action.get("style"):
                element["style"] = action["style"]
            if action.get("value"):
                element["value"] = action["value"]
            button_elements.append(element)

        blocks = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": text},
            },
            {
                "type": "actions",
                "elements": button_elements,
            },
        ]

        if callback_id:
            blocks[1]["block_id"] = callback_id

        return await self.post_message(channel=channel, text=text, blocks=blocks)

    async def send_notification(
        self,
        channel: str,
        title: str,
        body: str,
        color: str = "#1890ff",
        fields: Optional[list[dict[str, str]]] = None,
        actions: Optional[list[dict[str, str]]] = None,
    ) -> dict:
        """Send a structured notification message.

        Convenience method that builds a well-formatted Block Kit
        message with a header, body text, optional fields (key-value
        pairs), and optional action buttons.

        Args:
            channel: Channel or user ID.
            title: Bold header text.
            body: Description text (supports Slack mrkdwn).
            color: Sidebar color (hex code, e.g. "#36a64f" for green).
            fields: Optional list of {"title": ..., "value": ...} for
                inline fields (e.g. "Period: March 2026").
            actions: Optional action buttons (same format as send_interactive).
        """
        blocks: list[dict[str, Any]] = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": title},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": body},
            },
        ]

        if fields:
            field_elements = [
                {"type": "mrkdwn", "text": f"*{f['title']}*\n{f['value']}"} for f in fields
            ]
            blocks.append({"type": "section", "fields": field_elements})

        if actions:
            button_elements = []
            for action in actions:
                element: dict[str, Any] = {
                    "type": "button",
                    "text": {"type": "plain_text", "text": action["text"]},
                    "action_id": action["action_id"],
                }
                if action.get("style"):
                    element["style"] = action["style"]
                if action.get("value"):
                    element["value"] = action["value"]
                button_elements.append(element)
            blocks.append({"type": "actions", "elements": button_elements})

        return await self.post_message(
            channel=channel,
            text=f"{title}: {body}",
            blocks=blocks,
        )

    # ── Slash commands ───────────────────────────────────────────

    def register_slash_command(self, command: str, handler: Callable) -> None:
        """Register a handler for a Slack slash command.

        The handler receives (user_id, channel_id, text, response_url)
        and should return a dict with "text" (and optional "blocks").

        Commands are registered locally. The Slack App config must
        list the request URL pointing to the AITE webhook endpoint
        for each command.

        Args:
            command: Command name including slash (e.g. "/leave-balance").
            handler: Async callable to process the command.
        """
        if not command.startswith("/"):
            command = f"/{command}"
        self._slash_commands[command] = handler
        logger.info("Registered Slack slash command: %s", command)

    async def handle_slash_command(
        self,
        command: str,
        user_id: str,
        channel_id: str,
        text: str,
        response_url: str,
    ) -> dict:
        """Route an incoming slash command to its registered handler.

        Called by the webhook endpoint when Slack sends a slash command
        interaction.

        Returns:
            Response dict to send back to Slack (with "text" key at minimum).
        """
        handler = self._slash_commands.get(command)
        if handler is None:
            return {
                "response_type": "ephemeral",
                "text": f"Unknown command: {command}. Available: {', '.join(self._slash_commands.keys())}",
            }

        try:
            result = await handler(user_id, channel_id, text, response_url)
            return result
        except Exception as e:
            logger.exception("Slash command %s failed: %s", command, e)
            return {
                "response_type": "ephemeral",
                "text": "Something went wrong processing your command. Please try again.",
            }

    def list_slash_commands(self) -> list[str]:
        """List all registered slash command names."""
        return list(self._slash_commands.keys())

    # ── Webhook verification ─────────────────────────────────────

    def verify_request_signature(
        self,
        timestamp: str,
        body: str,
        signature: str,
    ) -> bool:
        """Verify an incoming Slack request signature.

        Slack signs each request with the app's signing secret using
        HMAC-SHA256. This prevents request forgery.

        Args:
            timestamp: X-Slack-Request-Timestamp header value.
            body: Raw request body string.
            signature: X-Slack-Signature header value (v0=...).

        Returns:
            True if signature is valid, False otherwise.
        """
        if not self._signing_secret:
            logger.warning("SLACK_SIGNING_SECRET not set — cannot verify signatures")
            return False

        # Reject requests older than 5 minutes to prevent replay attacks
        try:
            ts = int(timestamp)
        except (ValueError, TypeError):
            return False

        if abs(time.time() - ts) > 300:
            logger.warning("Slack request timestamp too old: %s", timestamp)
            return False

        sig_basestring = f"v0:{timestamp}:{body}"
        computed = (
            "v0="
            + hmac.new(
                self._signing_secret.encode(),
                sig_basestring.encode(),
                hashlib.sha256,
            ).hexdigest()
        )

        return hmac.compare_digest(computed, signature)

    # ── Utility ──────────────────────────────────────────────────

    async def lookup_user_by_email(self, email: str) -> Optional[str]:
        """Look up a Slack user ID by email address.

        Useful for sending DMs to employees when we only have their
        work email.

        Returns:
            Slack user ID, or None if not found.
        """
        try:
            result = await self._call_api("users.lookupByEmail", {"email": email})
            return result.get("user", {}).get("id")
        except SlackAPIError as e:
            if e.error == "users_not_found":
                return None
            raise

    async def open_dm(self, user_id: str) -> Optional[str]:
        """Open a DM channel with a user.

        Args:
            user_id: Slack user ID.

        Returns:
            DM channel ID, or None on failure.
        """
        try:
            result = await self._call_api("conversations.open", {"users": user_id})
            return result.get("channel", {}).get("id")
        except SlackAPIError:
            logger.exception("Failed to open DM with user %s", user_id)
            return None
