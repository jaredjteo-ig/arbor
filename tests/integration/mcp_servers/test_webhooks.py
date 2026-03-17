"""Integration tests for the webhook receiver framework.

Tests:
- Register handler -> handler called on webhook
- HMAC-SHA256 signature verification (correct passes, wrong fails)
- Invalid JSON payload -> error response
- Unknown provider -> error response
- Event logging
- No handler registered -> received status
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from unittest.mock import AsyncMock, patch

import pytest

from hr_advisory.mcp_servers.webhooks import (
    WEBHOOK_CONFIGS,
    WebhookEvent,
    WebhookRouter,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def router() -> WebhookRouter:
    return WebhookRouter()


def _make_signed_body(provider: str, payload: dict, secret: str) -> tuple[bytes, str]:
    """Create a signed webhook body and signature for a provider."""
    body = json.dumps(payload).encode("utf-8")
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return body, signature


# ---------------------------------------------------------------------------
# Handler Registration
# ---------------------------------------------------------------------------


class TestHandlerRegistration:
    """Registering and invoking webhook handlers."""

    @pytest.mark.asyncio
    async def test_registered_handler_called(self, router):
        handler = AsyncMock(return_value={"processed": True})
        router.register_handler("xero", handler)

        secret = "test_xero_secret"
        payload = {"event_type": "invoice.created", "data": {"id": "INV-001"}}
        body, signature = _make_signed_body("xero", payload, secret)
        headers = {"x-xero-signature": signature}

        with patch.dict(os.environ, {"XERO_WEBHOOK_KEY": secret}):
            result = await router.process_webhook("xero", headers, body)

        assert result["status"] == "processed"
        handler.assert_called_once()
        call_args = handler.call_args[0]
        assert isinstance(call_args[0], WebhookEvent)
        assert call_args[0].provider == "xero"

    @pytest.mark.asyncio
    async def test_handler_receives_parsed_payload(self, router):
        received_event = None

        async def capture_handler(event: WebhookEvent):
            nonlocal received_event
            received_event = event
            return {"ok": True}

        router.register_handler("xero", capture_handler)

        secret = "test_secret"
        payload = {"event_type": "contact.updated", "contact_id": "C-123"}
        body, signature = _make_signed_body("xero", payload, secret)
        headers = {"x-xero-signature": signature}

        with patch.dict(os.environ, {"XERO_WEBHOOK_KEY": secret}):
            await router.process_webhook("xero", headers, body)

        assert received_event is not None
        assert received_event.payload["contact_id"] == "C-123"
        assert received_event.event_type == "contact.updated"

    @pytest.mark.asyncio
    async def test_handler_result_in_response(self, router):
        handler = AsyncMock(return_value={"action_taken": "updated_contact"})
        router.register_handler("xero", handler)

        secret = "test_secret"
        payload = {"event_type": "test"}
        body, signature = _make_signed_body("xero", payload, secret)
        headers = {"x-xero-signature": signature}

        with patch.dict(os.environ, {"XERO_WEBHOOK_KEY": secret}):
            result = await router.process_webhook("xero", headers, body)

        assert result["result"] == {"action_taken": "updated_contact"}


# ---------------------------------------------------------------------------
# HMAC Signature Verification
# ---------------------------------------------------------------------------


class TestSignatureVerification:
    """HMAC-SHA256 signature verification."""

    def test_correct_signature_passes(self, router):
        secret = "test_webhook_secret"
        body = b'{"event": "test"}'
        expected_sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

        with patch.dict(os.environ, {"XERO_WEBHOOK_KEY": secret}):
            result = router.verify_signature("xero", expected_sig, body)

        assert result is True

    def test_wrong_signature_fails(self, router):
        secret = "test_webhook_secret"
        body = b'{"event": "test"}'

        with patch.dict(os.environ, {"XERO_WEBHOOK_KEY": secret}):
            result = router.verify_signature("xero", "invalid_signature", body)

        assert result is False

    def test_empty_secret_fails(self, router):
        body = b'{"event": "test"}'

        with patch.dict(os.environ, {"XERO_WEBHOOK_KEY": ""}):
            result = router.verify_signature("xero", "any_signature", body)

        assert result is False

    def test_signature_with_sha256_prefix(self, router):
        """Some providers prefix with 'sha256='."""
        secret = "test_secret"
        body = b'{"event": "test"}'
        raw_sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        prefixed_sig = f"sha256={raw_sig}"

        with patch.dict(os.environ, {"XERO_WEBHOOK_KEY": secret}):
            result = router.verify_signature("xero", prefixed_sig, body)

        assert result is True

    def test_unknown_provider_returns_false(self, router):
        result = router.verify_signature("nonexistent_provider", "sig", b"body")
        assert result is False

    @pytest.mark.asyncio
    async def test_bad_signature_returns_error(self, router):
        handler = AsyncMock(return_value={"ok": True})
        router.register_handler("xero", handler)

        secret = "test_secret"
        payload = {"event_type": "test"}
        body = json.dumps(payload).encode("utf-8")
        headers = {"x-xero-signature": "wrong_signature"}

        with patch.dict(os.environ, {"XERO_WEBHOOK_KEY": secret}):
            result = await router.process_webhook("xero", headers, body)

        assert result["status"] == "error"
        assert "Invalid signature" in result["message"]
        handler.assert_not_called()


# ---------------------------------------------------------------------------
# Invalid JSON Payload
# ---------------------------------------------------------------------------


class TestInvalidPayload:
    """Invalid JSON payload handling."""

    @pytest.mark.asyncio
    async def test_invalid_json_returns_error(self, router):
        handler = AsyncMock()
        router.register_handler("xero", handler)

        # No signature header = no verification attempt
        headers = {}
        body = b"not valid json {{{{"

        result = await router.process_webhook("xero", headers, body)

        assert result["status"] == "error"
        assert "Invalid JSON" in result["message"]
        handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_body_returns_error(self, router):
        headers = {}
        body = b""

        result = await router.process_webhook("xero", headers, body)

        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# Unknown Provider
# ---------------------------------------------------------------------------


class TestUnknownProvider:
    """Unknown provider handling."""

    @pytest.mark.asyncio
    async def test_unknown_provider_returns_error(self, router):
        headers = {"x-signature": "something"}
        body = json.dumps({"event": "test"}).encode("utf-8")

        result = await router.process_webhook("nonexistent_provider", headers, body)

        assert result["status"] == "error"
        assert "Unknown provider" in result["message"]


# ---------------------------------------------------------------------------
# No Handler Registered
# ---------------------------------------------------------------------------


class TestNoHandler:
    """Processing webhooks without a registered handler."""

    @pytest.mark.asyncio
    async def test_no_handler_returns_received_status(self, router):
        """Without a handler, webhook is received but not processed."""
        # Don't register any handler for xero
        payload = {"event_type": "test"}
        body = json.dumps(payload).encode("utf-8")
        headers = {}  # No signature = skip verification

        result = await router.process_webhook("xero", headers, body)

        assert result["status"] == "received"
        assert "No handler registered" in result["message"]
        assert "event_id" in result


# ---------------------------------------------------------------------------
# Event Logging
# ---------------------------------------------------------------------------


class TestEventLogging:
    """Webhook event logging."""

    @pytest.mark.asyncio
    async def test_event_logged(self, router):
        handler = AsyncMock(return_value={"ok": True})
        router.register_handler("xero", handler)

        secret = "test_secret"
        payload = {"event_type": "invoice.paid"}
        body, signature = _make_signed_body("xero", payload, secret)
        headers = {"x-xero-signature": signature}

        with patch.dict(os.environ, {"XERO_WEBHOOK_KEY": secret}):
            await router.process_webhook("xero", headers, body)

        events = router.get_recent_events()
        assert len(events) == 1
        assert events[0]["provider"] == "xero"
        assert events[0]["event_type"] == "invoice.paid"

    @pytest.mark.asyncio
    async def test_verified_flag_recorded(self, router):
        handler = AsyncMock(return_value={})
        router.register_handler("xero", handler)

        secret = "test_secret"
        payload = {"event_type": "test"}
        body, signature = _make_signed_body("xero", payload, secret)
        headers = {"x-xero-signature": signature}

        with patch.dict(os.environ, {"XERO_WEBHOOK_KEY": secret}):
            await router.process_webhook("xero", headers, body)

        events = router.get_recent_events()
        assert events[0]["verified"] is True

    @pytest.mark.asyncio
    async def test_unverified_flag_when_no_signature(self, router):
        handler = AsyncMock(return_value={})
        router.register_handler("xero", handler)

        payload = {"event_type": "test"}
        body = json.dumps(payload).encode("utf-8")
        headers = {}  # No signature header

        await router.process_webhook("xero", headers, body)

        events = router.get_recent_events()
        assert events[0]["verified"] is False

    @pytest.mark.asyncio
    async def test_processed_flag(self, router):
        handler = AsyncMock(return_value={})
        router.register_handler("xero", handler)

        secret = "test_secret"
        payload = {"event_type": "test"}
        body, signature = _make_signed_body("xero", payload, secret)
        headers = {"x-xero-signature": signature}

        with patch.dict(os.environ, {"XERO_WEBHOOK_KEY": secret}):
            await router.process_webhook("xero", headers, body)

        events = router.get_recent_events()
        assert events[0]["processed"] is True

    @pytest.mark.asyncio
    async def test_event_log_filtered_by_provider(self, router):
        handler = AsyncMock(return_value={})
        router.register_handler("xero", handler)
        router.register_handler("whatsapp", handler)

        secret_xero = "xero_secret"
        secret_wa = "wa_secret"

        payload = {"event_type": "test"}
        body_x, sig_x = _make_signed_body("xero", payload, secret_xero)
        body_w, sig_w = _make_signed_body("whatsapp", payload, secret_wa)

        with patch.dict(
            os.environ,
            {
                "XERO_WEBHOOK_KEY": secret_xero,
                "WHATSAPP_WEBHOOK_SECRET": secret_wa,
            },
        ):
            await router.process_webhook("xero", {"x-xero-signature": sig_x}, body_x)
            await router.process_webhook(
                "whatsapp",
                {"x-hub-signature-256": sig_w},
                body_w,
            )

        xero_events = router.get_recent_events(provider="xero")
        wa_events = router.get_recent_events(provider="whatsapp")

        assert len(xero_events) == 1
        assert len(wa_events) == 1
        assert xero_events[0]["provider"] == "xero"
        assert wa_events[0]["provider"] == "whatsapp"

    @pytest.mark.asyncio
    async def test_event_log_limit(self, router):
        handler = AsyncMock(return_value={})
        router.register_handler("xero", handler)

        payload = {"event_type": "test"}
        body = json.dumps(payload).encode("utf-8")
        headers = {}

        for _ in range(10):
            await router.process_webhook("xero", headers, body)

        events = router.get_recent_events(limit=5)
        assert len(events) == 5

    @pytest.mark.asyncio
    async def test_event_log_has_timestamp(self, router):
        payload = {"event_type": "test"}
        body = json.dumps(payload).encode("utf-8")
        headers = {}

        await router.process_webhook("xero", headers, body)

        events = router.get_recent_events()
        assert "received_at" in events[0]
        assert "T" in events[0]["received_at"]  # ISO 8601

    @pytest.mark.asyncio
    async def test_event_has_unique_id(self, router):
        payload = {"event_type": "test"}
        body = json.dumps(payload).encode("utf-8")
        headers = {}

        await router.process_webhook("xero", headers, body)
        await router.process_webhook("xero", headers, body)

        events = router.get_recent_events()
        ids = [e["id"] for e in events]
        assert len(ids) == len(set(ids)), "Event IDs must be unique"


# ---------------------------------------------------------------------------
# Handler Exception
# ---------------------------------------------------------------------------


class TestHandlerException:
    """Handler that raises an exception."""

    @pytest.mark.asyncio
    async def test_handler_exception_returns_error(self, router):
        async def failing_handler(event):
            raise ValueError("Handler crashed")

        router.register_handler("xero", failing_handler)

        payload = {"event_type": "test"}
        body = json.dumps(payload).encode("utf-8")
        headers = {}  # No signature

        result = await router.process_webhook("xero", headers, body)

        assert result["status"] == "error"
        assert "Handler crashed" in result["message"]
        assert "event_id" in result


# ---------------------------------------------------------------------------
# Webhook Configs
# ---------------------------------------------------------------------------


class TestWebhookConfigs:
    """Verify pre-configured webhook providers."""

    def test_xero_config_exists(self):
        assert "xero" in WEBHOOK_CONFIGS
        assert WEBHOOK_CONFIGS["xero"].signature_header == "x-xero-signature"
        assert WEBHOOK_CONFIGS["xero"].signature_algorithm == "hmac-sha256"

    def test_whatsapp_config_exists(self):
        assert "whatsapp" in WEBHOOK_CONFIGS
        assert WEBHOOK_CONFIGS["whatsapp"].signature_header == "x-hub-signature-256"

    def test_stripe_config_exists(self):
        assert "stripe" in WEBHOOK_CONFIGS
        assert WEBHOOK_CONFIGS["stripe"].signature_header == "stripe-signature"

    def test_slack_config_exists(self):
        assert "slack" in WEBHOOK_CONFIGS
        assert WEBHOOK_CONFIGS["slack"].signature_header == "x-slack-signature"

    def test_all_configs_use_hmac_sha256(self):
        for name, config in WEBHOOK_CONFIGS.items():
            assert (
                config.signature_algorithm == "hmac-sha256"
            ), f"Provider {name} uses {config.signature_algorithm}"
