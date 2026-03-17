# MCP Integration Architecture for AITE Shadow Agent

## Design Principle

Every external integration is exposed as MCP tools/resources. The shadow agent invokes them via natural language objectives. The user says "submit CPF for March" — the shadow agent calls the right MCP tools in sequence, confirms amounts with the user, and executes.

## Server Topology

5 domain-grouped MCP servers. Each server has its own credential scope, failure domain, and circuit breaker.

```
Shadow Agent (Kaizen IterativeLLMAgentNode)
    │
    ├── aite-government (CPF APEX, IRAS AIS, MOM OED, MyInfo, Data.gov.sg)
    │     └── OAuth 2.1 + CorpPass tokens per tenant
    │
    ├── aite-accounting (Xero, QuickBooks, Zoho Books, Financio)
    │     └── OAuth 2.0 tokens per tenant per provider
    │
    ├── aite-banking (DBS RAPID, UOB, OCBC, Aspire, GIRO/FAST file gen, PayNow QR)
    │     └── Bank-specific auth per tenant
    │
    ├── aite-communications (Email, WhatsApp, Telegram, Slack, Teams)
    │     └── Bot tokens + webhook URLs per tenant
    │
    └── aite-regulatory (SSO RSS, data.gov.sg, MOM sitemap, change detection)
          └── API keys + RSS feeds (shared, not per-tenant)
```

### Why Grouped, Not One-Per-API

