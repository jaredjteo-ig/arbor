# Arbor Integration Roadmap — 38 Connectors via MCP

**Scope**: 80 tasks (T204-T283) across 6 milestones. Covers all 38 connectors, 5 MCP servers, infrastructure, testing, and red team mitigations.
**Baseline**: T001-T203 complete. Advisory engine, HRIS, shadow agent, compliance, all live.
**User decisions**: All 38 connectors. File-based bank payments default. Government APIs Phase 2 (ahead of accounting).

---

## M28: Integration Infrastructure

Everything else depends on the shared MCP server framework, security primitives, and resilience patterns. No external API calls yet — pure internal infrastructure.

### T204: MCP Server Scaffold + Registry

Create the `src/hr_advisory/mcp_servers/` directory structure and base classes. All 5 MCP servers share common patterns: tool registration, tenant isolation middleware, audit decorator, health endpoint.

**Backend:**

- Create `src/hr_advisory/mcp_servers/__init__.py` with server registry
- Create `src/hr_advisory/mcp_servers/base.py` with `ArborMCPServer` base class wrapping Kailash `MCPServer`. Includes: tenant validation middleware (JWT company_id check), audit logging decorator, health endpoint, error standardization
- Create `src/hr_advisory/mcp_servers/registry.py` — registers all 5 servers, provides `get_server(name)` and `list_servers()` for the shadow agent
- Wire MCP servers into Nexus platform startup in `src/hr_advisory/api/platform.py`

**Evidence**: Import `ArborMCPServer`, instantiate, register a dummy tool, call it with a test JWT. Health endpoint returns 200.

**Dependencies**: None

### T205: Encrypted OAuth Token Store

Per-tenant, per-provider OAuth token storage using Fernet encryption (same pattern as PII encryption). Supports token refresh, expiry tracking, and revocation.

**Backend:**

- Create `src/hr_advisory/mcp_servers/auth/__init__.py`
- Create `src/hr_advisory/mcp_servers/auth/token_store.py` — `ExternalTokenManager` class with:
  - `store_token(tenant_id, provider, token_data)` — encrypts and stores in DB
  - `get_token(tenant_id, provider)` — decrypts, checks expiry, returns valid token
  - `refresh_token(tenant_id, provider)` — calls provider's refresh endpoint
  - `revoke_token(tenant_id, provider)` — deletes token, logs revocation
  - In-memory cache with TTL for hot path
- Create DataFlow model `IntegrationToken` with fields: tenant_id, provider, encrypted_token, refresh_token_encrypted, expires_at, scopes, created_at, updated_at
- Run DataFlow migration

**Evidence**: Store a test token, retrieve it, verify it decrypts correctly. Expired token triggers refresh. Revocation deletes from DB and cache.

**Dependencies**: T204

### T206: Circuit Breaker + Resilience Layer

Per-external-API circuit breakers with configurable thresholds. Prevents cascade failures when external APIs go down.

**Backend:**

- Create `src/hr_advisory/mcp_servers/resilience.py` — `CircuitBreaker` class with states (closed → open → half_open), configurable failure_threshold and recovery_timeout
- Create `ExternalAPIUnavailable` exception
- Pre-configure circuit breakers for each external API: CPF Board (3/120s), IRAS (3/120s), Xero/QBO/Zoho (5/60s), DBS/UOB/OCBC (3/300s), Email (10/30s), WhatsApp (5/60s), data.gov.sg (5/30s)
- Create `src/hr_advisory/mcp_servers/rate_limiter.py` — per-tenant, per-provider rate limiter to respect external API limits
- Integrate circuit breaker into `ArborMCPServer` base class as a decorator

**Evidence**: Trigger 3 failures on a test circuit → verify it opens. Wait recovery_timeout → verify half_open. Successful call → verify closed.

**Dependencies**: T204

### T207: Tool Invocation Audit Logger

PDPA-compliant audit trail for every MCP tool call. Extends existing PdpaAccessLog pattern.

**Backend:**

- Create `src/hr_advisory/mcp_servers/audit.py` — `@audited_tool` decorator that logs: tool_name, company_id, user_id, timestamp, status (success/error), duration_ms, error_type (if failed)
- Never log request/response payloads (may contain PII)
- Create DataFlow model `ToolInvocationLog` with the above fields
- Add `GET /admin/tool-audit-log` endpoint for admin access with pagination + filtering by tool, company, date range
- Wire into `ArborMCPServer` base class so all tools are automatically audited

**Evidence**: Call a test tool → verify log entry created in DB with correct fields. Verify no PII in log.

**Dependencies**: T204

### T208: Idempotency Ledger (Red Team C3)

Prevents double-submission of government filings and bank payments. Every high-stakes tool checks the ledger before executing.

**Backend:**

- Create DataFlow model `SubmissionLedger` with fields: id, tenant_id, submission_type (enum: cpf/ir8a/ir21/ir8s/oed/giro/fast/paynow), period, status (pending/submitted/confirmed/failed/cancelled), external_reference_id, idempotency_key, created_at, confirmed_at, error_detail
- Create `src/hr_advisory/mcp_servers/idempotency.py` — `@idempotent_submission` decorator that:
  - Generates idempotency key from (tenant_id, submission_type, period)
  - Checks ledger before execution: if pending/submitted/confirmed, block with clear message
  - Creates pending record before external call
  - Updates to submitted/confirmed/failed after external call
- Add `GET /admin/submission-ledger` endpoint for viewing submission history
- Add `POST /admin/submission-ledger/{id}/cancel` for manual cancellation of stuck submissions

**Evidence**: Submit CPF for March → record created. Attempt duplicate → blocked with message "CPF for 2026-03 already submitted (reference: X)". Failed submission allows retry.

**Dependencies**: T204

### T209: Saga State Machine (Red Team C4)

Recoverable multi-step workflow orchestration for shadow agent objectives. Each step is logged to DB so the agent can resume from failure.

**Backend:**

- Create DataFlow model `SagaExecution` with fields: id, tenant_id, saga_type (string, e.g. "submit_cpf", "post_payroll_to_xero"), status (pending/in_progress/completed/failed/cancelled), current_step, total_steps, step_log (JSONB — array of {step, status, result_summary, timestamp}), started_at, completed_at, error_detail
- Create `src/hr_advisory/mcp_servers/saga.py` — `SagaOrchestrator` class with:
  - `start_saga(tenant_id, saga_type, steps)` — creates DB record
  - `advance_step(saga_id, step_result)` — updates current_step, appends to step_log
  - `fail_step(saga_id, error)` — marks failed, preserves state for retry
  - `resume_saga(saga_id)` — returns last successful step so agent can continue
  - `get_saga_status(saga_id)` — returns full saga state for UI display
- Create `confirm_action` MCP tool (shared across all servers) — creates approval request, waits for human response via webhook or polling
- Add `GET /admin/sagas` endpoint for monitoring active/failed sagas

**Evidence**: Start 3-step saga → advance through steps → verify DB state at each step. Fail at step 2 → resume → verify continues from step 2.

**Dependencies**: T204, T208

### T210: PDPA PII Stripping Layer (Red Team C5)

Strips employee PII before data reaches the LLM in shadow agent queries that involve payroll/employee data. Replaces real names/NRICs with anonymized tokens, restores in response.

**Backend:**

