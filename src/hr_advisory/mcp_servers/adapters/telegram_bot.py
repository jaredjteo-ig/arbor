"""Telegram Bot adapter for sending notifications and documents.

Provides outbound messaging capabilities for the Arbor communications
server: text messages, interactive keyboards, and document delivery
(payslip PDFs) via the Telegram Bot API.

T223: Telegram Bot Connector (C04)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from hr_advisory.mcp_servers.resilience import get_circuit

logger = logging.getLogger(__name__)

_TELEGRAM_API_BASE = "https://api.telegram.org"


class InlineButton:
    """A single inline keyboard button."""

    __slots__ = ("text", "callback_data", "url")

    def __init__(
        self,
        text: str,
        callback_data: Optional[str] = None,
        url: Optional[str] = None,
    ):
        self.text = text
        self.callback_data = callback_data
        self.url = url

    def to_dict(self) -> dict:
        btn: dict[str, str] = {"text": self.text}
        if self.callback_data:
            btn["callback_data"] = self.callback_data
        elif self.url:
            btn["url"] = self.url
        return btn


class InlineKeyboard:
    """Builder for inline keyboard markup.

    Usage::

        kb = InlineKeyboard()
        kb.add_row([
            InlineButton("Approve", callback_data="leave_approve:123"),
            InlineButton("Reject", callback_data="leave_reject:123"),
        ])
        markup = kb.to_dict()
    """

    def __init__(self):
        self._rows: list[list[InlineButton]] = []

    def add_row(self, buttons: list[InlineButton]) -> "InlineKeyboard":
        self._rows.append(buttons)
        return self

    def to_dict(self) -> dict:
        return {"inline_keyboard": [[btn.to_dict() for btn in row] for row in self._rows]}


# Pre-built keyboard templates for common HR actions
def approval_keyboard(entity_type: str, entity_id: str) -> InlineKeyboard:
    """Create an approve/reject keyboard for leave, claims, etc."""
    kb = InlineKeyboard()
    kb.add_row(
        [
            InlineButton("Approve", callback_data=f"{entity_type}_approve:{entity_id}"),
            InlineButton("Reject", callback_data=f"{entity_type}_reject:{entity_id}"),
        ]
    )
    return kb


def payslip_keyboard(employee_id: str, period: str) -> InlineKeyboard:
    """Create a payslip download keyboard."""
    kb = InlineKeyboard()
    kb.add_row(
        [
            InlineButton(
                "Download Payslip",
                callback_data=f"payslip_download:{employee_id}:{period}",
            ),
        ]
    )
    return kb


class TelegramBotAdapter:
    """Adapter for sending messages and documents via Telegram Bot API.

    Handles outbound notifications, interactive keyboards for
    approvals, and file delivery (payslip PDFs) through Telegram.

    Usage::

        bot = TelegramBotAdapter()
        await bot.send_message(chat_id="12345", text="Your leave is approved!")
        await bot.send_document(chat_id="12345", file_bytes=pdf_data, filename="payslip.pdf")
    """

    def __init__(
        self,
        bot_token: Optional[str] = None,
    ):
        self._bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self._circuit = get_circuit("telegram")
        self._send_log: list[dict] = []

    @property
    def _api_base(self) -> str:
        return f"{_TELEGRAM_API_BASE}/bot{self._bot_token}"

    def _validate_token(self) -> None:
        if not self._bot_token:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN not configured. "
                "Set the environment variable or pass bot_token to constructor."
            )

    async def send_message(
        self,
        chat_id: str | int,
        text: str,
        reply_markup: Optional[dict] = None,
        parse_mode: str = "HTML",
        disable_notification: bool = False,
    ) -> dict:
        """Send a text message to a Telegram chat.

        Args:
            chat_id: Telegram chat ID (user, group, or channel).
            text: Message text. Supports HTML formatting.
            reply_markup: Optional inline keyboard markup dict.
            parse_mode: Parse mode ("HTML" or "Markdown").
            disable_notification: If True, send silently.

        Returns:
            Dict with "message_id" and "status".
        """
        self._validate_token()

        payload: dict[str, Any] = {
            "chat_id": str(chat_id),
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        if disable_notification:
            payload["disable_notification"] = True

        async def _do_send() -> dict:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self._api_base}/sendMessage",
                    json=payload,
                )
                resp.raise_for_status()
                return resp.json()

        result = await self._circuit.call(_do_send)

        if not result.get("ok"):
            error_desc = result.get("description", "Unknown error")
            logger.error(
                "Telegram sendMessage failed: %s (chat_id=%s)",
                error_desc,
                chat_id,
            )
            return {"status": "error", "error": error_desc}

        msg = result.get("result", {})
        message_id = msg.get("message_id")

        self._send_log.append(
            {
                "type": "message",
                "chat_id": str(chat_id),
                "message_id": message_id,
                "text_preview": text[:100],
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        logger.info(
            "Telegram message sent: chat_id=%s, message_id=%s",
            chat_id,
            message_id,
        )
        return {"message_id": message_id, "status": "sent"}

    async def send_document(
        self,
        chat_id: str | int,
        file_bytes: bytes,
        filename: str,
        caption: Optional[str] = None,
        reply_markup: Optional[dict] = None,
        disable_notification: bool = False,
    ) -> dict:
        """Send a document (file) to a Telegram chat.

        Args:
            chat_id: Telegram chat ID.
            file_bytes: Raw bytes of the file to send.
            filename: Filename with extension (e.g. "payslip_march_2026.pdf").
            caption: Optional caption text for the document.
            reply_markup: Optional inline keyboard markup dict.
            disable_notification: If True, send silently.

        Returns:
            Dict with "message_id" and "status".
        """
        self._validate_token()

        data: dict[str, Any] = {
            "chat_id": str(chat_id),
        }
        if caption:
            data["caption"] = caption
            data["parse_mode"] = "HTML"
        if reply_markup:
            # reply_markup must be JSON-serialized for multipart
            import json

            data["reply_markup"] = json.dumps(reply_markup)
        if disable_notification:
            data["disable_notification"] = "true"

        files = {
            "document": (filename, file_bytes, self._guess_content_type(filename)),
        }

        async def _do_send() -> dict:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self._api_base}/sendDocument",
                    data=data,
                    files=files,
                )
                resp.raise_for_status()
                return resp.json()

        result = await self._circuit.call(_do_send)

        if not result.get("ok"):
            error_desc = result.get("description", "Unknown error")
            logger.error(
                "Telegram sendDocument failed: %s (chat_id=%s, filename=%s)",
                error_desc,
                chat_id,
                filename,
            )
            return {"status": "error", "error": error_desc}

        msg = result.get("result", {})
        message_id = msg.get("message_id")

        self._send_log.append(
            {
                "type": "document",
                "chat_id": str(chat_id),
                "message_id": message_id,
                "filename": filename,
                "size_bytes": len(file_bytes),
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        logger.info(
            "Telegram document sent: chat_id=%s, filename=%s, size=%d bytes",
            chat_id,
            filename,
            len(file_bytes),
        )
        return {"message_id": message_id, "status": "sent"}

    async def send_leave_approval_request(
        self,
        manager_chat_id: str | int,
        employee_name: str,
        leave_type: str,
        start_date: str,
        end_date: str,
        days: int,
        leave_id: str,
    ) -> dict:
        """Send a leave approval request with approve/reject buttons."""
        text = (
            f"<b>Leave Approval Request</b>\n\n"
            f"<b>Employee:</b> {employee_name}\n"
            f"<b>Type:</b> {leave_type}\n"
            f"<b>Period:</b> {start_date} to {end_date}\n"
            f"<b>Days:</b> {days}\n\n"
            f"Please approve or reject this request."
        )

        kb = approval_keyboard("leave", leave_id)
        return await self.send_message(
            chat_id=manager_chat_id,
            text=text,
            reply_markup=kb.to_dict(),
        )

    async def send_claim_approval_request(
        self,
        manager_chat_id: str | int,
        employee_name: str,
        claim_type: str,
        amount: str,
        claim_id: str,
        description: str = "",
    ) -> dict:
        """Send a claim approval request with approve/reject buttons."""
        text = (
            f"<b>Claim Approval Request</b>\n\n"
            f"<b>Employee:</b> {employee_name}\n"
            f"<b>Type:</b> {claim_type}\n"
            f"<b>Amount:</b> ${amount}\n"
        )
        if description:
            text += f"<b>Description:</b> {description}\n"
        text += "\nPlease approve or reject this claim."

        kb = approval_keyboard("claim", claim_id)
        return await self.send_message(
            chat_id=manager_chat_id,
            text=text,
            reply_markup=kb.to_dict(),
        )

    async def send_payslip(
        self,
        employee_chat_id: str | int,
        pdf_bytes: bytes,
        period: str,
        employee_name: str,
        employee_id: str,
    ) -> dict:
        """Send a payslip PDF with a download confirmation keyboard."""
        caption = (
            f"<b>Payslip for {period}</b>\n\n" f"Hi {employee_name}, your payslip is attached."
        )
        return await self.send_document(
            chat_id=employee_chat_id,
            file_bytes=pdf_bytes,
            filename=f"payslip_{period.replace(' ', '_').lower()}.pdf",
            caption=caption,
        )

    async def register_webhook(self, url: str) -> dict:
        """Register a webhook URL for incoming messages.

        Args:
            url: HTTPS URL that Telegram will POST updates to.

        Returns:
            Dict with registration status.
        """
        self._validate_token()

        async def _do_register() -> dict:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self._api_base}/setWebhook",
                    json={
                        "url": url,
                        "allowed_updates": [
                            "message",
                            "callback_query",
                            "channel_post",
                        ],
                    },
                )
                resp.raise_for_status()
                return resp.json()

        result = await self._circuit.call(_do_register)

        if result.get("ok"):
            logger.info("Telegram webhook registered: %s", url)
            return {"status": "registered", "url": url}

        error = result.get("description", "Unknown error")
        logger.error("Failed to register Telegram webhook: %s", error)
        return {"status": "error", "error": error}

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: Optional[str] = None,
        show_alert: bool = False,
    ) -> dict:
        """Answer a callback query (from inline keyboard button press).

        Args:
            callback_query_id: ID from the callback_query update.
            text: Optional notification text shown to user.
            show_alert: If True, shows alert popup instead of toast.
        """
        self._validate_token()

        payload: dict[str, Any] = {
            "callback_query_id": callback_query_id,
        }
        if text:
            payload["text"] = text
        if show_alert:
            payload["show_alert"] = True

        async def _do_answer() -> dict:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self._api_base}/answerCallbackQuery",
                    json=payload,
                )
                resp.raise_for_status()
                return resp.json()

        return await self._circuit.call(_do_answer)

    @staticmethod
    def _guess_content_type(filename: str) -> str:
        """Guess MIME type from filename extension."""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        types = {
            "pdf": "application/pdf",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "xls": "application/vnd.ms-excel",
            "csv": "text/csv",
            "txt": "text/plain",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "xml": "application/xml",
        }
        return types.get(ext, "application/octet-stream")

    def get_send_log(self, limit: int = 100) -> list[dict]:
        """Return recent send log entries."""
        return self._send_log[-limit:]
