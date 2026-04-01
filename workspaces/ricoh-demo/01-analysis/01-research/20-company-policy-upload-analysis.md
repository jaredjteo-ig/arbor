# Company Policy Upload & Integration -- Deep Analysis

**Date**: 2026-03-31
**Analyst**: deep-analyst
**Complexity Score**: 26/30 (COMPLEX)
**Recommendation**: Phase the implementation into 3 stages. Do not attempt a single release.

---

## Executive Summary

Company policy upload is a high-value, high-complexity feature that touches five independent subsystems (DataFlow models, file storage, KB retrieval, advisory engine, compliance engine) and introduces a new class of content -- employer-authored, unstructured, legally significant text -- into a pipeline currently designed exclusively for curated statutory provisions. The primary risk is not technical difficulty but **trust contamination**: company-uploaded policies entering the advisory engine's context without proper authority-level separation, causing the LLM to conflate company policy with statutory requirements. A phased approach is essential, starting with CRUD and manual text entry (Phase 1), then file upload with parsing (Phase 2), then advisory/compliance integration (Phase 3).

---

## 1. Complexity Assessment

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| **Governance** | 8/10 | Company policies introduce employer-authored content that can contradict statutory minimums. Authority levels, tenant isolation, and PDPA obligations for policy documents (which may contain PII references) all apply. |
| **Legal** | 9/10 | Policies may contain clauses below statutory minimums (illegal but common in practice). The system must detect and flag these without providing legal advice on their enforceability. Integration with the compliance engine creates regulatory exposure if the system incorrectly validates a non-compliant policy. |
| **Strategic** | 9/10 | This is the feature that moves Arbor from "employment law reference tool" to "company-specific HR platform." It is the foundation for enterprise adoption. If done poorly (e.g., company policies override statutory provisions in advisory answers), it destroys platform credibility. |
| **Total** | **26/30** | **COMPLEX** -- requires full analysis chain, phased implementation, and review at each gate. |

---

## 2. Risk Register

### 2.1 Critical Risks (Likelihood x Impact = CRITICAL)

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|------------|--------|------------|
| R1 | **Trust contamination**: LLM treats company policy text as equivalent to statutory provisions, producing answers like "your company policy says X" without distinguishing it from "the law requires Y" | HIGH | CRITICAL | Implement strict `authority_level` separation. Company policies get `authority_level = "company_policy"`, never `"statute"` or `"guideline"`. The advisory engine's system prompt must explicitly instruct: "Company policies are supplementary. Always state the statutory position first, then the company position." |
| R2 | **Below-minimum policy ingestion**: Company uploads a leave policy granting 5 days annual leave (below EA s.88 minimum of 7 days). The system presents this as the employee's entitlement. | HIGH | CRITICAL | Phase 3 (compliance integration) must include a statutory floor check at upload time. When a company policy maps to a statutory domain, compare key values against known minimums. Flag but do not block -- the company may be uploading the policy for audit purposes. Advisory engine must ALWAYS cite the statutory minimum alongside the company figure. |
| R3 | **Stale company policies vs updated statutory requirements**: Statutory change (e.g., paternity leave increase effective 1 Jan 2025) makes a company policy non-compliant, but the system continues to serve the old company policy | MEDIUM | CRITICAL | Implement `next_review_date` on company policies. Compliance engine periodic check compares company policy effective dates against statutory provision effective dates. Alert when a statutory provision is newer than the company policy in the same domain. |
| R4 | **Tenant data leakage**: Company A's policies appear in Company B's advisory responses due to missing or insufficient `company_id` scoping in KB retrieval | LOW | CRITICAL | Company policies MUST be stored in a company-scoped table (already the case with `CompanyPolicy.company_id`). The retrieval path into the advisory engine MUST filter by `company_id` at query time, not post-retrieval. Add integration test: query from company A must never return company B policies. |

