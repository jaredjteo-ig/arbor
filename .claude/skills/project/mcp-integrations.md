# MCP Integration Layer Skill

External API integrations via 5 domain-grouped MCP servers. 38 connectors, 97 tools, 56 Python files, 484 tests.

## Module Map

### Infrastructure (root level)

| File                | Purpose                                                                              | Singleton Getter                          |
| ------------------- | ------------------------------------------------------------------------------------ | ----------------------------------------- |
| `base.py`           | `ArborMCPServer` base class: tenant isolation, audit log, tool/resource registration | N/A (instantiated per server)             |
| `registry.py`       | Central registry: discovery, cross-server tool routing, health aggregation           | `get_all_servers()`                       |
| `resilience.py`     | Circuit breakers (25 pre-configured) + per-tenant rate limiters (6 configured)       | `get_circuit(name)`, `check_rate_limit()` |
| `idempotency.py`    | Submission ledger: prevents double-submit of government/bank filings                 | `get_submission_ledger()`                 |
| `saga.py`           | Multi-step workflow state machine with 8 pre-defined templates                       | `get_saga_orchestrator()`                 |
| `pii_filter.py`     | PII stripping (NRIC, phone, bank, salary, email) before LLM calls                    | `get_pii_filter()`                        |
| `confirm_action.py` | Human-in-the-loop approval gates for irreversible operations                         | `get_approval_store()`                    |
| `webhooks.py`       | Inbound webhook receiver: signature verification, event routing                      | `get_webhook_router()`                    |
| `health.py`         | Connector health monitor: aggregates circuit breaker state per connector             | `get_health_monitor()`                    |
| `cost_tracker.py`   | Per-tenant API cost tracking for metered services (MyInfo S$1, ACRA S$5.50)          | `get_cost_tracker()`                      |
| `tool_selector.py`  | Dynamic tool loading: 15-25 tools per page context instead of 97                     | `get_tools_for_context()`                 |

### Auth (`auth/`)

| File             | Purpose                                                                |
| ---------------- | ---------------------------------------------------------------------- |
| `token_store.py` | Encrypted OAuth token store (Fernet). Per-tenant, per-provider.        |
| `corppass.py`    | CorpPass OAuth 2.1 + PKCE flow for GovTech APEX (CPF, IRAS, MOM APIs). |

### 5 MCP Servers

| Server File                | Server Name         | Tools | Domain                                                                            |
| -------------------------- | ------------------- | ----- | --------------------------------------------------------------------------------- |
| `government_server.py`     | arbor-government    | 33    | CPF, IRAS (IR8A/8S/21/Appendix 8A), MOM OED, MyInfo, ACRA, CorpPass, SkillsFuture |
| `accounting_server.py`     | arbor-accounting     | 22    | Xero, QuickBooks Online, Zoho Books, Financio, CSV/JSON export, claims sync       |
| `communications_server.py` | arbor-communications | 22    | Resend email, SES, Telegram bot, WhatsApp, Slack, Teams, Google Calendar, Outlook |
| `banking_server.py`        | arbor-banking        | 12    | ISO 20022 GIRO, FAST (DBS/UOB), PayNow QR, Aspire payouts                         |
| `regulatory_server.py`     | arbor-regulatory     | 8     | data.gov.sg, SSO RSS, MOM sitemap, web change detection, Telegram monitoring      |

### 38 Connectors (adapters/)

