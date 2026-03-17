# AITE Integration Landscape — Full Research (March 2026)

## Executive Summary

AITE has 13 deferred items from the feature parity matrix, mostly third-party integrations. The user wants ALL possible connectors built, using MCP as the integration architecture so the shadow agent can invoke them via natural language objectives.

**Key findings from research:**

1. **One-Stop Payroll (OSP) is the critical path** — CPF APEX, IRAS AIS, and MOM OED APIs all go through GovTech's APEX platform. Register as an OSP vendor once, get access to all three.
2. **MyInfo/Singpass** enables auto-populated employee onboarding from government-verified data (NRIC, address, CPF history, NOA).
3. **All 3 major SG banks have payment APIs** — DBS RAPID (180+ APIs), UOB Developer Portal, OCBC Connect2OCBC. Plus GIRO files use ISO 20022 pain.001 standard.
4. **Xero has the best accounting API** for SG (Manual Journals endpoint). QBO and Zoho Books also viable. Financio is partner-only.
5. **SSO has RSS feeds per Act** for regulatory monitoring. data.gov.sg has CPF rate datasets via API. Everything else needs change detection scraping.
6. **SkillsFuture SSG has a real Developer Portal** with Course, Grant Calculator, and SFC Credit Pay APIs — unique SG differentiator.
7. **WhatsApp (80%+ SG penetration) and Telegram (free, popular with SMEs)** are the highest-reach notification channels.
8. **No SG insurer has public APIs** — Great Eastern, AIA, NTUC Income are all file-based.
9. **PayNow QR** can be generated client-side with open-source libraries (SGQR standard). SG is ending corporate checks by end 2026.

---

## Integration Categories

### A. Singapore Government APIs

| Integration                              | API Exists?    | Auth                        | Format  | Onboarding                    | Priority        |
| ---------------------------------------- | -------------- | --------------------------- | ------- | ----------------------------- | --------------- |
| CPF APEX (e-Submit)                      | Yes            | OAuth 2.1 + CorpPass        | JSON    | High — OSP vendor             | P0              |
| IRAS AIS 2.0 (IR8A/IR21/IR8S)            | Yes            | OAuth 2.1 + CorpPass        | JSON    | High — annual validation      | P0              |
| MOM OED (employment data)                | Yes            | OAuth 2.1 + CorpPass        | JSON    | High — OSP vendor             | P1              |
| MyInfo v5 (employee onboarding)          | Yes            | OAuth 2.0 + PKCE + Singpass | JWE+JWS | Medium — FAPI 2.0 by Dec 2026 | P1              |
| Data.gov.sg (public holidays, CPF rates) | Yes            | API key                     | JSON    | Low — self-service            | P0 (quick win)  |
| CorpPass Auth API v2                     | Yes            | OAuth 2.1                   | JWT     | Bundled with OSP              | P0 (dependency) |
| ACRA Business Profile API                | Yes (Nov 2025) | TBD (likely CorpPass)       | TBD     | Medium                        | P2              |
| SSO Legislation                          | RSS only       | None                        | XML/RSS | None                          | P1              |
| MOM Work Pass check                      | No API         | N/A                         | N/A     | N/A                           | Not viable      |

**Critical path**: Register at onestoppayroll.gov.sg as an OSP vendor. This unlocks CPF, IRAS, and MOM APIs simultaneously through APEX.

### B. Accounting Platforms

| Integration       | API Quality | SG Relevance         | Key Endpoint               | Auth      | Priority |
| ----------------- | ----------- | -------------------- | -------------------------- | --------- | -------- |
| Xero              | Excellent   | High (dominant SG)   | `POST /ManualJournals`     | OAuth 2.0 | P0       |
| QuickBooks Online | Good        | Medium-High          | `POST /journalentry`       | OAuth 2.0 | P1       |
| Zoho Books        | Good        | High (SG GST native) | `POST /journals`           | OAuth 2.0 | P1       |
| Financio          | Private     | High (SG-native)     | Partner-only API           | TBD       | P2       |
| MYOB              | Good        | Low (AU/NZ)          | `POST /JournalTransaction` | OAuth 2.0 | P3       |

**Xero specifics**: No SG payroll — use Manual Journals for payroll posting. 60 calls/min, 5K/day. Python SDK: `xero-python`. Developer program: free Starter tier with 5 connections.

### C. Banking / Payments

| Integration           | API Quality           | Capabilities                      | Auth                          | Priority |
| --------------------- | --------------------- | --------------------------------- | ----------------------------- | -------- |
| DBS RAPID             | Excellent (180+ APIs) | Fund transfer, GIRO, PayNow, bulk | Dev token + corporate banking | P0       |
| UOB API               | Good                  | PayNow, FAST, GIRO, bulk          | Developer portal + corporate  | P1       |
| OCBC Connect2OCBC     | Moderate              | GIRO, balance, virtual accounts   | Self-serve portal             | P1       |
| Aspire                | Good (REST)           | Payout API, bulk payments         | Client ID + API key           | P1       |
| GIRO File (ISO 20022) | Standard              | pain.001.001.03 XML               | File upload                   | P0       |
| PayNow QR             | Open-source           | QR generation (SGQR standard)     | None for QR gen               | P1       |
| FAST Payment File     | Standard              | Bank-specific formats             | File upload                   | P1       |

**GIRO file format**: All SG banks accept ISO 20022 pain.001.001.03 XML. This is the standard for bulk salary payments.

### D. Communication / Notifications