- Create `src/hr_advisory/mcp_servers/pii_filter.py` — `PIIFilter` class with:
  - `strip(text, context)` — replaces NRIC patterns, names, bank accounts, salary amounts with tokens like `[EMPLOYEE_1]`, `[SALARY_1]`, `[NRIC_1]`
  - `restore(text, token_map)` — replaces tokens back to original values in the response
  - `get_token_map()` — returns the mapping (stored in-memory per request, never persisted)
- Integrate into shadow agent's `advisory` router — strip before LLM call, restore after
- Support configurable PII categories: nric, name, bank_account, salary, phone, address, work_pass
- Regex patterns for SG-specific PII: NRIC (S/T/F/G + 7 digits + letter), phone (+65...), postal code

**Evidence**: Input "John Tan (S1234567A) earns $5,000" → LLM sees "[EMPLOYEE_1] ([NRIC_1]) earns [SALARY_1]" → response references "[EMPLOYEE_1]" → output shows "John Tan".

**Dependencies**: None (can be built independently)

### T211: Connector Health Monitor

Real-time health dashboard for all 38 connectors. Shows which integrations are operational, degraded, or down.

**Backend:**

- Create `src/hr_advisory/mcp_servers/health.py` — `ConnectorHealthMonitor` class:
  - Tracks circuit breaker state per connector
  - Tracks last successful call timestamp per connector
  - Tracks error rate (rolling 5-minute window)
  - Provides `get_health_status()` returning status per connector (healthy/degraded/down)
- Add `GET /admin/connector-health` endpoint returning health for all connectors
- Add `GET /integrations/status` public endpoint (tenant-scoped) showing which of their connected integrations are healthy

**API:**

- Response: `{ "connectors": [{ "name": "xero", "status": "healthy", "last_success": "...", "error_rate": 0.0 }, ...] }`

**Evidence**: All connectors show "unknown" initially. After successful calls, show "healthy". After circuit breaker opens, show "down".

**Dependencies**: T206

### T212: Testing Strategy + Mock Adapter Framework

Create mock adapters for all external APIs so connectors can be tested without live API access. Contract testing approach.

**Backend:**

- Create `tests/integration/mcp_servers/` directory
- Create `tests/integration/mcp_servers/conftest.py` with shared fixtures: mock OAuth server, mock external API responses
- Create `src/hr_advisory/mcp_servers/adapters/mock_adapter.py` — base class for mock adapters that return realistic test data
- Create mock adapters for: data.gov.sg, Xero, QBO, Zoho, Resend, Telegram, each government API
- Each mock adapter records calls for assertion (spy pattern)
- Create `tests/integration/mcp_servers/test_base.py` — tests for ArborMCPServer base class, tenant isolation, audit logging

**Evidence**: Run `pytest tests/integration/mcp_servers/` — all pass. Mock adapters return realistic data. Tenant isolation blocks cross-tenant access.

**Dependencies**: T204, T205, T206, T207

---

## M29: Regulatory Intelligence + Communications + Quick Wins

The shadow agent gains real-time regulatory awareness and can send notifications. Users get live government data (public holidays, CPF rates) and upgraded bank file generation.

### T213: arbor-regulatory MCP Server Shell

Create the regulatory MCP server with its tool and resource registrations.

**Backend:**

- Create `src/hr_advisory/mcp_servers/regulatory_server.py` — instantiate `ArborMCPServer(name="arbor-regulatory")`
- Register MCP resources: `regulatory://cpf/rates/2026`, `regulatory://public-holidays/2026`, `regulatory://sdl/rates`, `regulatory://fwl/rates`, `regulatory://updates/feed`
- Resources backed by existing KB data from `hr_advisory/kb/` and `hr_advisory/workflows/regulatory_updates.py`
- Register tool stubs for R01-R06 (implemented in subsequent tasks)

**Evidence**: Start server, list tools and resources. Resources return valid data from existing KB.

**Dependencies**: T204

### T214: Data.gov.sg Public Holidays Connector (G08)

Replace hardcoded public holidays with live government data.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/data_gov_sg.py` — `DataGovSGAdapter` class with:
  - `fetch_public_holidays(year)` — calls data.gov.sg API, returns list of holidays
  - `fetch_cpf_rates()` — calls CPF rate dataset, returns rate tables
  - Response caching (24hr TTL for holidays, 7-day for rates)
  - API key from `DATA_GOV_SG_API_KEY` env var
- Register `government_get_public_holidays` tool in regulatory server
- Update `PublicHoliday` model seeding to pull from data.gov.sg instead of hardcoded list
- Update leave calendar working day calculation to use live holiday data

**Evidence**: Call tool → returns 2026 SG public holidays matching data.gov.sg. Leave calendar excludes these dates.

**Dependencies**: T213

### T215: Data.gov.sg CPF Rate Monitor (G09)

Auto-detect CPF rate changes from government data.

**Backend:**

- Add `fetch_cpf_rates()` to `DataGovSGAdapter` — fetches CPF contribution rate dataset
- Register `regulatory_check_cpf_rates` tool — compares data.gov.sg rates against hardcoded rates in `payroll_calculator.py`, flags differences
- Register `regulatory://cpf/rates/2026` resource backed by data.gov.sg data with 7-day cache
- Add admin notification when rate discrepancy detected

**Evidence**: Tool returns current CPF rates from data.gov.sg. When rates differ from hardcoded values, flags a discrepancy alert.

**Dependencies**: T214

### T216: SSO Per-Act RSS Monitor (R01)

Daily monitoring of Singapore Statutes Online for amendments to employment-related Acts.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/sso_rss.py` — `SSORSSAdapter` class:
  - Discovers RSS feed URLs for each Act (Employment Act, CPF Act, EFMA, WICA, WSHA, ITA, ECA, CDCSA, WFA, RRA)
  - Parses RSS XML, extracts amendment entries with dates
  - Stores last-seen entry per Act to detect new amendments
  - Handles SSO 403 responses gracefully (proper User-Agent, retry with backoff)
- Register `regulatory_get_act_amendments` tool — returns recent amendments for a specified Act
- Register `regulatory_check_updates` tool — polls all RSS feeds, returns new entries since last check
- Create DataFlow model `RegulatoryFeedEntry` with fields: id, source, act_name, title, url, published_at, first_seen_at, processed

**Evidence**: Parse a real SSO RSS feed (Employment Act). Store entries. On second call, detect no new entries. When a new amendment appears, flag it.

**Dependencies**: T213

### T217: MOM Sitemap Monitor (R03)

Parse MOM XML sitemap for new press releases and announcements.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/mom_sitemap.py` — `MOMSitemapAdapter`:
  - Fetches `mom.gov.sg/newsroom.xml`
  - Parses sitemap for press-release and announcement URLs with `lastmod` dates
  - Compares against stored URLs to detect new entries
  - Stores new URLs as `RegulatoryFeedEntry` records
- Wire into `regulatory_check_updates` tool

**Evidence**: Parse MOM sitemap, store entries. Detect new entries on subsequent calls.

**Dependencies**: T216

### T218: Web Change Detection Engine (R04)

