# Arbor Connector Catalog — 38 Connectors

Every connector Arbor will build, organized by MCP server. Each entry includes the external API, authentication method, key operations, and implementation approach.

---

## MCP Server 1: arbor-government (12 connectors)

### G01: CPF APEX Submission

- **External API**: CPF Board e-Submit via GovTech APEX Cloud
- **Auth**: OAuth 2.1 + CorpPass
- **Operations**: Validate CPF data, submit monthly contributions, check submission status
- **Data format**: JSON
- **Prerequisite**: OSP vendor registration at onestoppayroll.gov.sg
- **Fallback**: Generate CPF e-Submit CSV file for manual portal upload (already built)

### G02: IRAS AIS IR8A

- **External API**: IRAS AIS-API 2.0 via APEX
- **Auth**: OAuth 2.1 + CorpPass
- **Operations**: Submit IR8A annual employment income, Appendix 8A (benefits in kind), check filing status
- **Data format**: JSON (API) / TXT+XML (file fallback)
- **Prerequisite**: OSP vendor registration + annual IRAS validation test (Sep-Nov)
- **Fallback**: Generate IR8A TXT file for manual upload via IRAS VSA (already built)

### G03: IRAS AIS IR21

- **External API**: IRAS AIS-API 2.0 via APEX
- **Auth**: OAuth 2.1 + CorpPass (same as G02)
- **Operations**: Submit IR21 for departing foreign employees, check filing status
- **Fallback**: Generate IR21 data file (already built)

### G04: IRAS AIS IR8S

- **External API**: IRAS AIS-API 2.0 via APEX
- **Auth**: OAuth 2.1 + CorpPass (same as G02)
- **Operations**: Submit IR8S refund/voluntary contribution data
- **Note**: New connector — not previously built even as file generation

### G05: MOM OED Submission

- **External API**: MOM Occupational Employment Dataset via APEX
- **Auth**: OAuth 2.1 + CorpPass
- **Operations**: Submit occupational and employment data for all workers
- **Prerequisite**: OSP vendor registration
- **Note**: Mandatory under Statistics Act

### G06: MyInfo Employee Onboarding

- **External API**: MyInfo v5 via Singpass
- **Auth**: OAuth 2.0 + PKCE, Singpass authorization, FAPI 2.0
- **Operations**: Retrieve verified employee data (name, NRIC, DOB, address, race, CPF history, NOA)
- **Prerequisite**: Singpass Developer Portal registration, security review
- **Deadline**: FAPI 2.0 compliance by 31 Dec 2026
- **Pricing**: First 5,000 transactions/month free, then S$1.00/transaction
- **Value**: Auto-populate all employee fields during onboarding — no manual entry

### G07: CorpPass Authorization

- **External API**: CorpPass Authorization API v2
- **Auth**: OAuth 2.1
- **Operations**: Authenticate employer for government API submissions, manage CorpPass assignments
- **Note**: Dependency for G01-G05. Not a standalone feature — authentication layer.

### G08: Data.gov.sg Public Holidays

- **External API**: data.gov.sg REST API
- **Auth**: API key (header: `x-api-key`)
- **Operations**: Fetch SG gazetted public holidays, cache locally
- **Endpoint**: `https://data.gov.sg/api/action/datastore_search?resource_id=d_149b61ad0a22f61c09dc80f2df5bbec8`
- **Rate limit**: 30 calls/10s (production key)
- **Pricing**: Free
- **Value**: Replace hardcoded public holidays with live government data

### G09: Data.gov.sg CPF Rates

- **External API**: data.gov.sg REST API
- **Auth**: API key
- **Operations**: Fetch CPF contribution rate tables, detect rate changes
- **Endpoint**: Resource ID `d_98ffa142ae0dec40391f78f81d26aca9`
- **Pricing**: Free
- **Value**: Auto-detect CPF rate changes instead of manual updates

### G10: ACRA UEN Verification

