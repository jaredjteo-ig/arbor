"""SMS adapter via Twilio REST API.

Sends SMS messages for critical notifications only — payslip
delivery confirmations, CPF submission confirmations, and
security alerts. Reserved for high-priority messages due to
per-message cost.

T261: SMS Notification Connector (Red Team M6)
"""

from __future__ import annotations

import base64
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import httpx

from hr_advisory.mcp_servers.resilience import get_circuit

logger = logging.getLogger(__name__)

_TWILIO_API_BASE = "https://api.twilio.com/2010-04-01/"


class SMSDeliveryError(Exception):
    """Raised when SMS delivery fails."""

    def __init__(self, phone: str, error_code: Optional[int], detail: str):
        self.phone = phone
        self.error_code = error_code
        self.detail = detail
        super().__init__(f"SMS delivery failed for {phone}: [{error_code}] {detail}")


# Maximum SMS message length. Twilio concatenates longer messages
# but charges per segment (160 chars GSM, 70 chars Unicode).
_MAX_MESSAGE_LENGTH = 160


class SMSAdapter:
    """Adapter for Twilio SMS REST API.

    Reserved for critical-path notifications only due to per-message
    cost (~USD $0.07-0.15 per SMS to SG numbers). Do not use for
    routine notifications — use WhatsApp, email, or push instead.

    Appropriate use cases:
    - CPF submission confirmation
    - Payslip delivery confirmation (if WhatsApp unavailable)
    - Security alerts (password reset, suspicious login)
    - Two-factor authentication codes

    Usage::

        adapter = SMSAdapter()
        result = await adapter.send_sms(
            phone="+6591234567",
            message="Your March 2026 CPF submission has been confirmed. Ref: CPF-2026-03-ABC123",
        )
    """

    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        from_number: Optional[str] = None,
    ):
        self._account_sid = account_sid or os.environ.get("TWILIO_ACCOUNT_SID", "")
        self._auth_token = auth_token or os.environ.get("TWILIO_AUTH_TOKEN", "")
        self._from_number = from_number or os.environ.get("TWILIO_FROM_NUMBER", "")
        self._circuit = get_circuit("sms")

        if not self._account_sid:
            logger.warning("TWILIO_ACCOUNT_SID not set — SMS adapter will fail on send")
        if not self._auth_token:
            logger.warning("TWILIO_AUTH_TOKEN not set — SMS adapter will fail on send")
        if not self._from_number:
            logger.warning("TWILIO_FROM_NUMBER not set — SMS adapter will fail on send")

    @property
    def _messages_url(self) -> str:
        return f"{_TWILIO_API_BASE}Accounts/{self._account_sid}/Messages.json"

    def _auth_header(self) -> str:
        """Build Basic auth header for Twilio API."""
        credentials = f"{self._account_sid}:{self._auth_token}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    @staticmethod
    def normalize_phone(phone: str) -> str:
        """Normalize a phone number to E.164 format for Twilio.

        Twilio requires E.164: +[country code][number], e.g., +6591234567.
        """
        cleaned = phone.strip().replace(" ", "").replace("-", "")
        if not cleaned.startswith("+"):
            # Assume SG number if 8 digits starting with 6/8/9
            if len(cleaned) == 8 and cleaned[0] in ("6", "8", "9"):
                cleaned = f"+65{cleaned}"
            elif len(cleaned) == 10 and cleaned.startswith("65"):
                cleaned = f"+{cleaned}"
            else:
                cleaned = f"+{cleaned}"
        return cleaned

    async def send_sms(
        self,
        phone: str,
        message: str,
        tenant_id: str = "system",
    ) -> dict:
        """Send an SMS via Twilio.

        Args:
            phone: Recipient phone number (any format, normalized to E.164).
            message: Message body text. Should be concise — SMS charged
                per 160-character segment. Do not include PII (NRIC,
                salary, bank details) in the message body.
            tenant_id: Tenant ID for audit logging.

        Returns:
            Dict with message_sid, status, and segment count.

        Raises:
            SMSDeliveryError: If Twilio returns an error.
            ExternalAPIUnavailable: If circuit breaker is open.
        """
        normalized_phone = self.normalize_phone(phone)

        # Warn if message exceeds single segment
        if len(message) > _MAX_MESSAGE_LENGTH:
            segment_count = (len(message) + _MAX_MESSAGE_LENGTH - 1) // _MAX_MESSAGE_LENGTH
            logger.warning(
                "SMS to %s is %d chars (%d segments — billed per segment)",
                normalized_phone,
                len(message),
                segment_count,
            )
        else:
            segment_count = 1

        async def _do_send() -> dict:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    self._messages_url,
                    data={
                        "To": normalized_phone,
                        "From": self._from_number,
                        "Body": message,
                    },
                    headers={
                        "Authorization": self._auth_header(),
                    },
                )

                body = resp.json()

                if resp.status_code >= 400:
                    raise SMSDeliveryError(
                        phone=normalized_phone,
                        error_code=body.get("code"),
                        detail=body.get("message", resp.text[:500]),
                    )

                message_sid = body.get("sid", "unknown")
                logger.info(
                    "SMS sent to %s (sid=%s, segments=%d)",
                    normalized_phone,
                    message_sid,
                    body.get("num_segments", segment_count),
                )

                return {
                    "message_sid": message_sid,
                    "status": body.get("status", "queued"),
                    "to": normalized_phone,
                    "segments": body.get("num_segments", segment_count),
                    "provider": "twilio",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

        return await self._circuit.call(_do_send)

    async def get_message_status(self, message_sid: str) -> dict:
        """Check the delivery status of a sent SMS.

        Twilio message statuses:
        - queued: Waiting to be sent
        - sending: Being sent
        - sent: Delivered to carrier
        - delivered: Confirmed delivery to handset
        - undelivered: Carrier rejected
        - failed: Could not send

        Args:
            message_sid: Twilio message SID from send_sms response.

        Returns:
            Dict with status, error info (if any), and pricing.
        """
        url = f"{_TWILIO_API_BASE}Accounts/{self._account_sid}/Messages/{message_sid}.json"

        async def _do_fetch() -> dict:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    url,
                    headers={"Authorization": self._auth_header()},
                )
                if resp.status_code >= 400:
                    raise SMSDeliveryError(
                        phone="",
                        error_code=resp.status_code,
                        detail=f"Could not fetch message status: {resp.text[:200]}",
                    )

                body = resp.json()
                return {
                    "message_sid": message_sid,
                    "status": body.get("status"),
                    "to": body.get("to"),
                    "from": body.get("from"),
                    "error_code": body.get("error_code"),
                    "error_message": body.get("error_message"),
                    "price": body.get("price"),
                    "price_unit": body.get("price_unit"),
                    "date_sent": body.get("date_sent"),
                }

        return await self._circuit.call(_do_fetch)