Monitor government web pages for content changes — CPF Board, IRAS, TAFEP, eGazette.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/change_detector.py` — `ChangeDetectionEngine`:
  - Configurable list of URLs to monitor with CSS selectors for content area
  - Fetches page, extracts content, computes hash
  - Stores hash per URL in `WebPageSnapshot` DataFlow model (url, content_hash, last_checked, last_changed, diff_text)
  - When hash changes: extract diff, store as `RegulatoryFeedEntry`
  - Polite crawling: 1 request/second, proper User-Agent, respect robots.txt
- Configure monitoring for:
  - `cpf.gov.sg/member/infohub/news/news-releases`
  - `iras.gov.sg/news-events/newsroom`
  - `tal.sg/tafep/getting-started/fair/tripartite-guidelines`
  - `mom.gov.sg/employment-practices/employment-act`
  - `egazette.gov.sg/egazette-browse/`
- Wire into `regulatory_check_updates` tool

**Evidence**: First run stores baseline snapshots. Simulated change (test with modified mock page) triggers diff detection.

**Dependencies**: T216

### T219: Telegram Government Channel Monitor (R05)

Monitor @sgministryofmanpower, @CPFBoard, @govsg Telegram channels for regulatory posts.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/telegram_monitor.py` — `TelegramChannelMonitor`:
  - Uses Telegram Bot API to read public channel messages
  - Filters for HR/employment-relevant posts (keyword matching + optional LLM classification)
  - Stores relevant posts as `RegulatoryFeedEntry` records
  - Bot token from `TELEGRAM_MONITOR_BOT_TOKEN` env var
- Wire into `regulatory_check_updates` tool as supplementary signal

**Evidence**: Monitor a test Telegram channel, detect new posts, store as feed entries.

**Dependencies**: T216

### T220: Regulatory Change Classifier (R06)

LLM-powered classification of detected changes — is this relevant to HR/employment? Which Arbor modules are affected?

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/regulatory_classifier.py` — `RegulatoryChangeClassifier`:
  - Takes a `RegulatoryFeedEntry` (title, URL, diff text)
  - LLM classifies: relevant (yes/no), affected domains (payroll, leave, CPF, foreign workers, tax, safety, fair employment), urgency (critical/high/medium/low)
  - Generates plain-language summary for admin notification
  - Creates task in `regulatory_updates` pipeline for review
- Register `regulatory_classify_change` and `regulatory_summarize_change` tools
- PII stripping not needed here (regulatory text, not employee data)

**Evidence**: Feed a simulated "CPF OW ceiling increase to $8,500" change → classifies as relevant, domain=CPF/payroll, urgency=high, generates summary.

**Dependencies**: T210 (PII filter — shared dependency), T216

### T221: arbor-communications MCP Server Shell

Create the communications MCP server.

**Backend:**

- Create `src/hr_advisory/mcp_servers/communications_server.py` — instantiate `ArborMCPServer(name="arbor-communications")`
- Register tool stubs for C01-C08

**Evidence**: Start server, list tools. All return "not yet implemented" placeholder.

**Dependencies**: T204

### T222: Resend Email Connector (C01)

Transactional email delivery for payslips, notifications, onboarding invites.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/resend_email.py` — `ResendAdapter`:
  - `send_email(to, subject, html_body, from_address)` — sends via Resend API
  - `send_bulk(recipients, subject, html_template, merge_fields)` — batch send
  - API key from `RESEND_API_KEY` env var
  - Tracks delivery status via Resend webhooks
- Register `comms_send_email` and `comms_send_bulk_email` tools
- Integrate with existing payslip email delivery (replace placeholder in payroll router)
- HTML email templates for: payslip, leave approval, leave rejection, onboarding invite, compliance alert, regulatory update

**Evidence**: Send test email via Resend → verify delivery. Bulk send to 3 test addresses → all delivered. Payslip email renders correctly.

**Dependencies**: T221

### T223: Telegram Bot Connector (C04)

Notifications and interactive shadow agent via Telegram.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/telegram_bot.py` — `TelegramBotAdapter`:
  - `send_message(chat_id, text, reply_markup)` — sends text with optional inline keyboard
  - `send_document(chat_id, file_bytes, filename)` — sends payslip PDF
  - `register_webhook(url)` — sets up Telegram webhook for incoming messages
  - Bot token from `TELEGRAM_BOT_TOKEN` env var
- Register `comms_send_telegram` tool
- Create webhook handler in Nexus for incoming Telegram messages → routes to shadow agent advisory pipeline
- Interactive keyboards for: leave approve/reject, claim approve/reject, payslip download

**Evidence**: Send test notification → received in Telegram. Send payslip PDF → downloadable. Inline keyboard works for approve/reject.

**Dependencies**: T221

### T224: ISO 20022 GIRO File Generator Upgrade (B01)

Upgrade existing bank file generation from DBS fixed-width + generic CSV to ISO 20022 pain.001.001.03 XML standard. Universal compatibility with all SG banks.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/giro.py` — `GIROFileGenerator`:
  - `generate_pain001(payroll_run, payslips, employees, bank_config)` — generates pain.001.001.03 XML
  - Supports all SG banks: DBS, OCBC, UOB, Maybank, HSBC, Standard Chartered
  - Fields: BIC, payment purpose code, creditor reference, remittance info
  - Validates against pain.001 XSD schema before returning
- Create `src/hr_advisory/mcp_servers/banking_server.py` — instantiate arbor-banking MCP server
- Register `banking_generate_giro_file` tool — generates file, stores in S3/local, returns download URL
- Keep existing DBS fixed-width generator as fallback option
- Update payroll router to offer ISO 20022 as default format

**Evidence**: Generate pain.001 XML for a test payroll run with 5 employees across DBS and UOB. Validate against XSD. File is parseable by bank simulators.

**Dependencies**: T204

### T225: AWS S3 Document Storage Connector

Centralized document storage for payslips, receipts, statutory files, and generated bank files.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/s3_storage.py` — `S3StorageAdapter`:
  - `upload(tenant_id, file_key, file_bytes, content_type)` — uploads to S3 with tenant-prefixed key
  - `get_presigned_url(tenant_id, file_key, expires_in=3600)` — generates time-limited download URL
  - `delete(tenant_id, file_key)` — soft-delete with lifecycle policy
  - Bucket from `AWS_S3_BUCKET` env var, region `ap-southeast-1`
  - SSE-S3 encryption at rest
  - Tenant isolation via key prefix: `{tenant_id}/payslips/...`, `{tenant_id}/statutory/...`
- Register as shared utility (not a standalone MCP tool — used by other connectors)
- Migrate existing payslip/statutory file generation to use S3 storage

**Evidence**: Upload test file → retrieve via presigned URL → content matches. Cross-tenant access attempt returns 403.

**Dependencies**: T204

---

## M30: Government API Integrations

Arbor can submit CPF contributions, file IR8A/IR21/IR8S with IRAS, submit employment data to MOM, and auto-populate employee data from MyInfo. The shadow agent handles the entire government filing workflow with human confirmation gates.

### T226: CorpPass Authorization Flow (G07)

OAuth 2.1 + CorpPass authentication for all government APIs via APEX.

**Backend:**

- Create `src/hr_advisory/mcp_servers/auth/corppass.py` — `CorpPassAuthFlow`:
  - `initiate_auth(tenant_id, callback_url)` — redirects employer to CorpPass login
  - `handle_callback(auth_code, tenant_id)` — exchanges code for access token + refresh token
  - `get_valid_token(tenant_id)` — returns valid token, refreshes if expired
  - Stores tokens via `ExternalTokenManager` (T205)
  - JWKS endpoint for client assertion verification
  - PKI certificate management for APEX mTLS
- Create `src/hr_advisory/mcp_servers/government_server.py` — instantiate arbor-government MCP server
- Add `/integrations/corppass/connect` and `/integrations/corppass/callback` endpoints to Nexus
- Admin UI flow: "Connect to CorpPass" → redirects to CorpPass → callback stores token

**Evidence**: Full OAuth flow with CorpPass sandbox (or mock). Token stored encrypted. Refresh works. Token revocation clears store.

**Dependencies**: T205, T212 (mock adapter for sandbox)

### T227: CPF APEX Submission Connector (G01)

Submit monthly CPF contributions via CPF Board's APEX API.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/cpf_apex.py` — `CPFAPEXAdapter`:
  - `validate_cpf_data(tenant_id, period)` — checks payroll is finalized, validates employee NRIC/CPF data
  - `generate_submission(tenant_id, period)` — creates CPF submission payload from payslip data
  - `submit(tenant_id, period, submission_data)` — submits to CPF Board via APEX API
  - `check_status(tenant_id, submission_id)` — polls for acknowledgement
  - Uses CorpPass token from T226
  - Uses idempotency ledger from T208 to prevent double submission