| ID  | Connector                | External API / Format        | Adapter File                        | Status |
| --- | ------------------------ | ---------------------------- | ----------------------------------- | ------ |
| G01 | CPF APEX Submission      | CPF Board via APEX gateway   | `adapters/cpf_apex.py`              | Active |
| G02 | IRAS AIS IR8A            | IRAS AIS-API 2.0 via APEX    | `adapters/iras_ais.py`              | Active |
| G03 | IRAS AIS IR21            | IRAS AIS-API 2.0 via APEX    | `adapters/iras_ais.py`              | Active |
| G04 | IRAS AIS IR8S            | IRAS AIS-API 2.0 via APEX    | `adapters/iras_ais.py`              | Active |
| G05 | MOM OED                  | MOM via APEX gateway         | `adapters/mom_oed.py`               | Active |
| G06 | MyInfo Personal          | MyInfo v5 (FAPI 2.0)         | `adapters/myinfo.py`                | Active |
| G07 | CorpPass Auth            | CorpPass OAuth 2.1 + PKCE    | `auth/corppass.py`                  | Active |
| G08 | data.gov.sg              | Public holidays, CPF rates   | `adapters/data_gov_sg.py`           | Active |
| G09 | SSO RSS                  | Singapore Statutes Online    | `adapters/sso_rss.py`               | Active |
| G10 | ACRA UEN                 | ACRA + data.gov.sg           | `adapters/acra.py`                  | Active |
| G11 | SkillsFuture SSG         | SSG Developer Portal         | `adapters/skillsfuture.py`          | Active |
| A01 | Xero                     | Xero OAuth2, Accounting API  | `adapters/xero.py`                  | Active |
| A02 | QuickBooks Online        | Intuit QBO OAuth2            | `adapters/quickbooks.py`            | Active |
| A03 | Zoho Books               | Zoho OAuth2                  | `adapters/zoho.py`                  | Active |
| A04 | Financio                 | GL posting CSV export        | `adapters/financio.py`              | Active |
| A05 | Generic CSV Export       | CSV journal format           | `adapters/generic_export.py`        | Active |
| A06 | Claims Sync              | Routes claims to accounting  | `adapters/claims_sync.py`           | Active |
| B01 | ISO 20022 GIRO           | pain.001.001.03 XML          | `adapters/giro.py`                  | Active |
| B02 | DBS FAST                 | DBS IDEAL API                | `adapters/fast.py`                  | Active |
| B03 | UOB FAST                 | UOB BIBPlus format           | `adapters/fast.py`                  | Active |
| B04 | PayNow QR                | SGQR/EMVCo standard          | `adapters/paynow.py`                | Active |
| B05 | Aspire Payout            | Aspire Payout API            | `adapters/aspire.py`                | Active |
| B06 | Wise Transfer            | Wise Business API            | `adapters/wise.py`                  | Active |
| C01 | Resend Email             | Resend transactional API     | `adapters/resend_email.py`          | Active |
| C02 | AWS SES                  | SES v2 for bulk email        | `adapters/ses_email.py`             | Active |
| C03 | WhatsApp Business        | Meta Cloud API               | `adapters/whatsapp.py`              | Active |
| C04 | Telegram Bot             | Telegram Bot API             | `adapters/telegram_bot.py`          | Active |
| C05 | Slack Bot                | Slack Web API + Block Kit    | `adapters/slack.py`                 | Active |
| C06 | Microsoft Teams          | Incoming Webhooks + Cards    | `adapters/teams.py`                 | Active |
| C07 | Google Calendar          | Google Calendar API v3       | `adapters/google_calendar.py`       | Active |
| C08 | Outlook Calendar         | Microsoft Graph API          | `adapters/microsoft_graph.py`       | Active |
| C09 | SMS (Twilio)             | Twilio Messaging API         | `adapters/sms.py`                   | Active |
| C10 | S3 Document Storage      | AWS S3                       | `adapters/s3_storage.py`            | Active |
| R01 | MOM Sitemap              | MOM newsroom monitoring      | `adapters/mom_sitemap.py`           | Active |
| R02 | Change Detector          | Web page diff engine         | `adapters/change_detector.py`       | Active |
| R03 | Telegram Channel Monitor | Gov channel monitoring       | `adapters/telegram_monitor.py`      | Active |
| R04 | Regulatory Classifier    | Deterministic classification | `adapters/regulatory_classifier.py` | Active |
| H01 | Talenox Import           | Talenox HRIS API             | `adapters/talenox.py`               | Active |
| H02 | HREasily Import          | HREasily HRIS API            | `adapters/hreasily.py`              | Active |

## How to Add a New Connector

1. **Create adapter file** in `adapters/` following the naming pattern (`adapters/new_api.py`).

```python
# adapters/new_api.py
import os
import httpx
from hr_advisory.mcp_servers.resilience import get_circuit, check_rate_limit

API_KEY = os.environ.get("NEW_API_KEY", "")
API_BASE = os.environ.get("NEW_API_BASE_URL", "https://api.example.com")

class NewAPIAdapter:
    def __init__(self):
        self._circuit = get_circuit("new_api")  # Step 2: add to CIRCUITS

    async def do_something(self, tenant_id: str, data: dict) -> dict:
        check_rate_limit(tenant_id, "new_api")  # Step 3: optional rate limiter
        async def _call():
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(f"{API_BASE}/endpoint", json=data, ...)
                resp.raise_for_status()
                return resp.json()
        return await self._circuit.call(_call)
```

2. **Add circuit breaker** in `resilience.py`:

```python
CIRCUITS["new_api"] = CircuitBreaker("new_api", failure_threshold=5, recovery_timeout=60)
```

3. **Add rate limiter** (if needed) in `resilience.py`:

