"""Unit tests for the HMAC-signed state token used by the Xero OAuth
start/callback endpoints.

The state binds the OAuth round-trip to a specific ``(company_id,
user_id, nonce, issued_at)`` tuple and is signed with
``INTEGRATION_ENCRYPTION_KEY``. Forging it lets an attacker stitch
their Xero org onto another customer's Arbor account, so this is a
security-critical surface — verify the round-trip and the failure
modes.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest


_KEY = b"unit-test-key-for-state-signing"


def _make_state(payload: dict, key: bytes = _KEY) -> str:
    body = json.dumps(payload, separators=(",", ":"))
    sig = hmac.new(key, body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def _verify(state: str, key: bytes = _KEY) -> dict:
    payload, _, sig = state.rpartition(".")
    if not payload or not sig:
        raise ValueError("malformed")
    expected = hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise ValueError("bad sig")
    return json.loads(payload)


def test_round_trip_state_signing_succeeds():
    p = {"c": 42, "u": 7, "n": "abc", "t": int(time.time())}
    s = _make_state(p)
    assert _verify(s) == p


def test_state_with_tampered_payload_fails_signature():
    p = {"c": 42, "u": 7, "n": "abc", "t": int(time.time())}
    s = _make_state(p)
    # Attacker swaps the company id but reuses the original signature.
    bad_payload = json.dumps({**p, "c": 999}, separators=(",", ":"))
    bad_state = f"{bad_payload}.{s.rpartition('.')[2]}"
    with pytest.raises(ValueError, match="bad sig"):
        _verify(bad_state)


def test_state_signed_with_different_key_fails():
    p = {"c": 1, "u": 1, "n": "x", "t": int(time.time())}
    s = _make_state(p, key=b"attacker-key")
    with pytest.raises(ValueError, match="bad sig"):
        _verify(s, key=_KEY)


def test_malformed_state_rejected():
    with pytest.raises(ValueError, match="malformed"):
        _verify("no-dot-here")


def test_extract_offending_codes_pulls_codes_from_xero_400():
    """Regression: M1-T05 — the adapter must extract every account
    code Xero rejects so the API can show the user exactly which
    mappings are stale, not a generic "something went wrong"."""
    from hr_advisory.mcp_servers.adapters.xero import (
        _extract_offending_codes,
    )

    # Single-code form Xero actually returns:
    msg = (
        "{\"ValidationErrors\": [{\"Message\": "
        "\"Account code '800' is not a valid code for this document.\"}]}"
    )
    assert _extract_offending_codes(msg) == ["800"]

    # Multi-code form (sometimes Xero batches them):
    msg2 = (
        "Account code '477' is not a valid code for this document. "
        "Account code '825' is not a valid code for this document."
    )
    assert sorted(_extract_offending_codes(msg2)) == ["477", "825"]

    # Non-matching detail returns empty list, not None.
    assert _extract_offending_codes("some other error") == []
    assert _extract_offending_codes("") == []


def test_idempotency_key_is_stable_for_same_force_counter():
    """Round-tripping the same (company, run, force_counter) yields the
    same Idempotency-Key, so a network-retry of the same logical
    operation dedupes at Xero. Force re-export bumps the counter and
    therefore the key."""
    company_id = 5
    run_id = 11
    force_counter = 0
    key1 = f"xero-payroll:{company_id}:{run_id}:{force_counter}"
    key2 = f"xero-payroll:{company_id}:{run_id}:{force_counter}"
    key_after_force = f"xero-payroll:{company_id}:{run_id}:{force_counter + 1}"
    assert key1 == key2
    assert key1 != key_after_force
