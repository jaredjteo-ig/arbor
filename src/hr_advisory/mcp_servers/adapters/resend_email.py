"""Resend email adapter for transactional email delivery.

Sends payslip notifications, leave approvals, onboarding invites,
and other HR communications via the Resend REST API.

T222: Resend Email Connector (C01)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from hr_advisory.mcp_servers.resilience import get_circuit

logger = logging.getLogger(__name__)

_RESEND_API_BASE = "https://api.resend.com"


# ── HTML Email Templates ──────────────────────────────────────

_TEMPLATE_PAYSLIP = """
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
  <div style="background: #f8f9fa; border-radius: 8px; padding: 24px; margin-bottom: 16px;">
    <h2 style="margin: 0 0 8px; color: #1a1a1a;">Payslip for {period}</h2>
    <p style="margin: 0; color: #666;">Hi {employee_name},</p>
  </div>
  <div style="padding: 16px;">
    <p>Your payslip for <strong>{period}</strong> is now available.</p>
    <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
      <tr style="border-bottom: 1px solid #eee;">
        <td style="padding: 8px 0; color: #666;">Gross Pay</td>
        <td style="padding: 8px 0; text-align: right; font-weight: 600;">${gross_pay}</td>
      </tr>
      <tr style="border-bottom: 1px solid #eee;">
        <td style="padding: 8px 0; color: #666;">Deductions</td>
        <td style="padding: 8px 0; text-align: right; color: #dc3545;">${deductions}</td>
      </tr>
      <tr>
        <td style="padding: 8px 0; font-weight: 600;">Net Pay</td>
        <td style="padding: 8px 0; text-align: right; font-weight: 700; font-size: 1.1em; color: #28a745;">${net_pay}</td>
      </tr>
    </table>
    <p style="color: #666; font-size: 0.9em;">Log in to your Arbor portal to view the full breakdown and download your payslip PDF.</p>
  </div>
  <div style="border-top: 1px solid #eee; padding-top: 16px; margin-top: 16px; color: #999; font-size: 0.8em;">
    <p>This is an automated message from {company_name}. Please do not reply to this email.</p>
  </div>
</body>
</html>
"""

_TEMPLATE_LEAVE_APPROVAL = """
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
  <div style="background: #d4edda; border-radius: 8px; padding: 24px; margin-bottom: 16px;">
    <h2 style="margin: 0 0 8px; color: #155724;">Leave Approved</h2>
    <p style="margin: 0; color: #155724;">Hi {employee_name},</p>
  </div>
  <div style="padding: 16px;">
    <p>Your leave request has been <strong style="color: #28a745;">approved</strong>.</p>
    <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
      <tr style="border-bottom: 1px solid #eee;">
        <td style="padding: 8px 0; color: #666;">Leave Type</td>
        <td style="padding: 8px 0; text-align: right;">{leave_type}</td>
      </tr>
      <tr style="border-bottom: 1px solid #eee;">
        <td style="padding: 8px 0; color: #666;">Period</td>
        <td style="padding: 8px 0; text-align: right;">{start_date} to {end_date}</td>
      </tr>
      <tr>
        <td style="padding: 8px 0; color: #666;">Days</td>
        <td style="padding: 8px 0; text-align: right; font-weight: 600;">{days} day(s)</td>
      </tr>
    </table>
    <p style="color: #666;">Approved by: {approver_name}</p>
  </div>
  <div style="border-top: 1px solid #eee; padding-top: 16px; margin-top: 16px; color: #999; font-size: 0.8em;">
    <p>This is an automated message from {company_name}.</p>
  </div>
</body>
</html>
"""

_TEMPLATE_LEAVE_REJECTION = """
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
  <div style="background: #f8d7da; border-radius: 8px; padding: 24px; margin-bottom: 16px;">
    <h2 style="margin: 0 0 8px; color: #721c24;">Leave Request Declined</h2>
    <p style="margin: 0; color: #721c24;">Hi {employee_name},</p>
  </div>
  <div style="padding: 16px;">
    <p>Your leave request has been <strong style="color: #dc3545;">declined</strong>.</p>
    <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
      <tr style="border-bottom: 1px solid #eee;">
        <td style="padding: 8px 0; color: #666;">Leave Type</td>
        <td style="padding: 8px 0; text-align: right;">{leave_type}</td>
      </tr>
      <tr style="border-bottom: 1px solid #eee;">
        <td style="padding: 8px 0; color: #666;">Period</td>
        <td style="padding: 8px 0; text-align: right;">{start_date} to {end_date}</td>
      </tr>
    </table>
    <p><strong>Reason:</strong> {rejection_reason}</p>
    <p style="color: #666;">Please discuss with your manager if you have questions.</p>
  </div>
  <div style="border-top: 1px solid #eee; padding-top: 16px; margin-top: 16px; color: #999; font-size: 0.8em;">
    <p>This is an automated message from {company_name}.</p>
  </div>