```python
RATE_LIMITERS["new_api"] = RateLimiter(max_calls=100, window_seconds=60)
```

4. **Register tool** in the appropriate server file (e.g., `accounting_server.py`):

```python
@server.tool(
    "accounting_new_action",  # {domain}_{verb}_{noun}
    description="Human-readable description for LLM tool selection.",
    requires_confirmation=False,  # True for irreversible operations
)
async def accounting_new_action(ctx: TenantContext, param: str) -> dict:
    adapter = NewAPIAdapter()
    return await adapter.do_something(tenant_id=ctx.company_id, data={"param": param})
```

5. **Sync tool_selector.py** -- add the tool name to `TOOL_DOMAINS`:

```python
"accounting_new_action": "accounting",
```

6. **Add to PAGE_TOOL_DOMAINS** if the tool should appear on specific pages:

```python
"claims": ["accounting", "banking", "communications"],  # already includes "accounting"
```

7. **Write tests** in `tests/integration/mcp_servers/`.

8. **Add env vars** to `.env.example` and document in this skill file.

## How the Shadow Agent Discovers and Calls Tools

1. Shadow agent receives a natural language objective (e.g., "Submit CPF for March").
2. `tool_selector.get_tools_for_context(page, role, connected_providers)` returns 15-25 relevant tool names.
3. Shadow agent uses LLM tool-calling to select a tool and generate parameters.
4. `registry.call_tool(tool_name, company_id=..., user_id=..., **params)` routes to the correct server.
5. `ArborMCPServer.call_tool()` wraps with tenant context, audit logging, and error standardization.
6. If `requires_confirmation=True`, the tool returns `status: "pending_approval"` and waits for human approval via `confirm_action.py`.

## How Idempotency Prevents Double-Submission

```python
ledger = get_submission_ledger()

# Before any government/bank submission:
record = ledger.create_submission("company_123", SubmissionType.CPF, "2026-03")
# If same (tenant, type, period) already exists in pending/submitted/confirmed state:
#   -> raises DuplicateSubmissionError (blocks the submission)
# If previous attempt was FAILED or CANCELLED:
#   -> allows retry (creates new record)

# After successful external API call:
ledger.mark_submitted(record.id, external_ref="CPF-REF-123")

# After external system confirms receipt:
ledger.mark_confirmed(record.id)
```

The idempotency key is `{tenant_id}:{submission_type}:{period}`. Covered types: CPF, IR8A, IR21, IR8S, OED, GIRO, FAST, PayNow, Aspire payout, Wise transfer, Xero/QBO/Zoho journal.

## How the Saga Orchestrator Handles Multi-Step Objectives

```python
orchestrator = get_saga_orchestrator()

# Start from a pre-defined template:
saga = orchestrator.start_saga(
    tenant_id="company_123",
    saga_type="submit_cpf",
    step_names=SAGA_TEMPLATES["submit_cpf"],
    # Steps: validate_readiness -> generate_file -> confirm_action -> submit_to_cpf -> verify_acknowledgement
)

# Execute each step:
orchestrator.start_step(saga.id)
# ... execute step logic ...
orchestrator.complete_step(saga.id, {"employees": 47})
# Automatically advances to next step

# On failure:
orchestrator.fail_step(saga.id, "CPF Board API timeout")
# Saga paused at failed step — can be resumed later:
orchestrator.resume_saga(saga.id)

# On human approval gate:
orchestrator.set_awaiting_approval(saga.id)
# After approval granted:
orchestrator.start_step(saga.id)  # continues from the paused step
```

Pre-defined saga templates: `submit_cpf`, `file_ir8a`, `file_ir21`, `post_payroll_to_accounting`, `bulk_salary_payment`, `send_payslips`, `import_from_hris`, `myinfo_onboarding`.

## How the PII Filter Protects Employee Data Before LLM Calls

```python
pii = get_pii_filter()

# Before sending to LLM:
cleaned, token_map = pii.strip(
    "John Tan (S1234567A) earns $5,000/month",
    strip_names=["John Tan"],
)
# cleaned: "[PERSON_1] ([NRIC_1]) earns [AMOUNT_1]/month"

# Send cleaned text to LLM...
llm_response = "[PERSON_1] is entitled to 14 days annual leave."

# Restore PII in the response:
restored = pii.restore(llm_response, token_map)
# restored: "John Tan is entitled to 14 days annual leave."
```

Patterns detected: NRIC/FIN (`[STFGM]\d{7}[A-Z]`), SG phone numbers, bank accounts, email addresses, dollar amounts (4+ digits).