### 2.2 Major Risks (Likelihood x Impact = MAJOR)

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|------------|--------|------------|
| R5 | **PDF/DOCX parsing quality**: Uploaded policy documents contain tables, headers, footers, page numbers, images, and legal formatting that produce garbage text when naively extracted | HIGH | MAJOR | Use a robust extraction pipeline: `pdfplumber` or `PyMuPDF` for PDFs, `python-docx` for DOCX. Strip headers/footers/page numbers. Provide a preview step where the admin can review extracted text before saving. Never auto-ingest without human confirmation. |
| R6 | **Policy versioning conflicts**: Admin uploads v2 of a policy but doesn't deactivate v1. Employees see contradictory content. Advisory engine retrieves both versions. | MEDIUM | MAJOR | Implement version chain: when a new version of the same `policy_type` is created, automatically deactivate the previous version (set `is_active = False`, record `superseded_by_id`). Only active versions enter the advisory pipeline. Keep version history accessible in the admin UI. |
| R7 | **Unstructured text retrieval accuracy**: Company policies are free-form prose. Keyword search (the current KB search method) will have poor recall for nuanced questions like "can I work from home on Fridays?" against a 20-page employee handbook | MEDIUM | MAJOR | Phase 2: Chunk company policies into paragraphs or sections during ingestion. Generate embeddings for each chunk (using existing `EmbeddingPipeline`). Phase 3: Add a `search_company_policies` tool to the advisory engine that performs semantic search against company policy chunks. |
| R8 | **PDPA exposure in uploaded documents**: Policy documents may contain employee names, NRIC numbers, salary bands, or disciplinary procedures naming specific individuals | MEDIUM | MAJOR | Scan uploaded content for PDPA-sensitive patterns (NRIC regex, email addresses, phone numbers) at upload time. Warn the admin. Do not block upload but flag for review. Never include raw policy text containing PII in advisory responses -- serve sanitised summaries instead. |
| R9 | **Oversize documents**: Admin uploads a 200-page employee handbook as a single policy. Text extraction produces 100K+ tokens that cannot fit in LLM context. | MEDIUM | MAJOR | Enforce per-document size limits (e.g., 50 pages / 5MB for policy documents). During ingestion, chunk into sections. At retrieval time, return only the top-N most relevant chunks, not the entire document. |

### 2.3 Significant Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|------------|--------|------------|
| R10 | **Conflicting policies**: Two active policies in the same company cover the same topic (e.g., a "Leave Policy" and an "Employee Handbook" both specify annual leave entitlements, with different numbers) | MEDIUM | SIGNIFICANT | Add `policy_type` uniqueness constraint per company for structured policy types. For free-form policies, implement overlap detection at upload time by comparing topic tags. Advisory engine should cite the most recent effective date when conflicts exist. |
| R11 | **No acknowledgment trail**: Company uploads a new policy but has no record of which employees have read it. Legal exposure if a dispute arises. | LOW | SIGNIFICANT | Phase 2: Add `PolicyAcknowledgment` model (employee_id, policy_id, acknowledged_at, ip_address). Send notification to employees when a new policy is published. Track acknowledgment status on the admin dashboard. |
| R12 | **Advisory engine latency increase**: Adding a second retrieval step (search KB provisions + search company policies) doubles the pre-LLM retrieval time | MEDIUM | SIGNIFICANT | Run statutory KB search and company policy search in parallel. Cap company policy search at 3 chunks. Monitor p95 latency and set a 2-second timeout on company policy retrieval with graceful degradation (statutory-only answer if company policies time out). |
| R13 | **File storage costs and cleanup**: Uploaded PDF/DOCX files accumulate on disk or S3 without lifecycle management | LOW | SIGNIFICANT | Store uploaded files with a reference count. When a policy version is hard-deleted (if ever), clean up the associated file. For S3: use lifecycle rules to move old versions to Glacier after 1 year. For local: implement a periodic cleanup job. |

