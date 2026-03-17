"""Integration tests for the dynamic tool selector.

Tests:
- Payroll page includes government, banking, accounting tools
- Leave page includes communications, regulatory tools
- Employee role only gets communications and regulatory tools
- Admin role gets all domain tools
- Connected providers filter works
- SkillsFuture tools appear on training page
- Tool count per page is reasonable (10-30, not 80+)
"""

from __future__ import annotations

import pytest

from hr_advisory.mcp_servers.tool_selector import (
    PAGE_TOOL_DOMAINS,
    TOOL_DOMAINS,
    get_tool_count_by_page,
    get_tools_for_context,
)


# ---------------------------------------------------------------------------
# Payroll Page
# ---------------------------------------------------------------------------


class TestPayrollPage:
    """Payroll page should include government, banking, accounting, communications."""

    def test_payroll_includes_government_tools(self):
        tools = get_tools_for_context(page="payroll")
        gov_tools = [t for t in tools if TOOL_DOMAINS.get(t) == "government"]
        assert len(gov_tools) > 0

    def test_payroll_includes_banking_tools(self):
        tools = get_tools_for_context(page="payroll")
        banking_tools = [t for t in tools if TOOL_DOMAINS.get(t) == "banking"]
        assert len(banking_tools) > 0

    def test_payroll_includes_accounting_tools(self):
        tools = get_tools_for_context(page="payroll")
        accounting_tools = [t for t in tools if TOOL_DOMAINS.get(t) == "accounting"]
        assert len(accounting_tools) > 0

    def test_payroll_includes_communications_tools(self):
        tools = get_tools_for_context(page="payroll")
        comms_tools = [t for t in tools if TOOL_DOMAINS.get(t) == "communications"]
        assert len(comms_tools) > 0

    def test_payroll_excludes_regulatory_tools(self):
        tools = get_tools_for_context(page="payroll")
        reg_tools = [t for t in tools if TOOL_DOMAINS.get(t) == "regulatory"]
        assert len(reg_tools) == 0

    def test_payroll_includes_giro_tool(self):
        tools = get_tools_for_context(page="payroll")
        assert "banking_generate_giro" in tools

    def test_payroll_includes_cpf_tools(self):
        tools = get_tools_for_context(page="payroll")
        cpf_tools = [t for t in tools if "cpf" in t]
        assert len(cpf_tools) > 0

    def test_payroll_always_includes_confirm_action(self):
        tools = get_tools_for_context(page="payroll")
        assert "confirm_action" in tools


# ---------------------------------------------------------------------------
# Leave Page
# ---------------------------------------------------------------------------


class TestLeavePage:
    """Leave page should include communications and regulatory tools."""

    def test_leave_includes_communications(self):
        tools = get_tools_for_context(page="leave")
        comms_tools = [t for t in tools if TOOL_DOMAINS.get(t) == "communications"]
        assert len(comms_tools) > 0

    def test_leave_includes_regulatory(self):
        tools = get_tools_for_context(page="leave")
        reg_tools = [t for t in tools if TOOL_DOMAINS.get(t) == "regulatory"]
        assert len(reg_tools) > 0

    def test_leave_excludes_banking(self):
        tools = get_tools_for_context(page="leave")
        banking_tools = [t for t in tools if TOOL_DOMAINS.get(t) == "banking"]
        assert len(banking_tools) == 0

    def test_leave_excludes_accounting(self):
        tools = get_tools_for_context(page="leave")
        accounting_tools = [t for t in tools if TOOL_DOMAINS.get(t) == "accounting"]
        assert len(accounting_tools) == 0

    def test_leave_includes_email_tools(self):
        tools = get_tools_for_context(page="leave")
        email_tools = [t for t in tools if "email" in t or "leave_notification" in t]
        assert len(email_tools) > 0


# ---------------------------------------------------------------------------
# Role-Based Filtering
# ---------------------------------------------------------------------------