- **External API**: ACRA Business Profile API (launched Nov 2025)
- **Auth**: TBD (likely CorpPass)
- **Operations**: Verify company UEN, retrieve entity name, status, directors, SSIC codes
- **Pricing**: S$5.50 per query
- **Fallback**: data.gov.sg ACRA entity dataset (free, bulk, not real-time)

### G11: SkillsFuture SSG APIs

- **External API**: SSG Developer Portal (developer.ssg-wsg.gov.sg)
- **Auth**: API key (SSG approval required)
- **Operations**: Search courses, calculate grant eligibility, enable SFC credit payment, submit enrollment records
- **Pricing**: Free (government service)
- **Value**: Unique SG differentiator — employees can browse SkillsFuture courses, check grants, and use credits from within Arbor

### G12: MyInfo Business (Company)

- **External API**: MyInfo Business API
- **Auth**: OAuth 2.0 via CorpPass
- **Operations**: Auto-populate company profile during onboarding (UEN, name, directors, SSIC)
- **Value**: Streamlines company onboarding — no manual entry of company details

---

## MCP Server 2: arbor-accounting (5 connectors)

### A01: Xero Integration

- **External API**: Xero Accounting API
- **Auth**: OAuth 2.0 (Python SDK: `xero-python`)
- **Operations**:
  - Connect/disconnect OAuth flow
  - Get chart of accounts (`GET /Accounts`)
  - Post payroll journal (`POST /ManualJournals`) — debit salary expense, credit CPF payable, credit net pay
  - Post claims journal — approved claims as expense entries
  - Get trial balance for verification
- **Rate limits**: 60 calls/min, 5K/day per connection
- **Developer tier**: Free Starter (5 connections)

### A02: QuickBooks Online Integration

- **External API**: Intuit QBO API
- **Auth**: OAuth 2.0 via Intuit Developer Portal
- **Operations**: Same as Xero — connect, chart of accounts, payroll journal (`POST /journalentry`), claims journal
- **Rate limits**: 500 req/min, 10 concurrent
- **Developer tier**: Free Builder (500K CorePlus credits/month)

### A03: Zoho Books Integration

- **External API**: Zoho Books API v3
- **Auth**: OAuth 2.0
- **Operations**: Same as Xero — connect, chart of accounts, payroll journal (`POST /journals`), claims journal
- **Rate limits**: 2,500 calls/day per org
- **SG support**: Native GST, SG chart of accounts

### A04: Financio Integration

- **External API**: Financio (ABSS) partner API
- **Auth**: TBD (partner access required)
- **Operations**: Post payroll journal, export GL data
- **Prerequisite**: Partnership application to ABSS
- **Fallback**: Export payroll journal as text file for manual Financio import (common HRIS pattern)

### A05: Generic Accounting Export

- **No external API** — generates standard formats
- **Operations**: Export payroll data as CSV journal entry file compatible with any accounting software
- **Formats**: CSV (generic), Excel, JSON
- **Value**: Fallback for accounting platforms without API integration

---

## MCP Server 3: arbor-banking (7 connectors)

### B01: ISO 20022 GIRO File Generator

- **No external API** — generates standard file format
- **Operations**: Generate pain.001.001.03 XML file for bulk salary GIRO payments
- **Compatibility**: All SG banks (DBS, OCBC, UOB, Maybank, HSBC, Standard Chartered)
- **Value**: Universal bank file format — works everywhere via e-banking upload
- **Note**: Upgrades existing DBS fixed-width + generic CSV to ISO 20022 standard

### B02: FAST Payment File Generator

- **No external API** — generates bank-specific file formats
- **Operations**: Generate FAST payment files for same-day salary transfers
- **Formats**: UOB Bulk FAST/GIRO format (v3.04), DBS IDEAL format
- **Value**: Faster than GIRO (same-day vs T+1)

### B03: DBS RAPID Integration

- **External API**: DBS RAPID (~180 APIs)
- **Auth**: Developer token + DBS corporate banking account
- **Operations**: Initiate fund transfers, PayNow payments, check payment status
- **Prerequisite**: DBS corporate banking customer, register at dbs.com/dbsdevelopers
- **Value**: Real-time salary payments without file upload