### 2.4 Minor Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|------------|--------|------------|
| R14 | **Encoding issues in uploaded documents**: PDF contains non-UTF-8 characters (e.g., CJK text in a Thailand deployment) that break text extraction or storage | LOW | MINOR | Normalise all extracted text to UTF-8 with replacement characters. Log warnings for lossy conversions. |
| R15 | **Admin accidentally deletes the only active policy**: No undo mechanism | LOW | MINOR | Implement soft delete (already supported by DataFlow). Provide a "Restore" option in the admin UI for 30 days. |

---

## 3. Architecture Analysis

### 3.1 Current Architecture (Advisory Query Flow)

```
User Question
    |
    v
[Input Sanitisation] --> [Rate Limit] --> [Guardrails Screening]
    |
    v
[Advisory Engine (LLM + Function Calling)]
    |                       |
    v                       v
[search_kb tool]        [calculator tools]
    |                       |
    v                       v
[KB: Provisions table]  [Deterministic calculators]
(statutory only)        (CPF, leave, overtime, etc.)
    |
    v
[LLM generates response with statutory citations]
    |
    v
[Output Screening] --> [Citation Validation] --> [Disclaimer] --> [Response]
```

### 3.2 Proposed Architecture (With Company Policies)

```
User Question
    |
    v
[Input Sanitisation] --> [Rate Limit] --> [Guardrails Screening]
    |
    v
[Advisory Engine (LLM + Function Calling)]
    |                       |                       |
    v                       v                       v
[search_kb tool]        [search_company_policies]  [calculator tools]
(statutory)             (NEW tool)                 (deterministic)
    |                       |                       |
    v                       v                       v
[KB: Provisions]       [CompanyPolicy +             [Calculators]
                        PolicyChunk tables]
                        (filtered by company_id)
    |
    v
[LLM generates response]
--> MUST separate: "Under the Employment Act, ..." vs "Your company policy provides ..."
    |
    v
[Output Screening] --> [Citation Validation] --> [Statutory Floor Check] --> [Disclaimer] --> [Response]
                                                  (NEW step)
```

### 3.3 Key Architecture Decisions

**Decision 1: Separate table vs KB Provision table for company policies?**

- **Option A**: Store company policies in the existing `Provision` table with `authority_level = "company_policy"` and a new `company_id` field.
  - Pro: Unified search. Existing KB search works.
  - Con: Requires modifying a core model. Every KB query must now filter by company_id OR authority_level. Risk of cross-tenant leakage is structural.

- **Option B**: Keep company policies in the existing `CompanyPolicy` table with a new `PolicyChunk` table for searchable chunks. Separate retrieval tool in the advisory engine.
  - Pro: Clean separation of concerns. Tenant isolation is inherent (CompanyPolicy already has company_id). No risk of statutory/company policy mixing at the data layer.
  - Con: Two retrieval paths. Slightly more complex advisory engine.

- **RECOMMENDATION: Option B.** The risk of trust contamination (R1) and tenant data leakage (R4) both argue for strict separation. The advisory engine already supports multiple tools; adding `search_company_policies` is straightforward.

**Decision 2: Where does text extraction happen?**

- **Option A**: Synchronous, during the upload HTTP request.
  - Pro: Simple. Admin sees extracted text immediately for review.
  - Con: Large PDFs block the request. 30-second timeout risk.

- **Option B**: Async background job triggered after upload. Admin sees "Processing..." status.
  - Pro: Non-blocking. Can handle large documents.
  - Con: More infrastructure (task queue). Admin must return later to review.

- **RECOMMENDATION: Option A for MVP (Phase 2), with a size limit (5MB / 50 pages).** The target user is an SME admin uploading a 5-10 page policy document, not a 200-page legal brief. If documents regularly exceed the limit, add async processing in a later phase.

**Decision 3: How does the advisory engine decide when to search company policies?**

- **Option A**: Always search company policies for every query (if company_id is available).
  - Pro: Never misses relevant company policy context.
  - Con: Unnecessary latency for purely statutory questions. Noise in results.

