# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""Response formatter for the Shadow Agent.

All Shadow Agent responses carry the "Arbor: " prefix to establish
the Arbor identity. The formatter translates raw API responses into
user-friendly messages based on module and action context.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "ArborFormatter",
]


class ArborFormatter:
    """Format Shadow Agent responses with the Arbor identity.

    Every response from the Shadow Agent starts with "Arbor: " to
    clearly identify the intelligence layer to the user.
    """

    PREFIX = "Arbor: "

    def format_read(self, data: dict[str, Any], module: str, action: str) -> str:
        """Format a successful read operation response.

        Args:
            data: The parsed API response data.
            module: The module that was queried.
            action: The action that was performed.

        Returns:
            A human-readable summary string with the Arbor prefix.
        """
        # Module-specific formatters
        formatter = _READ_FORMATTERS.get(f"{module}.{action}")
        if formatter is not None:
            return self.PREFIX + formatter(data)

        # Generic list response
        if isinstance(data, dict):
            # Common list response patterns
            for key in ("records", "items", "employees", "applications", "results", "data"):
                items = data.get(key)
                if isinstance(items, list):
                    count = len(items)
                    total = data.get("total", data.get("count", count))
                    return (
                        self.PREFIX + f"Found {total} {module} record{'s' if total != 1 else ''}."
                    )

            # Single record response
            if "id" in data or "name" in data or "full_name" in data:
                name = data.get("full_name") or data.get("name") or data.get("title") or ""
                if name:
                    return self.PREFIX + f"Here are the details for {name}."
                return self.PREFIX + f"Here are the {module} details."

        return self.PREFIX + f"Here are the {module} results."

    def format_write(self, result: dict[str, Any], module: str, action: str) -> str:
        """Format a successful write operation response.

        Args:
            result: The parsed API response data.
            module: The module that was modified.
            action: The action that was performed.

        Returns:
            A human-readable confirmation string with the Arbor prefix.
        """
        formatter = _WRITE_FORMATTERS.get(f"{module}.{action}")
        if formatter is not None:
            return self.PREFIX + formatter(result)

        # Generic write confirmation
        action_past = _action_past_tense(action)
        return self.PREFIX + f"Successfully {action_past} the {module} record."

    def format_multi_step(self, session_dict: dict[str, Any]) -> str:
        """Format the result of a completed multi-step PACE session.

        Args:
            session_dict: The serialized PaceSession dict.

        Returns:
            A human-readable summary of all steps with the Arbor prefix.
        """
        steps = session_dict.get("steps", [])
        results = session_dict.get("results", [])
        status = session_dict.get("status", "unknown")

        total = len(steps)
        succeeded = sum(1 for s in steps if s.get("status") == "done")
        failed = sum(1 for s in steps if s.get("status") == "failed")

        if status == "done" and failed == 0:
            parts = [f"All {total} step{'s' if total != 1 else ''} completed successfully."]
        elif failed > 0:
            parts = [
                f"{succeeded} of {total} steps completed. {failed} step{'s' if failed != 1 else ''} failed."
            ]
        else:
            parts = [f"Session status: {status}. {succeeded}/{total} steps completed."]

        # Add individual step summaries
        for i, step in enumerate(steps):
            step_status = step.get("status", "unknown")
            step_desc = step.get("description", f"Step {i + 1}")
            icon = (
                "Done"
                if step_status == "done"
                else ("Failed" if step_status == "failed" else "Skipped")
            )
            parts.append(f"  {icon}: {step_desc}")

        return self.PREFIX + "\n".join(parts)

    def format_preview(self, session_dict: dict[str, Any]) -> str:
        """Format a PACE session preview for user confirmation.

        Args:
            session_dict: The serialized PaceSession dict.

        Returns:
            A human-readable preview with the Arbor prefix.
        """
        message = session_dict.get("confirmation_message", "")
        steps = session_dict.get("steps", [])

        parts = [message or "I'm ready to perform the following action:"]

        if len(steps) > 1:
            parts.append(f"\nThis involves {len(steps)} steps:")
            for i, step in enumerate(steps, 1):
                parts.append(f"  {i}. {step.get('description', 'Unknown step')}")

        parts.append("\nShall I proceed? Reply 'confirm' to execute or 'cancel' to abort.")

        return self.PREFIX + "\n".join(parts)

    def format_error(self, error: str) -> str:
        """Format an error message with the Arbor prefix.

        Args:
            error: The error message to display.

        Returns:
            The error with the Arbor prefix.
        """
        return self.PREFIX + error

    def format_navigation(self, route: str, description: str) -> dict[str, Any]:
        """Format a navigation instruction for the frontend.

        Navigation responses are structured differently — they contain
        a route for the frontend to navigate to, plus a display message.

        Args:
            route: The frontend route to navigate to (e.g. "/leave/calendar").
            description: Human-readable description of the navigation.

        Returns:
            A dict with type, route, and message fields.
        """
        return {
            "type": "navigation",
            "route": route,
            "message": self.PREFIX + f"Navigating to {description}.",
        }

    def format_advisory_routing(self, query: str) -> str:
        """Format a message indicating the query is being routed to the advisory pipeline.

        Args:
            query: The user's original query.

        Returns:
            A human-readable routing message with the Arbor prefix.
        """
        return self.PREFIX + "Let me look that up for you in our employment law knowledge base."

    def format_attachment_prompt(self, attachment_intent: str) -> str:
        """Format a prompt for the user to upload an attachment.

        Args:
            attachment_intent: The type of attachment expected.

        Returns:
            A human-readable prompt with the Arbor prefix.
        """
        prompts = {
            "bulk_import": "Please upload your CSV or Excel file, and I'll preview the import for you.",
            "document_upload": "Please attach the document you'd like to upload.",
            "receipt_upload": "Please attach the receipt image or PDF for this claim.",
            "payroll_import": "Please upload the payroll data file (CSV or Excel format).",
        }
        msg = prompts.get(attachment_intent, "Please attach the file you'd like to upload.")
        return self.PREFIX + msg