- Fewer connections for the shadow agent to manage (5 vs 40+)
- Related tools appear together, aiding LLM tool selection
- Shared auth patterns within a domain (all government APIs use CorpPass)
- Independent failure domains (banking down doesn't affect accounting)

### Why Not One Giant Server

- Least-privilege: banking server has no access to government credentials
- Blast radius: if one server crashes, others continue
- Scaling: government server needs longer timeouts (120s) vs comms (5s)

## Tool Naming Convention

`{domain}_{verb}_{noun}` — self-documenting for LLM tool selection.

### Government Server Tools

```
government_submit_cpf              — Submit monthly CPF contributions via APEX
government_validate_cpf_readiness  — Check if payroll is finalized for CPF submission
government_generate_cpf_file       — Generate CPF e-Submit file (for manual upload fallback)
government_file_ir8a               — Submit IR8A via IRAS AIS-API 2.0
government_file_ir21               — Submit IR21 for departing foreign employee
government_file_ir8s               — Submit IR8S refund/voluntary contribution
government_get_filing_status       — Check status of a pending government submission
government_fetch_myinfo            — Retrieve employee data from MyInfo (with Singpass consent)
government_verify_uen              — Verify company UEN via ACRA
government_get_public_holidays     — Fetch SG public holidays from data.gov.sg
government_get_cpf_rates           — Fetch CPF contribution rates from data.gov.sg
government_submit_oed              — Submit occupational employment data to MOM
```

### Accounting Server Tools

```
accounting_connect                 — Initiate OAuth flow for accounting provider
accounting_get_chart_of_accounts   — Retrieve chart of accounts
accounting_post_payroll_journal    — Post payroll journal entry (salary, CPF, SDL, etc.)
accounting_post_claims_journal     — Post approved claims as journal entries
accounting_reconcile_bank          — Match bank transactions to payroll payments
accounting_get_trial_balance       — Retrieve trial balance for verification
accounting_disconnect              — Revoke OAuth connection
```

### Banking Server Tools

```
banking_generate_giro_file         — Generate ISO 20022 pain.001 GIRO file for bulk salary
banking_generate_fast_file         — Generate FAST payment file
banking_initiate_payment           — Initiate real-time payment via bank API (DBS/UOB/OCBC)
banking_initiate_bulk_payout       — Bulk payout via Aspire API
banking_get_payment_status         — Check payment processing status
banking_generate_paynow_qr        — Generate PayNow QR code for employee reimbursement
banking_list_supported_banks       — List configured bank integrations for the company
```

### Communications Server Tools

```
comms_send_email                   — Send transactional email (payslip, notification)
comms_send_bulk_email              — Send bulk emails (all payslips for a payroll run)
comms_send_whatsapp                — Send WhatsApp notification (uses approved template)
comms_send_telegram                — Send Telegram message via bot
comms_send_slack                   — Post to Slack channel or DM
comms_send_teams                   — Post to Teams channel via webhook
comms_sync_leave_to_calendar       — Sync approved leave to Google Calendar or Outlook
comms_get_delivery_status          — Check delivery status of sent notifications
```

### Regulatory Server Tools + Resources

```
# Tools
regulatory_check_updates           — Check all sources for new regulatory changes
regulatory_get_act_amendments      — Get recent amendments to a specific Act (via SSO RSS)
regulatory_classify_change         — LLM classifies if a detected change affects AITE
regulatory_summarize_change        — LLM summarizes a regulatory change in plain language

# MCP Resources (read-only, subscribable)
regulatory://cpf/rates/2026        — CPF contribution rate tables
regulatory://employment-act/{section} — Employment Act section text
regulatory://updates/feed          — Live feed of published regulatory changes
regulatory://public-holidays/2026  — SG public holidays
regulatory://sdl/rates             — SDL rate table
regulatory://fwl/rates             — Foreign worker levy rates by sector
```

## Shadow Agent Objective Handling

The shadow agent receives natural language objectives and orchestrates MCP tool calls. Examples:

### "Submit CPF for March 2026"

1. `government_validate_cpf_readiness(period="2026-03")` — check payroll finalized
2. If not ready: inform user "Payroll for March hasn't been run yet"
3. `government_generate_cpf_file(period="2026-03")` — generate submission data
4. `confirm_action(description="Submit CPF for 47 employees, total $38,450")` — human gate
5. `government_submit_cpf(period="2026-03")` — submit via APEX
6. Report submission ID and status

### "Post payroll to Xero"

1. `accounting_get_chart_of_accounts()` — verify mapping
2. `accounting_post_payroll_journal(period="2026-03")` — create journal entry
3. Report journal reference number

### "Send payslips to all employees"

1. `comms_send_bulk_email(payroll_run_id="...", template="payslip")` — email delivery
2. If WhatsApp configured: `comms_send_whatsapp(template="payslip_ready")` — notification
3. Report delivery count and any failures

### "Check if any regulations changed this week"

1. `regulatory_check_updates()` — poll all sources
2. Report any new changes with plain-language summaries

## Security Architecture

### Tenant Isolation

- Every MCP tool call includes `company_id` from JWT
- MCP server validates `company_id` matches JWT `tenant_id` claim
- Cross-tenant access is blocked server-side (not reliant on shadow agent)

### OAuth Token Management

- External API tokens stored encrypted (Fernet, same as PII encryption)
- Token refresh handled server-side in the MCP server
- Tokens never returned in tool responses or logged
- Per-tenant, per-provider token storage

### Human Confirmation Gates

High-stakes actions require explicit human approval before execution:

| Action Category                         | Confirmation Required                          |
| --------------------------------------- | ---------------------------------------------- |
| Government submissions (CPF, IR8A, OED) | Always                                         |
| Bank payments (GIRO, FAST, PayNow)      | Always                                         |
| Accounting journal posts                | Always (first time per run), then configurable |
| Bulk email (payslips)                   | Always                                         |
| Data import (HRIS sync)                 | Always                                         |
| Regulatory data reads                   | Never                                          |
| Calendar sync                           | Never (once authorized)                        |
| Single notification                     | Never                                          |

### Circuit Breakers

Per-external-API circuit breakers with configurable thresholds:

| External API       | Failure Threshold | Recovery Timeout |
| ------------------ | ----------------- | ---------------- |
| CPF Board          | 3 failures        | 120s             |
| IRAS               | 3 failures        | 120s             |
| Xero / QBO / Zoho  | 5 failures        | 60s              |
| DBS / UOB / OCBC   | 3 failures        | 300s             |
| Email (Resend/SES) | 10 failures       | 30s              |
| WhatsApp           | 5 failures        | 60s              |

### Audit Logging

Every MCP tool invocation logged to PDPA-compliant audit trail:

- Tool name, company_id, user_id, timestamp
- Success/failure status, duration
- Never logs request/response payloads (may contain PII)
- Extends existing PdpaAccessLog pattern

## File Structure

```
src/hr_advisory/mcp_servers/
├── __init__.py
├── government_server.py      — CPF, IRAS, MOM, MyInfo, Data.gov.sg
├── accounting_server.py      — Xero, QBO, Zoho, Financio
├── banking_server.py         — DBS, UOB, OCBC, Aspire, GIRO/FAST, PayNow
├── communications_server.py  — Email, WhatsApp, Telegram, Slack, Teams
├── regulatory_server.py      — SSO RSS, data.gov.sg, change detection
├── auth/
│   ├── __init__.py
│   ├── token_store.py        — Encrypted OAuth token storage per tenant
│   └── corppass.py           — CorpPass OAuth 2.1 flow for government APIs
├── resilience.py             — Circuit breakers per external API
├── audit.py                  — Tool invocation audit logging
└── adapters/
    ├── __init__.py
    ├── xero.py               — Xero Manual Journals adapter
    ├── quickbooks.py         — QBO Journal Entry adapter
    ├── zoho.py               — Zoho Books Journals adapter
    ├── financio.py           — Financio partner API adapter
    ├── dbs.py                — DBS RAPID adapter
    ├── uob.py                — UOB payment API adapter
    ├── ocbc.py               — OCBC Connect2OCBC adapter
    ├── aspire.py             — Aspire Payout API adapter
    ├── giro.py               — ISO 20022 pain.001 file generator
    ├── fast.py               — FAST payment file generator
    ├── paynow.py             — PayNow QR generator (SGQR standard)
    ├── cpf_apex.py           — CPF Board APEX API adapter
    ├── iras_ais.py           — IRAS AIS-API 2.0 adapter
    ├── mom_oed.py            — MOM OED API adapter
    ├── myinfo.py             — MyInfo v5 + FAPI 2.0 adapter
    ├── corppass_auth.py      — CorpPass authorization flow
    ├── data_gov_sg.py        — Data.gov.sg REST API adapter
    ├── acra.py               — ACRA Business Profile API adapter
    ├── sso_rss.py            — SSO per-Act RSS feed parser
    ├── change_detector.py    — Web page change detection engine
    ├── telegram_monitor.py   — Telegram channel monitoring
    ├── resend_email.py       — Resend email adapter
    ├── ses_email.py          — AWS SES email adapter
    ├── whatsapp.py           — WhatsApp Cloud API adapter
    ├── telegram_bot.py       — Telegram Bot API adapter
    ├── slack.py              — Slack API adapter
    ├── teams.py              — MS Teams webhook adapter
    ├── google_calendar.py    — Google Calendar API adapter
    ├── microsoft_graph.py    — Microsoft Graph API adapter
    ├── talenox.py            — Talenox REST API adapter
    ├── hreasily.py           — HReasily unified API adapter
    ├── skillsfuture.py       — SSG Developer Portal API adapter
    └── s3_storage.py         — AWS S3 document storage adapter
```

## Implementation Phases

### Phase 1: Foundation + Quick Wins

- `aite-regulatory` server (read-only, uses existing KB data + SSO RSS + data.gov.sg)
- `aite-communications` server (email via Resend, Telegram bot)
- Data.gov.sg public holidays integration
- ISO 20022 GIRO file generator (pain.001.001.03)

### Phase 2: Accounting + Banking Files

- `aite-accounting` server (Xero Manual Journals, QBO Journal Entry, Zoho Journals)
- `aite-banking` server (GIRO file gen, FAST file gen, PayNow QR, Aspire Payout API)
- Claims-to-accounting sync pipeline

### Phase 3: Government APIs

- OSP vendor registration (unlocks CPF + IRAS + MOM)
- `aite-government` server (CPF APEX, IRAS AIS-API 2.0, MOM OED)
- CorpPass authentication flow
- MyInfo v5 employee onboarding

### Phase 4: Extended Integrations

- WhatsApp Cloud API notifications
- Slack + Teams bots
- Google Calendar + Microsoft Graph leave sync
- Talenox / HReasily data import
- SkillsFuture SSG course/grant APIs
- ACRA UEN verification
- Change detection engine for MOM, CPF Board, IRAS, TAFEP websites