- **Option B**: LLM decides via function calling (add `search_company_policies` as a tool).
  - Pro: LLM only calls when relevant. Fits existing autonomous engine architecture.
  - Con: LLM may not know to call it. Needs clear tool description.

- **Option C**: Keyword heuristic decides (if query mentions "company", "our policy", "my entitlement", etc., also search company policies).
  - Pro: Deterministic, fast.
  - Con: Brittle. Misses implicit queries like "how many leave days do I get?"

- **RECOMMENDATION: Option B.** The advisory engine already uses LLM function calling for `search_kb`, `calculate_cpf`, etc. Adding `search_company_policies` as another tool is architecturally consistent. The tool description should instruct: "Search the user's company-specific policies. Call this when the question relates to internal company benefits, entitlements, or procedures that may differ from statutory minimums."

---

## 4. Cross-Reference Audit

### 4.1 Files Directly Affected by This Feature

| File | Impact | Notes |
|------|--------|-------|
| `/src/hr_advisory/models/company_user.py` | **MODIFY** | `CompanyPolicy` model needs new fields: `source_file_id`, `version`, `superseded_by_id`, `uploaded_by`, `policy_category`. New model: `PolicyChunk` (for searchable segments). New model: `PolicyAcknowledgment`. |
| `/src/hr_advisory/api/routers/employees.py` | **MODIFY** | Add CRUD endpoints: POST/PUT/DELETE for company policies. Currently only has GET `/policies`. |
| `/src/hr_advisory/agents/advisory_engine.py` | **MODIFY** | Add `search_company_policies` tool definition and execution handler. Modify system prompt to include company policy handling instructions. |
| `/src/hr_advisory/api/routers/compliance.py` | **MODIFY** | Add company policy vs statutory floor comparison. Currently only checks KB provision coverage. |
| `/src/hr_advisory/kb/embeddings.py` | **MODIFY** | Extend to generate embeddings for `PolicyChunk` records (not just `Provision`). |
| `/src/hr_advisory/services/company_seeding.py` | **REVIEW** | Default policies seeding should set `version = 1` and new fields. |
| `/apps/web/src/app/(dashboard)/policies/page.tsx` | **REWRITE** | Transform from read-only display to full CRUD interface with upload, edit, version history, and acknowledgment tracking. |
| `/apps/web/src/services/api/employees.ts` | **MODIFY** | Add API methods for policy CRUD, file upload, acknowledgment. |

### 4.2 Inconsistencies Found

1. **Frontend `CompanyPolicy` type mismatch**: The TypeScript interface (`CompanyPolicy` in `employees.ts`) has `content: string[]` (array of paragraphs), but the backend model stores `content: str` (single string). The frontend policies page hardcodes `STANDARD_POLICIES` with pre-split content arrays. The API endpoint at `GET /employees/policies` returns the raw `content` string, not an array. The frontend `mapApiPolicyToSection` would need to handle both formats.

2. **No dedicated policies router**: Policy endpoints are buried inside the `employees.py` router (2700+ lines). CRUD operations for company policies should have their own router (`/api/policies/`) to avoid further bloating the employees router.

3. **Compliance engine is KB-only**: The compliance engine at `/src/hr_advisory/api/routers/compliance.py` exclusively queries KB provisions (statutory). It has no awareness of company policies. The gap analysis endpoint reports missing statutory coverage, not whether company policies meet statutory requirements.

4. **Advisory engine `get_company_context` tool returns company profile, not policies**: The existing `get_company_context` tool fetches sector, headcount, and compliance status. It does not retrieve company policies. This is a separate concern and should remain separate (company profile vs company policies).

---

## 5. Failure Point Analysis (5-Why Framework)

### Failure Scenario: "Advisory engine tells employee they get 5 days leave when the law guarantees 7"

