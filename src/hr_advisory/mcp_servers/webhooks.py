"""Webhook receiver framework for inbound events from external APIs.

Handles signature verification, event routing, and delivery confirmation
for webhooks from Xero, WhatsApp, Stripe, bank APIs, and other services.

T262: Webhook Receiver Framework (Red Team M7)
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class WebhookConfig:
    """Configuration for a webhook provider."""

    provider: str
    signature_header: str  # HTTP header containing the signature
    signature_algorithm: str  # "hmac-sha256", "hmac-sha1", etc.
    secret_env_var: str  # Environment variable containing the signing secret
    handler: Optional[Callable] = None


@dataclass
class WebhookEvent:
    """An inbound webhook event."""

    id: str
    provider: str
    event_type: str
    payload: dict
    headers: dict
    received_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    verified: bool = False
    processed: bool = False


# Pre-configured webhook providers
WEBHOOK_CONFIGS: dict[str, WebhookConfig] = {
    "xero": WebhookConfig(
        provider="xero",
        signature_header="x-xero-signature",
        signature_algorithm="hmac-sha256",
        secret_env_var="XERO_WEBHOOK_KEY",
    ),
    "whatsapp": WebhookConfig(
        provider="whatsapp",
        signature_header="x-hub-signature-256",
        signature_algorithm="hmac-sha256",
        secret_env_var="WHATSAPP_WEBHOOK_SECRET",
    ),
    "stripe": WebhookConfig(
        provider="stripe",
        signature_header="stripe-signature",
        signature_algorithm="hmac-sha256",
        secret_env_var="STRIPE_WEBHOOK_SECRET",
    ),
    "slack": WebhookConfig(
        provider="slack",
        signature_header="x-slack-signature",
        signature_algorithm="hmac-sha256",
        secret_env_var="SLACK_SIGNING_SECRET",
    ),
}


class WebhookRouter:
    """Routes and verifies inbound webhooks from external services.

    Usage::

        router = get_webhook_router()

        # Register handlers
        router.register_handler("xero", handle_xero_event)
        router.register_handler("whatsapp", handle_whatsapp_event)

        # Process an incoming webhook (called from FastAPI endpoint)
        result = await router.process_webhook("xero", headers, body)
    """

    def __init__(self, max_events: int = 10_000):
        self._handlers: dict[str, Callable] = {}
        self._event_log: list[WebhookEvent] = []
        self._max_events = max_events

    def register_handler(self, provider: str, handler: Callable) -> None:
        """Register a handler function for a webhook provider."""
        self._handlers[provider] = handler
        config = WEBHOOK_CONFIGS.get(provider)
        if config:
            config.handler = handler
        logger.info("Webhook handler registered for %s", provider)

    def verify_signature(
        self,
        provider: str,
        signature: str,
        body: bytes,
    ) -> bool:
        """Verify the webhook signature using the provider's signing secret.

        Returns True if signature is valid, False otherwise.
        """
        import os

        config = WEBHOOK_CONFIGS.get(provider)
        if config is None:
            logger.warning("Unknown webhook provider: %s", provider)
            return False

        secret = os.environ.get(config.secret_env_var, "")
        if not secret:
            logger.warning(
                "Webhook secret not configured for %s (env: %s)",
                provider,
                config.secret_env_var,
            )
            return False

        if config.signature_algorithm == "hmac-sha256":
            expected = hmac.new(
                secret.encode(),
                body,
                hashlib.sha256,
            ).hexdigest()

            # Some providers prefix with algorithm name
            signature_clean = signature.removeprefix("sha256=").removeprefix("v0=")
            return hmac.compare_digest(expected, signature_clean)

        logger.warning("Unsupported signature algorithm: %s", config.signature_algorithm)
        return False

    async def process_webhook(
        self,
        provider: str,
        headers: dict[str, str],
        body: bytes,
    ) -> dict:
        """Process an inbound webhook: verify, parse, and route to handler.

        Args:
            provider: The webhook provider name (e.g., "xero", "whatsapp").
            headers: HTTP headers from the request.
            body: Raw request body bytes.

        Returns:
            Processing result dict.
        """
        import json
        import uuid

        config = WEBHOOK_CONFIGS.get(provider)
        if config is None:
            return {"status": "error", "message": f"Unknown provider: {provider}"}

        # Verify signature — reject unsigned webhooks for providers with signing secrets
        signature = headers.get(config.signature_header, "")
        if signature:
            verified = self.verify_signature(provider, signature, body)
            if not verified:
                logger.warning("Webhook signature verification failed for %s", provider)
                return {"status": "error", "message": "Invalid signature"}
        else:
            # Check if this provider has a signing secret configured
            import os

            has_secret = bool(os.environ.get(config.secret_env_var, ""))
            if has_secret:
                logger.warning(
                    "Webhook from %s rejected — no signature header but signing secret is configured",
                    provider,
                )
                return {"status": "error", "message": "Missing signature header"}
            verified = False
            logger.info(
                "Webhook from %s accepted without signature (no secret configured)", provider
            )

        # Parse payload
        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {"status": "error", "message": "Invalid JSON payload"}

        # Create event record
        event = WebhookEvent(
            id=str(uuid.uuid4()),
            provider=provider,
            event_type=payload.get("event_type", payload.get("type", "unknown")),
            payload=payload,
            headers=dict(headers),
            verified=verified,
        )
        self._event_log.append(event)
        if len(self._event_log) > self._max_events:
            self._event_log = self._event_log[-self._max_events :]

        # Route to handler
        handler = self._handlers.get(provider)
        if handler is None:
            logger.warning("No handler registered for %s webhook", provider)
            return {
                "status": "received",
                "event_id": event.id,
                "message": "No handler registered",
            }

        try:
            result = await handler(event)
            event.processed = True
            return {
                "status": "processed",
                "event_id": event.id,
                "result": result,
            }
        except Exception as e:
            logger.exception("Webhook handler failed for %s: %s", provider, e)
            return {
                "status": "error",
                "event_id": event.id,
                "message": str(e),
            }

    def get_recent_events(
        self,
        provider: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """Get recent webhook events for monitoring."""
        events = self._event_log
        if provider:
            events = [e for e in events if e.provider == provider]
        events = sorted(events, key=lambda e: e.received_at, reverse=True)[:limit]
        return [
            {
                "id": e.id,
                "provider": e.provider,
                "event_type": e.event_type,
                "verified": e.verified,
                "processed": e.processed,
                "received_at": e.received_at.isoformat(),
            }
            for e in events
        ]


# Singleton
_router: Optional[WebhookRouter] = None


def get_webhook_router() -> WebhookRouter:
    """Get or create the global webhook router."""
    global _router
    if _router is None:
        _router = WebhookRouter()
    return _router
