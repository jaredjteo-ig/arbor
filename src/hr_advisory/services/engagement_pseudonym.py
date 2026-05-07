"""HMAC-based pseudonym computation for pseudonymous engagement surveys.

Round-3 product revision keeps three anonymity tiers — identified,
pseudonymous, anonymous. Pseudonymous mode lets HR see cross-survey
trends per employee (e.g. "this respondent's growth scores are
trending down over 6 pulses") without storing employee_id on the
response row.

Mechanism:
- Each company has a secret (`Company.engagement_secret_vN`) generated
  on first use of pseudonymous mode and never sent in any API response.
- Pseudonym = HMAC-SHA256(secret, f"{employee_id}|{survey_id}").
  Returned as a 64-char hex string.
- Same (secret, employee, survey) → same pseudonym (allows trend joins).
  Different employee or different survey → different pseudonym.
- Versioning (Z02): rotation produces a new secret. Responses record
  `pseudonym_version`; verification routes by version. Pre-rotation
  pseudonyms remain valid for trend continuity up to the rotation point.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from typing import Optional

from hr_advisory.security.encryption import decrypt_field, encrypt_field
from hr_advisory.services import dataflow_crud

logger = logging.getLogger(__name__)

__all__ = [
    "compute_pseudonym",
    "get_or_create_company_secret",
    "rotate_company_secret",
]


def compute_pseudonym(
    secret_hex: str,
    employee_id: int,
    survey_id: int,
) -> str:
    """Compute a deterministic HMAC pseudonym for a (employee, survey) pair.

    Pure function — accepts the secret as input rather than reading from
    the DB. Callers (the submit handler, the cross-stage join service)
    pass the secret resolved via `get_or_create_company_secret`.

    Args:
        secret_hex: hex-encoded secret bytes. Must be at least 32 hex
            characters (128 bits) — enforced by the secret generator
            below.
        employee_id: the employee's ID. Must be > 0 — anonymous-tier
            responses use a different code path that doesn't compute
            pseudonyms.
        survey_id: the parent survey's ID.

    Returns:
        64-character hex string (HMAC-SHA256 digest).
    """
    if not secret_hex or len(secret_hex) < 32:
        raise ValueError(
            "secret_hex must be at least 32 hex chars; lazy-generation "
            "produces 64. Check get_or_create_company_secret."
        )
    if employee_id <= 0:
        raise ValueError("employee_id must be > 0 for pseudonym computation.")
    if survey_id <= 0:
        raise ValueError("survey_id must be > 0 for pseudonym computation.")

    try:
        secret_bytes = bytes.fromhex(secret_hex)
    except ValueError as exc:
        raise ValueError("secret_hex must be valid hex.") from exc

    message = f"{employee_id}|{survey_id}".encode("utf-8")
    digest = hmac.new(secret_bytes, message, hashlib.sha256).hexdigest()
    return digest


def get_or_create_company_secret(
    company_id: int,
    version: Optional[int] = None,
) -> str:
    """Return the company's engagement secret for the given version.

    Lazy-generates if missing. Stored encrypted at rest. The secret is
    256 bits (64 hex chars), generated via `secrets.token_hex(32)`.

    Args:
        company_id: target company.
        version: secret version to resolve. Defaults to the company's
            `engagement_secret_active_version` field. Pass an explicit
            version (e.g. 1) to verify a historical pseudonym after
            rotation.

    Returns:
        Plaintext hex-encoded secret. Never log or echo this value.
    """
    rows = dataflow_crud.list_records(
        "Company",
        {"id": int(company_id)},
        cache_ttl=0,
    )
    if not rows:
        raise ValueError(f"Company {company_id} not found.")
    company = rows[0]

    active_version = int(company.get("engagement_secret_active_version") or 1)
    target_version = int(version) if version is not None else active_version
    if target_version not in (1, 2):
        raise ValueError(
            f"Unsupported secret version {target_version} (only 1, 2 supported)."
        )

    field_name = f"engagement_secret_v{target_version}"
    encrypted = company.get(field_name) or ""

    if encrypted:
        try:
            return decrypt_field(encrypted)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "engagement_secret_decrypt_failed",
                extra={"company_id": company_id, "version": target_version},
            )
            raise RuntimeError(
                f"Could not decrypt engagement_secret_v{target_version} "
                f"for company {company_id}. Possible key rotation issue."
            ) from exc

    # Lazy-generate. Only the active version is generated on first use;
    # rotation explicitly populates v2 via rotate_company_secret.
    if target_version != active_version:
        raise ValueError(
            f"engagement_secret_v{target_version} is unset for company "
            f"{company_id}. Only the active version lazy-generates."
        )

    new_secret = secrets.token_hex(32)
    encrypted_secret = encrypt_field(new_secret)
    dataflow_crud.update(
        "Company",
        int(company_id),
        {field_name: encrypted_secret},
    )
    logger.info(
        "engagement_secret_generated",
        extra={"company_id": company_id, "version": target_version},
    )
    return new_secret


def rotate_company_secret(company_id: int) -> int:
    """Rotate a company's engagement secret to a new version.

    Currently supports v1 → v2. After rotation, new responses use v2;
    historical responses keep their `pseudonym_version=1` and remain
    verifiable via the v1 secret which is preserved.

    Returns the new active version.
    """
    rows = dataflow_crud.list_records(
        "Company",
        {"id": int(company_id)},
        cache_ttl=0,
    )
    if not rows:
        raise ValueError(f"Company {company_id} not found.")
    company = rows[0]

    current = int(company.get("engagement_secret_active_version") or 1)
    if current >= 2:
        raise NotImplementedError(
            "Rotation beyond v2 not yet supported. Schema-level extension "
            "required to add engagement_secret_v3 etc."
        )

    new_version = current + 1
    new_secret = secrets.token_hex(32)
    encrypted_secret = encrypt_field(new_secret)
    dataflow_crud.update(
        "Company",
        int(company_id),
        {
            f"engagement_secret_v{new_version}": encrypted_secret,
            "engagement_secret_active_version": new_version,
        },
    )
    logger.warning(
        "engagement_secret_rotated",
        extra={
            "company_id": company_id,
            "from_version": current,
            "to_version": new_version,
        },
    )
    return new_version