- Register tools: `government_validate_cpf_readiness`, `government_submit_cpf`, `government_get_filing_status`
- Saga definition for "submit CPF" objective: validate → generate → confirm_action → submit → check_status
- Fallback: if APEX unavailable, generate CPF e-Submit CSV file (existing T163 functionality)

**Evidence**: Full saga in sandbox: validate → generate → confirm → submit → acknowledged. Duplicate blocked by idempotency ledger. Fallback CSV generated when APEX is down.

**Dependencies**: T226, T208, T209

### T228: IRAS AIS IR8A Submission Connector (G02)

Submit annual IR8A employment income data via IRAS AIS-API 2.0.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/iras_ais.py` — `IRASAISAdapter`:
  - `generate_ir8a_data(tenant_id, year_of_assessment)` — creates IR8A payload from payroll history
  - `submit_ir8a(tenant_id, ya, ir8a_data)` — submits via IRAS AIS-API 2.0
  - `submit_appendix_8a(tenant_id, ya, data)` — submits benefits in kind data
  - `check_filing_status(tenant_id, submission_id)` — checks IRAS acknowledgement
  - Uses CorpPass token
  - Uses idempotency ledger (submission_type="ir8a")
- Register `government_file_ir8a` tool
- Saga: generate data → preview for admin → confirm_action → submit → check status
- Fallback: generate IR8A TXT file for manual upload via IRAS VSA

**Evidence**: Generate IR8A data for test company. Submit in sandbox. Receive acknowledgement. Duplicate blocked.

**Dependencies**: T226, T208, T209

### T229: IRAS AIS IR21 Submission Connector (G03)

Submit IR21 for departing foreign employees.

**Backend:**

- Add `submit_ir21(tenant_id, employee_id)` to `IRASAISAdapter`
- Triggers automatically when foreign employee's end_date is set (or manually via shadow agent)
- Register `government_file_ir21` tool
- Uses existing IR21 data generation from `statutory_files.py`

**Evidence**: Set foreign employee end_date → IR21 data generated → submitted in sandbox.

**Dependencies**: T228

### T230: IRAS AIS IR8S Submission Connector (G04)

Submit IR8S refund/voluntary CPF contribution data.

**Backend:**

- Add `submit_ir8s(tenant_id, ya, data)` to `IRASAISAdapter`
- Create IR8S data generation in `statutory_files.py` (new — not previously built)
- Fields: employer voluntary CPF, excess CPF refund, employee-elected CPF
- Register `government_file_ir8s` tool

**Evidence**: Generate IR8S data. Submit in sandbox. Verify fields match IRAS spec.

**Dependencies**: T228

### T231: MOM OED Submission Connector (G05)

Submit occupational employment data to MOM via APEX.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/mom_oed.py` — `MOMOEDAdapter`:
  - `generate_oed_data(tenant_id)` — creates OED payload from employee records (occupation, salary, nationality, etc.)
  - `submit_oed(tenant_id, data)` — submits via MOM APEX API
  - `check_submission_status(tenant_id, submission_id)` — polls for acknowledgement
  - Uses CorpPass token, idempotency ledger
- Register `government_submit_oed` tool

**Evidence**: Generate OED data for test company. Submit in sandbox.

**Dependencies**: T226, T208

### T232: MyInfo Employee Onboarding Connector (G06)

Auto-populate employee data from government-verified MyInfo during onboarding.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/myinfo.py` — `MyInfoAdapter`:
  - `initiate_consent(employee_email, callback_url)` — redirects employee to Singpass
  - `handle_callback(auth_code)` — exchanges code for access token
  - `fetch_person_data(access_token)` — retrieves and decrypts MyInfo data (JWE+JWS)
  - Requested scopes: name, nric, dob, sex, race, nationality, residential_status, regadd, cpfcontributions (15 months)
  - Maps MyInfo fields to Employee model fields
  - Build directly on FAPI 2.0 (PAR, JARM) per red team H5 recommendation
- Register `government_fetch_myinfo` tool
- Add `/integrations/myinfo/callback` endpoint
- Employee onboarding flow: admin invites → employee clicks "Verify with Singpass" → MyInfo auto-fills profile

**Evidence**: Full OAuth/FAPI flow with MyInfo sandbox. Employee data auto-populates. NRIC encrypted on storage. PDPA consent recorded.

**Dependencies**: T226, T205

### T233: MyInfo Business Company Onboarding Connector (G12)

Auto-populate company profile from MyInfo Business during company registration.

**Backend:**

- Add `fetch_business_data(access_token)` to MyInfo adapter
- Maps MyInfo Business fields to company profile: UEN, entity_name, status, SSIC, directors, registered_address
- Register `government_fetch_myinfo_business` tool
- Company onboarding flow: admin clicks "Verify with CorpPass" → company data auto-fills

**Evidence**: Retrieve business data from MyInfo Business sandbox. Company profile populated.

**Dependencies**: T232

---

## M31: Accounting + Banking File Integrations

Arbor can post payroll journals to Xero, QuickBooks, and Zoho Books. Generate FAST payment files, PayNow QR codes, and Aspire bulk payouts. Claims sync to accounting.

### T234: arbor-accounting MCP Server Shell

Create the accounting MCP server with OAuth connection management.

**Backend:**

- Create `src/hr_advisory/mcp_servers/accounting_server.py`
- Register tool stubs for A01-A05
- Create `/integrations/accounting/connect/{provider}` endpoint — initiates OAuth flow for Xero/QBO/Zoho
- Create `/integrations/accounting/callback/{provider}` — handles OAuth callback, stores tokens
- Create `/integrations/accounting/disconnect/{provider}` — revokes token
- Create `GET /integrations/accounting/status` — shows which provider is connected

**Evidence**: Connect flow initiates correctly. Callback stores token. Status shows connected.

**Dependencies**: T204, T205

### T235: Xero Integration (A01)

Post payroll and claims journals to Xero via Manual Journals API.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/xero.py` — `XeroAdapter`:
  - `get_chart_of_accounts(tenant_id)` — retrieves SG chart of accounts, caches 24hr
  - `post_payroll_journal(tenant_id, payroll_run_id)` — creates Manual Journal with debit/credit lines: Salary Expense (debit), CPF Employer (debit), SDL (debit), Employee CPF Payable (credit), Net Pay Clearing (credit)
  - `post_claims_journal(tenant_id, claim_ids)` — creates journal for approved claims
  - `get_trial_balance(tenant_id)` — retrieves for verification
  - Uses `xero-python` SDK, OAuth tokens from token store
  - Handles Xero rate limits (60/min, 5K/day) with queuing