## Known Gotchas

1. **In-memory persistence**: `SubmissionLedger`, `SagaOrchestrator`, `ApprovalStore`, `CostTracker`, and `ExternalTokenManager` are all singletons with in-memory dicts. Data is lost on server restart. Production MUST persist these to DataFlow models or Redis.

2. **Tool name sync**: Tool names in `tool_selector.py` `TOOL_DOMAINS` dict MUST exactly match `@server.tool("name")` registrations in server files. A mismatch means the tool exists but the shadow agent will never select it.

3. **GIRO XML namespace**: The ISO 20022 GIRO adapter (`adapters/giro.py`) uses stripped XML namespace for `ElementTree.findall()` queries. If namespace handling changes, all XPath queries break silently.

4. **MyInfo state parameter**: The security audit found the MyInfo callback accepted calls without a state parameter. The `state` parameter is now REQUIRED (not optional) in `gov_myinfo_callback`. Requests without it return an error.

5. **OAuth CSRF states expire**: All OAuth flows (CorpPass, Xero, QBO, Zoho) use 10-minute TTL state tokens stored in-memory. If the user takes longer than 10 minutes to authenticate, the callback will fail with "invalid state."

6. **Webhook signature enforcement**: When a webhook signing secret env var is configured for a provider, unsigned webhooks are rejected. If no secret is configured, webhooks are accepted without signature verification (development mode).

7. **Circuit breaker reset requires admin role**: The `/integrations/circuits/{name}/reset` endpoint requires `owner` or `hr_manager` role. Do not expose circuit reset to regular users.

8. **Cost tracker cents vs dollars**: `CostTracker` stores costs in cents (integer). The `get_monthly_cost()` response includes both `total_cents` and `total_sgd` (float). Always use `total_cents` for comparisons.

9. **Aspire sandbox mode**: `ASPIRE_SANDBOX=true` (default) uses the test environment. Aspire requires separate production API credentials via `ASPIRE_API_KEY`.

## Environment Variables

### Government APIs

| Variable                        | Required | Purpose                           |
| ------------------------------- | -------- | --------------------------------- |
| `APEX_CLIENT_ID`                | Prod     | GovTech APEX OAuth client ID      |
| `APEX_CLIENT_SECRET`            | Prod     | GovTech APEX OAuth client secret  |
| `APEX_APP_ID`                   | Prod     | APEX application ID               |
| `APEX_API_KEY`                  | Prod     | APEX API key for direct calls     |
| `APEX_USE_SANDBOX`              | No       | `true` (default) for sandbox      |
| `CORPPASS_ESERVICE_ID`          | Prod     | CorpPass e-Service ID from OSP    |
| `MYINFO_CLIENT_ID`              | Prod     | MyInfo API client ID              |
| `MYINFO_CLIENT_SECRET`          | Prod     | MyInfo API client secret          |
| `MYINFO_PRIVATE_SIGNING_KEY`    | Prod     | MyInfo request signing key        |
| `MYINFO_PRIVATE_ENCRYPTION_KEY` | Prod     | MyInfo response decryption key    |
| `MYINFO_USE_SANDBOX`            | No       | `true` (default) for sandbox      |
| `DATA_GOV_SG_API_KEY`           | No       | data.gov.sg API key (optional)    |
| `CPF_EMPLOYER_ACCOUNT`          | Prod     | CPF employer submission account   |
| `SSG_API_KEY`                   | No       | SkillsFuture SSG Developer Portal |

### Accounting

| Variable             | Required | Purpose                  |
| -------------------- | -------- | ------------------------ |
| `XERO_CLIENT_ID`     | If Xero  | Xero OAuth2 client ID    |
| `XERO_CLIENT_SECRET` | If Xero  | Xero OAuth2 secret       |
| `QBO_CLIENT_ID`      | If QBO   | QuickBooks OAuth2 ID     |
| `QBO_CLIENT_SECRET`  | If QBO   | QuickBooks OAuth2 secret |
| `ZOHO_CLIENT_ID`     | If Zoho  | Zoho OAuth2 client ID    |
| `ZOHO_CLIENT_SECRET` | If Zoho  | Zoho OAuth2 secret       |

### Banking

| Variable           | Required  | Purpose                      |
| ------------------ | --------- | ---------------------------- |
| `ASPIRE_API_KEY`   | If Aspire | Aspire Payout API key        |
| `ASPIRE_CLIENT_ID` | If Aspire | Aspire client ID             |
| `ASPIRE_SANDBOX`   | No        | `true` (default) for sandbox |
| `WISE_API_KEY`     | If Wise   | Wise Business API key        |

