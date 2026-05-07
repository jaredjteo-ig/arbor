"""Regression tests for shared survey-token helpers (T01).

Covers:
- Mint + decode roundtrip with explicit `kind` claim.
- Cross-kind replay rejection (exit token at engagement endpoint).
- 30-day legacy grace: a token with no `kind` claim is treated as
  `"exit"` so existing exit-interview tokens in the wild keep working.
- Audience mismatch rejection.
- Expiry rejection.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import jwt
import pytest
from fastapi import HTTPException

from hr_advisory.api.routers._survey_tokens import (
    ENGAGEMENT_TOKEN_AUDIENCE,
    ENGAGEMENT_TOKEN_KIND,
    EXIT_TOKEN_AUDIENCE,
    EXIT_TOKEN_EXPIRY_DAYS,
    EXIT_TOKEN_KIND,
    decode_token,
    make_token,
)
from hr_advisory.config.settings import get_settings


def _settings():
    return get_settings()


@pytest.mark.regression
def test_mint_and_decode_exit_token_roundtrip():
    token = make_token(record_id=42, company_id=1, kind=EXIT_TOKEN_KIND)
    decoded = decode_token(token, expected_kind=EXIT_TOKEN_KIND)
    assert decoded["ei"] == 42
    assert decoded["co"] == 1
    assert decoded["kind"] == "exit"
    assert decoded["aud"] == EXIT_TOKEN_AUDIENCE


@pytest.mark.regression
def test_mint_engagement_kind_token_decodes_for_engagement_audience():
    """The engagement-kind path is reserved for future alumni-cycle use.

    v1 does not mint these in production code, but the primitives must
    support it so the kind isolation isn't dead weight.
    """
    token = make_token(
        record_id=7,
        company_id=1,
        kind=ENGAGEMENT_TOKEN_KIND,
        audience=ENGAGEMENT_TOKEN_AUDIENCE,
    )
    decoded = decode_token(
        token,
        expected_kind=ENGAGEMENT_TOKEN_KIND,
        expected_audience=ENGAGEMENT_TOKEN_AUDIENCE,
    )
    assert decoded["kind"] == "engagement"


@pytest.mark.regression
def test_exit_token_replayed_at_engagement_kind_is_rejected():
    """An exit token presented at an engagement endpoint must be rejected.

    This is the core threat model for the kind claim — if the audiences
    happened to overlap (or audience checks were skipped), a leaver's
    exit token could otherwise be replayed against future engagement
    endpoints. Audience mismatch is the first defence; kind mismatch is
    the second.
    """
    exit_token = make_token(record_id=42, company_id=1, kind=EXIT_TOKEN_KIND)
    # Same audience, wrong expected_kind — reject 401.
    with pytest.raises(HTTPException) as exc_info:
        decode_token(
            exit_token,
            expected_kind=ENGAGEMENT_TOKEN_KIND,
            expected_audience=EXIT_TOKEN_AUDIENCE,
            legacy_default_kind=None,
        )
    assert exc_info.value.status_code == 401


@pytest.mark.regression
def test_legacy_token_without_kind_claim_decodes_as_exit():
    """The 30-day backwards-compat grace.

    Tokens minted before the kind isolation rollout are valid JWTs but
    have no `kind` claim. For exit-interview decoding, we treat the
    missing claim as `"exit"` so live tokens keep working.
    """
    # Mint a legacy-shape token by hand (no `kind` claim).
    settings = _settings()
    now = datetime.now(timezone.utc)
    legacy_payload = {
        "iss": "arbor",
        "aud": EXIT_TOKEN_AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": int(now.timestamp() + 86400),
        "ei": 99,
        "co": 1,
    }
    legacy_token = jwt.encode(
        legacy_payload, settings.jwt_secret_key, algorithm="HS256"
    )

    decoded = decode_token(
        legacy_token,
        expected_kind=EXIT_TOKEN_KIND,
        expected_audience=EXIT_TOKEN_AUDIENCE,
        legacy_default_kind=EXIT_TOKEN_KIND,
    )
    assert decoded["ei"] == 99


@pytest.mark.regression
def test_legacy_grace_disabled_rejects_unkinded_token():
    """When the grace period is over (legacy_default_kind=None), an
    unkinded token is rejected. Z01 will use this to fail-loud once the
    grace ends.
    """
    settings = _settings()
    now = datetime.now(timezone.utc)
    legacy_payload = {
        "iss": "arbor",
        "aud": EXIT_TOKEN_AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": int(now.timestamp() + 86400),
        "ei": 99,
        "co": 1,
    }
    legacy_token = jwt.encode(
        legacy_payload, settings.jwt_secret_key, algorithm="HS256"
    )

    with pytest.raises(HTTPException) as exc_info:
        decode_token(
            legacy_token,
            expected_kind=EXIT_TOKEN_KIND,
            expected_audience=EXIT_TOKEN_AUDIENCE,
            legacy_default_kind=None,
        )
    assert exc_info.value.status_code == 401


@pytest.mark.regression
def test_audience_mismatch_rejected():
    token = make_token(record_id=1, company_id=1, kind=EXIT_TOKEN_KIND)
    with pytest.raises(HTTPException) as exc_info:
        decode_token(
            token,
            expected_kind=EXIT_TOKEN_KIND,
            expected_audience="arbor.something-else",
        )
    assert exc_info.value.status_code == 401


@pytest.mark.regression
def test_expired_token_rejected():
    token = make_token(
        record_id=1, company_id=1, kind=EXIT_TOKEN_KIND, expiry_days=-1
    )
    with pytest.raises(HTTPException) as exc_info:
        decode_token(token, expected_kind=EXIT_TOKEN_KIND)
    assert exc_info.value.status_code == 401
    assert "expired" in exc_info.value.detail.lower()


@pytest.mark.regression
def test_make_token_default_kind_is_exit():
    """Defensive: if a future caller forgets to pass `kind`, the default
    is `EXIT_TOKEN_KIND` — never `engagement`. The risky default would
    silently mint engagement-kind tokens for exit interviews.
    """
    token = make_token(record_id=1, company_id=1)
    decoded = decode_token(token)  # default expected_kind is also exit
    assert decoded["kind"] == "exit"


@pytest.mark.regression
def test_token_includes_default_expiry():
    token = make_token(record_id=1, company_id=1, kind=EXIT_TOKEN_KIND)
    decoded = decode_token(token, expected_kind=EXIT_TOKEN_KIND)
    expected_lifetime_seconds = EXIT_TOKEN_EXPIRY_DAYS * 86400
    actual_lifetime = decoded["exp"] - decoded["iat"]
    assert abs(actual_lifetime - expected_lifetime_seconds) < 5