### B04: UOB API Integration

- **External API**: UOB Developer Portal
- **Auth**: Corporate client registration
- **Operations**: PayNow, FAST, GIRO payments; real-time payment status
- **Prerequisite**: UOB corporate banking customer

### B05: OCBC Connect2OCBC Integration

- **External API**: OCBC API Store (api.ocbc.com/store)
- **Auth**: Self-serve portal registration
- **Operations**: GIRO setup, account balance, virtual accounts
- **Note**: Smaller API surface than DBS/UOB

### B06: Aspire Payout API

- **External API**: Aspire Gateway API
- **Auth**: Client ID + API key
- **Operations**: Single and bulk payouts, multi-currency, domestic + cross-border
- **Docs**: docs.gateway.aspireapp.com
- **Value**: Modern neobank API, good for SMEs. Aspire has existing partnerships with SG HRIS platforms.

### B07: PayNow QR Generator

- **No external API** — client-side QR generation using SGQR standard
- **Library**: Open-source `PaynowQR` (Node.js), PHP equivalents exist, Python implementation straightforward
- **Operations**: Generate PayNow QR code for employee reimbursements (by mobile, NRIC, or UEN)
- **Value**: Instant reimbursement — employee scans QR to receive payment. SG ending corporate checks by end 2026.

---

## MCP Server 4: arbor-communications (8 connectors)

### C01: Resend Email

- **External API**: Resend REST API
- **Auth**: API key
- **Operations**: Send transactional emails (payslip delivery, notifications, onboarding invites)
- **Pricing**: Free 3K/month, Pro $20/month for 50K
- **Value**: Primary email delivery for MVP/development

### C02: AWS SES Email

- **External API**: AWS SES REST API
- **Auth**: IAM credentials
- **Operations**: Same as Resend — transactional email at scale
- **Pricing**: $0.10/1K emails, free 62K/month from EC2
- **Value**: Cost-effective at scale, SG region (ap-southeast-1)

### C03: WhatsApp Business

- **External API**: Meta WhatsApp Cloud API
- **Auth**: OAuth 2.0 via Meta Business Suite
- **Operations**: Send template notifications (payslip ready, leave approved, compliance alert), interactive messages (approve/reject buttons)
- **Pricing**: Utility: $0.012/msg, Service (within 24hr): free
- **Prerequisite**: Meta business verification, template approval (24-48hrs)
- **Value**: Highest reach channel in SG (~80%+ penetration)

### C04: Telegram Bot

- **External API**: Telegram Bot API
- **Auth**: Bot token from @BotFather
- **Operations**: Send notifications, interactive keyboards (approve/reject), send documents (payslip PDFs), conversational shadow agent interaction
- **Pricing**: Completely free
- **Value**: Popular with SG SMEs, free, excellent developer experience. Shadow agent via Telegram is fully feasible.

### C05: Slack Bot

- **External API**: Slack API (Bot + Incoming Webhooks)
- **Auth**: OAuth 2.0 (app install), bot token
- **Operations**: Post notifications, interactive messages (leave approve/reject), slash commands (/leave-balance, /payslip)
- **Pricing**: Free (API)
- **Value**: Tech company market, rich interactive capabilities

### C06: Microsoft Teams Bot

- **External API**: Microsoft Bot Framework + Graph API
- **Auth**: Azure AD OAuth 2.0, Azure Bot Service registration
- **Operations**: Post notifications via webhook, Adaptive Cards (approve/reject), proactive messaging
- **Pricing**: Free (Azure Bot F0 tier)
- **Value**: Enterprise/MNC market in SG

### C07: Google Calendar Sync

- **External API**: Google Calendar API
- **Auth**: OAuth 2.0 (user consent) or Service Account with domain-wide delegation
- **Operations**: Create Out-of-Office events for approved leave, sync public holidays
- **Quotas**: 1M queries/day
- **Value**: Approved leave automatically appears in employee's Google Calendar

### C08: Microsoft Outlook Calendar Sync

