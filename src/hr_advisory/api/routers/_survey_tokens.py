"""Shared token primitives for survey-style routers.

Originally extracted from `exit_interviews.py` so engagement surveys,
appraisal request links, and any future tokenised public-survey flow
can share a single mint/decode implementation.

Round-3 product revision (`workspaces/engagement-survey/02-plans/04-product-revision-round3.md`)
ships engagement as in-app only. Engagement-kind tokens are reserved
for future use (e.g. alumni-cycle eNPS one year after departure) and
are not minted by any v1 code path. The kind-isolation work still
ships so an exit-interview token cannot be replayed at any future
engagement endpoint.

Backwards compatibility: tokens minted before this rollout have no
`kind` claim. For a 30-day grace window, `decode_token` treats a
missing `kind` as `EXIT_TOKEN_KIND` so live exit-interview tokens
keep working. After the grace ends, Z01 wires the failing test that
forces removal of the legacy fallback.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import jwt
from fastapi import HTTPException

from hr_advisory.config.settings import get_settings

logger = logging.getLogger(__name__)

__all__ = [
    "make_token",
    "decode_token",
    "EXIT_TOKEN_AUDIENCE",
    "EXIT_TOKEN_KIND",
    "EXIT_TOKEN_EXPIRY_DAYS",
    "ENGAGEMENT_TOKEN_AUDIENCE",
    "ENGAGEMENT_TOKEN_KIND",
    "ENGAGEMENT_TOKEN_EXPIRY_DAYS",
]

EXIT_TOKEN_AUDIENCE = "arbor.exit-interview"
EXIT_TOKEN_KIND = "exit"
EXIT_TOKEN_EXPIRY_DAYS = 30

ENGAGEMENT_TOKEN_AUDIENCE = "arbor.engagement-survey"
ENGAGEMENT_TOKEN_KIND = "engagement"
ENGAGEMENT_TOKEN_EXPIRY_DAYS = 30


def make_token(
    record_id: int,
    company_id: int,
    *,
    kind: str = EXIT_TOKEN_KIND,
    audience: str = EXIT_TOKEN_AUDIENCE,
    expiry_days: int = EXIT_TOKEN_EXPIRY_DAYS,
) -> str:
    """Mint a JWT for a tokenised public survey response.

    The `kind` claim isolates token namespaces so a token minted for one
    survey type cannot be replayed at another. The default is `"exit"`
    (the only kind minted in v1 code paths) — callers minting other
    kinds must pass both `kind` and `audience` explicitly.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "iss": "arbor",
        "aud": audience,
        "kind": kind,
        "iat": int(now.timestamp()),
        "exp": int(now.timestamp() + expiry_days * 86400),
        "ei": record_id,
        "co": company_id,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def decode_token(
    token: str,
    *,
    expected_kind: str = EXIT_TOKEN_KIND,
    expected_audience: str = EXIT_TOKEN_AUDIENCE,
    legacy_default_kind: str | None = EXIT_TOKEN_KIND,
) -> dict:
    """Decode a survey JWT and verify both audience and kind.

    Raises 401 HTTPException on:
    - Bad signature, expired, or audience mismatch (handled by PyJWT).
    - Kind mismatch (the cross-replay defence).
    - Missing kind claim when `legacy_default_kind` is None.

    Set `legacy_default_kind=None` to enforce the kind claim strictly
    (used after the 30-day grace ends, or in any new endpoint that
    never had legacy tokens to support).
    """
    settings = get_settings()
    try:
        decoded = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=["HS256"],
            audience=expected_audience,
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid token.") from exc

    kind_claim = decoded.get("kind")
    if kind_claim is None:
        if legacy_default_kind is None:
            raise HTTPException(status_code=401, detail="Invalid token.")
        kind_claim = legacy_default_kind
        # Z31 metric hook: ops can grep for this to know when the
        # legacy fallback is still firing in production.
        logger.info(
            "legacy_token_kind_assumed",
            extra={
                "metric": "engagement.legacy_token_kind_assumed_total",
                "assumed_kind": legacy_default_kind,
            },
        )

    if kind_claim != expected_kind:
        raise HTTPException(status_code=401, detail="Invalid token.")

    return decoded