### Communications

| Variable                     | Required      | Purpose                             |
| ---------------------------- | ------------- | ----------------------------------- |
| `RESEND_API_KEY`             | If email      | Resend transactional email          |
| `SES_FROM_EMAIL`             | If SES        | AWS SES sender address              |
| `AWS_ACCESS_KEY_ID`          | If S3/SES     | AWS credentials                     |
| `AWS_SECRET_ACCESS_KEY`      | If S3/SES     | AWS credentials                     |
| `AWS_REGION`                 | If S3/SES     | AWS region                          |
| `TELEGRAM_BOT_TOKEN`         | If Telegram   | Telegram Bot API token              |
| `TELEGRAM_MONITOR_BOT_TOKEN` | If monitoring | Separate bot for channel monitoring |
| `WHATSAPP_ACCESS_TOKEN`      | If WhatsApp   | Meta Cloud API access token         |
| `WHATSAPP_PHONE_NUMBER_ID`   | If WhatsApp   | WhatsApp Business phone ID          |
| `SLACK_BOT_TOKEN`            | If Slack      | Slack Bot OAuth token               |
| `SLACK_SIGNING_SECRET`       | If Slack      | Slack webhook signing secret        |
| `GOOGLE_CLIENT_ID`           | If Google Cal | Google OAuth2 client ID             |
| `GOOGLE_CLIENT_SECRET`       | If Google Cal | Google OAuth2 secret                |
| `MICROSOFT_CLIENT_ID`        | If Outlook    | Microsoft Graph client ID           |
| `MICROSOFT_CLIENT_SECRET`    | If Outlook    | Microsoft Graph secret              |
| `MICROSOFT_TENANT_ID`        | If Outlook    | Azure AD tenant ID                  |
| `TWILIO_ACCOUNT_SID`         | If SMS        | Twilio account SID                  |
| `TWILIO_AUTH_TOKEN`          | If SMS        | Twilio auth token                   |
| `TWILIO_FROM_NUMBER`         | If SMS        | Twilio sender number                |

### Infrastructure

| Variable                     | Required  | Purpose                               |
| ---------------------------- | --------- | ------------------------------------- |
| `INTEGRATION_ENCRYPTION_KEY` | Prod      | Fernet key for OAuth token encryption |
| `XERO_WEBHOOK_KEY`           | If Xero   | Xero webhook signing secret           |
| `WHATSAPP_WEBHOOK_SECRET`    | If WA     | WhatsApp webhook signing secret       |
| `STRIPE_WEBHOOK_SECRET`      | If Stripe | Stripe webhook signing secret         |

## Test Coverage

| Test File                     | What It Covers                                        | Tests   |
| ----------------------------- | ----------------------------------------------------- | ------- |
| `test_base.py`                | ArborMCPServer tool registration, audit, tenant ctx    | ~30     |
| `test_resilience.py`          | Circuit breaker states, rate limiter, recovery        | ~40     |
| `test_idempotency.py`         | Submission ledger, duplicate blocking, retry on fail  | ~35     |
| `test_saga.py`                | Saga lifecycle, step progression, resume, cancel      | ~40     |
| `test_pii_filter.py`          | NRIC/phone/bank/salary stripping and restoration      | ~35     |
| `test_confirm_action.py`      | Approval store, approve/reject, tenant listing        | ~30     |
| `test_webhooks.py`            | Signature verification, event routing, rejection      | ~30     |
| `test_token_store.py`         | Token encryption, expiry, refresh, revocation         | ~35     |
| `test_tool_selector.py`       | Page-based filtering, role filtering, provider filter | ~40     |
| `test_cost_tracker.py`        | Cost recording, monthly totals, ceiling checks        | ~25     |
| `test_health.py`              | Connector status aggregation, summary                 | ~20     |
| `test_adapters_giro.py`       | ISO 20022 XML generation, bank compatibility          | ~40     |
| `test_adapters_paynow.py`     | PayNow QR data, SGQR format, CRC calculation          | ~30     |
| `test_adapters_data_gov.py`   | Public holiday fetch, CPF rate lookup                 | ~25     |
| `test_adapters_classifier.py` | Regulatory change classification rules                | ~29     |
| **Total**                     |                                                       | **484** |

## Related Files

- `src/hr_advisory/api/routers/integrations.py` -- 13 endpoint groups for admin dashboard
- `src/hr_advisory/api/platform.py` -- Integration router registration
- `tests/integration/mcp_servers/` -- All integration tests