1. **Why?** The advisory engine cited the company policy (5 days) without citing the statutory minimum (7 days).
2. **Why?** The LLM treated company policy text as the authoritative source for leave entitlement.
3. **Why?** Company policy chunks were returned by `search_company_policies` and the LLM did not also call `search_kb` for the statutory position.
4. **Why?** The system prompt did not enforce the rule: "For any entitlement question, ALWAYS search statutory provisions first, then company policies."
5. **Why?** The integration was designed as "additive context" without a mandatory statutory-first constraint.

**Root Cause**: Missing architectural invariant that statutory provisions are always primary and company policies are always supplementary.

**Fix**: The advisory engine system prompt must include an explicit, non-negotiable instruction:

> "STATUTORY PRIMACY RULE: For any question about employee entitlements, obligations, or rights, you MUST search the statutory knowledge base (search_kb) FIRST. If a company policy provides LESS than the statutory minimum, you MUST state: 'Note: Your company policy states [X], but the statutory minimum under [Act] is [Y]. The statutory minimum applies.' Never present a company policy entitlement that is below the statutory floor without this warning."

Additionally, the output screening step should detect responses that cite company policy entitlements below known statutory minimums and inject a disclaimer.

### Failure Scenario: "Company B's WFH policy appears in Company A's advisory response"

1. **Why?** The advisory response included a company policy belonging to a different company.
2. **Why?** The `search_company_policies` tool returned policies from the wrong company.
3. **Why?** The company_id filter was not applied correctly in the policy chunk search.
4. **Why?** The tool received a `company_id` parameter but the underlying query did not enforce it as a mandatory filter.
5. **Why?** No integration test verified cross-tenant isolation for the company policy retrieval path.

**Root Cause**: Missing tenant isolation enforcement in the new retrieval path.

**Fix**: The `search_company_policies` tool implementation must:
- Accept `company_id` as a required parameter (injected by the advisory router, not provided by the LLM).
- Apply `company_id` as a DataFlow filter, not a post-retrieval filter.
- Include an assertion: `assert all(chunk["company_id"] == company_id for chunk in results)`.
- Add an integration test that creates policies for two companies and verifies strict isolation.

---

## 6. Integration Points

### 6.1 Advisory Engine Integration (Phase 3)

**New tool: `search_company_policies`**

```
{
  "name": "search_company_policies",
  "description": "Search the user's company-specific internal policies (leave policy, employee handbook, FWA guidelines, etc.). Returns relevant excerpts from company-uploaded or company-configured policies. Call this when the question relates to internal company benefits, entitlements, or procedures. ALWAYS also call search_kb for the statutory position.",
  "parameters": {
    "query": { "type": "string", "description": "Search query for company policies" }
  }
}
```

The `company_id` is NOT a tool parameter -- it is injected by the advisory router from the authenticated user's JWT, preventing the LLM from querying other companies' policies.

**Integration in `_execute_tool_call`**: New branch handling `search_company_policies` that:
1. Retrieves `company_id` from the engine's context (passed in at `.run()` call).
2. Queries `PolicyChunk` records filtered by `company_id` and ranked by relevance.
3. Returns results with explicit `"source": "company_policy"` tagging.

### 6.2 Compliance Engine Integration (Phase 3)

**New endpoint: `POST /compliance/policy-check`**

Accepts a `company_id` and compares active company policies against statutory provisions:
- For each company policy with a mapped `statutory_domain` (e.g., leave policy maps to "employment_act"):
  - Retrieve statutory provisions for that domain.
  - Compare key extractable values (e.g., annual leave days, notice periods) against statutory minimums.
  - Return findings: `compliant` (meets or exceeds), `below_minimum` (below statutory floor), `unverifiable` (unable to extract comparable values from free-text policy).

### 6.3 Notification Integration (Phase 2)

When a new policy version is published:
1. All active employees in the company receive a notification.
2. Notification links to the policies page.
3. Acknowledgment status is tracked per employee.

### 6.4 Employee Self-Service Integration (Phase 1)

- Employees see company policies on the existing `/policies` page.
- Policies fetched from API show company-specific content (already partially implemented).
- Admin users see edit/upload controls; employees see read-only + acknowledge.

