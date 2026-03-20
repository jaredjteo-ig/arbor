# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""Central tool registry for the Shadow Agent.

Maps (module, action) pairs to API call configurations. Each tool
definition includes the HTTP method, path, required parameters, trust
level, and a human-readable description.

Core modules (employees, payroll, leave, attendance, navigation) are
registered inline. Additional modules will be added in M62.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

__all__ = [
    "ToolDefinition",
    "ToolRegistry",
]


@dataclass(frozen=True)
class ToolDefinition:
    """Configuration for a single API tool the Shadow Agent can invoke."""

    module: str
    action: str
    method: str  # GET, POST, PATCH, DELETE
    path: str  # e.g. "/leave/balances/{employee_id}"
    params: list[str]  # required parameters (path and body)
    trust_level: str  # "autonomous", "propose", "always_propose"
    description: str  # human-readable description for PACE preview
    is_mcp: bool = False  # whether this calls an MCP tool vs REST API


class ToolRegistry:
    """Central registry mapping (module, action) to API tool definitions.

    Tools are organized by module. Each module can have multiple actions,
    each mapped to a specific API endpoint.
    """

    def __init__(self) -> None:
        self._tools: dict[str, list[ToolDefinition]] = {}
        self._register_core_tools()

    def register(self, tool: ToolDefinition) -> None:
        """Register a tool definition."""
        if tool.module not in self._tools:
            self._tools[tool.module] = []
        self._tools[tool.module].append(tool)

    def get_tools(self, module: str) -> list[ToolDefinition]:
        """Get all tools registered for a module.

        Args:
            module: The module name (e.g. "employees", "payroll").

        Returns:
            List of ToolDefinitions for the module, or empty list.
        """
        return list(self._tools.get(module, []))

    def resolve_tool(self, module: str, action: str) -> ToolDefinition | None:
        """Resolve a specific (module, action) pair to a tool definition.

        Args:
            module: The module name.
            action: The action name within the module.

        Returns:
            The matching ToolDefinition, or None if not found.
        """
        for tool in self._tools.get(module, []):
            if tool.action == action:
                return tool
        return None

    def get_all_modules(self) -> list[str]:
        """Get the list of all registered module names.

        Returns:
            Sorted list of module name strings.
        """
        return sorted(self._tools.keys())

    def get_all_tools(self) -> list[ToolDefinition]:
        """Get a flat list of all registered tools across all modules.

        Returns:
            List of all ToolDefinitions.
        """
        all_tools: list[ToolDefinition] = []
        for tools in self._tools.values():
            all_tools.extend(tools)
        return all_tools

    def _register_core_tools(self) -> None:
        """Register the core tool set for the most important modules.

        Covers employees, payroll, leave, attendance, claims, navigation,
        and settings. Full module coverage is added in M62.
        """
        # ── Employees ────────────────────────────────────────────
        self.register(
            ToolDefinition(
                module="employees",
                action="list",
                method="GET",
                path="/employees",
                params=[],
                trust_level="autonomous",
                description="List all employees in the company",
            )
        )
        self.register(
            ToolDefinition(
                module="employees",
                action="get",
                method="GET",
                path="/employees/{employee_id}",
                params=["employee_id"],
                trust_level="autonomous",
                description="Get details of a specific employee",
            )
        )
        self.register(
            ToolDefinition(
                module="employees",
                action="search",
                method="GET",
                path="/employees",
                params=[],
                trust_level="autonomous",
                description="Search employees by name or other criteria",
            )
        )
        self.register(
            ToolDefinition(
                module="employees",
                action="create",
                method="POST",
                path="/employees/invite",
                params=["email", "full_name", "role"],
                trust_level="propose",
                description="Invite a new employee to the company",
            )
        )
        self.register(
            ToolDefinition(
                module="employees",
                action="update",
                method="PATCH",
                path="/employees/{employee_id}",
                params=["employee_id"],
                trust_level="propose",
                description="Update an employee's profile information",
            )
        )
        self.register(
            ToolDefinition(
                module="employees",
                action="delete",
                method="DELETE",
                path="/employees/{employee_id}",
                params=["employee_id"],
                trust_level="always_propose",
                description="Delete an employee record (irreversible)",
            )
        )
        self.register(
            ToolDefinition(
                module="employees",
                action="me",
                method="GET",
                path="/employees/me",
                params=[],
                trust_level="autonomous",
                description="Get your own employee profile",
            )
        )
        self.register(
            ToolDefinition(
                module="employees",
                action="confirm_probation",
                method="POST",
                path="/employees/{employee_id}/confirm",
                params=["employee_id"],
                trust_level="propose",
                description="Confirm an employee's probation period",
            )
        )
        self.register(
            ToolDefinition(
                module="employees",
                action="org_chart",
                method="GET",
                path="/employees/org-chart/data",
                params=[],
                trust_level="autonomous",
                description="View the company organisation chart",
            )
        )
        self.register(
            ToolDefinition(
                module="employees",
                action="import",
                method="POST",
                path="/employees/import/preview",
                params=[],
                trust_level="propose",
                description="Preview bulk employee import from CSV/Excel",
            )
        )
        self.register(
            ToolDefinition(
                module="employees",
                action="probation_due",
                method="GET",
                path="/employees/probation/due",
                params=[],
                trust_level="autonomous",
                description="List employees with upcoming probation reviews",
            )
        )

        # ── Payroll ──────────────────────────────────────────────
        self.register(
            ToolDefinition(
                module="payroll",
                action="calculate",
                method="POST",
                path="/payroll/calculate",
                params=["year", "month"],
                trust_level="propose",
                description="Calculate payroll for a given month",
            )
        )
        self.register(
            ToolDefinition(
                module="payroll",
                action="list_runs",
                method="GET",
                path="/payroll/runs",
                params=[],
                trust_level="autonomous",
                description="List all payroll runs",
            )
        )
        self.register(
            ToolDefinition(
                module="payroll",
                action="get_run",
                method="GET",
                path="/payroll/runs/{run_id}",
                params=["run_id"],
                trust_level="autonomous",
                description="Get details of a specific payroll run",
            )
        )
        self.register(
            ToolDefinition(
                module="payroll",
                action="approve_run",
                method="POST",
                path="/payroll/runs/{run_id}/approve",
                params=["run_id"],
                trust_level="propose",
                description="Approve a payroll run for payment",
            )
        )
        self.register(
            ToolDefinition(
                module="payroll",
                action="mark_paid",
                method="POST",
                path="/payroll/runs/{run_id}/mark-paid",
                params=["run_id"],
                trust_level="always_propose",
                description="Mark a payroll run as paid (cannot be undone)",
            )
        )
        self.register(
            ToolDefinition(
                module="payroll",
                action="cancel_run",
                method="POST",
                path="/payroll/runs/{run_id}/cancel",
                params=["run_id"],
                trust_level="always_propose",
                description="Cancel a payroll run",
            )
        )
        self.register(
            ToolDefinition(
                module="payroll",
                action="my_payslips",
                method="GET",
                path="/payroll/my-payslips",
                params=[],
                trust_level="autonomous",
                description="View your own payslips",
            )
        )
        self.register(
            ToolDefinition(
                module="payroll",
                action="get_payslip",
                method="GET",
                path="/payroll/runs/{run_id}/payslips/{payslip_id}",
                params=["run_id", "payslip_id"],
                trust_level="autonomous",
                description="View a specific payslip",
            )
        )
        self.register(
            ToolDefinition(
                module="payroll",
                action="cpf_ytd",
                method="GET",
                path="/payroll/cpf-ytd/{employee_id}",
                params=["employee_id"],
                trust_level="autonomous",
                description="View CPF year-to-date contributions for an employee",
            )
        )
        self.register(
            ToolDefinition(
                module="payroll",
                action="simulate",
                method="POST",
                path="/payroll/simulate",
                params=[],
                trust_level="autonomous",
                description="Simulate a payroll run without saving",
            )
        )
        self.register(
            ToolDefinition(
                module="payroll",
                action="variance",
                method="GET",
                path="/payroll/variance",
                params=[],
                trust_level="autonomous",
                description="View payroll variance report",
            )
        )
        self.register(
            ToolDefinition(
                module="payroll",
                action="generate_ir8a",
                method="POST",
                path="/payroll/tax/generate-ir8a",
                params=[],
                trust_level="propose",
                description="Generate IR8A tax filings for employees",
            )
        )
        self.register(
            ToolDefinition(
                module="payroll",
                action="generate_ir21",
                method="POST",
                path="/payroll/tax/generate-ir21/{employee_id}",
                params=["employee_id"],
                trust_level="propose",
                description="Generate IR21 tax clearance for a departing employee",
            )
        )
        self.register(
            ToolDefinition(
                module="payroll",
                action="create_adhoc",
                method="POST",
                path="/payroll/runs/adhoc",
                params=[],
                trust_level="propose",
                description="Create an ad-hoc payroll run",
            )
        )

        # ── Leave ────────────────────────────────────────────────
        self.register(
            ToolDefinition(
                module="leave",
                action="apply",
                method="POST",
                path="/leave/apply",
                params=["leave_type_id", "start_date", "end_date"],
                trust_level="propose",
                description="Apply for leave",
            )
        )
        self.register(
            ToolDefinition(
                module="leave",
                action="list",
                method="GET",
                path="/leave/applications",
                params=[],
                trust_level="autonomous",
                description="List leave applications",
            )
        )
        self.register(
            ToolDefinition(
                module="leave",
                action="approve",
                method="PATCH",
                path="/leave/applications/{application_id}/approve",
                params=["application_id"],
                trust_level="propose",
                description="Approve a leave application",
            )
        )
        self.register(
            ToolDefinition(
                module="leave",
                action="reject",
                method="PATCH",
                path="/leave/applications/{application_id}/reject",
                params=["application_id"],
                trust_level="propose",
                description="Reject a leave application",
            )
        )
        self.register(
            ToolDefinition(
                module="leave",
                action="withdraw",
                method="PATCH",
                path="/leave/applications/{application_id}/withdraw",
                params=["application_id"],
                trust_level="propose",
                description="Withdraw a leave application",
            )
        )
        self.register(
            ToolDefinition(
                module="leave",
                action="cancel",
                method="PATCH",
                path="/leave/applications/{application_id}/cancel",
                params=["application_id"],
                trust_level="always_propose",
                description="Cancel an approved leave application",
            )
        )
        self.register(
            ToolDefinition(
                module="leave",
                action="balance",
                method="GET",
                path="/leave/balances/{employee_id}",
                params=["employee_id"],
                trust_level="autonomous",
                description="Check leave balances for an employee",
            )
        )
        self.register(
            ToolDefinition(
                module="leave",
                action="types",
                method="GET",
                path="/leave/types",
                params=[],
                trust_level="autonomous",
                description="List available leave types",
            )
        )
        self.register(
            ToolDefinition(
                module="leave",
                action="calendar",
                method="GET",
                path="/leave/calendar",
                params=[],
                trust_level="autonomous",
                description="View the leave calendar",
            )
        )
        self.register(
            ToolDefinition(
                module="leave",
                action="public_holidays",
                method="GET",
                path="/leave/public-holidays",
                params=[],
                trust_level="autonomous",
                description="List public holidays",
            )
        )
        self.register(
            ToolDefinition(
                module="leave",
                action="encash",
                method="POST",
                path="/leave/encash",
                params=["employee_id", "leave_type_id", "days"],
                trust_level="propose",
                description="Encash unused leave days",
            )
        )
        self.register(
            ToolDefinition(
                module="leave",
                action="off_in_lieu",
                method="POST",
                path="/leave/off-in-lieu",
                params=["employee_id", "date", "hours"],
                trust_level="propose",
                description="Record off-in-lieu for overtime worked",
            )
        )
        self.register(
            ToolDefinition(
                module="leave",
                action="policies",
                method="GET",
                path="/leave/policies",
                params=[],
                trust_level="autonomous",
                description="View company leave policies",
            )
        )

        # ── Attendance ───────────────────────────────────────────
        self.register(
            ToolDefinition(
                module="attendance",
                action="clock_in",
                method="POST",
                path="/attendance/clock-in",
                params=[],
                trust_level="propose",
                description="Record clock-in for today",
            )
        )
        self.register(
            ToolDefinition(
                module="attendance",
                action="clock_out",
                method="POST",
                path="/attendance/clock-out",
                params=[],
                trust_level="propose",
                description="Record clock-out for today",
            )
        )
        self.register(
            ToolDefinition(
                module="attendance",
                action="today",
                method="GET",
                path="/attendance/today",
                params=[],
                trust_level="autonomous",
                description="View today's attendance status",
            )
        )
        self.register(
            ToolDefinition(
                module="attendance",
                action="records",
                method="GET",
                path="/attendance/records",
                params=[],
                trust_level="autonomous",
                description="View attendance records",
            )
        )
        self.register(
            ToolDefinition(
                module="attendance",
                action="summary",
                method="GET",
                path="/attendance/summary",
                params=[],
                trust_level="autonomous",
                description="View attendance summary",
            )
        )
        self.register(
            ToolDefinition(
                module="attendance",
                action="dashboard",
                method="GET",
                path="/attendance/today/dashboard",
                params=[],
                trust_level="autonomous",
                description="View today's attendance dashboard",
            )
        )
        self.register(
            ToolDefinition(
                module="attendance",
                action="settings",
                method="GET",
                path="/attendance/settings",
                params=[],
                trust_level="autonomous",
                description="View attendance settings",
            )
        )
        self.register(
            ToolDefinition(
                module="attendance",
                action="submit_timesheet",
                method="POST",
                path="/attendance/timesheet/submit",
                params=[],
                trust_level="propose",
                description="Submit your timesheet for approval",
            )
        )
        self.register(
            ToolDefinition(
                module="attendance",
                action="approve_timesheet",
                method="PATCH",
                path="/attendance/timesheet/{timesheet_id}/approve",
                params=["timesheet_id"],
                trust_level="propose",
                description="Approve a timesheet",
            )
        )
        self.register(
            ToolDefinition(
                module="attendance",
                action="list_timesheets",
                method="GET",
                path="/attendance/timesheets",
                params=[],
                trust_level="autonomous",
                description="List timesheets",
            )
        )

        # ── Claims ───────────────────────────────────────────────
        self.register(
            ToolDefinition(
                module="claims",
                action="list",
                method="GET",
                path="/claims",
                params=[],
                trust_level="autonomous",
                description="List your expense claims",
            )
        )
        self.register(
            ToolDefinition(
                module="claims",
                action="create",
                method="POST",
                path="/claims",
                params=["category_id", "description", "amount"],
                trust_level="propose",
                description="Create a new expense claim",
            )
        )
        self.register(
            ToolDefinition(
                module="claims",
                action="get",
                method="GET",
                path="/claims/{claim_id}",
                params=["claim_id"],
                trust_level="autonomous",
                description="View a specific claim",
            )
        )
        self.register(
            ToolDefinition(
                module="claims",
                action="submit",
                method="PATCH",
                path="/claims/{claim_id}/submit",
                params=["claim_id"],
                trust_level="propose",
                description="Submit a claim for approval",
            )
        )
        self.register(
            ToolDefinition(
                module="claims",
                action="approve",
                method="PATCH",
                path="/claims/{claim_id}/approve",
                params=["claim_id"],
                trust_level="propose",
                description="Approve a submitted claim",
            )
        )
        self.register(
            ToolDefinition(
                module="claims",
                action="reject",
                method="PATCH",
                path="/claims/{claim_id}/reject",
                params=["claim_id"],
                trust_level="propose",
                description="Reject a submitted claim",
            )
        )
        self.register(
            ToolDefinition(
                module="claims",
                action="categories",
                method="GET",
                path="/claims/categories",
                params=[],
                trust_level="autonomous",
                description="List claim categories",
            )
        )

        # ── Navigation ───────────────────────────────────────────
        # Navigation tools don't call the API — they return frontend routes
        self.register(
            ToolDefinition(
                module="navigation",
                action="navigate",
                method="GET",
                path="",  # No API call — frontend handles this
                params=["route"],
                trust_level="autonomous",
                description="Navigate to a page in the application",
            )
        )

        # ── Documents ────────────────────────────────────────────
        self.register(
            ToolDefinition(
                module="documents",
                action="list_templates",
                method="GET",
                path="/document/templates",
                params=[],
                trust_level="autonomous",
                description="List available document templates",
            )
        )
        self.register(
            ToolDefinition(
                module="documents",
                action="generate",
                method="POST",
                path="/document/generate",
                params=["template_id"],
                trust_level="propose",
                description="Generate a document from a template",
            )
        )
        self.register(
            ToolDefinition(
                module="documents",
                action="history",
                method="GET",
                path="/document/history",
                params=[],
                trust_level="autonomous",
                description="View document generation history",
            )
        )

        # ── Reports ──────────────────────────────────────────────
        self.register(
            ToolDefinition(
                module="reports",
                action="payroll_summary",
                method="GET",
                path="/payroll/reports/summary",
                params=[],
                trust_level="autonomous",
                description="View payroll summary report",
            )
        )
        self.register(
            ToolDefinition(
                module="reports",
                action="payroll_ytd",
                method="GET",
                path="/payroll/reports/ytd",
                params=[],
                trust_level="autonomous",
                description="View payroll year-to-date report",
            )
        )

        # ── Calculator ───────────────────────────────────────────
        self.register(
            ToolDefinition(
                module="calculator",
                action="calculate_cpf",
                method="POST",
                path="/calculator/cpf",
                params=["gross_salary", "age", "citizenship_status"],
                trust_level="autonomous",
                description="Calculate CPF contributions",
            )
        )

        # ── Settings ─────────────────────────────────────────────
        self.register(
            ToolDefinition(
                module="settings",
                action="get",
                method="GET",
                path="/settings",
                params=[],
                trust_level="autonomous",
                description="View company settings",
            )
        )

        # ── Shifts ───────────────────────────────────────────────
        self.register(
            ToolDefinition(
                module="shifts",
                action="my_schedule",
                method="GET",
                path="/shifts/my-schedule",
                params=[],
                trust_level="autonomous",
                description="View your shift schedule",
            )
        )
        self.register(
            ToolDefinition(
                module="shifts",
                action="list_templates",
                method="GET",
                path="/shifts/templates",
                params=[],
                trust_level="autonomous",
                description="List shift templates",
            )
        )
        self.register(
            ToolDefinition(
                module="shifts",
                action="schedule",
                method="GET",
                path="/shifts/schedule",
                params=[],
                trust_level="autonomous",
                description="View the team shift schedule",
            )
        )

        # ── Compliance ───────────────────────────────────────────
        self.register(
            ToolDefinition(
                module="compliance",
                action="check",
                method="GET",
                path="/compliance",
                params=[],
                trust_level="autonomous",
                description="Run a compliance check",
            )
        )

        # ── Search ───────────────────────────────────────────────
        self.register(
            ToolDefinition(
                module="search",
                action="search",
                method="GET",
                path="/search",
                params=["q"],
                trust_level="autonomous",
                description="Search across all modules",
            )
        )

        # ── M62: Additional modules ──────────────────────────────────

        # Recruitment
        for action, method, path, params, trust, desc in [
            (
                "post_job",
                "POST",
                "/recruitment/jobs",
                ["title", "department", "description"],
                "propose",
                "Post a new job listing",
            ),
            ("list_jobs", "GET", "/recruitment/jobs", [], "autonomous", "List all job listings"),
            (
                "add_candidate",
                "POST",
                "/recruitment/candidates",
                ["name", "email", "job_id"],
                "propose",
                "Add a candidate to the pipeline",
            ),
            (
                "list_candidates",
                "GET",
                "/recruitment/candidates",
                [],
                "autonomous",
                "List candidates for a job",
            ),
            (
                "schedule_interview",
                "POST",
                "/recruitment/interviews",
                ["candidate_id", "date", "interviewer_id"],
                "propose",
                "Schedule an interview",
            ),
            (
                "update_candidate_status",
                "PATCH",
                "/recruitment/candidates/{id}/status",
                ["status"],
                "propose",
                "Update candidate pipeline status",
            ),
            (
                "hire_candidate",
                "POST",
                "/recruitment/candidates/{id}/hire",
                [],
                "always_propose",
                "Convert candidate to employee",
            ),
        ]:
            self.register(
                ToolDefinition(
                    module="recruitment",
                    action=action,
                    method=method,
                    path=path,
                    params=params,
                    trust_level=trust,
                    description=desc,
                )
            )

        # Projects
        for action, method, path, params, trust, desc in [
            (
                "create",
                "POST",
                "/projects",
                ["name", "start_date"],
                "propose",
                "Create a new project",
            ),
            ("list", "GET", "/projects", [], "autonomous", "List all projects"),
            ("get", "GET", "/projects/{id}", [], "autonomous", "Get project details"),
            (
                "add_member",
                "POST",
                "/projects/{id}/members",
                ["employee_id", "role"],
                "propose",
                "Add team member to project",
            ),
            (
                "log_time",
                "POST",
                "/projects/{id}/timesheets",
                ["employee_id", "hours", "date"],
                "propose",
                "Log time to project",
            ),
            (
                "list_timesheets",
                "GET",
                "/projects/{id}/timesheets",
                [],
                "autonomous",
                "List project timesheets",
            ),
        ]:
            self.register(
                ToolDefinition(
                    module="projects",
                    action=action,
                    method=method,
                    path=path,
                    params=params,
                    trust_level=trust,
                    description=desc,
                )
            )

        # Inventory
        for action, method, path, params, trust, desc in [
            ("list_items", "GET", "/inventory/items", [], "autonomous", "List inventory items"),
            (
                "get_item",
                "GET",
                "/inventory/items/{id}",
                [],
                "autonomous",
                "Get inventory item details",
            ),
            (
                "create_item",
                "POST",
                "/inventory/items",
                ["name", "category_id", "location_id"],
                "propose",
                "Create inventory item",
            ),
            (
                "request_item",
                "POST",
                "/inventory/requests",
                ["item_id", "quantity", "reason"],
                "propose",
                "Request an inventory item",
            ),
            (
                "approve_request",
                "PATCH",
                "/inventory/requests/{id}/approve",
                [],
                "propose",
                "Approve inventory request",
            ),
            (
                "transfer",
                "POST",
                "/inventory/items/{id}/transfer",
                ["to_location_id"],
                "propose",
                "Transfer item between locations",
            ),
        ]:
            self.register(
                ToolDefinition(
                    module="inventory",
                    action=action,
                    method=method,
                    path=path,
                    params=params,
                    trust_level=trust,
                    description=desc,
                )
            )

        # Appraisals
        for action, method, path, params, trust, desc in [
            (
                "list_cycles",
                "GET",
                "/appraisals/periods",
                [],
                "autonomous",
                "List appraisal cycles",
            ),
            (
                "launch_cycle",
                "POST",
                "/appraisals/periods/{id}/launch",
                [],
                "always_propose",
                "Launch an appraisal cycle",
            ),
            (
                "list_reviews",
                "GET",
                "/appraisals/reviews",
                [],
                "autonomous",
                "List appraisal reviews",
            ),
            (
                "submit_review",
                "POST",
                "/appraisals/reviews/{id}/submit",
                ["content"],
                "propose",
                "Submit an appraisal review",
            ),
            (
                "sign_off",
                "PATCH",
                "/appraisals/reviews/{id}/signoff",
                [],
                "propose",
                "Sign off on an appraisal review",
            ),
        ]:
            self.register(
                ToolDefinition(
                    module="appraisals",
                    action=action,
                    method=method,
                    path=path,
                    params=params,
                    trust_level=trust,
                    description=desc,
                )
            )

        # Government (MCP tools — double_confirm required for all)
        for action, method, path, params, trust, desc in [
            (
                "cpf_generate",
                "POST",
                "/integrations/government/cpf/generate",
                ["month"],
                "double_confirm",
                "Generate CPF submission file",
            ),
            (
                "cpf_submit",
                "POST",
                "/integrations/government/cpf/submit",
                ["month"],
                "double_confirm",
                "Submit CPF to CPF Board",
            ),
            (
                "ir8a_generate",
                "POST",
                "/integrations/government/iras/ir8a/generate",
                ["year"],
                "double_confirm",
                "Generate IR8A tax filing",
            ),
            (
                "ir8a_submit",
                "POST",
                "/integrations/government/iras/ir8a/submit",
                ["year"],
                "double_confirm",
                "Submit IR8A to IRAS",
            ),
            (
                "ir21_generate",
                "POST",
                "/integrations/government/iras/ir21/generate",
                ["employee_id"],
                "double_confirm",
                "Generate IR21 for departing foreign employee",
            ),
        ]:
            self.register(
                ToolDefinition(
                    module="government",
                    action=action,
                    method=method,
                    path=path,
                    params=params,
                    trust_level=trust,
                    description=desc,
                    is_mcp=True,
                )
            )

        # Accounting (MCP tools — financial actions use double_confirm)
        for action, method, path, params, trust, desc in [
            (
                "post_payroll_journal",
                "POST",
                "/integrations/accounting/xero/payroll-journal",
                ["month"],
                "double_confirm",
                "Post payroll journal to Xero",
            ),
            (
                "post_claims_journal",
                "POST",
                "/integrations/accounting/xero/claims-journal",
                ["month"],
                "double_confirm",
                "Post claims journal to Xero",
            ),
            (
                "export_csv",
                "POST",
                "/integrations/accounting/export/csv",
                ["type", "month"],
                "propose",
                "Export accounting data as CSV",
            ),
        ]:
            self.register(
                ToolDefinition(
                    module="accounting",
                    action=action,
                    method=method,
                    path=path,
                    params=params,
                    trust_level=trust,
                    description=desc,
                    is_mcp=True,
                )
            )

        # Admin
        for action, method, path, params, trust, desc in [
            (
                "list_users",
                "GET",
                "/admin/users",
                [],
                "autonomous",
                "List all users in the company",
            ),
            (
                "invite_user",
                "POST",
                "/employees/invite",
                ["email", "name", "role"],
                "propose",
                "Invite a new user to the platform",
            ),
            (
                "update_role",
                "PATCH",
                "/admin/users/{id}/role",
                ["role"],
                "always_propose",
                "Change a user's role",
            ),
            ("company_settings", "GET", "/settings", [], "autonomous", "View company settings"),
        ]:
            self.register(
                ToolDefinition(
                    module="admin",
                    action=action,
                    method=method,
                    path=path,
                    params=params,
                    trust_level=trust,
                    description=desc,
                )
            )

        # Advisory (routes to existing advisory pipeline)
        self.register(
            ToolDefinition(
                module="advisory",
                action="query",
                method="POST",
                path="/advisory/query",
                params=["query"],
                trust_level="autonomous",
                description="Ask an HR advisory question (routes to existing advisory pipeline)",
            )
        )

        # ── Navigation: All 33 routes ─────────────────────────────────
        _nav_routes = [
            ("dashboard", "/dashboard", "Main dashboard"),
            ("my_dashboard", "/my-dashboard", "Personal dashboard"),
            ("employees", "/employees", "Employee roster"),
            ("payroll", "/payroll", "Payroll management"),
            ("my_payslips", "/my-payslips", "My payslips"),
            ("leave", "/leave", "Leave management"),
            ("my_leave", "/my-leave", "My leave"),
            ("attendance", "/attendance", "Attendance tracking"),
            ("my_timesheets", "/my-timesheets", "My timesheets"),
            ("shifts", "/shifts", "Shift scheduling"),
            ("claims", "/claims", "Claims and expenses"),
            ("appraisals", "/appraisals", "Performance appraisals"),
            ("projects", "/projects", "Project management"),
            ("inventory", "/inventory", "Inventory management"),
            ("my_inventory", "/my-inventory", "My inventory requests"),
            ("recruitment", "/recruitment", "Recruitment pipeline"),
            ("reports", "/reports", "Reports and analytics"),
            ("admin", "/admin", "Admin console"),
            ("advisory", "/advisory", "HR advisory"),
            ("compliance", "/compliance", "Compliance dashboard"),
            ("alerts", "/alerts", "Regulatory alerts"),
            ("documents", "/documents", "Document templates"),
            ("calculators", "/calculators", "HR calculators"),
            ("help", "/help", "Help center"),
            ("settings", "/settings", "Settings"),
            ("settings_ai", "/settings/ai", "AI configuration"),
            ("profile", "/profile", "Company profile"),
            ("my_profile", "/my-profile", "My profile"),
            ("analytics", "/analytics", "Analytics"),
            ("emergency", "/emergency", "Emergency procedures"),
            ("learning", "/learning", "Learning and training"),
            ("approvals", "/approvals", "Approval workflows"),
            ("policies", "/policies", "Company policies"),
        ]
        for nav_action, route, desc in _nav_routes:
            self.register(
                ToolDefinition(
                    module="navigation",
                    action=nav_action,
                    method="NAV",
                    path=route,
                    params=[],
                    trust_level="autonomous",
                    description=f"Navigate to {desc}",
                )
            )

        total = sum(len(tools) for tools in self._tools.values())
        logger.debug(
            "Tool registry initialised: %d tools across %d modules",
            total,
            len(self._tools),
        )


# Module-level singleton for shared access
_registry: ToolRegistry | None = None


def get_tool_registry() -> ToolRegistry:
    """Get or create the shared ToolRegistry singleton."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
