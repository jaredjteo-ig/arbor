"""arbor-accounting MCP server.

Exposes accounting integration tools for the shadow agent:
- Xero, QuickBooks, Zoho Books: OAuth connect, chart of accounts, journal posting
- Financio: GL posting file export
- Generic: CSV and JSON journal export
- Claims sync: route approved claims to connected accounting provider

Tools follow the {domain}_{verb}_{noun} naming convention.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Optional

from hr_advisory.mcp_servers.base import ArborMCPServer, TenantContext

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------

server = ArborMCPServer(
    name="arbor-accounting",
    description=(
        "Accounting integrations for Arbor HR Advisory Platform. "
        "Connects payroll and claims to Xero, QuickBooks Online, Zoho Books, "
        "Financio, or generic CSV/JSON exports."
    ),
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# OAuth CSRF state store for accounting providers
# ---------------------------------------------------------------------------

# Maps state_token -> {"tenant_id": str, "provider": str, "created_at": float}
_oauth_states: dict[str, dict[str, str | float]] = {}
_OAUTH_STATE_EXPIRY = 600  # 10 minutes


def _clean_expired_oauth_states() -> None:
    """Remove expired OAuth state tokens."""
    now = time.time()
    expired = [k for k, v in _oauth_states.items() if now - v["created_at"] > _OAUTH_STATE_EXPIRY]
    for k in expired:
        del _oauth_states[k]


def _generate_oauth_state(tenant_id: str, provider: str) -> str:
    """Generate and store a CSRF state token for an OAuth connect flow."""
    _clean_expired_oauth_states()
    state = uuid.uuid4().hex
    _oauth_states[state] = {
        "tenant_id": tenant_id,
        "provider": provider,
        "created_at": time.time(),
    }
    return state


def _validate_oauth_state(state: str, tenant_id: str, provider: str) -> None:
    """Validate and consume an OAuth CSRF state token.

    Raises ValueError if state is missing, expired, or does not match
    the expected tenant_id and provider.
    """
    _clean_expired_oauth_states()
    entry = _oauth_states.pop(state, None)
    if entry is None:
        raise ValueError(
            f"Invalid or expired OAuth state for {provider}. "
            "Please restart the authorization flow."
        )
    if entry["tenant_id"] != tenant_id:
        raise ValueError(
            f"OAuth state tenant mismatch for {provider}. " "Please restart the authorization flow."
        )
    if entry["provider"] != provider:
        raise ValueError(
            f"OAuth state provider mismatch: expected {provider}. "
            "Please restart the authorization flow."
        )


# ---------------------------------------------------------------------------
# Xero tools
# ---------------------------------------------------------------------------


@server.tool(
    "accounting_connect_xero",
    description=(
        "Generate Xero OAuth authorization URL. The admin visits this URL "
        "to authorize Arbor to access their Xero organization."
    ),
)
async def connect_xero(ctx: TenantContext, redirect_uri: str) -> dict:
    """Start Xero OAuth flow."""
    from hr_advisory.mcp_servers.adapters.xero import get_xero_adapter

    state = _generate_oauth_state(ctx.company_id, "xero")
    adapter = get_xero_adapter()
    url = adapter.get_authorization_url(ctx.company_id, redirect_uri)
    # Append our server-side CSRF state to the URL
    url = f"{url}&state={state}"
    return {
        "status": "authorization_url_generated",
        "url": url,
        "provider": "xero",
        "state": state,
    }


@server.tool(
    "accounting_callback_xero",
    description="Complete Xero OAuth flow by exchanging the authorization code for tokens.",
)
async def callback_xero(ctx: TenantContext, code: str, redirect_uri: str, state: str = "") -> dict:
    """Complete Xero OAuth callback."""
    if not state:
        return {
            "status": "error",
            "error": "missing_state",
            "message": "OAuth state parameter is required for CSRF protection.",
            "provider": "xero",
        }
    _validate_oauth_state(state, ctx.company_id, "xero")

    from hr_advisory.mcp_servers.adapters.xero import get_xero_adapter

    adapter = get_xero_adapter()
    return await adapter.handle_oauth_callback(ctx.company_id, code, redirect_uri)


@server.tool(
    "accounting_get_xero_accounts",
    description=(
        "Fetch chart of accounts from Xero. Cached for 24 hours. "
        "Returns account codes, names, types, and tax types."
    ),
)
async def get_xero_accounts(
    ctx: TenantContext,
    xero_tenant_id: str = "",
    force_refresh: bool = False,
) -> dict:
    """Fetch Xero chart of accounts."""
    from hr_advisory.mcp_servers.adapters.xero import get_xero_adapter

    adapter = get_xero_adapter()
    accounts = await adapter.get_chart_of_accounts(
        ctx.company_id,
        xero_tenant_id=xero_tenant_id or None,
        force_refresh=force_refresh,
    )
    return {"accounts": accounts, "count": len(accounts), "provider": "xero"}


@server.tool(
    "accounting_post_xero_payroll_journal",
    description=(
        "Post a payroll journal entry to Xero as a ManualJournal. "
        "Debits salary expense accounts and credits CPF payable, net pay payable. "
        "Validates that debits equal credits before posting."
    ),
    requires_confirmation=True,
)
async def post_xero_payroll_journal(
    ctx: TenantContext,
    journal_data: dict,
    xero_tenant_id: str = "",
) -> dict:
    """Post payroll journal to Xero."""
    from hr_advisory.mcp_servers.adapters.xero import get_xero_adapter

    adapter = get_xero_adapter()
    return await adapter.post_payroll_journal(
        ctx.company_id,
        journal_data,
        xero_tenant_id=xero_tenant_id or None,
    )


@server.tool(
    "accounting_post_xero_claims_journal",
    description=(
        "Post approved claims as a journal entry to Xero. "
        "Groups claims by expense category, debits expense accounts, "
        "credits claims payable."
    ),
    requires_confirmation=True,
)
async def post_xero_claims_journal(
    ctx: TenantContext,
    claims_data: dict,
    xero_tenant_id: str = "",
) -> dict:
    """Post claims journal to Xero."""
    from hr_advisory.mcp_servers.adapters.xero import get_xero_adapter

    adapter = get_xero_adapter()
    return await adapter.post_claims_journal(
        ctx.company_id,
        claims_data,
        xero_tenant_id=xero_tenant_id or None,
    )


@server.tool(
    "accounting_get_xero_trial_balance",
    description="Fetch trial balance report from Xero for verification and reconciliation.",
)
async def get_xero_trial_balance(
    ctx: TenantContext,
    xero_tenant_id: str = "",
    date: str = "",
) -> dict:
    """Fetch Xero trial balance."""
    from hr_advisory.mcp_servers.adapters.xero import get_xero_adapter

    adapter = get_xero_adapter()
    return await adapter.get_trial_balance(
        ctx.company_id,
        xero_tenant_id=xero_tenant_id or None,
        date=date or None,
    )


@server.tool(
    "accounting_disconnect_xero",
    description="Disconnect Xero integration. Revokes stored tokens.",
)
async def disconnect_xero(ctx: TenantContext) -> dict:
    """Disconnect Xero."""
    from hr_advisory.mcp_servers.adapters.xero import get_xero_adapter

    adapter = get_xero_adapter()
    revoked = await adapter.disconnect(ctx.company_id)
    return {"status": "disconnected" if revoked else "not_connected", "provider": "xero"}


# ---------------------------------------------------------------------------
# QuickBooks tools
# ---------------------------------------------------------------------------


@server.tool(
    "accounting_connect_quickbooks",
    description="Generate QuickBooks Online OAuth authorization URL.",
)
async def connect_quickbooks(ctx: TenantContext, redirect_uri: str) -> dict:
    """Start QBO OAuth flow."""
    from hr_advisory.mcp_servers.adapters.quickbooks import get_quickbooks_adapter

    state = _generate_oauth_state(ctx.company_id, "quickbooks")
    adapter = get_quickbooks_adapter()
    url = adapter.get_authorization_url(ctx.company_id, redirect_uri)
    url = f"{url}&state={state}"
    return {
        "status": "authorization_url_generated",
        "url": url,
        "provider": "quickbooks",
        "state": state,
    }


@server.tool(
    "accounting_callback_quickbooks",
    description="Complete QuickBooks OAuth flow with authorization code and realm ID.",
)
async def callback_quickbooks(
    ctx: TenantContext,
    code: str,
    realm_id: str,
    redirect_uri: str,
    state: str = "",
) -> dict:
    """Complete QBO OAuth callback."""
    if not state:
        return {
            "status": "error",
            "error": "missing_state",
            "message": "OAuth state parameter is required for CSRF protection.",
            "provider": "quickbooks",
        }
    _validate_oauth_state(state, ctx.company_id, "quickbooks")

    from hr_advisory.mcp_servers.adapters.quickbooks import get_quickbooks_adapter

    adapter = get_quickbooks_adapter()
    return await adapter.handle_oauth_callback(ctx.company_id, code, realm_id, redirect_uri)


@server.tool(
    "accounting_get_quickbooks_accounts",
    description=(
        "Fetch chart of accounts from QuickBooks Online. "
        "Cached for 24 hours. Returns account IDs, names, types."
    ),
)
async def get_quickbooks_accounts(
    ctx: TenantContext,
    realm_id: str = "",
    force_refresh: bool = False,
) -> dict:
    """Fetch QBO chart of accounts."""
    from hr_advisory.mcp_servers.adapters.quickbooks import get_quickbooks_adapter

    adapter = get_quickbooks_adapter()
    accounts = await adapter.get_chart_of_accounts(
        ctx.company_id,
        realm_id=realm_id or None,
        force_refresh=force_refresh,
    )
    return {"accounts": accounts, "count": len(accounts), "provider": "quickbooks"}


@server.tool(
    "accounting_post_quickbooks_journal",
    description=(
        "Post a journal entry to QuickBooks Online. " "Used for payroll and claims journal entries."
    ),
    requires_confirmation=True,
)
async def post_quickbooks_journal(
    ctx: TenantContext,
    journal_data: dict,
    realm_id: str = "",
) -> dict:
    """Post journal entry to QBO."""
    from hr_advisory.mcp_servers.adapters.quickbooks import get_quickbooks_adapter

    adapter = get_quickbooks_adapter()
    return await adapter.post_journal_entry(
        ctx.company_id,
        journal_data,
        realm_id=realm_id or None,
    )


@server.tool(
    "accounting_disconnect_quickbooks",
    description="Disconnect QuickBooks Online integration.",
)
async def disconnect_quickbooks(ctx: TenantContext) -> dict:
    """Disconnect QBO."""
    from hr_advisory.mcp_servers.adapters.quickbooks import get_quickbooks_adapter

    adapter = get_quickbooks_adapter()
    revoked = await adapter.disconnect(ctx.company_id)
    return {"status": "disconnected" if revoked else "not_connected", "provider": "quickbooks"}


# ---------------------------------------------------------------------------
# Zoho Books tools
# ---------------------------------------------------------------------------


@server.tool(
    "accounting_connect_zoho",
    description="Generate Zoho Books OAuth authorization URL.",
)
async def connect_zoho(ctx: TenantContext, redirect_uri: str) -> dict:
    """Start Zoho OAuth flow."""
    from hr_advisory.mcp_servers.adapters.zoho import get_zoho_adapter

    state = _generate_oauth_state(ctx.company_id, "zoho")
    adapter = get_zoho_adapter()
    url = adapter.get_authorization_url(ctx.company_id, redirect_uri)
    url = f"{url}&state={state}"
    return {
        "status": "authorization_url_generated",
        "url": url,
        "provider": "zoho",
        "state": state,
    }


@server.tool(
    "accounting_callback_zoho",
    description="Complete Zoho Books OAuth flow.",
)
async def callback_zoho(ctx: TenantContext, code: str, redirect_uri: str, state: str = "") -> dict:
    """Complete Zoho OAuth callback."""
    if not state:
        return {
            "status": "error",
            "error": "missing_state",
            "message": "OAuth state parameter is required for CSRF protection.",
            "provider": "zoho",
        }
    _validate_oauth_state(state, ctx.company_id, "zoho")

    from hr_advisory.mcp_servers.adapters.zoho import get_zoho_adapter

    adapter = get_zoho_adapter()
    return await adapter.handle_oauth_callback(ctx.company_id, code, redirect_uri)


@server.tool(
    "accounting_get_zoho_accounts",
    description=(
        "Fetch chart of accounts from Zoho Books. AGGRESSIVELY cached for 48 hours "
        "due to Zoho's low daily API limit (2,500/day)."
    ),
)
async def get_zoho_accounts(
    ctx: TenantContext,
    organization_id: str = "",
    force_refresh: bool = False,
) -> dict:
    """Fetch Zoho chart of accounts."""
    from hr_advisory.mcp_servers.adapters.zoho import get_zoho_adapter

    adapter = get_zoho_adapter()
    accounts = await adapter.get_chart_of_accounts(
        ctx.company_id,
        organization_id=organization_id or None,
        force_refresh=force_refresh,
    )
    usage = adapter.get_daily_usage(ctx.company_id)
    return {
        "accounts": accounts,
        "count": len(accounts),
        "provider": "zoho",
        "daily_api_usage": usage,
    }


@server.tool(
    "accounting_post_zoho_journal",
    description=(
        "Post a journal entry to Zoho Books. "
        "Mind the 2,500/day API limit — each post uses 1 call."
    ),
    requires_confirmation=True,
)
async def post_zoho_journal(
    ctx: TenantContext,
    journal_data: dict,
    organization_id: str = "",
) -> dict:
    """Post journal to Zoho Books."""
    from hr_advisory.mcp_servers.adapters.zoho import get_zoho_adapter

    adapter = get_zoho_adapter()
    result = await adapter.post_journal(
        ctx.company_id,
        journal_data,
        organization_id=organization_id or None,
    )
    result["daily_api_usage"] = adapter.get_daily_usage(ctx.company_id)
    return result


@server.tool(
    "accounting_get_zoho_usage",
    description="Check current Zoho Books daily API usage for rate limit awareness.",
)
async def get_zoho_usage(ctx: TenantContext) -> dict:
    """Get Zoho daily API usage."""
    from hr_advisory.mcp_servers.adapters.zoho import get_zoho_adapter

    adapter = get_zoho_adapter()
    return adapter.get_daily_usage(ctx.company_id)


@server.tool(
    "accounting_disconnect_zoho",
    description="Disconnect Zoho Books integration.",
)
async def disconnect_zoho(ctx: TenantContext) -> dict:
    """Disconnect Zoho."""
    from hr_advisory.mcp_servers.adapters.zoho import get_zoho_adapter

    adapter = get_zoho_adapter()
    revoked = await adapter.disconnect(ctx.company_id)
    return {"status": "disconnected" if revoked else "not_connected", "provider": "zoho"}


# ---------------------------------------------------------------------------
# Financio export tools
# ---------------------------------------------------------------------------


@server.tool(
    "accounting_export_financio",
    description=(
        "Generate a Financio (ABSS) GL Posting text file for manual import. "
        "Used when direct API is not available."
    ),
)
async def export_financio(ctx: TenantContext, payroll_data: dict) -> dict:
    """Export payroll journal as Financio GL posting file."""
    from hr_advisory.mcp_servers.adapters.financio import get_financio_adapter

    adapter = get_financio_adapter()
    content = adapter.export_payroll_journal(payroll_data)
    return {
        "status": "exported",
        "provider": "financio",
        "format": "text/tab-separated-values",
        "content": content,
        "line_count": len(payroll_data.get("lines", [])),
    }


# ---------------------------------------------------------------------------
# Generic export tools
# ---------------------------------------------------------------------------


@server.tool(
    "accounting_export_csv",
    description=(
        "Generate a standard CSV journal entry file compatible with any "
        "accounting software. Universal fallback format."
    ),
)
async def export_csv(ctx: TenantContext, payroll_data: dict) -> dict:
    """Export payroll journal as generic CSV."""
    from hr_advisory.mcp_servers.adapters.generic_export import get_generic_export_adapter

    adapter = get_generic_export_adapter()
    content = adapter.export_csv(payroll_data)
    return {
        "status": "exported",
        "provider": "generic",
        "format": "text/csv",
        "content": content,
        "line_count": len(payroll_data.get("lines", [])),
    }


@server.tool(
    "accounting_export_json",
    description=(
        "Generate a structured JSON journal entry export. "
        "Machine-readable format for custom integrations."
    ),
)
async def export_json(ctx: TenantContext, payroll_data: dict) -> dict:
    """Export payroll journal as structured JSON."""
    from hr_advisory.mcp_servers.adapters.generic_export import get_generic_export_adapter

    adapter = get_generic_export_adapter()
    content = adapter.export_json(payroll_data)
    return {
        "status": "exported",
        "provider": "generic",
        "format": "application/json",
        "content": content,
        "line_count": len(payroll_data.get("lines", [])),
    }


# ---------------------------------------------------------------------------
# Claims sync tool
# ---------------------------------------------------------------------------


@server.tool(
    "accounting_sync_claims",
    description=(
        "Sync approved employee claims to the connected accounting provider. "
        "Groups claims by expense category, creates balanced journal entries, "
        "and posts to Xero, QuickBooks, Zoho, or exports to file."
    ),
    requires_confirmation=True,
)
async def sync_claims(
    ctx: TenantContext,
    claims: list,
    provider: str,
    xero_tenant_id: str = "",
    qbo_realm_id: str = "",
    zoho_org_id: str = "",
    date: str = "",
    reference: str = "",
) -> dict:
    """Sync claims to accounting provider."""
    from hr_advisory.mcp_servers.adapters.claims_sync import get_claims_sync_adapter

    adapter = get_claims_sync_adapter()
    return await adapter.sync_claims_to_accounting(
        tenant_id=ctx.company_id,
        claims=claims,
        provider=provider,
        xero_tenant_id=xero_tenant_id or None,
        qbo_realm_id=qbo_realm_id or None,
        zoho_org_id=zoho_org_id or None,
        date=date or None,
        reference=reference or None,
    )


# ---------------------------------------------------------------------------
# Connection status resource
# ---------------------------------------------------------------------------


@server.resource(
    "accounting://connections",
    name="Accounting Connections",
    description="List all connected accounting providers for the current tenant.",
)
def list_connections() -> dict:
    """List accounting provider connections."""
    from hr_advisory.mcp_servers.auth.token_store import get_token_manager

    manager = get_token_manager()
    # This resource is not tenant-scoped (resources don't receive context).
    # In practice, the shadow agent would call with tenant context.
    return {
        "providers": ["xero", "quickbooks", "zoho", "financio", "generic"],
        "note": "Use individual connect tools to check per-tenant status.",
    }
