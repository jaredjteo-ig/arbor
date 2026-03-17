"""Dynamic tool selector for shadow agent context.

Only injects relevant MCP tools based on the user's current page,
role, and connected integrations. Reduces tool count from 80+ to
~15-25 per context, improving LLM tool selection accuracy.

T263: Dynamic Tool Loading (Red Team M8)

IMPORTANT: Tool names MUST match actual registered names in MCP servers.
Sync with: government_server.py, accounting_server.py, banking_server.py,
communications_server.py, regulatory_server.py.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Page-to-tool-domain mapping
PAGE_TOOL_DOMAINS: dict[str, list[str]] = {
    "dashboard": ["regulatory", "communications"],
    "payroll": ["government", "banking", "accounting", "communications"],
    "leave": ["communications", "regulatory"],
    "employees": ["government", "communications"],
    "claims": ["accounting", "banking", "communications"],
    "compliance": ["regulatory", "government"],
    "calculator": ["regulatory"],
    "documents": ["regulatory"],
    "attendance": ["communications"],
    "shifts": ["communications"],
    "settings": ["government", "accounting", "banking", "communications", "regulatory"],
    "training": ["government"],
}

# Actual registered tool names mapped to their server domain.
# These MUST match the @server.tool("name") registrations in each server file.
TOOL_DOMAINS: dict[str, str] = {
    # ── Government server (gov_*) ──
    "gov_corppass_initiate": "government",
    "gov_corppass_callback": "government",
    "gov_corppass_status": "government",
    "gov_corppass_disconnect": "government",
    "gov_cpf_validate": "government",
    "gov_cpf_generate": "government",
    "gov_cpf_submit": "government",
    "gov_cpf_status": "government",
    "gov_cpf_csv_fallback": "government",
    "gov_iras_ir8a_generate": "government",
    "gov_iras_ir8a_submit": "government",
    "gov_iras_appendix8a_generate": "government",
    "gov_iras_appendix8a_submit": "government",
    "gov_iras_ir8s_generate": "government",
    "gov_iras_ir8s_submit": "government",
    "gov_iras_ir21_generate": "government",
    "gov_iras_ir21_submit": "government",
    "gov_iras_filing_status": "government",
    "gov_mom_oed_generate": "government",
    "gov_mom_oed_submit": "government",
    "gov_mom_oed_status": "government",
    "gov_myinfo_initiate": "government",
    "gov_myinfo_callback": "government",
    "gov_myinfo_business": "government",
    "gov_acra_verify_uen": "government",
    "gov_acra_business_profile": "government",
    "gov_acra_cost_summary": "government",
    "gov_submission_saga_start": "government",
    "gov_submission_saga_status": "government",
    "gov_submissions_list": "government",
    "gov_skillsfuture_search_courses": "government",
    "gov_skillsfuture_calculate_grant": "government",
    "gov_skillsfuture_course_details": "government",
    # ── Accounting server (accounting_*) ──
    "accounting_connect_xero": "accounting",
    "accounting_callback_xero": "accounting",
    "accounting_get_xero_accounts": "accounting",
    "accounting_post_xero_payroll_journal": "accounting",
    "accounting_post_xero_claims_journal": "accounting",
    "accounting_get_xero_trial_balance": "accounting",
    "accounting_disconnect_xero": "accounting",
    "accounting_connect_quickbooks": "accounting",
    "accounting_callback_quickbooks": "accounting",
    "accounting_get_quickbooks_accounts": "accounting",
    "accounting_post_quickbooks_journal": "accounting",
    "accounting_disconnect_quickbooks": "accounting",
    "accounting_connect_zoho": "accounting",
    "accounting_callback_zoho": "accounting",
    "accounting_get_zoho_accounts": "accounting",
    "accounting_post_zoho_journal": "accounting",
    "accounting_get_zoho_usage": "accounting",
    "accounting_disconnect_zoho": "accounting",
    "accounting_export_financio": "accounting",
    "accounting_export_csv": "accounting",
    "accounting_export_json": "accounting",
    "accounting_sync_claims": "accounting",
    # ── Banking server (banking_*) ──
    "banking_generate_giro": "banking",
    "banking_validate_giro_config": "banking",
    "banking_list_supported_banks": "banking",
    "banking_generate_dbs_fast": "banking",
    "banking_generate_uob_fast": "banking",
    "banking_generate_paynow_qr": "banking",
    "banking_generate_paynow_data": "banking",
    "banking_aspire_payout": "banking",
    "banking_aspire_bulk_payout": "banking",
    "banking_aspire_status": "banking",
    "banking_aspire_verify": "banking",
    "banking_generate_legacy_giro": "banking",
    # ── Communications server (comms_*) ──
    "comms_send_email": "communications",
    "comms_send_bulk_email": "communications",
    "comms_send_payslip_email": "communications",
    "comms_send_leave_notification": "communications",
    "comms_send_onboarding_invite": "communications",
    "comms_list_email_templates": "communications",
    "comms_send_telegram": "communications",
    "comms_send_telegram_document": "communications",
    "comms_send_telegram_leave_approval": "communications",
    "comms_send_telegram_claim_approval": "communications",
    "comms_send_telegram_payslip": "communications",
    "comms_register_telegram_webhook": "communications",
    "comms_send_whatsapp": "communications",
    "comms_send_slack": "communications",
    "comms_send_teams": "communications",
    "comms_sync_google_calendar": "communications",
    "comms_sync_outlook_calendar": "communications",
    "comms_send_ses_email": "communications",
    # ── Regulatory server (regulatory_*) ──
    "regulatory_check_cpf_rates": "regulatory",
    "regulatory_get_act_amendments": "regulatory",
    "regulatory_check_updates": "regulatory",
    "regulatory_classify_change": "regulatory",
    "regulatory_get_monitor_status": "regulatory",
    "regulatory_get_recent_classifications": "regulatory",
    "regulatory_get_recent_changes": "regulatory",
    # ── Shared tools ──
    "confirm_action": "shared",
}


def get_tools_for_context(
    page: str = "dashboard",
    role: str = "admin",
    connected_providers: Optional[list[str]] = None,
) -> list[str]:
    """Return the subset of tool names relevant to the current context.

    Args:
        page: Current page (e.g., "payroll", "leave", "employees").
        role: User role ("admin", "hr_manager", "employee").
        connected_providers: List of connected provider names.

    Returns:
        List of tool names to inject into the shadow agent's tool set.
    """
    domains = PAGE_TOOL_DOMAINS.get(page, PAGE_TOOL_DOMAINS["dashboard"])

    relevant_tools = []
    for tool_name, domain in TOOL_DOMAINS.items():
        if domain in domains or domain == "shared":
            relevant_tools.append(tool_name)

    # Filter by connected providers if specified
    if connected_providers is not None:
        provider_domains = set()
        provider_map = {
            "xero": "accounting",
            "quickbooks": "accounting",
            "zoho": "accounting",
            "dbs": "banking",
            "uob": "banking",
            "ocbc": "banking",
            "aspire": "banking",
            "corppass": "government",
            "resend": "communications",
            "ses": "communications",
            "whatsapp": "communications",
            "telegram": "communications",
            "slack": "communications",
            "teams": "communications",
            "google_calendar": "communications",
            "microsoft_graph": "communications",
        }
        for provider in connected_providers:
            d = provider_map.get(provider)
            if d:
                provider_domains.add(d)

        # Always available (no connection needed)
        provider_domains.add("regulatory")
        provider_domains.add("shared")
        provider_domains.add("government")  # data.gov.sg always available

        relevant_tools = [
            t for t in relevant_tools if TOOL_DOMAINS.get(t, "unknown") in provider_domains
        ]

    # Role-based filtering
    if role == "employee":
        employee_allowed = {"communications", "regulatory", "shared"}
        relevant_tools = [t for t in relevant_tools if TOOL_DOMAINS.get(t) in employee_allowed]

    logger.debug(
        "Tool selection for page=%s role=%s: %d tools (from %d total)",
        page,
        role,
        len(relevant_tools),
        len(TOOL_DOMAINS),
    )
    return relevant_tools


def get_tool_count_by_page() -> dict[str, int]:
    """Return the tool count per page (for monitoring/debugging)."""
    return {page: len(get_tools_for_context(page=page)) for page in PAGE_TOOL_DOMAINS}
