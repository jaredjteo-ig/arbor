"""arbor-communications MCP server.

Provides communication tools for the shadow agent:
- Email delivery (Resend) — payslips, leave notifications, onboarding
- Telegram Bot — notifications, interactive approvals, file delivery
- S3 storage — document upload and presigned URL generation
- AWS SES Email (C02) — production-scale email delivery
- WhatsApp Business (C03) — template messages via Meta Cloud API
- Slack Bot (C05) — channel messages and Block Kit formatting
- Microsoft Teams Bot (C06) — Adaptive Cards via Incoming Webhooks
- Google Calendar Sync (C07) — Out-of-Office events for approved leave
- Microsoft Outlook Calendar Sync (C08) — OOO events via Graph API

T221: arbor-communications MCP Server Shell
T222: Resend Email Connector
T223: Telegram Bot Connector
T225: AWS S3 Document Storage Connector
T244-T248, T254: Additional channel connectors
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from hr_advisory.mcp_servers.base import ArborMCPServer, TenantContext
from hr_advisory.mcp_servers.adapters.resend_email import ResendAdapter
from hr_advisory.mcp_servers.adapters.telegram_bot import TelegramBotAdapter
from hr_advisory.mcp_servers.adapters.s3_storage import S3StorageAdapter

logger = logging.getLogger(__name__)

# ── Singleton adapter instances ───────────────────────────────

_resend: ResendAdapter | None = None
_telegram: TelegramBotAdapter | None = None
_s3: S3StorageAdapter | None = None


def _get_resend() -> ResendAdapter:
    global _resend
    if _resend is None:
        _resend = ResendAdapter()
    return _resend


def _get_telegram() -> TelegramBotAdapter:
    global _telegram
    if _telegram is None:
        _telegram = TelegramBotAdapter()
    return _telegram


def _get_s3() -> S3StorageAdapter:
    global _s3
    if _s3 is None:
        _s3 = S3StorageAdapter()
    return _s3


# ── MCP Server ────────────────────────────────────────────────

server = ArborMCPServer(
    name="arbor-communications",
    description=(
        "Communication and delivery: email (Resend), Telegram Bot, "
        "document storage (S3), and future channels (WhatsApp, Slack, Teams, Calendar)."
    ),
    version="1.0.0",
)


# ── MCP Tools: Resend Email (C01) ────────────────────────────


@server.tool(
    name="comms_send_email",
    description=(
        "Send a transactional email via Resend. "
        "Supports HTML body and optional reply-to address."
    ),
)
async def tool_send_email(
    ctx: TenantContext,
    to: str,
    subject: str,
    html_body: str,
    from_address: str = "",
    reply_to: str = "",
) -> dict:
    adapter = _get_resend()
    return await adapter.send_email(
        to=to,
        subject=subject,
        html_body=html_body,
        from_address=from_address or None,
        reply_to=reply_to or None,
    )


@server.tool(
    name="comms_send_bulk_email",
    description=(
        "Send bulk transactional emails using a template. "
        "Templates: payslip, leave_approval, leave_rejection, "
        "onboarding_invite, compliance_alert, regulatory_update. "
        "Pass per-recipient merge field overrides in the recipients list."
    ),
)
async def tool_send_bulk_email(
    ctx: TenantContext,
    recipients: list[dict[str, str]],
    template_name: str,
    merge_fields: dict[str, str],
    subject: str,
    from_address: str = "",
) -> dict:
    adapter = _get_resend()
    return await adapter.send_bulk(
        recipients=recipients,
        template_name=template_name,
        merge_fields=merge_fields,
        subject=subject,
        from_address=from_address or None,
    )


@server.tool(
    name="comms_send_payslip_email",
    description=(
        "Send a payslip notification email to an employee. "
        "Uses the pre-built payslip template with salary breakdown."
    ),
)
async def tool_send_payslip_email(
    ctx: TenantContext,
    employee_email: str,
    employee_name: str,
    period: str,
    gross_pay: str,
    deductions: str,
    net_pay: str,
    company_name: str,
) -> dict:
    adapter = _get_resend()
    return await adapter.send_payslip_notification(
        employee_email=employee_email,
        employee_name=employee_name,
        period=period,
        gross_pay=gross_pay,
        deductions=deductions,
        net_pay=net_pay,
        company_name=company_name,
    )


@server.tool(
    name="comms_send_leave_notification",
    description=(
        "Send a leave approval or rejection notification to an employee. "
        "Set approved=true for approval, approved=false for rejection."
    ),
)
async def tool_send_leave_notification(
    ctx: TenantContext,
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
    adapter = _get_resend()
    return await adapter.send_leave_notification(
        employee_email=employee_email,
        employee_name=employee_name,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        days=days,
        approved=approved,
        approver_name=approver_name,
        rejection_reason=rejection_reason,
        company_name=company_name,
    )


@server.tool(
    name="comms_send_onboarding_invite",
    description=(
        "Send an onboarding invitation email to a new employee. "
        "Includes a link to complete onboarding, position, department, start date."
    ),
)
async def tool_send_onboarding_invite(
    ctx: TenantContext,
    employee_email: str,
    employee_name: str,
    company_name: str,
    onboarding_url: str,
    position: str = "",
    department: str = "",
    start_date: str = "",
) -> dict:
    adapter = _get_resend()
    return await adapter.send_onboarding_invite(
        employee_email=employee_email,
        employee_name=employee_name,
        company_name=company_name,
        onboarding_url=onboarding_url,
        position=position,
        department=department,
        start_date=start_date,
    )


@server.tool(
    name="comms_list_email_templates",
    description="List available email templates for bulk email sending.",
)
async def tool_list_email_templates(ctx: TenantContext) -> dict:
    adapter = _get_resend()
    return {"templates": adapter.list_templates()}


# ── MCP Tools: Telegram Bot (C04) ────────────────────────────


@server.tool(
    name="comms_send_telegram",
    description=(
        "Send a text message via Telegram Bot. "
        "Supports HTML formatting and optional inline keyboard buttons."
    ),
)
async def tool_send_telegram(
    ctx: TenantContext,
    chat_id: str,
    text: str,
    reply_markup: dict | None = None,
) -> dict:
    adapter = _get_telegram()
    return await adapter.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
    )


@server.tool(
    name="comms_send_telegram_document",
    description=(
        "Send a document (file) via Telegram Bot. "
        "Pass raw file bytes, filename, and optional caption."
    ),
)
async def tool_send_telegram_document(
    ctx: TenantContext,
    chat_id: str,
    file_bytes: bytes,
    filename: str,
    caption: str = "",
) -> dict:
    adapter = _get_telegram()
    return await adapter.send_document(
        chat_id=chat_id,
        file_bytes=file_bytes,
        filename=filename,
        caption=caption or None,
    )


@server.tool(
    name="comms_send_telegram_leave_approval",
    description=(
        "Send a leave approval request to a manager via Telegram "
        "with Approve/Reject inline buttons."
    ),
)
async def tool_send_telegram_leave_approval(
    ctx: TenantContext,
    manager_chat_id: str,
    employee_name: str,
    leave_type: str,
    start_date: str,
    end_date: str,
    days: int,
    leave_id: str,
) -> dict:
    adapter = _get_telegram()
    return await adapter.send_leave_approval_request(
        manager_chat_id=manager_chat_id,
        employee_name=employee_name,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        days=days,
        leave_id=leave_id,
    )


@server.tool(
    name="comms_send_telegram_claim_approval",
    description=(
        "Send a claim approval request to a manager via Telegram "
        "with Approve/Reject inline buttons."
    ),
)
async def tool_send_telegram_claim_approval(
    ctx: TenantContext,
    manager_chat_id: str,
    employee_name: str,
    claim_type: str,
    amount: str,
    claim_id: str,
    description: str = "",
) -> dict:
    adapter = _get_telegram()
    return await adapter.send_claim_approval_request(
        manager_chat_id=manager_chat_id,
        employee_name=employee_name,
        claim_type=claim_type,
        amount=amount,
        claim_id=claim_id,
        description=description,
    )


@server.tool(
    name="comms_send_telegram_payslip",
    description=("Send a payslip PDF to an employee via Telegram."),
)
async def tool_send_telegram_payslip(
    ctx: TenantContext,
    employee_chat_id: str,
    pdf_bytes: bytes,
    period: str,
    employee_name: str,
    employee_id: str,
) -> dict:
    adapter = _get_telegram()
    return await adapter.send_payslip(
        employee_chat_id=employee_chat_id,
        pdf_bytes=pdf_bytes,
        period=period,
        employee_name=employee_name,
        employee_id=employee_id,
    )


@server.tool(
    name="comms_register_telegram_webhook",
    description="Register a webhook URL for incoming Telegram messages.",
    requires_confirmation=True,
)
async def tool_register_telegram_webhook(
    ctx: TenantContext,
    webhook_url: str,
) -> dict:
    adapter = _get_telegram()
    return await adapter.register_webhook(webhook_url)


# ── MCP Tools: S3 Storage (shared utility) ───────────────────


@server.tool(
    name="storage_upload_document",
    description=(
        "Upload a document to S3 with tenant-isolated storage. "
        "Returns the storage key for later retrieval."
    ),
)
async def tool_upload_document(
    ctx: TenantContext,
    file_key: str,
    file_bytes: bytes,
    content_type: str = "application/octet-stream",
) -> dict:
    adapter = _get_s3()
    return await adapter.upload(
        tenant_id=ctx.company_id,
        file_key=file_key,
        file_bytes=file_bytes,
        content_type=content_type,
    )


@server.tool(
    name="storage_get_download_url",
    description=(
        "Generate a time-limited download URL for a stored document. "
        "Default expiry: 1 hour. Maximum: 7 days."
    ),
)
async def tool_get_download_url(
    ctx: TenantContext,
    file_key: str,
    expires_in: int = 3600,
) -> dict:
    adapter = _get_s3()
    return await adapter.get_presigned_url(
        tenant_id=ctx.company_id,
        file_key=file_key,
        expires_in=expires_in,
    )


@server.tool(
    name="storage_delete_document",
    description="Delete a document from S3 storage.",
    requires_confirmation=True,
)
async def tool_delete_document(
    ctx: TenantContext,
    file_key: str,
) -> dict:
    adapter = _get_s3()
    return await adapter.delete(
        tenant_id=ctx.company_id,
        file_key=file_key,
    )


@server.tool(
    name="storage_list_documents",
    description=(
        "List documents in S3 storage for the current tenant. "
        "Optionally filter by prefix (e.g. 'payslips/', 'statutory/')."
    ),
)
async def tool_list_documents(
    ctx: TenantContext,
    prefix: str = "",
    max_keys: int = 100,
) -> dict:
    adapter = _get_s3()
    objects = await adapter.list_objects(
        tenant_id=ctx.company_id,
        prefix=prefix,
        max_keys=max_keys,
    )
    return {
        "prefix": prefix,
        "total": len(objects),
        "objects": objects,
    }


# ── Additional connectors (C02-C08) ──────────────────────────
# Each tool delegates to its adapter. If the adapter module is
# unavailable (missing dependency), it returns adapter_unavailable.


@server.tool(
    name="comms_send_whatsapp",
    description=(
        "Send a WhatsApp template message via Meta Cloud API. "
        "Supports pre-approved templates: payslip_ready, leave_approved, "
        "leave_rejected, compliance_alert, deadline_reminder. "
        "Requires WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID env vars."
    ),
)
async def tool_send_whatsapp(
    ctx: TenantContext,
    phone: str = "",
    template_name: str = "",
    parameters: list = [],
    language_code: str = "en",
    **kwargs: Any,
) -> dict:
    try:
        from hr_advisory.mcp_servers.adapters.whatsapp import WhatsAppAdapter
    except ImportError:
        return {"status": "adapter_unavailable", "message": "WhatsApp adapter not available."}

    adapter = WhatsAppAdapter()
    return await adapter.send_template(
        phone=phone,
        template_name=template_name,
        parameters=parameters,
        language_code=language_code,
        tenant_id=ctx.company_id,
    )


@server.tool(
    name="comms_send_slack",
    description=(
        "Send a Slack message via Slack Bot API. "
        "Posts to a channel or DM with optional Block Kit formatting. "
        "Requires SLACK_BOT_TOKEN env var."
    ),
)
async def tool_send_slack(
    ctx: TenantContext,
    channel: str = "",
    text: str = "",
    blocks: Optional[list] = None,
    thread_ts: Optional[str] = None,
    **kwargs: Any,
) -> dict:
    try:
        from hr_advisory.mcp_servers.adapters.slack import SlackAdapter
    except ImportError:
        return {"status": "adapter_unavailable", "message": "Slack adapter not available."}

    adapter = SlackAdapter()
    return await adapter.post_message(
        channel=channel,
        text=text,
        blocks=blocks,
        thread_ts=thread_ts,
    )


@server.tool(
    name="comms_send_teams",
    description=(
        "Send a Teams notification via Incoming Webhook. "
        "Builds and sends an Adaptive Card to the configured Teams channel. "
        "Pass webhook_url (from tenant settings), title, and body."
    ),
)
async def tool_send_teams(
    ctx: TenantContext,
    webhook_url: str = "",
    title: str = "",
    body: str = "",
    actions: Optional[list] = None,
    facts: Optional[list] = None,
    **kwargs: Any,
) -> dict:
    try:
        from hr_advisory.mcp_servers.adapters.teams import TeamsAdapter
    except ImportError:
        return {"status": "adapter_unavailable", "message": "Teams adapter not available."}

    adapter = TeamsAdapter()
    card = adapter.create_adaptive_card(
        title=title,
        body=body,
        actions=actions,
        facts=facts,
    )
    return await adapter.send_webhook(
        webhook_url=webhook_url,
        card=card,
        tenant_id=ctx.company_id,
    )


@server.tool(
    name="comms_sync_google_calendar",
    description=(
        "Sync approved leave records to an employee's Google Calendar. "
        "Creates Out-of-Office events for each approved leave. "
        "Requires GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET env vars, "
        "and the employee must have connected their Google Calendar."
    ),
)
async def tool_sync_google_calendar(
    ctx: TenantContext,
    employee_calendar_id: str = "primary",
    leave_records: list = [],
    user_id: str = "",
    **kwargs: Any,
) -> dict:
    try:
        from hr_advisory.mcp_servers.adapters.google_calendar import GoogleCalendarAdapter
    except ImportError:
        return {
            "status": "adapter_unavailable",
            "message": "Google Calendar adapter not available.",
        }

    adapter = GoogleCalendarAdapter()
    return await adapter.sync_leave(
        employee_calendar_id=employee_calendar_id,
        leave_records=leave_records,
        tenant_id=ctx.company_id,
        user_id=user_id or ctx.user_id,
    )


@server.tool(
    name="comms_sync_outlook_calendar",
    description=(
        "Sync approved leave records to an employee's Outlook Calendar via Microsoft Graph. "
        "Creates Out-of-Office events for each approved leave. "
        "Requires MICROSOFT_CLIENT_ID and MICROSOFT_CLIENT_SECRET env vars, "
        "and the employee must have connected their Microsoft account."
    ),
)
async def tool_sync_outlook_calendar(
    ctx: TenantContext,
    user_id: str = "",
    leave_records: list = [],
    **kwargs: Any,
) -> dict:
    try:
        from hr_advisory.mcp_servers.adapters.microsoft_graph import MicrosoftGraphAdapter
    except ImportError:
        return {
            "status": "adapter_unavailable",
            "message": "Microsoft Graph adapter not available.",
        }

    adapter = MicrosoftGraphAdapter()
    return await adapter.sync_leave(
        user_id=user_id or ctx.user_id,
        leave_records=leave_records,
        tenant_id=ctx.company_id,
    )


@server.tool(
    name="comms_send_ses_email",
    description=(
        "Send email via AWS SES. "
        "Supports HTML body, reply-to, CC, BCC, and tracking tags. "
        "Requires boto3 and valid AWS credentials. "
        "Falls back to Resend adapter if SES is not configured."
    ),
)
async def tool_send_ses_email(
    ctx: TenantContext,
    to: str = "",
    subject: str = "",
    html: str = "",
    from_email: str = "",
    reply_to: str = "",
    **kwargs: Any,
) -> dict:
    try:
        from hr_advisory.mcp_servers.adapters.ses_email import SESAdapter
    except ImportError:
        return {"status": "adapter_unavailable", "message": "SES adapter not available."}

    adapter = SESAdapter()
    return await adapter.send_email(
        to=to,
        subject=subject,
        html=html,
        from_email=from_email or None,
        reply_to=reply_to or None,
    )