- Register tools: `accounting_get_chart_of_accounts`, `accounting_post_payroll_journal`, `accounting_post_claims_journal`, `accounting_get_trial_balance`
- Saga for "post payroll to Xero": fetch chart → map accounts → generate journal → confirm_action → post

**Evidence**: Post payroll journal for test run → journal appears in Xero sandbox. Claims journal posted. Trial balance retrieved.

**Dependencies**: T234

### T236: QuickBooks Online Integration (A02)

Same as Xero but for QBO Journal Entry endpoint.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/quickbooks.py` — `QuickBooksAdapter`:
  - Same methods as Xero adapter but using QBO API
  - `POST /journalentry` for journals
  - Handles QBO rate limits (500/min, 10 concurrent)
- Register same tool names (routed by connected provider)

**Evidence**: Post payroll journal → appears in QBO sandbox.

**Dependencies**: T234

### T237: Zoho Books Integration (A03)

Same as Xero but for Zoho Books Journals API. Note: aggressive caching needed due to 2,500/day limit (red team H3).

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/zoho.py` — `ZohoAdapter`:
  - Same methods as Xero adapter but using Zoho API
  - `POST /journals` for journal entries
  - Aggressive caching for chart of accounts (48hr TTL)
  - Batch journal entries where possible to minimize API calls
  - Rate limit tracking with warning at 80% of daily limit
- Register same tool names

**Evidence**: Post payroll journal with <10 API calls. Rate limit warning triggers at threshold.

**Dependencies**: T234

### T238: Financio Integration (A04)

Export payroll journal as text file compatible with Financio import format.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/financio.py` — `FinancioAdapter`:
  - `export_payroll_journal(payroll_run_id)` — generates text file matching Financio GL Posting format
  - If Financio partner API becomes available: add direct posting
- Register `accounting_post_payroll_journal` with provider="financio" routing to file export

**Evidence**: Generated text file matches Financio import format specification.

**Dependencies**: T234

### T239: Generic Accounting Export (A05)

CSV/Excel/JSON export for any accounting platform without API integration.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/generic_export.py`:
  - `export_csv(payroll_run_id)` — standard journal entry CSV
  - `export_excel(payroll_run_id)` — Excel with headers and formatting
  - `export_json(payroll_run_id)` — structured JSON
- Register as fallback when no provider is connected

**Evidence**: All 3 formats generated. CSV importable into any accounting software.

**Dependencies**: T234

### T240: FAST Payment File Generator (B02)

Generate FAST payment files for same-day salary transfers.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/fast.py` — `FASTFileGenerator`:
  - `generate_dbs_fast(payroll_run, payslips, employees)` — DBS IDEAL FAST format
  - `generate_uob_fast(payroll_run, payslips, employees)` — UOB BIBPlus format (v3.04)
  - Both use ISO 20022 pain.001 base with FAST-specific extensions
- Register `banking_generate_fast_file` tool
- Store in S3, return presigned download URL

**Evidence**: Generate FAST files for DBS and UOB formats. Files match bank specifications.

**Dependencies**: T224, T225

### T241: PayNow QR Generator (B07)

Generate PayNow QR codes for employee reimbursements using SGQR standard.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/paynow.py` — `PayNowQRGenerator`:
  - `generate_qr(recipient_type, recipient_id, amount, reference)` — generates SGQR-compliant QR code
  - `recipient_type`: "mobile" (phone number), "nric", "uen"
  - Returns PNG image bytes and QR data string
  - Pure client-side generation — no external API needed
  - Implements EMVCo SGQR specification
- Register `banking_generate_paynow_qr` tool
- Use case: employee submits approved claim → admin generates PayNow QR → employee scans to receive reimbursement

**Evidence**: Generate QR for test mobile number → scannable by any PayNow-compatible banking app. Amount and reference embedded correctly.

**Dependencies**: T224

### T242: Aspire Payout API Connector (B06)

Single and bulk payouts via Aspire neobank API.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/aspire.py` — `AspireAdapter`:
  - `initiate_payout(tenant_id, recipient, amount, currency, reference)` — single payout
  - `initiate_bulk_payout(tenant_id, payroll_run_id)` — bulk salary payout
  - `get_payout_status(tenant_id, payout_id)` — check status
  - Auth: Client ID + API key from token store
  - Uses idempotency ledger for payment deduplication
- Register `banking_initiate_bulk_payout`, `banking_get_payment_status` tools
- Requires: company has Aspire business account + API credentials configured

**Evidence**: Initiate test payout in Aspire sandbox. Bulk payout for 5 employees. Status check returns correct state.

**Dependencies**: T224, T208

### T243: Claims-to-Accounting Sync Pipeline

When claims are approved and marked paid, automatically post journal entries to connected accounting platform.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/claims_sync.py`:
  - Listens for claim status changes (approved → paid)
  - Groups paid claims by category
  - Calls `accounting_post_claims_journal` with grouped entries
  - Tracks sync status per claim (synced/pending/failed)
- Add `claims_synced_to_accounting` field to Claim model
- Add `GET /claims/accounting-sync-status` endpoint

**Evidence**: Approve 3 claims → mark as paid → journal entry appears in connected accounting platform. Sync status shows "synced".

**Dependencies**: T235 (or T236 or T237)

---

## M32: Extended Integrations

WhatsApp, Slack, Teams notifications. Calendar sync. HRIS data import. SkillsFuture. ACRA verification. Wise cross-border payments.

### T244: WhatsApp Business Connector (C03)

Notifications via WhatsApp Cloud API using approved templates.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/whatsapp.py` — `WhatsAppAdapter`:
  - `send_template(phone, template_name, parameters)` — sends approved template message
  - `send_interactive(phone, body, buttons)` — within 24hr window only
  - Templates: `payslip_ready`, `leave_approved`, `leave_rejected`, `compliance_alert`, `deadline_reminder`
  - All templates notification-only ("View in Arbor") — no financial data in message body (red team H4)
  - Meta business verification required
  - Phone number from `WHATSAPP_PHONE_NUMBER_ID` env var
- Register `comms_send_whatsapp` tool
- Add employee phone number opt-in for WhatsApp notifications in profile settings

**Evidence**: Send template notification → received on WhatsApp. Interactive buttons work within 24hr window.

**Dependencies**: T221

### T245: Slack Bot Connector (C05)

Post notifications and interactive messages to Slack.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/slack.py` — `SlackAdapter`:
  - `post_message(channel, text, blocks)` — posts to channel or DM
  - `send_interactive(channel, text, actions)` — buttons for approve/reject
  - Webhook handler for interactive message callbacks
  - Slash commands: `/leave-balance`, `/payslip`, `/ask-arbor`
  - OAuth app installation flow
- Register `comms_send_slack` tool
- Add `/integrations/slack/install` and `/integrations/slack/callback` endpoints

**Evidence**: Post notification to test channel. Interactive leave approval works. Slash command returns leave balance.

**Dependencies**: T221

### T246: Microsoft Teams Bot Connector (C06)