---

## 7. Data Model Changes

### 7.1 Modified: `CompanyPolicy`

New fields to add:

| Field | Type | Purpose |
|-------|------|---------|
| `version` | `int` (default 1) | Version number for change tracking |
| `superseded_by_id` | `Optional[int]` | Points to the newer version |
| `uploaded_by` | `int` (default 0) | User ID of the admin who created/uploaded |
| `source_file_path` | `Optional[str]` | Path to the uploaded PDF/DOCX (if file-based) |
| `source_file_name` | `Optional[str]` | Original filename for display |
| `statutory_domain` | `Optional[str]` | Links to a KB domain (e.g., "employment_act") for compliance mapping |
| `policy_category` | `str` (default "") | Broader categorisation (e.g., "benefits", "conduct", "safety", "data_security") |
| `requires_acknowledgment` | `bool` (default False) | Whether employees must acknowledge this policy |
| `published_at` | `Optional[str]` | When the policy was made visible to employees |

### 7.2 New Model: `PolicyChunk`

For searchable segments of company policies (enables semantic search over long documents).

| Field | Type | Purpose |
|-------|------|---------|
| `company_id` | `int` | Tenant isolation |
| `policy_id` | `int` | FK to CompanyPolicy |
| `chunk_index` | `int` | Order within the policy |
| `chunk_text` | `str` | The text content of this chunk |
| `section_heading` | `Optional[str]` | Extracted section heading, if any |
| `embedding` | `Optional[str]` | JSON-serialised embedding vector |

### 7.3 New Model: `PolicyAcknowledgment`

| Field | Type | Purpose |
|-------|------|---------|
| `company_id` | `int` | Tenant isolation |
| `policy_id` | `int` | FK to CompanyPolicy |
| `employee_id` | `int` | FK to Employee |
| `acknowledged_at` | `str` | ISO timestamp |
| `ip_address` | `Optional[str]` | For audit trail |

---

## 8. Implementation Roadmap

### Phase 1: CRUD + Manual Text Entry (MVP)
**Effort**: 3-5 days | **Risk**: LOW

1. Add new fields to `CompanyPolicy` model (version, superseded_by_id, uploaded_by, statutory_domain, policy_category, requires_acknowledgment, published_at).
2. Create dedicated `/api/policies/` router with:
   - `GET /api/policies/` -- list company policies (scoped by company_id)
   - `POST /api/policies/` -- create policy (manual text entry)
   - `GET /api/policies/{id}` -- get single policy
   - `PUT /api/policies/{id}` -- update policy (creates new version, supersedes old)
   - `DELETE /api/policies/{id}` -- soft delete
   - `GET /api/policies/{id}/versions` -- version history
3. Rewrite frontend policies page: admin CRUD interface, employee read-only view.
4. Update company seeding to use new fields.
5. Add role-based access: owner/hr_manager can create/edit/delete; employees can read.

**Success Criteria**:
- Admin can create, edit, and delete company policies through the UI.
- Version history is preserved (editing creates a new version, old version is marked superseded).
- Employees see only active policies for their company.
- Tenant isolation test passes: Company A admin cannot see or modify Company B policies.

### Phase 2: File Upload + Parsing + Acknowledgment
**Effort**: 5-7 days | **Risk**: MEDIUM

1. Add file upload endpoint: `POST /api/policies/upload` (multipart/form-data, PDF/DOCX).
2. Implement text extraction pipeline (pdfplumber for PDF, python-docx for DOCX).
3. Add preview step: extracted text shown to admin for review before saving.
4. Create `PolicyChunk` model and chunking logic (split by headings/paragraphs, max 500 tokens per chunk).
5. Generate embeddings for chunks using existing `EmbeddingPipeline`.
6. Add `PolicyAcknowledgment` model and endpoints.
7. Add notification trigger when policy is published.
8. Implement PDPA content scanning (warn on PII patterns in uploaded text).

