"""Server-side feature-flag endpoints (round-13 S1-T2).

Three round-13 toggles that previously lived in ``localStorage`` are now
persisted on the company record as a JSON ``feature_flags`` map:

  - ``ai-scorecards``   — AI scorecard generation in recruitment
  - ``tafep-ai``        — TAFEP AI second-pass scanner in job posting
  - ``chat-onboarding`` — chat-style company onboarding for new signups

Endpoints:

  - ``GET  /companies/me/feature-flags`` — any authenticated user reads their
    own company's flags. Always returns the full allow-list with default
    ``False`` for keys the company hasn't explicitly set.

  - ``PATCH /companies/me/feature-flags`` — owner-only. Accepts a partial
    map and merges it into the existing flags. Unknown keys are rejected
    with 400 to prevent owners from scribbling arbitrary state into the
    JSON column.

Security notes:

  - Both endpoints derive the target ``company_id`` from the JWT, never
    from the request body or path. There is no cross-tenant write surface
    here — a tenant A owner cannot reach tenant B's flags by guessing an
    ID, and ``validate_company_access`` is invoked anyway as defence in
    depth (returns 403 if the resolved company doesn't match the user).

  - PATCH is rate-limited per user to prevent flag-flapping abuse.

  - Every flag write is logged at INFO level so we have a basic audit
    trail until the dedicated audit-log infrastructure lands.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from hr_advisory.api.middleware.auth_middleware import get_current_user, require_role
from hr_advisory.api.middleware.rate_limit import check_rate_limit
from hr_advisory.api.middleware.tenant_isolation import validate_company_access

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Allow-list — only these keys may be stored in the feature_flags JSON column.
# Adding a new flag is a code change; we never accept arbitrary keys from
# the wire. Defaults are False so a fresh company sees nothing on.
# ---------------------------------------------------------------------------

ALLOWED_FLAGS: tuple[str, ...] = (
    "ai-scorecards",
    "tafep-ai",
    "chat-onboarding",
)

DEFAULT_FLAGS: dict[str, bool] = {flag: False for flag in ALLOWED_FLAGS}


def _execute_node(node_type: str, node_id: str, params: dict) -> dict:
    """Run a single DataFlow workflow node and return the result.

    Mirrors the helper in ``company.py`` so this router doesn't reach into
    another router's internals.
    """
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401 -- ensure models are registered

    workflow = WorkflowBuilder()
    workflow.add_node(node_type, node_id, params)
    runtime = LocalRuntime()
    results, _ = runtime.execute(workflow.build())
    return results[node_id]


def _normalise_flags(raw: object) -> dict[str, bool]:
    """Coerce a stored flags blob into the canonical ``{flag: bool}`` shape.

    Older companies may have ``feature_flags = None``; storage layers that
    serialise JSON to text might hand us a string we still need to handle
    sensibly. We always return the full allow-list with defaults filled in
    so the frontend has a stable contract.
    """
    flags: dict[str, bool] = dict(DEFAULT_FLAGS)
    if isinstance(raw, dict):
        for key in ALLOWED_FLAGS:
            if key in raw:
                flags[key] = bool(raw[key])
    return flags


def _read_company(company_id: int) -> dict:
    """Read the company record by ID, raising 404 if missing."""
    try:
        record = _execute_node(
            "CompanyReadNode",
            "read_company_for_flags",
            {"id": company_id},
        )
    except Exception as exc:
        logger.error("Failed to read company id=%s for feature flags: %s", company_id, exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to load feature flags. Please try again later.",
        ) from exc

    if not record or record.get("error") or record.get("failed"):
        # The owner's JWT pointed at a company that no longer exists. Treat
        # as 404 — the front-end can recover by re-onboarding.
        raise HTTPException(
            status_code=404,
            detail="Company not found.",
        )
    return record


# ---------------------------------------------------------------------------
# GET /companies/me/feature-flags
# ---------------------------------------------------------------------------


@router.get("/me/feature-flags")
async def get_my_feature_flags(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Return the current company's feature flags.

    Any authenticated user attached to the company can read flags — the UI
    needs to know which surfaces to show, regardless of role. The response
    always includes the full allow-list so the frontend has a deterministic
    shape to consume.

    Status codes:
        200: Flags returned.
        403: User has no company associated with their account.
        404: User's company id no longer resolves to a record.
    """
    company_id = current_user.get("company_id")

    if company_id is None:
        # User hasn't completed onboarding yet — they have no company to
        # read flags from. The frontend treats this as "use defaults" and
        # for the chat-onboarding case we explicitly default it ON in the
        # onboarding page itself.
        return {
            "company_id": None,
            "flags": dict(DEFAULT_FLAGS),
            "defaulted": True,
        }

    # Belt-and-braces tenant check — the JWT is the source of truth, but
    # we run this for symmetry with other company-scoped endpoints.
    validate_company_access(current_user, requested_company_id=company_id)

    record = _read_company(company_id)
    flags = _normalise_flags(record.get("feature_flags"))

    return {
        "company_id": company_id,
        "flags": flags,
        "defaulted": False,
    }


