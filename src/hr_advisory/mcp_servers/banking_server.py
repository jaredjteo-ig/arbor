"""aite-banking MCP server.

Exposes banking and payment integration tools for the shadow agent:
- ISO 20022 GIRO file generation (pain.001.001.03)
- FAST payment file generation (DBS IDEAL, UOB BIBPlus)
- PayNow QR code generation (SGQR/EMVCo standard)
- Aspire Payout API (single and bulk payouts)

Tools follow the {domain}_{verb}_{noun} naming convention.
"""

from __future__ import annotations

import base64
import logging
from typing import Optional

from hr_advisory.mcp_servers.base import AiteMCPServer, TenantContext

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------

server = AiteMCPServer(
    name="aite-banking",
    description=(
        "Banking and payment integrations for AITE HR Advisory Platform. "
        "Generates GIRO/FAST payment files, PayNow QR codes, and "
        "connects to Aspire for real-time payouts."
    ),
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# ISO 20022 GIRO tools
# ---------------------------------------------------------------------------


@server.tool(
    "banking_generate_giro",
    description=(
        "Generate ISO 20022 pain.001.001.03 XML file for bulk salary GIRO payments. "
        "Compatible with all SG banks: DBS, OCBC, UOB, Maybank, HSBC, SCB. "
        "Upload to corporate e-banking portal for batch salary transfers."
    ),
    requires_confirmation=True,
)
async def generate_giro(
    ctx: TenantContext,
    payroll_run: dict,
    payslips: list,
    employees: list,
    bank_config: dict,
) -> dict:
    """Generate ISO 20022 GIRO file."""
    from hr_advisory.mcp_servers.adapters.giro import get_giro_adapter

    adapter = get_giro_adapter()
    xml_content = adapter.generate_pain001(payroll_run, payslips, employees, bank_config)

    return {
        "status": "generated",
        "format": "iso20022_pain001",
        "content": xml_content,
        "transaction_count": sum(1 for ps in payslips if ps.get("net_salary", 0) > 0),
        "total_amount": sum(
            ps.get("net_salary", 0) for ps in payslips if ps.get("net_salary", 0) > 0
        ),
        "filename_suggestion": f"GIRO_{payroll_run.get('id', 'payroll')}_{payroll_run.get('pay_date', '')}.xml",
        "provider": "giro_iso20022",
    }


@server.tool(
    "banking_validate_giro_config",
    description=(
        "Validate bank configuration before generating a GIRO file. "
        "Checks originator name, account, and BIC/bank code."
    ),
)
async def validate_giro_config(ctx: TenantContext, bank_config: dict) -> dict:
    """Validate bank config for GIRO generation."""
    from hr_advisory.mcp_servers.adapters.giro import get_giro_adapter

    adapter = get_giro_adapter()
    errors = adapter.validate_bank_config(bank_config)
    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }


@server.tool(
    "banking_list_supported_banks",
    description="List all supported Singapore banks with BIC/SWIFT codes for GIRO payments.",
)
async def list_supported_banks(ctx: TenantContext) -> dict:
    """List supported SG banks."""
    from hr_advisory.mcp_servers.adapters.giro import GiroAdapter

    banks = GiroAdapter.get_supported_banks()
    return {"banks": banks, "count": len(banks)}


# ---------------------------------------------------------------------------
# FAST payment tools
# ---------------------------------------------------------------------------


@server.tool(
    "banking_generate_dbs_fast",
    description=(
        "Generate DBS IDEAL FAST payment file for same-day salary transfers. "
        "Fixed-width format for DBS corporate e-banking upload."
    ),
    requires_confirmation=True,
)
async def generate_dbs_fast(
    ctx: TenantContext,
    payroll_run: dict,
    payslips: list,
    employees: list,
    company_id: str = "",
) -> dict:
    """Generate DBS IDEAL FAST file."""
    from hr_advisory.mcp_servers.adapters.fast import get_fast_adapter

    adapter = get_fast_adapter()
    content = adapter.generate_dbs_fast(
        payroll_run, payslips, employees, company_id=company_id or None
    )

    return {
        "status": "generated",
        "format": "dbs_ideal_fast",
        "content": content,
        "transaction_count": sum(1 for ps in payslips if ps.get("net_salary", 0) > 0),
        "total_amount": sum(
            ps.get("net_salary", 0) for ps in payslips if ps.get("net_salary", 0) > 0
        ),
        "filename_suggestion": f"DBS_FAST_{payroll_run.get('id', 'payroll')}_{payroll_run.get('pay_date', '')}.txt",
        "provider": "dbs_fast",
    }