**Success Criteria**:
- Admin can upload a 10-page PDF, review extracted text, and save as a policy.
- Policy chunks are created and searchable.
- Employees receive notification when a new policy is published.
- Acknowledgment status is tracked per employee per policy.
- PDPA scanner flags documents containing NRIC patterns or phone numbers.

### Phase 3: Advisory + Compliance Integration
**Effort**: 5-7 days | **Risk**: HIGH (requires careful testing)

1. Add `search_company_policies` tool to advisory engine.
2. Modify advisory engine system prompt to enforce statutory primacy rule.
3. Implement company policy semantic search (query PolicyChunk table with embedding similarity).
4. Add statutory floor check to output screening (detect below-minimum company entitlements).
5. Add `POST /compliance/policy-check` endpoint for company policy vs statutory comparison.
6. Add compliance dashboard widget showing policy compliance status.
7. Implement stale policy detection: alert when statutory provisions are newer than company policy effective dates.

**Success Criteria**:
- When an employee asks "how many days of leave do I get?", the advisory engine answers with BOTH statutory entitlement AND company policy (if it provides more).
- When a company policy provides less than statutory minimum, the response includes an explicit warning.
- Company A's policies never appear in Company B's advisory responses (cross-tenant test).
- Compliance check flags company policies that fall below statutory minimums.
- Advisory latency increase is less than 500ms at p95.

---

## 9. Decision Points Requiring Stakeholder Input

1. **Should the system block upload of policies that are clearly below statutory minimums?** Or should it allow upload with a warning and flag for review? (Recommendation: warn but allow -- companies may be documenting current state for improvement planning.)

2. **Should employees be required to acknowledge all policies, or only policies marked as "requires acknowledgment"?** (Recommendation: per-policy setting controlled by admin.)

3. **What is the maximum file size and page count for policy uploads?** (Recommendation: 5MB / 50 pages for MVP.)

4. **Should company policies be visible to employees immediately upon upload, or should there be a "draft" state?** (Recommendation: draft -> published workflow. Admin can save a draft, preview, then publish when ready.)