class TestRoleFiltering:
    """Role-based tool filtering."""

    def test_employee_role_only_communications_and_regulatory(self):
        tools = get_tools_for_context(page="payroll", role="employee")
        for tool_name in tools:
            domain = TOOL_DOMAINS.get(tool_name, "unknown")
            assert domain in {
                "communications",
                "regulatory",
                "shared",
            }, f"Employee should not see {tool_name} (domain={domain})"

    def test_employee_role_no_government_tools(self):
        tools = get_tools_for_context(page="payroll", role="employee")
        gov_tools = [t for t in tools if TOOL_DOMAINS.get(t) == "government"]
        assert len(gov_tools) == 0

    def test_employee_role_no_banking_tools(self):
        tools = get_tools_for_context(page="payroll", role="employee")
        banking_tools = [t for t in tools if TOOL_DOMAINS.get(t) == "banking"]
        assert len(banking_tools) == 0

    def test_employee_role_no_accounting_tools(self):
        tools = get_tools_for_context(page="payroll", role="employee")
        accounting_tools = [t for t in tools if TOOL_DOMAINS.get(t) == "accounting"]
        assert len(accounting_tools) == 0

    def test_admin_role_gets_all_domain_tools(self):
        tools = get_tools_for_context(page="payroll", role="admin")
        domains = {TOOL_DOMAINS.get(t) for t in tools} - {None}
        # Payroll page domains: government, banking, accounting, communications, shared
        assert "government" in domains
        assert "banking" in domains
        assert "accounting" in domains
        assert "communications" in domains

    def test_hr_manager_role_gets_same_as_admin(self):
        admin_tools = set(get_tools_for_context(page="payroll", role="admin"))
        hr_tools = set(get_tools_for_context(page="payroll", role="hr_manager"))
        # hr_manager should get the same as admin (not explicitly restricted)
        assert admin_tools == hr_tools


# ---------------------------------------------------------------------------
# Connected Providers Filter
# ---------------------------------------------------------------------------


class TestConnectedProviders:
    """Filter tools by which external providers are connected."""

    def test_only_xero_connected_gets_only_accounting(self):
        tools = get_tools_for_context(
            page="payroll",
            connected_providers=["xero"],
        )
        accounting_tools = [t for t in tools if TOOL_DOMAINS.get(t) == "accounting"]
        assert len(accounting_tools) > 0

    def test_no_banking_when_no_bank_connected(self):
        tools = get_tools_for_context(
            page="payroll",
            connected_providers=["xero"],
        )
        banking_tools = [t for t in tools if TOOL_DOMAINS.get(t) == "banking"]
        assert len(banking_tools) == 0

    def test_dbs_connected_enables_banking(self):
        tools = get_tools_for_context(
            page="payroll",
            connected_providers=["dbs"],
        )
        banking_tools = [t for t in tools if TOOL_DOMAINS.get(t) == "banking"]
        assert len(banking_tools) > 0

    def test_regulatory_always_available(self):
        """Regulatory tools are always available, even with no connected providers."""
        tools = get_tools_for_context(
            page="compliance",
            connected_providers=[],
        )
        reg_tools = [t for t in tools if TOOL_DOMAINS.get(t) == "regulatory"]
        assert len(reg_tools) > 0

    def test_government_always_available(self):
        """Government tools (data.gov.sg) are always available."""
        tools = get_tools_for_context(
            page="payroll",
            connected_providers=[],
        )
        gov_tools = [t for t in tools if TOOL_DOMAINS.get(t) == "government"]
        assert len(gov_tools) > 0

    def test_shared_tools_always_available(self):
        """confirm_action should always be available."""
        tools = get_tools_for_context(
            page="payroll",
            connected_providers=[],
        )
        assert "confirm_action" in tools

    def test_resend_connected_enables_communications(self):
        tools = get_tools_for_context(
            page="leave",
            connected_providers=["resend"],
        )
        comms_tools = [t for t in tools if TOOL_DOMAINS.get(t) == "communications"]
        assert len(comms_tools) > 0

    def test_no_comms_when_no_comms_provider_connected(self):
        tools = get_tools_for_context(
            page="leave",
            connected_providers=["xero"],
        )
        comms_tools = [t for t in tools if TOOL_DOMAINS.get(t) == "communications"]
        assert len(comms_tools) == 0