Notifications via Teams webhook and Adaptive Cards.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/teams.py` — `TeamsAdapter`:
  - `send_webhook(webhook_url, card)` — posts Adaptive Card to Teams channel
  - `send_notification(user_id, text, actions)` — proactive message via Bot Framework
  - Adaptive Card templates: payslip notification, leave approval, compliance alert
  - Azure Bot Service registration (F0 free tier)
- Register `comms_send_teams` tool

**Evidence**: Post Adaptive Card to test channel. Approve/reject buttons work.

**Dependencies**: T221

### T247: Google Calendar Sync (C07)

Sync approved leave to Google Calendar as Out-of-Office events.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/google_calendar.py` — `GoogleCalendarAdapter`:
  - `create_ooo_event(calendar_id, start, end, summary)` — creates Out-of-Office event
  - `sync_leave(tenant_id, employee_id)` — syncs all approved leave for an employee
  - `sync_public_holidays(tenant_id, calendar_id)` — adds SG public holidays
  - OAuth 2.0 per employee (consent flow)
  - Uses Google Calendar API v3
- Register `comms_sync_leave_to_calendar` tool
- Add `/integrations/google/connect` and `/integrations/google/callback` endpoints
- Employee settings: "Sync my leave to Google Calendar"

**Evidence**: Approve leave → OOO event appears in Google Calendar. Public holidays synced.

**Dependencies**: T221, T214

### T248: Microsoft Outlook Calendar Sync (C08)

Sync approved leave to Outlook Calendar via Microsoft Graph API.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/microsoft_graph.py` — `MicrosoftGraphAdapter`:
  - Same capabilities as Google Calendar adapter but using Graph API
  - `create_ooo_event`, `sync_leave`, `sync_public_holidays`
  - OAuth 2.0 via Entra ID
  - Uses Graph API (NOT EWS — deprecated Oct 2026, red team note)
- Register same `comms_sync_leave_to_calendar` tool (routes by connected provider)
- Add `/integrations/microsoft/connect` and callback

**Evidence**: Approve leave → OOO event appears in Outlook Calendar.

**Dependencies**: T221, T214

### T249: Talenox Data Import Connector

Import employee data from Talenox for companies migrating to Arbor.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/talenox.py` — `TalenoxAdapter`:
  - `fetch_employees(api_token)` — retrieves all employee records via Talenox REST API
  - `fetch_payroll_history(api_token, year)` — retrieves payroll data
  - `fetch_leave_balances(api_token)` — retrieves leave data
  - Maps Talenox fields to Arbor Employee model
  - Dry-run mode: preview import without committing
  - Validation report: missing fields, format mismatches, duplicate detection
- Register `hris_import_from_talenox` tool
- Migration flow: admin enters Talenox API token → preview → confirm → import

**Evidence**: Import test employees from Talenox sandbox. Preview shows field mapping. Confirm creates employees in Arbor. Duplicate detection works.

**Dependencies**: T204

### T250: HReasily Data Import Connector

Import from HReasily via their unified API.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/hreasily.py` — `HREasilyAdapter`:
  - Same pattern as Talenox adapter
  - Uses HReasily's unified API interface
- Register `hris_import_from_hreasily` tool

**Evidence**: Import test employees. Mapping correct.

**Dependencies**: T204

### T251: SkillsFuture SSG Integration (G11)

Browse courses, check grant eligibility, enable SFC credit payment.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/skillsfuture.py` — `SkillsFutureAdapter`:
  - `search_courses(query, filters)` — search SSG course catalog
  - `get_course_details(course_id)` — detailed course info
  - `calculate_grant(tenant_id, employee_id, course_id)` — calculate eligible training grants
  - `initiate_sfc_payment(employee_id, course_id)` — redirect to SFC credit payment gateway
  - API key from SSG Developer Portal
- Register tools in government server: `government_search_courses`, `government_calculate_training_grant`, `government_initiate_sfc_payment`
- Employee flow: "Find me a course on employment law" → browse → check grant → use SFC credits

**Evidence**: Search courses → results returned. Grant calculation returns eligible amount. Payment flow redirects to SFC portal.

**Dependencies**: T226

### T252: ACRA UEN Verification (G10)

Verify company UEN and retrieve entity details.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/acra.py` — `ACRAAdapter`:
  - `verify_uen(uen)` — checks UEN validity, returns entity name and status
  - `get_business_profile(uen)` — full business profile (directors, SSIC, address)
  - Uses data.gov.sg bulk dataset for basic validation (free)
  - Uses ACRA Business Profile API for full profile (S$5.50/query — cache 30 days, red team H9)
  - Cost tracking per tenant
- Register `government_verify_uen` tool
- Wire into company onboarding: auto-verify UEN on registration

**Evidence**: Verify test UEN → returns correct entity name. Cache prevents repeated API calls. Cost tracked.

**Dependencies**: T214

### T253: Wise Cross-Border Payments (Red Team H1)

Cross-border payments for foreign contractors via Wise Business API.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/wise.py` — `WiseAdapter`:
  - `create_transfer(source_currency, target_currency, amount, recipient)` — creates transfer
  - `get_exchange_rate(source, target)` — real-time rate
  - `get_transfer_status(transfer_id)` — track status
  - `create_batch_transfers(transfers)` — bulk cross-border payments
  - API key from `WISE_API_KEY` env var
  - Uses idempotency ledger for payment deduplication
- Register `banking_initiate_cross_border_payment` tool

**Evidence**: Create test transfer in Wise sandbox. Rate retrieved. Status tracked.

**Dependencies**: T224, T208

### T254: AWS SES Email Connector (C02)

Production-scale email delivery as alternative to Resend.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/ses_email.py` — `SESAdapter`:
  - Same interface as Resend adapter
  - Uses AWS SES via boto3
  - SG region (ap-southeast-1)
  - Configurable: use SES or Resend via `EMAIL_PROVIDER` env var
- Register as alternative implementation of `comms_send_email`

**Evidence**: Send test email via SES. Delivery confirmed.

**Dependencies**: T221

---

## M33: Premium Features + Polish

Direct bank API integrations (premium), payroll reconciliation loop, connector versioning, InvoiceNow, SMS notifications.

### T255: DBS RAPID Integration (B03)

Real-time salary payments via DBS RAPID API. Premium feature — requires employer's DBS corporate account.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/dbs.py` — `DBSRAPIDAdapter`:
  - `initiate_fund_transfer(tenant_id, recipient, amount)` — real-time payment
  - `initiate_paynow(tenant_id, recipient_proxy, amount)` — PayNow via DBS
  - `get_payment_status(tenant_id, reference_id)` — status check
  - Developer token + corporate banking auth
  - Idempotency ledger integration
- Register `banking_initiate_payment` tool with provider="dbs"
- Per-tenant onboarding flow: employer grants Arbor access via DBS IDEAL

**Evidence**: Initiate test payment in DBS sandbox. Status polling works. Duplicate blocked.

**Dependencies**: T224, T208

### T256: UOB API Integration (B04)

Same as DBS but for UOB Developer Portal.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/uob.py` — `UOBAdapter`
- Same interface as DBS adapter
- Register with provider="uob"

**Dependencies**: T224, T208

### T257: OCBC Connect2OCBC Integration (B05)

Same as DBS but for OCBC API Store.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/ocbc.py` — `OCBCAdapter`
- Register with provider="ocbc"

**Dependencies**: T224, T208

### T258: Payroll Reconciliation Loop (Red Team H8)