# ── Module-specific read formatters ──────────────────────────


def _format_employee_list(data: dict) -> str:
    """Format employee list response."""
    records = data.get("records", data.get("employees", []))
    if isinstance(data, list):
        records = data
    count = len(records) if isinstance(records, list) else 0
    total = data.get("total", data.get("count", count))
    return f"Found {total} employee{'s' if total != 1 else ''} in your company."


def _format_employee_get(data: dict) -> str:
    """Format single employee detail response."""
    name = data.get("full_name") or data.get("name") or "the employee"
    role = data.get("job_title") or data.get("role") or ""
    dept = data.get("department") or ""
    parts = [f"Here are the details for {name}"]
    if role:
        parts[0] += f" ({role})"
    if dept:
        parts[0] += f" in {dept}"
    parts[0] += "."
    return parts[0]


def _format_leave_balance(data: dict) -> str:
    """Format leave balance response."""
    balances = data.get("balances", data.get("records", []))
    if not isinstance(balances, list) or not balances:
        return "No leave balance records found."
    parts = ["Your leave balances:"]
    for bal in balances[:10]:  # Cap at 10 to avoid overwhelming output
        name = bal.get("leave_type_name") or bal.get("name") or "Leave"
        entitled = bal.get("entitled", 0)
        used = bal.get("used", 0)
        remaining = bal.get("remaining", entitled - used)
        parts.append(f"  {name}: {remaining} days remaining (used {used} of {entitled})")
    return "\n".join(parts)


def _format_payroll_my_payslips(data: dict) -> str:
    """Format payslips list response."""
    payslips = data.get("payslips", data.get("records", []))
    if isinstance(data, list):
        payslips = data
    count = len(payslips) if isinstance(payslips, list) else 0
    if count == 0:
        return "No payslips found."
    return f"Found {count} payslip{'s' if count != 1 else ''}."