</body>
</html>
"""

_TEMPLATE_ONBOARDING_INVITE = """
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
  <div style="background: #cce5ff; border-radius: 8px; padding: 24px; margin-bottom: 16px;">
    <h2 style="margin: 0 0 8px; color: #004085;">Welcome to {company_name}!</h2>
    <p style="margin: 0; color: #004085;">Hi {employee_name},</p>
  </div>
  <div style="padding: 16px;">
    <p>You have been invited to join <strong>{company_name}</strong> on Arbor.</p>
    <p>Please complete your onboarding by clicking the link below:</p>
    <div style="text-align: center; margin: 24px 0;">
      <a href="{onboarding_url}" style="background: #007bff; color: white; padding: 12px 32px; border-radius: 6px; text-decoration: none; font-weight: 600;">Complete Onboarding</a>
    </div>
    <p style="color: #666; font-size: 0.9em;">This link will expire in 7 days. If you have trouble, please contact your HR manager.</p>
    <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
      <tr style="border-bottom: 1px solid #eee;">
        <td style="padding: 8px 0; color: #666;">Position</td>
        <td style="padding: 8px 0; text-align: right;">{position}</td>
      </tr>
      <tr style="border-bottom: 1px solid #eee;">
        <td style="padding: 8px 0; color: #666;">Department</td>
        <td style="padding: 8px 0; text-align: right;">{department}</td>
      </tr>
      <tr>
        <td style="padding: 8px 0; color: #666;">Start Date</td>
        <td style="padding: 8px 0; text-align: right; font-weight: 600;">{start_date}</td>
      </tr>
    </table>
  </div>
  <div style="border-top: 1px solid #eee; padding-top: 16px; margin-top: 16px; color: #999; font-size: 0.8em;">
    <p>This is an automated invitation from {company_name} via Arbor HR Platform.</p>
  </div>
</body>
</html>
"""

_TEMPLATE_COMPLIANCE_ALERT = """
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
  <div style="background: #fff3cd; border-radius: 8px; padding: 24px; margin-bottom: 16px;">
    <h2 style="margin: 0 0 8px; color: #856404;">Compliance Alert</h2>
    <p style="margin: 0; color: #856404;">{alert_title}</p>
  </div>
  <div style="padding: 16px;">
    <p>{alert_description}</p>
    <div style="background: #f8f9fa; border-left: 4px solid #ffc107; padding: 12px 16px; margin: 16px 0;">
      <p style="margin: 0; font-weight: 600;">Urgency: {urgency}</p>
      <p style="margin: 4px 0 0;">Affected areas: {affected_areas}</p>
    </div>
    <p><strong>Action Required:</strong></p>
    <ul>{action_items_html}</ul>
    <p style="color: #666; font-size: 0.9em;">Log in to your Arbor admin panel for details.</p>
  </div>
  <div style="border-top: 1px solid #eee; padding-top: 16px; margin-top: 16px; color: #999; font-size: 0.8em;">
    <p>This is an automated compliance alert from Arbor for {company_name}.</p>
  </div>
</body>
</html>
"""

_TEMPLATE_REGULATORY_UPDATE = """
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
  <div style="background: #e2e3e5; border-radius: 8px; padding: 24px; margin-bottom: 16px;">
    <h2 style="margin: 0 0 8px; color: #383d41;">Regulatory Update</h2>
    <p style="margin: 0; color: #383d41;">{update_title}</p>
  </div>
  <div style="padding: 16px;">
    <p>{update_summary}</p>
    <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
      <tr style="border-bottom: 1px solid #eee;">
        <td style="padding: 8px 0; color: #666;">Source</td>
        <td style="padding: 8px 0; text-align: right;">{source}</td>
      </tr>
      <tr style="border-bottom: 1px solid #eee;">
        <td style="padding: 8px 0; color: #666;">Effective Date</td>
        <td style="padding: 8px 0; text-align: right;">{effective_date}</td>
      </tr>
      <tr>
        <td style="padding: 8px 0; color: #666;">Domains Affected</td>
        <td style="padding: 8px 0; text-align: right;">{domains}</td>
      </tr>
    </table>
    <p style="color: #666; font-size: 0.9em;">Review this update in the Arbor admin panel.</p>
  </div>
  <div style="border-top: 1px solid #eee; padding-top: 16px; margin-top: 16px; color: #999; font-size: 0.8em;">
    <p>This is an automated regulatory intelligence alert from Arbor for {company_name}.</p>
  </div>