- **External API**: Microsoft Graph API (Calendar)
- **Auth**: OAuth 2.0 via Entra ID
- **Operations**: Create Out-of-Office events, schedule meetings (performance reviews)
- **Note**: EWS deprecated Oct 2026 — must use Graph API
- **Value**: Enterprise market — leave sync to Outlook Calendar

---

## MCP Server 5: arbor-regulatory (6 connectors)

### R01: SSO Per-Act RSS Monitor

- **External API**: Singapore Statutes Online RSS feeds
- **Auth**: None
- **Operations**: Poll RSS feeds for Employment Act, CPF Act, EFMA, WICA, WSHA, ITA, ECA, CDCSA, WFA, RRA amendments
- **Frequency**: Daily
- **Note**: SSO returns 403 to some automated fetchers — may need proper User-Agent headers

### R02: Data.gov.sg Rate Monitor

- **External API**: data.gov.sg REST API
- **Auth**: API key
- **Operations**: Poll CPF contribution rate datasets, check `last_updated` field for changes
- **Frequency**: Weekly
- **Value**: Auto-detect CPF rate changes before they affect payroll calculations

### R03: MOM Sitemap Monitor

- **External API**: mom.gov.sg XML sitemap
- **Auth**: None
- **Operations**: Parse sitemap for new press releases and announcements, detect new URLs
- **Frequency**: Daily
- **Supplement**: Monitor @sgministryofmanpower Telegram channel

### R04: Web Change Detection Engine

- **External API**: None (self-hosted, uses changedetection.io or custom)
- **Auth**: N/A
- **Operations**: Monitor specific government web pages for content changes:
  - CPF Board news releases
  - IRAS newsroom
  - TAFEP guidelines
  - MOM employment practices pages
  - eGazette browse page
- **Frequency**: Daily for news, weekly for guidelines
- **Architecture**: Crawl → Diff → Classify (LLM) → Summarize → Alert

### R05: Telegram Channel Monitor

- **External API**: Telegram Bot API (read channel messages)
- **Auth**: Bot token
- **Operations**: Monitor government Telegram channels (@sgministryofmanpower, @CPFBoard, @govsg) for new posts
- **Frequency**: Real-time (webhook) or polling
- **Value**: Supplementary signal — government agencies often post on Telegram before updating websites

### R06: Regulatory Change Classifier

- **No external API** — internal LLM-based classifier
- **Operations**: When any monitor (R01-R05) detects a change:
  1. Classify: Is this change relevant to HR/employment? (filter noise)
  2. Map: Which Arbor modules are affected? (payroll, leave, CPF, foreign workers, etc.)
  3. Summarize: Plain-language summary for admin notification
  4. Queue: Create update task in regulatory_updates pipeline
- **Value**: Turns raw change detection into actionable regulatory intelligence

---

## Summary

| MCP Server          | Connectors | External APIs                | Ready to Build               | Needs Partnership/Registration                       |
| ------------------- | ---------- | ---------------------------- | ---------------------------- | ---------------------------------------------------- |
| arbor-government     | 12         | 8 real APIs + 4 data sources | G08, G09 (data.gov.sg)       | G01-G05 (OSP), G06 (Singpass), G10 (ACRA), G11 (SSG) |
| arbor-accounting     | 5          | 4 OAuth APIs + 1 file gen    | A01-A03, A05                 | A04 (Financio partner)                               |
| arbor-banking        | 7          | 4 bank APIs + 3 file/QR gen  | B01, B02, B07                | B03-B06 (bank corporate accounts)                    |
| arbor-communications | 8          | 6 APIs + 2 calendar APIs     | C01, C02, C04, C05, C07, C08 | C03 (Meta business verification)                     |
| arbor-regulatory     | 6          | 2 APIs + 4 monitoring        | All ready                    | None                                                 |
| **Total**           | **38**     |                              | **17 ready now**             | **21 need registration**                             |

**17 connectors can be built immediately** without any external partnership. The remaining 21 require registration processes (OSP, Singpass, bank corporate accounts, Meta business verification) that can proceed in parallel with development.