# ---------------------------------------------------------------------------
# PATCH /companies/me/feature-flags
# ---------------------------------------------------------------------------


@router.patch("/me/feature-flags")
async def update_my_feature_flags(
    request: Request,
    current_user: dict = Depends(require_role("owner", "platform_admin")),
) -> dict:
    """Merge submitted flags into the current company's feature_flags map.

    Only owners (and platform admins) can flip flags. The body must be a
    flat ``{flag_name: bool}`` map — nested objects, arrays, and unknown
    keys are rejected. Existing keys not in the patch are preserved.

    Status codes:
        200: Flags updated; full merged map returned.
        400: Body is malformed or contains a flag outside the allow-list.
        403: User is not an owner / not in the target company.
        404: Company no longer exists.
        429: Too many flag changes — slow down.
    """
    user_id = int(current_user.get("sub", 0))
    company_id = current_user.get("company_id")

    if company_id is None:
        # An owner without a company shouldn't exist, but be defensive.
        raise HTTPException(
            status_code=403,
            detail="No company associated with this account.",
        )

    validate_company_access(current_user, requested_company_id=company_id)

    # Rate-limit per user — owners shouldn't be flipping flags more than a
    # few times per minute. 30/min is generous and matches other
    # owner-mutating endpoints in this codebase.
    check_rate_limit(
        f"feature_flags_update:{user_id}",
        max_requests=30,
        window_seconds=60,
        action_name="update feature flags",
    )

    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from exc

    if not isinstance(body, dict):
        raise HTTPException(
            status_code=400,
            detail="Request body must be a JSON object of {flag_name: bool}.",
        )

    # Allow callers to send either ``{"flags": {...}}`` or a flat map.
    # The flat shape is preferred for PATCH semantics; we accept both for
    # forward-compat with a possible future "set everything" endpoint.
    incoming = body.get("flags") if isinstance(body.get("flags"), dict) else body

    # Validate every key against the allow-list and every value as a bool.
    # We do this BEFORE reading the company so a bad payload fails fast.
    unknown = [key for key in incoming.keys() if key not in ALLOWED_FLAGS]
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown feature flag(s): {sorted(unknown)}. "
                f"Allowed flags: {list(ALLOWED_FLAGS)}."
            ),
        )

    for key, value in incoming.items():
        if not isinstance(value, bool):
            raise HTTPException(
                status_code=400,
                detail=f"Flag '{key}' must be a boolean (got {type(value).__name__}).",
            )

    # Read existing record so we can MERGE rather than REPLACE.
    record = _read_company(company_id)
    current_flags = _normalise_flags(record.get("feature_flags"))
    merged = dict(current_flags)
    merged.update(incoming)

    try:
        _execute_node(
            "CompanyUpdateNode",
            "update_company_flags",
            {
                "filter": {"id": company_id},
                "fields": {"feature_flags": merged},
            },
        )
    except Exception as exc:
        logger.error("Failed to update feature flags for company %s: %s", company_id, exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to update feature flags. Please try again later.",
        ) from exc

    # Audit trail — until the round-12 H16 audit-log table lands, INFO-level
    # logging gives us a searchable record of who flipped what and when.
    logger.info(
        "feature_flags.update user=%s company=%s changed=%s merged=%s",
        user_id,
        company_id,
        sorted(incoming.keys()),
        merged,
    )

    return {
        "company_id": company_id,
        "flags": merged,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