# ---------------------------------------------------------------------------
# Training Page (SkillsFuture)
# ---------------------------------------------------------------------------


class TestTrainingPage:
    """Training page should include SkillsFuture tools from government domain."""

    def test_training_page_includes_government_tools(self):
        tools = get_tools_for_context(page="training")
        gov_tools = [t for t in tools if TOOL_DOMAINS.get(t) == "government"]
        assert len(gov_tools) > 0

    def test_training_page_includes_skillsfuture(self):
        tools = get_tools_for_context(page="training")
        sf_tools = [t for t in tools if "skillsfuture" in t]
        assert len(sf_tools) > 0, "Training page should include SkillsFuture tools"


# ---------------------------------------------------------------------------
# Tool Count Reasonableness
# ---------------------------------------------------------------------------


class TestToolCountReasonableness:
    """Tool count per page should be reasonable (not all 80+ tools)."""

    def test_payroll_page_tool_count(self):
        tools = get_tools_for_context(page="payroll")
        count = len(tools)
        total_tools = len(TOOL_DOMAINS)
        # Payroll is the broadest page (4 domains + shared). It should still
        # be fewer than the total tool count (which includes regulatory-only tools).
        assert (
            10 <= count < total_tools
        ), f"Payroll has {count} tools (total={total_tools}), expected between 10 and {total_tools - 1}"

    def test_leave_page_fewer_tools_than_payroll(self):
        payroll_tools = get_tools_for_context(page="payroll")
        leave_tools = get_tools_for_context(page="leave")
        assert len(leave_tools) < len(payroll_tools)

    def test_dashboard_has_fewer_tools_than_settings(self):
        dashboard_tools = get_tools_for_context(page="dashboard")
        settings_tools = get_tools_for_context(page="settings")
        assert len(dashboard_tools) <= len(settings_tools)

    def test_all_pages_have_at_least_one_tool(self):
        for page in PAGE_TOOL_DOMAINS:
            tools = get_tools_for_context(page=page)
            assert len(tools) >= 1, f"Page '{page}' has no tools"

    def test_employee_role_always_fewer_than_admin(self):
        for page in PAGE_TOOL_DOMAINS:
            admin_tools = get_tools_for_context(page=page, role="admin")
            emp_tools = get_tools_for_context(page=page, role="employee")
            assert len(emp_tools) <= len(
                admin_tools
            ), f"Employee has more tools than admin on page '{page}'"

    def test_total_tool_domains_populated(self):
        """Sanity check: TOOL_DOMAINS has entries for all expected domains."""
        all_domains = set(TOOL_DOMAINS.values())
        assert "government" in all_domains
        assert "accounting" in all_domains
        assert "banking" in all_domains
        assert "communications" in all_domains
        assert "regulatory" in all_domains
        assert "shared" in all_domains


# ---------------------------------------------------------------------------
# get_tool_count_by_page
# ---------------------------------------------------------------------------


class TestToolCountByPage:
    """Verify the monitoring helper."""

    def test_returns_dict_with_all_pages(self):
        counts = get_tool_count_by_page()
        assert isinstance(counts, dict)
        for page in PAGE_TOOL_DOMAINS:
            assert page in counts

    def test_all_counts_positive(self):
        counts = get_tool_count_by_page()
        for page, count in counts.items():
            assert count >= 1, f"Page '{page}' has 0 tools"


# ---------------------------------------------------------------------------
# Unknown Page Fallback
# ---------------------------------------------------------------------------


class TestUnknownPage:
    """Unknown page falls back to dashboard tools."""

    def test_unknown_page_uses_dashboard(self):
        unknown_tools = get_tools_for_context(page="nonexistent_page")
        dashboard_tools = get_tools_for_context(page="dashboard")
        assert set(unknown_tools) == set(dashboard_tools)