</body>
</html>
"""

TEMPLATES: dict[str, str] = {
    "payslip": _TEMPLATE_PAYSLIP,
    "leave_approval": _TEMPLATE_LEAVE_APPROVAL,
    "leave_rejection": _TEMPLATE_LEAVE_REJECTION,
    "onboarding_invite": _TEMPLATE_ONBOARDING_INVITE,
    "compliance_alert": _TEMPLATE_COMPLIANCE_ALERT,
    "regulatory_update": _TEMPLATE_REGULATORY_UPDATE,
}


class ResendAdapter:
    """Adapter for the Resend transactional email API.

    Sends emails for payslip delivery, leave notifications, onboarding
    invites, compliance alerts, and regulatory updates. Supports
    single-send and bulk-send operations.

    Usage::

        adapter = ResendAdapter()
        result = await adapter.send_email(
            to="employee@company.com",
            subject="Your payslip for March 2026",
            html_body="<h1>Payslip</h1>...",
        )
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_from: str = "Arbor HR Platform <noreply@arbor.sg>",
    ):
        self._api_key = api_key or os.environ.get("RESEND_API_KEY", "")
        self._default_from = default_from
        self._circuit = get_circuit("resend")
        self._send_log: list[dict] = []

    def _validate_api_key(self) -> None:
        if not self._api_key:
            raise ValueError(
                "RESEND_API_KEY not configured. "
                "Set the environment variable or pass api_key to constructor."
            )

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def send_email(
        self,
        to: str | list[str],
        subject: str,
        html_body: str,
        from_address: Optional[str] = None,
        reply_to: Optional[str] = None,
        tags: Optional[list[dict[str, str]]] = None,
    ) -> dict:
        """Send a single transactional email via Resend.

        Args:
            to: Recipient email address or list of addresses.
            subject: Email subject line.
            html_body: HTML content of the email.
            from_address: Sender address (defaults to platform default).
            reply_to: Reply-to address.
            tags: Optional Resend tags for tracking.

        Returns:
            Dict with "id" (Resend message ID) and "status".
        """
        self._validate_api_key()

        recipients = [to] if isinstance(to, str) else to
        payload: dict[str, Any] = {
            "from": from_address or self._default_from,
            "to": recipients,
            "subject": subject,
            "html": html_body,
        }
        if reply_to:
            payload["reply_to"] = reply_to
        if tags:
            payload["tags"] = tags

        async def _do_send() -> dict:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{_RESEND_API_BASE}/emails",
                    json=payload,
                    headers=self._headers(),
                )
                resp.raise_for_status()
                return resp.json()

        result = await self._circuit.call(_do_send)

        log_entry = {
            "id": result.get("id", "unknown"),
            "to": recipients,
            "subject": subject,
            "status": "sent",
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }
        self._send_log.append(log_entry)

        logger.info(
            "Email sent via Resend: id=%s, to=%s, subject='%s'",
            result.get("id"),
            recipients[0],
            subject[:50],
        )
        return {"id": result.get("id"), "status": "sent"}

    async def send_bulk(
        self,
        recipients: list[dict[str, str]],
        template_name: str,
        merge_fields: dict[str, str],
        subject: str,
        from_address: Optional[str] = None,
    ) -> dict:
        """Send bulk emails using a template with per-recipient merge fields.

        Args:
            recipients: List of dicts with "email" and optionally "name"
                plus any per-recipient merge field overrides.
            template_name: Name of the template (e.g. "payslip", "leave_approval").
            merge_fields: Shared merge fields applied to all recipients.
            subject: Email subject line (can contain {merge_field} placeholders).
            from_address: Sender address.

        Returns:
            Dict with "total", "sent", "failed", and "results" list.
        """
        self._validate_api_key()

        template = TEMPLATES.get(template_name)
        if template is None:
            available = ", ".join(sorted(TEMPLATES.keys()))
            raise ValueError(f"Unknown template '{template_name}'. Available: {available}")

        results: list[dict] = []
        sent = 0
        failed = 0

        for recipient in recipients:
            email = recipient["email"]
            # Merge shared fields with per-recipient overrides
            fields = {**merge_fields}
            for key, val in recipient.items():
                if key != "email":
                    fields[key] = val

            try:
                rendered_html = self._render_template(template, fields)
                rendered_subject = self._render_template(subject, fields)

                result = await self.send_email(
                    to=email,
                    subject=rendered_subject,
                    html_body=rendered_html,
                    from_address=from_address,
                )
                results.append({"email": email, "status": "sent", "id": result["id"]})
                sent += 1
            except Exception as exc:
                logger.warning(
                    "Failed to send bulk email to %s: %s",
                    email,
                    exc,
                )
                results.append(
                    {
                        "email": email,
                        "status": "failed",
                        "error": str(exc),
                    }
                )
                failed += 1

        return {
            "total": len(recipients),
            "sent": sent,
            "failed": failed,
            "results": results,
        }

    async def send_payslip_notification(
        self,
        employee_email: str,
        employee_name: str,
        period: str,
        gross_pay: str,
        deductions: str,
        net_pay: str,
        company_name: str,
    ) -> dict:
        """Send a payslip notification email with pre-formatted template."""
        html = self._render_template(
            _TEMPLATE_PAYSLIP,
            {
                "employee_name": employee_name,
                "period": period,
                "gross_pay": gross_pay,
                "deductions": deductions,
                "net_pay": net_pay,
                "company_name": company_name,
            },
        )
        return await self.send_email(
            to=employee_email,
            subject=f"Your Payslip for {period}",
            html_body=html,
        )

    async def send_leave_notification(
        self,
        employee_email: str,
        employee_name: str,
        leave_type: str,
        start_date: str,
        end_date: str,
        days: str,
        approved: bool,
        approver_name: str = "",
        rejection_reason: str = "",
        company_name: str = "",
    ) -> dict:
        """Send a leave approval or rejection notification."""
        if approved:
            html = self._render_template(
                _TEMPLATE_LEAVE_APPROVAL,
                {
                    "employee_name": employee_name,
                    "leave_type": leave_type,
                    "start_date": start_date,
                    "end_date": end_date,
                    "days": days,
                    "approver_name": approver_name,
                    "company_name": company_name,
                },
            )
            subject = f"Leave Approved: {leave_type} ({start_date} - {end_date})"
        else:
            html = self._render_template(
                _TEMPLATE_LEAVE_REJECTION,
                {
                    "employee_name": employee_name,
                    "leave_type": leave_type,
                    "start_date": start_date,
                    "end_date": end_date,
                    "rejection_reason": rejection_reason or "No reason provided",
                    "company_name": company_name,
                },
            )
            subject = f"Leave Request Declined: {leave_type} ({start_date} - {end_date})"

        return await self.send_email(to=employee_email, subject=subject, html_body=html)

    async def send_onboarding_invite(
        self,
        employee_email: str,
        employee_name: str,
        company_name: str,
        onboarding_url: str,
        position: str = "",
        department: str = "",
        start_date: str = "",
    ) -> dict:
        """Send an onboarding invitation email to a new employee."""
        html = self._render_template(
            _TEMPLATE_ONBOARDING_INVITE,
            {
                "employee_name": employee_name,
                "company_name": company_name,
                "onboarding_url": onboarding_url,
                "position": position or "Not specified",
                "department": department or "Not specified",
                "start_date": start_date or "To be confirmed",
            },
        )
        return await self.send_email(
            to=employee_email,
            subject=f"Welcome to {company_name} - Complete Your Onboarding",
            html_body=html,
        )

    @staticmethod
    def _render_template(template: str, fields: dict[str, str]) -> str:
        """Render a template by replacing {field_name} placeholders.

        Unknown fields are left as-is to avoid KeyError on partial data.
        """
        result = template
        for key, value in fields.items():
            result = result.replace("{" + key + "}", str(value))
        return result

    def get_send_log(self, limit: int = 100) -> list[dict]:
        """Return recent send log entries."""
        return self._send_log[-limit:]

    def list_templates(self) -> list[str]:
        """Return available template names."""
        return sorted(TEMPLATES.keys())