@server.tool(
    "banking_generate_uob_fast",
    description=(
        "Generate UOB BIBPlus FAST payment file for same-day salary transfers. "
        "Pipe-delimited format for UOB corporate e-banking upload."
    ),
    requires_confirmation=True,
)
async def generate_uob_fast(
    ctx: TenantContext,
    payroll_run: dict,
    payslips: list,
    employees: list,
    company_account: str = "",
) -> dict:
    """Generate UOB BIBPlus FAST file."""
    from hr_advisory.mcp_servers.adapters.fast import get_fast_adapter

    adapter = get_fast_adapter()
    content = adapter.generate_uob_fast(
        payroll_run, payslips, employees, company_account=company_account or None
    )

    return {
        "status": "generated",
        "format": "uob_bibplus_fast",
        "content": content,
        "transaction_count": sum(1 for ps in payslips if ps.get("net_salary", 0) > 0),
        "total_amount": sum(
            ps.get("net_salary", 0) for ps in payslips if ps.get("net_salary", 0) > 0
        ),
        "filename_suggestion": f"UOB_FAST_{payroll_run.get('id', 'payroll')}_{payroll_run.get('pay_date', '')}.txt",
        "provider": "uob_fast",
    }


# ---------------------------------------------------------------------------
# PayNow QR tools
# ---------------------------------------------------------------------------


@server.tool(
    "banking_generate_paynow_qr",
    description=(
        "Generate a PayNow QR code for employee reimbursement or ad-hoc payment. "
        "Implements SGQR (EMVCo) standard. Returns QR data string and PNG image. "
        "No external API -- pure client-side generation."
    ),
)
async def generate_paynow_qr(
    ctx: TenantContext,
    recipient_type: str,
    recipient_id: str,
    amount: float = 0,
    reference: str = "",
    merchant_name: str = "",
) -> dict:
    """Generate PayNow QR code."""
    from hr_advisory.mcp_servers.adapters.paynow import get_paynow_adapter, ProxyType

    adapter = get_paynow_adapter()

    # Map string to ProxyType enum
    type_map = {
        "mobile": ProxyType.MOBILE,
        "uen": ProxyType.UEN,
        "nric": ProxyType.NRIC,
    }
    proxy_type = type_map.get(recipient_type.lower())
    if not proxy_type:
        return {
            "status": "error",
            "message": f"Invalid recipient_type: {recipient_type}. Use 'mobile' or 'uen'.",
        }

    qr_data, png_bytes = adapter.generate_qr(
        recipient_type=proxy_type,
        recipient_id=recipient_id,
        amount=amount if amount > 0 else None,
        reference=reference,
        merchant_name=merchant_name,
    )

    # Base64 encode PNG for transport
    png_b64 = base64.b64encode(png_bytes).decode("ascii")

    return {
        "status": "generated",
        "qr_data": qr_data,
        "png_base64": png_b64,
        "png_size_bytes": len(png_bytes),
        "recipient_type": recipient_type,
        "amount": amount if amount > 0 else None,
        "reference": reference,
        "provider": "paynow",
    }


@server.tool(
    "banking_generate_paynow_data",
    description=(
        "Generate only the PayNow QR data string (no image). "
        "Use when the frontend will render the QR code."
    ),
)
async def generate_paynow_data(
    ctx: TenantContext,
    recipient_type: str,
    recipient_id: str,
    amount: float = 0,
    reference: str = "",
) -> dict:
    """Generate PayNow QR data string only."""
    from hr_advisory.mcp_servers.adapters.paynow import get_paynow_adapter, ProxyType

    adapter = get_paynow_adapter()

    type_map = {
        "mobile": ProxyType.MOBILE,
        "uen": ProxyType.UEN,
    }
    proxy_type = type_map.get(recipient_type.lower())
    if not proxy_type:
        return {
            "status": "error",
            "message": f"Invalid recipient_type: {recipient_type}. Use 'mobile' or 'uen'.",
        }

    qr_data = adapter.generate_qr_data_only(
        recipient_type=proxy_type,
        recipient_id=recipient_id,
        amount=amount if amount > 0 else None,
        reference=reference,
    )

    return {
        "status": "generated",
        "qr_data": qr_data,
        "provider": "paynow",
    }


# ---------------------------------------------------------------------------
# Aspire Payout tools
# ---------------------------------------------------------------------------


@server.tool(
    "banking_aspire_payout",
    description=(
        "Initiate a single payout via Aspire neobank API. "
        "Supports FAST (same-day), GIRO, and WIRE transfers."
    ),
    requires_confirmation=True,
)
async def aspire_payout(
    ctx: TenantContext,
    recipient_name: str,
    recipient_account: str,
    recipient_bank_code: str,
    amount: float,
    currency: str = "SGD",
    reference: str = "",
    description: str = "",
    payment_method: str = "FAST",
) -> dict:
    """Initiate single Aspire payout."""
    from hr_advisory.mcp_servers.adapters.aspire import get_aspire_adapter

    adapter = get_aspire_adapter()
    return await adapter.initiate_payout(
        recipient={
            "name": recipient_name,
            "bank_code": recipient_bank_code,
            "account": recipient_account,
        },
        amount=amount,
        currency=currency,
        reference=reference,
        description=description,
        payment_method=payment_method,
    )


