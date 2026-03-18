# Red Team Report — Integration Analysis

## Severity Summary

- **6 Critical** — Would block launch or create legal/financial liability
- **9 High** — Would cause significant user pain or competitive vulnerability
- **12 Medium** — Should be addressed but will not block launch

---

## CRITICAL Findings

### C1: No testing strategy for any connector

The entire connector catalog contains zero mentions of testing, sandbox, mock, or stub. CPF APEX, IRAS AIS, and bank APIs all have test/UAT environments that require separate registration. Without a testing strategy, the first real submission will be on live government systems with real employer liability.

**Recommendation**: Add a testing tier document — sandbox availability per connector, mock adapter strategy, contract testing approach, parallel-run framework.

### C2: OSP vendor registration timeline is unquantified

OSP registration requires: (a) registered software vendor status, (b) GovTech security assessment, (c) APEX onboarding with PKI certificate, (d) UAT in sandbox, (e) production credentials. This typically takes **3-6 months**. Phase 3 has no timeline buffer.

**Recommendation**: Start OSP registration immediately, in parallel with Phase 1. Document as a gated dependency with monthly checkpoints.

### C3: Double-submission / idempotency risk on government APIs

If the shadow agent retries (network timeout, user clicks again, circuit breaker recovery), a second CPF submission could create duplicate employer contributions. CPF Board does not auto-deduplicate. The architecture has zero mention of idempotency keys.

**Recommendation**: Add a `submission_ledger` table tracking (tenant_id, submission_type, period, status, external_reference_id). Block duplicate submissions at MCP server level.

### C4: No error recovery for partially completed multi-step objectives

If step 5 of 6 fails after the human confirmed in step 4, the user thinks it submitted. No saga patterns or compensation logic exist.

**Recommendation**: Implement a saga/workflow state machine for multi-step objectives. Each step must be recoverable. Log saga state to database, not agent memory.

### C5: PDPA cross-border data transfer gap for LLM API calls

The shadow agent routes employee salary data, NRIC, and CPF amounts through offshore LLM providers (OpenAI/Anthropic). Under PDPA Section 26, cross-border transfer of PII requires consent or contractual safeguards. Not addressed anywhere.

**Recommendation**: Strip PII before sending to LLM, use SG-region LLM deployment, or add explicit PDPA consent in employee onboarding. Document as first-class architectural concern.

### C6: Bank API access requires per-tenant corporate banking relationships

DBS RAPID, UOB, OCBC all require the **employer** (not Arbor) to have a corporate account AND authorize Arbor. This is per-tenant, per-bank onboarding — not a one-time Arbor registration.

**Recommendation**: Prioritize file-based approach (GIRO/FAST files) as primary. Position direct bank API as premium feature with guided onboarding.

---

## HIGH Findings

### H1: Missing connector — Wise (cross-border payroll)

Many SG SMEs pay foreign contractors in Malaysia, Philippines, India. Wise Business API is well-documented and dominant for this.

### H2: Missing connector — InvoiceNow / Peppol e-invoicing

SG mandating InvoiceNow for GST-registered businesses in phases from 2025.

### H3: Zoho Books rate limit dangerously low (2,500/day)

A company with 200 employees could hit the limit in a single payroll cycle.

### H4: WhatsApp template approval is a blocking dependency

Template rejection is common, resubmission required. Financial data in payslip templates may violate Meta's commerce policy.

### H5: MyInfo FAPI 2.0 deadline — build on v5/FAPI 2.0 from start

Building on current OAuth and migrating later wastes effort.

### H6: Change detection scraping is legally and technically fragile

Computer Misuse Act applies. Government sites block automated access.

### H7: No connector versioning or deprecation strategy

38 connectors evolving at different rates with no version registry.

### H8: Missing — Payroll reconciliation loop (three-way: payroll, bank, accounting)

Key differentiator over competitors who leave reconciliation manual.

### H9: ACRA API S$5.50/query creates cost leak at scale

10,000 companies = S$55,000 for verification alone.

---

## MEDIUM Findings

- M1: Missing MAS DPMS / Direct Debit connector
- M2: No offline/degradation UX for external API failures
- M3: CorpPass token refresh during off-hours
- M4: No data migration path design (fundamentally different from runtime connectors)
- M5: Xero 5-connection limit on free tier
- M6: SMS not included as notification channel
- M7: No webhook receivers for inbound events from external APIs
- M8: Shadow agent tool count (38+) may exceed LLM context window efficiency
- M9: No cost monitoring or per-tenant billing for API consumption
- M10: SSG API approval is not self-service and historically slow
- M11: Financio/ABSS partner API is likely vapor — deprioritize to P3
- M12: No connector health monitoring or SLA tracking

---

## Decision Points for Stakeholder

1. **Phase order**: Should government APIs (regulatory intelligence) move ahead of accounting (convenience)?
2. **PDPA consent model**: How does LLM processing of employee PII work under PDPA?
3. **OSP registration entity**: Does Arbor have the corporate structure GovTech requires?
4. **Bank integration model**: File-based only for first 12 months, or direct API?
5. **Scope**: 38 connectors or focus on 20 deep, well-tested ones?
6. **Cost ceiling**: What's the per-tenant API cost at steady state?

---

## Integration Blind Spots

- Some HRIS platforms already have exclusive banking integrations (e.g., Aspire)
- HRIS platforms could restrict API access if they detect competitor migration
- IRAS AIS validation window is Sep-Nov — missing it means waiting a full year for March filing
- Incumbent platforms could release connector APIs to let advisory tools work alongside them

---

## Immediate Actions (This Week)

1. Start OSP vendor registration with GovTech
2. Start Xero Partner Program application
3. Start SSG developer application
4. Write testing strategy document
5. Resolve PDPA cross-border LLM question
6. Design idempotency/saga infrastructure