5. **Should the advisory engine proactively mention company policy when the employee only asks about statutory entitlements?** For example, if an employee asks "what is the minimum annual leave?", should the response also say "your company provides 14 days"? (Recommendation: yes, always provide the company position alongside statutory, since the employee's actual entitlement is the higher of the two.)

6. **For the Ricoh Thailand demo context: should the MVP focus on manual text entry only (faster), or does the demo need PDF upload capability?** (Recommendation: Phase 1 manual text entry is sufficient for demo. It demonstrates the core value proposition without PDF parsing complexity.)

---

## 10. Dependencies and Constraints

| Dependency | Status | Impact |
|------------|--------|--------|
| `CompanyPolicy` DataFlow model | EXISTS | Needs field additions but the core model is already registered and has DataFlow CRUD nodes |
| File upload infrastructure | EXISTS | Employee document upload (`POST /{employee_id}/documents`) already handles multipart/form-data, PDF, DOCX, size limits, and disk storage. Pattern can be reused. |
| KB embedding pipeline | EXISTS | `EmbeddingPipeline` in `kb/embeddings.py` generates and stores embeddings via OpenAI-compatible API. Needs extension to handle `PolicyChunk` records. |
| Advisory engine tool system | EXISTS | `AdvisoryEngine` in `advisory_engine.py` already supports multiple tools via OpenAI function calling. Adding a new tool is a well-defined extension point. |
| Compliance engine | EXISTS | `compliance.py` router has domain check, gap analysis, and status endpoints. Needs new endpoint for company policy vs statutory comparison. |
| python-docx | NOT INSTALLED | Required for DOCX text extraction. Add to `pyproject.toml` dependencies. |
| pdfplumber | NOT INSTALLED | Required for PDF text extraction (better table handling than PyMuPDF). Add to `pyproject.toml` dependencies. |
| Dedicated policies router | DOES NOT EXIST | Currently policies are served from the employees router. Need to create `/api/routers/policies.py`. |

---

## 11. Security Considerations

1. **File upload security**: Reuse existing employee document upload patterns -- validate MIME type, check file extension, enforce size limit, generate UUID filename, never serve uploaded files directly (use signed URLs or a download endpoint).

2. **Content injection via policy text**: A malicious admin could craft policy text designed to inject instructions into the LLM prompt (e.g., "IGNORE PREVIOUS INSTRUCTIONS..."). The advisory engine's guardrails (input screening in `guardrails.py`) must also apply to company policy content retrieved by tools. The `screen_injection` function should be called on policy chunks before they are added to the LLM context.

3. **Tenant isolation**: Every database query for company policies MUST include `company_id` as a filter. The `company_id` must come from the authenticated user's JWT, never from request parameters. The advisory engine's `search_company_policies` tool must receive `company_id` as an injected parameter, not as an LLM-determined argument.

4. **PDPA compliance**: Policy documents may contain personal data. The system should not log or cache the full text of uploaded policies. Audit log entries should reference policy IDs, not content. The PDPA content scanner (R8 mitigation) should warn admins before saving.

5. **Role-based access control**: Only `owner` and `hr_manager` roles can create, edit, delete, or upload policies. Employees can read active published policies and submit acknowledgments. Platform admins can view (but not modify) policies for any company.

---

## 12. Testing Strategy

### Unit Tests
- Policy CRUD operations (create, read, update, delete, version chain).
- Text extraction from PDF and DOCX (use fixture files with known content).
- Policy chunking logic (correct split points, chunk sizes, section heading extraction).
- Statutory floor check logic (compare company values against known minimums).
- PDPA content scanner (detect NRIC patterns, phone numbers, email addresses).

### Integration Tests
- **Tenant isolation**: Create policies for Company A and Company B. Verify Company A can only access Company A policies through every endpoint and tool.
- **Advisory engine with company policies**: Submit a leave entitlement question with company policies loaded. Verify response includes both statutory and company positions.
- **Version supersession**: Create v1, update to v2, verify v1 is inactive and v2 is returned by list endpoints.
- **Compliance policy check**: Upload a below-minimum leave policy. Verify compliance check flags it.

### Adversarial Tests
- Upload a policy containing prompt injection text. Verify advisory engine does not follow injected instructions.
- Upload a policy with content identical to a statutory provision. Verify the advisory engine does not double-cite.
- Query with company_id manipulation (send a different company_id in the request body vs JWT). Verify tenant isolation rejects it.

---

## Appendix A: Current File Reference

| File Path | Relevance |
|-----------|-----------|
| `/src/hr_advisory/models/company_user.py` (line 1040) | `CompanyPolicy` model definition |
| `/src/hr_advisory/services/company_seeding.py` (line 79) | Default policy seeding (4 policies) |
| `/src/hr_advisory/api/routers/employees.py` (line 1901) | `GET /employees/policies` endpoint |
| `/src/hr_advisory/agents/advisory_engine.py` | Advisory engine with tool definitions and execution |
| `/src/hr_advisory/api/routers/advisory.py` | Advisory query endpoints and safety chain |
| `/src/hr_advisory/api/routers/compliance.py` | Compliance check, gap analysis, status endpoints |
| `/src/hr_advisory/kb/admin.py` | KB search and provision management |
| `/src/hr_advisory/kb/pipeline.py` | KB content loading pipeline |
| `/src/hr_advisory/kb/embeddings.py` | Embedding generation for semantic search |
| `/src/hr_advisory/api/middleware/tenant_isolation.py` | Tenant isolation helpers |
| `/apps/web/src/app/(dashboard)/policies/page.tsx` | Frontend policies page (read-only with hardcoded fallback) |
| `/apps/web/src/services/api/employees.ts` (line 141) | Frontend `CompanyPolicy` TypeScript interface |