@server.tool(
    "banking_aspire_bulk_payout",
    description=(
        "Initiate bulk salary payout via Aspire. "
        "Accepts list of payout instructions for batch processing."
    ),
    requires_confirmation=True,
)
async def aspire_bulk_payout(
    ctx: TenantContext,
    payouts: list,
    batch_reference: str = "",
) -> dict:
    """Initiate bulk Aspire payout."""
    from hr_advisory.mcp_servers.adapters.aspire import get_aspire_adapter

    adapter = get_aspire_adapter()
    return await adapter.initiate_bulk_payout(
        payouts=payouts,
        batch_reference=batch_reference,
    )


@server.tool(
    "banking_aspire_status",
    description="Check the status of an Aspire payout by payout ID.",
)
async def aspire_payout_status(ctx: TenantContext, payout_id: str) -> dict:
    """Check Aspire payout status."""
    from hr_advisory.mcp_servers.adapters.aspire import get_aspire_adapter

    adapter = get_aspire_adapter()
    return await adapter.get_payout_status(payout_id)


@server.tool(
    "banking_aspire_verify",
    description="Verify Aspire API connection and credentials.",
)
async def aspire_verify(ctx: TenantContext) -> dict:
    """Verify Aspire connection."""
    from hr_advisory.mcp_servers.adapters.aspire import get_aspire_adapter

    adapter = get_aspire_adapter()
    return await adapter.verify_connection()


# ---------------------------------------------------------------------------
# Legacy bank file tools (backward compatibility with existing statutory_files)
# ---------------------------------------------------------------------------


@server.tool(
    "banking_generate_legacy_giro",
    description=(
        "Generate legacy bank GIRO file (DBS fixed-width or generic CSV). "
        "For banks that don't accept ISO 20022 format. "
        "Uses existing statutory_files.generate_bank_giro()."
    ),
    requires_confirmation=True,
)
async def generate_legacy_giro(
    ctx: TenantContext,
    payroll_run: dict,
    payslips: list,
    employees: list,
    bank_format: str = "generic",
) -> dict:
    """Generate legacy GIRO file via statutory_files module."""
    from hr_advisory.services.statutory_files import generate_bank_giro

    content = generate_bank_giro(payroll_run, payslips, employees, bank_format=bank_format)
    return {
        "status": "generated",
        "format": f"legacy_{bank_format}",
        "content": content,
        "transaction_count": sum(1 for ps in payslips if ps.get("net_salary", 0) > 0),
        "provider": "legacy_giro",
    }


# ---------------------------------------------------------------------------
# Payment method comparison resource
# ---------------------------------------------------------------------------


@server.resource(
    "banking://payment-methods",
    name="Payment Methods",
    description=(
        "Compare available payment methods: GIRO (T+1, free), "
        "FAST (same-day, $0.50-2.00), PayNow (instant, free for $200K max)."
    ),
)
def payment_methods_comparison() -> dict:
    """Return payment method comparison for SG."""
    return {
        "methods": [
            {
                "name": "GIRO",
                "settlement": "T+1 (next business day)",
                "cost": "Free or minimal bank fees",
                "limit": "No per-transaction limit",
                "format": "ISO 20022 XML or legacy bank-specific",
                "best_for": "Regular monthly salary payments",
            },
            {
                "name": "FAST",
                "settlement": "Same-day (within minutes)",
                "cost": "$0.50 - $2.00 per transaction (bank-dependent)",
                "limit": "$200,000 per transaction",
                "format": "Bank-specific (DBS IDEAL, UOB BIBPlus)",
                "best_for": "Urgent salary payments, ad-hoc transfers",
            },
            {
                "name": "PayNow",
                "settlement": "Instant (seconds)",
                "cost": "Free",
                "limit": "$200,000 per transaction",
                "format": "QR code (SGQR standard)",
                "best_for": "Employee reimbursements, small ad-hoc payments",
            },
            {
                "name": "Aspire Payout",
                "settlement": "FAST (same-day) or WIRE (1-3 days)",
                "cost": "Varies by plan (see Aspire pricing)",
                "limit": "Per account limits",
                "format": "API-based (no file upload needed)",
                "best_for": "Companies using Aspire as corporate bank, multi-currency",
            },
        ],
    }