def _format_attendance_today(data: dict) -> str:
    """Format today's attendance status."""
    clock_in = data.get("clock_in_time") or data.get("clock_in") or ""
    clock_out = data.get("clock_out_time") or data.get("clock_out") or ""
    status = data.get("status", "")
    if clock_in and clock_out:
        return f"Today: Clocked in at {clock_in}, clocked out at {clock_out}."
    elif clock_in:
        return f"Today: Clocked in at {clock_in}. Not yet clocked out."
    else:
        return "Today: No attendance recorded yet."


def _format_leave_list(data: dict) -> str:
    """Format leave applications list."""
    applications = data.get("applications", data.get("records", []))
    if isinstance(data, list):
        applications = data
    count = len(applications) if isinstance(applications, list) else 0
    total = data.get("total", data.get("count", count))
    return f"Found {total} leave application{'s' if total != 1 else ''}."


_READ_FORMATTERS: dict[str, Any] = {
    "employees.list": _format_employee_list,
    "employees.get": _format_employee_get,
    "employees.me": _format_employee_get,
    "employees.search": _format_employee_list,
    "leave.balance": _format_leave_balance,
    "leave.list": _format_leave_list,
    "payroll.my_payslips": _format_payroll_my_payslips,
    "attendance.today": _format_attendance_today,
}

# ── Module-specific write formatters ─────────────────────────


def _format_leave_apply(data: dict) -> str:
    """Format leave application response."""
    leave_type = data.get("leave_type_name") or data.get("leave_type") or "leave"
    start = data.get("start_date", "")
    end = data.get("end_date", "")
    if start and end and start != end:
        return (
            f"Your {leave_type} application from {start} to {end} has been submitted for approval."
        )
    elif start:
        return f"Your {leave_type} application for {start} has been submitted for approval."
    return f"Your {leave_type} application has been submitted for approval."


def _format_attendance_clock_in(data: dict) -> str:
    """Format clock-in confirmation."""
    time_str = data.get("clock_in_time") or data.get("clock_in") or data.get("time") or ""
    if time_str:
        return f"Clocked in at {time_str}. Have a productive day!"
    return "Clock-in recorded successfully."


def _format_attendance_clock_out(data: dict) -> str:
    """Format clock-out confirmation."""
    time_str = data.get("clock_out_time") or data.get("clock_out") or data.get("time") or ""
    if time_str:
        return f"Clocked out at {time_str}. See you tomorrow!"
    return "Clock-out recorded successfully."


def _format_payroll_calculate(data: dict) -> str:
    """Format payroll calculation response."""
    run_id = data.get("id") or data.get("run_id") or ""
    count = data.get("payslip_count") or data.get("employee_count") or 0
    total = data.get("total_net_pay") or data.get("total_gross") or ""
    parts = ["Payroll calculated successfully."]
    if count:
        parts.append(f"{count} payslip{'s' if count != 1 else ''} generated.")
    if total:
        parts.append(
            f"Total net pay: ${total:,.2f}"
            if isinstance(total, (int, float))
            else f"Total: {total}"
        )
    return " ".join(parts)


_WRITE_FORMATTERS: dict[str, Any] = {
    "leave.apply": _format_leave_apply,
    "attendance.clock_in": _format_attendance_clock_in,
    "attendance.clock_out": _format_attendance_clock_out,
    "payroll.calculate": _format_payroll_calculate,
}


def _action_past_tense(action: str) -> str:
    """Convert an action name to past tense for confirmation messages."""
    past_map = {
        "create": "created",
        "update": "updated",
        "delete": "deleted",
        "approve": "approved",
        "reject": "rejected",
        "submit": "submitted",
        "cancel": "cancelled",
        "apply": "applied for",
        "withdraw": "withdrawn",
        "generate": "generated",
        "calculate": "calculated",
        "clock_in": "clocked in",
        "clock_out": "clocked out",
        "publish": "published",
        "confirm_probation": "confirmed probation for",
        "mark_paid": "marked as paid",
        "invite": "invited",
        "import": "imported",
        "encash": "encashed",
    }
    return past_map.get(action, f"completed '{action}' on")