| Integration        | API Quality | SG Reach             | Cost                            | Priority |
| ------------------ | ----------- | -------------------- | ------------------------------- | -------- |
| Email (Resend/SES) | Excellent   | Universal            | Resend free 3K/mo; SES $0.10/1K | P0       |
| WhatsApp Cloud API | Good        | ~80%+ SG penetration | Utility: $0.012/msg             | P1       |
| Telegram Bot API   | Excellent   | High (SMEs)          | Free                            | P1       |
| Slack API          | Excellent   | Tech companies       | Free (API)                      | P2       |
| MS Teams Bot       | Good        | Enterprise/MNC       | Free (Azure Bot F0)             | P2       |

### E. Productivity / Calendar

| Integration         | API Quality | SG Relevance         | Key Use                           | Priority |
| ------------------- | ----------- | -------------------- | --------------------------------- | -------- |
| Google Calendar API | Excellent   | High (SMEs/startups) | Leave-to-calendar sync            | P1       |
| Microsoft Graph API | Excellent   | High (enterprise)    | Leave-to-calendar, directory sync | P1       |
| Zoom API            | Good        | Medium               | Performance review scheduling     | P3       |

### F. Document / Storage

| Integration          | API Quality | SG Region       | Priority |
| -------------------- | ----------- | --------------- | -------- |
| AWS S3               | Excellent   | ap-southeast-1  | P0       |
| Google Cloud Storage | Excellent   | asia-southeast1 | P2 (alt) |

### G. HRIS Migration (Data Import)

| Platform    | API Quality                | Notes                            | Priority      |
| ----------- | -------------------------- | -------------------------------- | ------------- |
| Talenox     | Good (public REST + OAuth) | Public docs at talenox.github.io | P1            |
| HReasily    | Emerging (unified API)     | Launched 2025                    | P2            |
| Payboy      | Private/partner-only       | Integration via partnership      | P2            |
| Swingvy     | No API                     | No programmatic access           | P3 (CSV only) |
| JustLogin   | No public API              | Pre-built integrations only      | P3 (CSV only) |
| Info-Tech   | No public API              | Internal integrations only       | P3 (CSV only) |
| Generic CSV | Built (existing)           | Already implemented in AITE      | Done          |

### H. Regulatory Monitoring

| Source                | Official Feed?    | Method                                 | Frequency |
| --------------------- | ----------------- | -------------------------------------- | --------- |
| SSO (per-Act RSS)     | Yes — RSS feeds   | RSS parser                             | Daily     |
| data.gov.sg CPF rates | Yes — REST API    | API poll (check `last_updated`)        | Weekly    |
| MOM Newsroom          | XML sitemap only  | Sitemap parser + change detection      | Daily     |
| CPF Board news        | Telegram only     | Change detection + Telegram monitoring | Daily     |
| IRAS updates          | Email alerts only | Change detection                       | Weekly    |
| TAFEP/TAL             | None              | Change detection                       | Weekly    |
| eGazette              | None              | Change detection                       | Weekly    |

### I. Training / Learning

| Integration       | API Quality              | SG Relevance                         | Priority |
| ----------------- | ------------------------ | ------------------------------------ | -------- |
| SkillsFuture SSG  | Good (official portal)   | Very high — unique SG differentiator | P1       |
| LinkedIn Learning | Restricted (partnership) | Medium (enterprise only)             | P3       |
| Coursera          | Restricted (enterprise)  | Low                                  | P3       |

### J. Insurance / Benefits

| Provider      | API  | Notes           | Priority |
| ------------- | ---- | --------------- | -------- |
| Great Eastern | None | File-based only | P4       |
| AIA           | None | File-based only | P4       |
| NTUC Income   | None | File-based only | P4       |

**Approach**: Build clean CSV/Excel export for insurance enrollment data. Partner with insurtech middleware (CXA/Aon, CoverGo) if API-level integration needed later.

---

## Deferred Items Resolution

Mapping the 13 deferred items to concrete integration approaches:

| #   | Deferred Feature            | Resolution                                 | Connector Type  |
| --- | --------------------------- | ------------------------------------------ | --------------- |
| 16  | ESPP                        | Skip — no SG SME demand                    | N/A             |
| 26  | Platform Workers CPF (PCTS) | Skip — gig worker scheme, low demand       | N/A             |
| 28  | CPF APEX submission         | Build — OSP vendor registration → APEX API | MCP: government |
| 30  | IR8A AIS direct submission  | Build — IRAS AIS-API 2.0 via APEX          | MCP: government |
| 32  | Appendix 8B (stock options) | Skip — ESPP deferred                       | N/A             |
| 34  | IR8S (refund/voluntary)     | Build — same IRAS AIS API endpoint         | MCP: government |
| 36  | Bank FAST payment file      | Build — pain.001 XML + bank APIs           | MCP: banking    |
| 45  | Xero integration            | Build — Manual Journals endpoint           | MCP: accounting |
| 46  | QuickBooks integration      | Build — Journal Entry endpoint             | MCP: accounting |
| 47  | Financio integration        | Build — partner API (request access)       | MCP: accounting |
| 85  | Claims accounting sync      | Build — routes through Xero/QBO/Zoho       | MCP: accounting |
| N1  | Aspire bank file            | Build — Aspire Payout API                  | MCP: banking    |
| N2  | 1-click IR8A AIS            | Build — same as #30                        | MCP: government |

**Net result**: 3 items genuinely skipped (ESPP, PCTS, Appendix 8B). 10 items resolved via MCP connectors.

---

## Sources

All source URLs documented in individual research agent outputs (government APIs, accounting/banking, communications, regulatory monitoring research files).