Three-way reconciliation: payroll run ↔ bank payment ↔ accounting journal.

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/reconciliation.py` — `PayrollReconciler`:
  - `reconcile(tenant_id, payroll_run_id)` — cross-references:
    1. Payroll run total (from payslips)
    2. Bank payment total (from GIRO file / bank API status)
    3. Accounting journal total (from Xero/QBO/Zoho)
  - Returns match status per leg: matched/unmatched/pending
  - Flags discrepancies with specific amounts
- Register `payroll_reconcile` tool
- Add `GET /payroll/runs/{id}/reconciliation` endpoint
- Shadow agent can proactively check: "Your March payroll has a $450 discrepancy between bank payment and accounting journal"

**Evidence**: All three legs match → "reconciled". Introduce $100 discrepancy → flagged with details.

**Dependencies**: T235, T224

### T259: Connector Version Registry (Red Team H7)

Track API versions per connector, deprecation warnings, feature flags.

**Backend:**

- Create `src/hr_advisory/mcp_servers/version_registry.py`:
  - Each adapter declares: `api_version`, `min_supported_version`, `deprecation_date` (if known)
  - `get_connector_versions()` — returns version info for all connectors
  - `check_deprecations()` — returns list of connectors approaching deprecation
  - Admin notification when a connector's upstream API announces deprecation
- Add version info to connector health endpoint (T211)

**Evidence**: Registry returns version info for all 38 connectors. Deprecation check flags test entry.

**Dependencies**: T211

### T260: InvoiceNow / Peppol Compatibility (Red Team H2)

Ensure accounting journal postings are InvoiceNow-compatible for GST-registered businesses.

**Backend:**

- Audit Xero, QBO, Zoho adapters for InvoiceNow compliance
- Add GST treatment flags to payroll journal entries
- For providers that support InvoiceNow natively (Xero SG, Financio): verify compliance
- For providers without native support: document limitations

**Evidence**: Payroll journal in Xero includes correct GST codes. InvoiceNow compliance documented per provider.

**Dependencies**: T235

### T261: SMS Notification Connector (Red Team M6)

SMS for critical notifications (payslip, CPF submission confirmation).

**Backend:**

- Create `src/hr_advisory/mcp_servers/adapters/sms.py` — `SMSAdapter`:
  - `send_sms(phone, message)` — sends via Twilio or Vonage
  - API key from `SMS_PROVIDER_API_KEY` env var
  - Reserved for critical-path notifications only (cost control)
- Register `comms_send_sms` tool

**Evidence**: Send test SMS. Delivery confirmed.

**Dependencies**: T221

### T262: Webhook Receiver Framework (Red Team M7)

Inbound webhook handling for external API events (Xero changes, bank payment status, WhatsApp delivery receipts).

**Backend:**

- Create `src/hr_advisory/mcp_servers/webhooks.py` — `WebhookRouter`:
  - `register_webhook(provider, endpoint, handler)` — registers handler for provider webhooks
  - HMAC signature verification per provider (Xero: `x-xero-signature`, etc.)
  - Webhook endpoints: `/webhooks/xero`, `/webhooks/whatsapp`, `/webhooks/stripe`, etc.
  - Routes events to appropriate MCP server adapter
- Wire into Nexus platform

**Evidence**: Receive test Xero webhook → signature verified → event routed to handler.

**Dependencies**: T204

### T263: Dynamic Tool Loading for Shadow Agent (Red Team M8)

Only inject relevant MCP tools based on the user's current context (page, role, connected integrations).

**Backend:**

- Create `src/hr_advisory/mcp_servers/tool_selector.py` — `ContextualToolSelector`:
  - `get_tools_for_context(page, role, connected_providers)` — returns subset of tools
  - Page mappings: payroll → government + banking + accounting tools; leave → comms + calendar tools; employees → government (MyInfo) + HRIS tools
  - Only include tools for providers the tenant has actually connected
  - Reduces tool count from 38+ to ~10-15 per context
- Integrate with shadow agent's MCP client configuration

**Evidence**: Payroll context returns ~12 tools. Leave context returns ~8 tools. Disconnected providers excluded.

**Dependencies**: T204, T211

### T264: Per-Tenant Cost Tracker (Red Team M9)

Track API consumption costs per tenant for MyInfo, ACRA, WhatsApp, LLM calls.

**Backend:**

- Create DataFlow model `APIConsumptionLog` with fields: tenant_id, provider, endpoint, cost_cents, timestamp
- Create `src/hr_advisory/mcp_servers/cost_tracker.py` — `CostTracker`:
  - `record_cost(tenant_id, provider, cost)` — logs API cost
  - `get_monthly_cost(tenant_id)` — returns cost breakdown by provider
  - `check_cost_ceiling(tenant_id)` — warns if approaching limit
  - Configurable ceiling per tenant (default: S$50/month for free tier)
- Wire into MyInfo, ACRA, WhatsApp adapters
- Add `GET /admin/costs` and `GET /integrations/costs` endpoints

**Evidence**: MyInfo call → cost logged. Monthly report shows breakdown. Ceiling warning triggers.

**Dependencies**: T204

---

## M34: Frontend Integration UIs

Web and mobile interfaces for managing integrations, viewing connector status, and handling OAuth flows.

### T265: Integration Settings Page (Web)

Admin page for connecting/disconnecting external services.

**Frontend (apps/web):**

- Create integration settings page at `/settings/integrations`
- Sections: Accounting (Xero/QBO/Zoho/Financio), Banking (bank selection, file format preference), Government (CorpPass status), Communications (email, WhatsApp, Telegram, Slack, Teams), Calendar (Google/Outlook)
- Each section shows: connection status (connected/disconnected), last sync time, health indicator
- "Connect" buttons initiate OAuth flows
- "Disconnect" buttons with confirmation dialog
- "Test Connection" button per provider

**Evidence**: Connect to Xero via OAuth → shows "Connected" with green indicator. Disconnect → confirmation → shows "Disconnected".

**Dependencies**: T234, T226, T221

### T266: Connector Health Dashboard (Web)

Real-time dashboard showing health of all connected integrations.

**Frontend (apps/web):**

- Create dashboard widget at `/dashboard` showing integration health summary
- Full health page at `/settings/integrations/health`
- Per-connector: status (healthy/degraded/down), last successful call, error rate, circuit breaker state
- Auto-refresh every 30 seconds
- Alert banner when any connected integration is degraded

**Evidence**: All connectors show "healthy". Simulate failure → shows "degraded" with error details.

**Dependencies**: T211, T265

### T267: Government Filing Status Page (Web)

Track CPF, IR8A, IR21, OED submission history and status.

**Frontend (apps/web):**

- Create `/payroll/filings` page
- Table: submission type, period, status (pending/submitted/confirmed/failed), submitted_at, reference_id
- Detail view: saga steps with status per step
- "Retry" button for failed submissions
- Export filing history as CSV

**Evidence**: After CPF submission → filing appears in table with correct status. Saga steps visible in detail view.

**Dependencies**: T208, T209, T227

### T268: Accounting Sync Status Page (Web)

Track payroll-to-accounting journal sync status.

**Frontend (apps/web):**

- Create `/payroll/accounting-sync` page
- Per payroll run: sync status (synced/pending/failed/not connected), journal reference, provider
- Reconciliation summary: payroll total vs accounting journal total vs bank payment total
- "Sync Now" button for manual trigger
- "View Journal" link to accounting platform

**Evidence**: After payroll journal posted → shows "synced" with reference. Reconciliation shows matched/unmatched.

**Dependencies**: T243, T258

### T269: Notification Preferences Page (Web + Mobile)

Employee and admin settings for notification channels.

**Frontend (apps/web + apps/mobile):**

- Create `/settings/notifications` page
- Per notification type (payslip, leave, claims, compliance, regulatory): choose channels (email, WhatsApp, Telegram, Slack, Teams, SMS)
- Employee self-service: opt-in/out per channel
- Admin: set company defaults, override per employee
- Phone number and Telegram chat ID collection for messaging channels

**Evidence**: Employee enables WhatsApp for payslips → receives payslip notification via WhatsApp on next payroll run.

**Dependencies**: T222, T223, T244

### T270: SkillsFuture Course Browser (Web + Mobile)

Browse SkillsFuture courses, check grants, use SFC credits.

**Frontend (apps/web + apps/mobile):**

- Create `/training/skillsfuture` page
- Course search with filters (topic, duration, provider, funding)
- Course detail: description, schedule, fees, grant eligibility
- "Check My Grant" button → calculates eligible amount
- "Use SFC Credits" button → redirects to SFC payment gateway
- Employee view: browse and apply. Admin view: view team training history

**Evidence**: Search "employment law" → courses listed. Check grant → shows eligible amount. SFC payment redirects correctly.

**Dependencies**: T251

### T271: Migration Wizard (Web)

Guided import from Talenox, HReasily, or CSV.

**Frontend (apps/web):**

- Create `/settings/import` page
- Step 1: Select source (Talenox API, HReasily API, CSV upload)
- Step 2: For API sources: enter API token. For CSV: upload file
- Step 3: Preview — field mapping table, validation errors, duplicate detection
- Step 4: Confirm — shows summary (X new employees, Y updates, Z skipped)
- Step 5: Import — progress bar, success/error report

**Evidence**: Upload test CSV → preview shows mapped fields → confirm → employees created. Duplicates flagged.

**Dependencies**: T249, T250

### T272: PayNow QR Display (Web + Mobile)

Display PayNow QR codes for employee reimbursements.

**Frontend (apps/web + apps/mobile):**

- Add "Generate PayNow QR" button to approved claims
- Modal displays QR code with amount and reference
- Employee scans with banking app to receive payment
- Admin can also generate QR from claim detail page

**Evidence**: Approved claim → "Generate QR" → scannable QR displayed with correct amount.

**Dependencies**: T241

---

## M35: Integration Testing + Hardening

End-to-end testing of all integration flows, security hardening, and production readiness.

### T273: Integration Test Suite — Government APIs

Full end-to-end tests using mock APEX/CorpPass sandbox.

**Tests:**

- CPF submission saga: validate → generate → confirm → submit → acknowledge
- IR8A filing: generate data → preview → submit → acknowledge
- IR21 for departing employee trigger
- MyInfo onboarding flow
- CorpPass token refresh and expiry handling
- Idempotency: duplicate CPF submission blocked
- Circuit breaker: APEX down → fallback to CSV file generation

**Evidence**: All tests pass. Coverage >90% for government server adapters.

**Dependencies**: T227-T233

### T274: Integration Test Suite — Accounting + Banking

Full end-to-end tests for accounting journal posting and file generation.

**Tests:**

- Xero payroll journal: correct debit/credit lines, GST codes
- QBO journal entry: same verification
- Zoho journal: verify rate limit handling
- GIRO pain.001 XML: schema validation, multi-bank compatibility
- FAST file: format validation per bank
- PayNow QR: SGQR compliance, scannability
- Aspire payout: sandbox end-to-end
- Claims-to-accounting sync: automatic journal on claim approval
- Reconciliation: three-way match and discrepancy detection

**Evidence**: All tests pass. Generated files validate against bank specifications.

**Dependencies**: T234-T243

### T275: Integration Test Suite — Communications + Calendar

Full end-to-end tests for notification delivery and calendar sync.

**Tests:**

- Email: payslip delivery, bulk send, template rendering
- Telegram: notification delivery, interactive keyboard, document send
- WhatsApp: template send, delivery receipt
- Slack: channel post, interactive message, slash command
- Teams: Adaptive Card, webhook
- Google Calendar: OOO event creation from approved leave
- Outlook Calendar: same
- SMS: delivery for critical notifications

**Evidence**: All tests pass with mock adapters. Real delivery verified in staging.

**Dependencies**: T222-T248

### T276: Security Review — Integration Layer

Security audit of all MCP servers, OAuth flows, token storage, and data handling.

**Review scope:**

- OAuth token storage: verify Fernet encryption, no plaintext tokens anywhere
- CorpPass flow: verify PKCE, state parameter, nonce handling
- MyInfo: verify JWE+JWS decryption, FAPI 2.0 compliance
- Tenant isolation: cross-tenant access attempts on every tool
- PII stripping: verify LLM never sees raw NRIC, salary, bank account
- Webhook signature verification: test with forged signatures
- Rate limiting: verify per-tenant limits enforced
- Audit logging: verify no PII in logs
- Secret scanning: no API keys in code or logs

**Evidence**: Security review report with all findings addressed. Zero critical/high findings.

**Dependencies**: T273, T274, T275

### T277: Production Configuration + Deployment

Configure all MCP servers for production deployment.

**Backend:**

- Environment variables for all API keys/tokens documented in `.env.example`
- Docker Compose service definitions for each MCP server
- Health check endpoints wired to monitoring
- Log aggregation configured
- Circuit breaker thresholds tuned for production
- Rate limits configured per external API's actual limits
- S3 bucket created and configured (ap-southeast-1)
- DNS for webhook endpoints

**Evidence**: All 5 MCP servers start in Docker. Health checks pass. Monitoring dashboard shows all green.

**Dependencies**: T273, T274, T275, T276

---

## Task Summary

| Milestone                 | Tasks                    | Description                                                                                                                           |
| ------------------------- | ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------- |
| M28: Infrastructure       | T204-T212 (9 tasks)      | MCP scaffold, auth, resilience, audit, idempotency, saga, PII filter, health, testing                                                 |
| M29: Regulatory + Comms   | T213-T225 (13 tasks)     | Regulatory server, data.gov.sg, RSS/sitemap/change detection, email, Telegram, GIRO upgrade, S3                                       |
| M30: Government APIs      | T226-T233 (8 tasks)      | CorpPass, CPF APEX, IRAS AIS (IR8A/IR21/IR8S), MOM OED, MyInfo person + business                                                      |
| M31: Accounting + Banking | T234-T243 (10 tasks)     | Accounting server, Xero, QBO, Zoho, Financio, generic export, FAST, PayNow QR, Aspire, claims sync                                    |
| M32: Extended             | T244-T264 (21 tasks)     | WhatsApp, Slack, Teams, calendars, Talenox/HReasily import, SkillsFuture, ACRA, Wise, SES, SMS, webhooks, tool selector, cost tracker |
| M33: Premium + Polish     | T255-T264 (10 tasks)     | Direct bank APIs (DBS/UOB/OCBC), reconciliation, versioning, InvoiceNow, SMS, webhooks, tool selector, cost tracker                   |
| M34: Frontend UIs         | T265-T272 (8 tasks)      | Settings pages, health dashboard, filing status, accounting sync, notifications, SkillsFuture browser, migration wizard, PayNow QR    |
| M35: Testing + Deploy     | T273-T277 (5 tasks)      | Integration tests (3 suites), security review, production config                                                                      |
| **Total**                 | **T204-T277 (74 tasks)** |                                                                                                                                       |

Note: Some tasks in M32 and M33 overlap (T255-T264 appear in both due to phasing). Net unique tasks: **74**.
