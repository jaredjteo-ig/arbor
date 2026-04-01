# Company Policy Upload & Integration -- Requirements Analysis

## Executive Summary

- **Feature**: Company Policy Upload & Integration with Advisory Engine
- **Complexity**: High -- crosses storage, parsing, search, advisory, and compliance subsystems
- **Risk Level**: Medium -- no new infrastructure required, but integration touches the safety-critical advisory pipeline
- **Estimated Effort**: 8-12 days across 3 phases

---

## 1. User Stories

### US-01: HR Manager Uploads a Company Policy

> As an HR Manager, I want to upload my company's internal policies (PDF, Word, or text) so that Arbor's advisory engine can reference them alongside statutory requirements when answering employee questions.

**Acceptance Criteria**:
- I can upload files up to 10 MB in PDF, DOCX, or TXT format from the Policies page.
- The system extracts the text content and stores it against my company profile.
- I can assign a policy type (leave, FWA, handbook, safety, benefits, other) and a title.
- I see the upload status and can confirm the extracted content looks correct.
- The policy is immediately available to the advisory engine for my company's queries.

### US-02: HR Manager Manages Policy Versions

> As an HR Manager, I want to update or replace a policy document so that the advisory engine always references the current version without losing audit history.

**Acceptance Criteria**:
- I can upload a new version of an existing policy. The old version is marked inactive; the new version becomes the active one.
- I can deactivate a policy without uploading a replacement.
- I can see the effective date and when each policy was last updated.
- The advisory engine only references active policies.

### US-03: Employee Views Company Policies

> As an Employee, I want to view my company's published policies in a single page so that I can understand what rules apply to me beyond the statutory minimums.

**Acceptance Criteria**:
- The Policies page shows both statutory guidance and company-specific policies, clearly labelled.
- Company policies display the extracted text, not just a download link.
- If my company has no uploaded policies, I see the standard statutory defaults (existing behaviour).

### US-04: Advisory Engine Answers with Both Statutory and Company Policy

> As any user asking an HR question, I want the advisory engine to include relevant company policy alongside statutory provisions so that I get a complete, company-specific answer.

**Acceptance Criteria**:
- When I ask "What is my leave entitlement?", the answer includes both the statutory minimum (Employment Act) and any company-specific leave policy (e.g., "Your company provides 14 days annual leave, which exceeds the statutory minimum of 7 days for your tenure").
- Citations distinguish between statutory provisions and company policies.
- If company policy is silent on a topic, the advisory engine says so and falls back to statutory provisions only.

### US-05: Compliance Engine Checks Company Policy Against Statutory Minimums

> As an HR Manager, I want the compliance checker to flag when my company policies fall below statutory minimums so that I can fix them before an MOM inspection.

**Acceptance Criteria**:
- The compliance check compares uploaded leave policy entitlements against Employment Act minimums.
- If a company policy sets annual leave at 5 days (below the statutory 7-day minimum), it is flagged as "non-compliant" with a critical severity.
- The compliance report shows which specific company policy clause conflicts with which statutory provision.

### US-06: Admin Reviews Uploaded Policies Across Companies

> As a platform administrator or consultant, I want to see an overview of which companies have uploaded policies and which have not, so I can advise clients to complete their setup.

**Acceptance Criteria**:
- Admin dashboard shows policy upload completeness per company.
- Consultant users can view policies for companies they manage.

---

## 2. Functional Requirements Matrix

| ID | Requirement | Input | Output | Business Logic | Edge Cases | Existing SDK Component |
|----|-------------|-------|--------|----------------|------------|----------------------|
| FR-01 | Upload policy file | File (PDF/DOCX/TXT), metadata | Stored policy record with extracted text | Validate file type/size, extract text, store file + text | Corrupt PDF, scanned image PDF (no text), password-protected DOCX, empty file | `UploadFile` (FastAPI), `S3StorageAdapter`, `CompanyPolicy` model |
| FR-02 | Text extraction from PDF | PDF bytes | Plain text string | Use `PyPDF2` or `pdfplumber` to extract text pages | OCR-only PDFs return empty text; multi-column layouts; headers/footers | New -- no extraction pipeline exists |
| FR-03 | Text extraction from DOCX | DOCX bytes | Plain text string | Use `python-docx` to walk paragraphs + tables | Embedded images, tracked changes, complex formatting | New |
| FR-04 | CRUD for company policies | API requests | Policy records | Create, read, update (new version), soft-delete; tenant-isolated | Duplicate policy types, large content fields, concurrent uploads | `CompanyPolicyListNode`, `CompanyPolicyCreateNode`, `CompanyPolicyUpdateNode` (auto-generated by DataFlow) |
| FR-05 | Policy versioning | New upload for existing type | Old version deactivated, new version active | Set `is_active=False` on old, create new record with same `policy_type` | Upload same file twice, reactivate old version | `CompanyPolicy.is_active`, `CompanyPolicy.effective_date` |
| FR-06 | Company policy search | Query string, company_id | Matching policy sections | Keyword search across `content` field, scoped to company | Empty content, very large policy documents (50+ pages) | New -- extends `search_provisions` pattern |
| FR-07 | Advisory engine integration | User query + company_id | Response with statutory + company policy citations | New tool `search_company_policies` in `TOOL_DEFINITIONS`; LLM decides when to call it | Company has no policies, policy contradicts statute, query spans multiple policy types | `AdvisoryEngine`, `TOOL_DEFINITIONS` |
| FR-08 | Compliance gap analysis | Company policies + statutory provisions | Gap findings with severity | Compare extracted entitlements against statutory minimums | Company policy is ambiguous (e.g., "competitive leave"), policy has no numeric values to compare | `compliance_checker.py`, `ComplianceCheckInput` |
| FR-09 | Frontend upload UI | File picker, form fields | Upload confirmation, content preview | Multipart form, progress indicator, content review step | Large file upload timeout, browser memory on large PDFs | Frontend `PoliciesPage` (currently read-only) |
| FR-10 | Citation differentiation | Advisory response | Citations marked as "statutory" or "company_policy" | New `authority_level` value for company policy citations | Mixed citations from both sources | `AdvisoryEngine._extract_citations()` |

---

## 3. Non-Functional Requirements

### Performance

| Metric | Target | Rationale |
|--------|--------|-----------|
| File upload (10 MB) | < 5 seconds | User should not wait long for upload acknowledgement |
| Text extraction (50-page PDF) | < 15 seconds | Can be async/background, but user needs status feedback |
| Policy search (advisory engine tool call) | < 200 ms | Must not add significant latency to the advisory response loop; keyword search over company policies is fast (small corpus per company) |
| Advisory response including company policy | < 2 seconds added latency | Additional tool call + context should not noticeably slow the existing response |

### Security

| Requirement | Implementation |
|-------------|---------------|
| Tenant isolation | All policy queries MUST filter by `company_id`; use existing `validate_company_access()` middleware |
| Upload authorization | Only `owner` and `hr_manager` roles can upload; employees can only read |
| File validation | Verify MIME type server-side (not just extension); scan file header bytes |
| Content sanitization | Strip executable content from extracted text (JavaScript in PDFs, macros in DOCX) |
| Storage encryption | S3 server-side encryption (AES-256) for file storage; already configured in `S3StorageAdapter` |
| Size limits | 10 MB per file (existing `MAX_FILE_SIZE`); 500 KB extracted text limit per policy |

### Data Retention

| Policy | Duration |
|--------|----------|
| Active policy files | Retained as long as company account is active |
| Superseded policy files | Retained for 7 years (Singapore statutory record retention for employment records) |
| Extracted text from deleted policies | Soft-deleted, recoverable for 90 days |

### Scalability

| Concern | Design |
|---------|--------|
| Storage growth | File bytes in S3 (not in database); only extracted text in PostgreSQL |
| Search performance | Per-company policy corpus is small (typically < 20 documents, < 100 KB total text); keyword search is sufficient for v1 |
| Future: vector search | `CompanyPolicy` model can gain an `embedding` column in a future phase, using the same `EmbeddingPipeline` pattern as statutory provisions |

---

## 4. Scope Boundaries

### In Scope for v1

1. **File upload** -- PDF, DOCX, TXT with server-side text extraction
2. **CRUD API** -- Create, list, read, update (version), deactivate
3. **Advisory integration** -- New `search_company_policies` tool in `AdvisoryEngine` `TOOL_DEFINITIONS`
4. **Citation differentiation** -- Advisory responses distinguish statutory vs company policy sources
5. **Frontend upload UI** -- File picker, metadata form, content preview, version management
6. **Basic compliance comparison** -- Flag when company leave entitlements are below statutory minimums (leave policy only for v1)
7. **Role-based access** -- Owner/HR Manager can upload; all roles can read

### Out of Scope for v1 (Future Phases)

1. **OCR for scanned PDFs** -- Requires Tesseract or cloud OCR service; not needed for most SME documents which are digital-native
2. **Semantic/vector search over company policies** -- Keyword search is sufficient given small per-company corpus; embedding pipeline can be added later
3. **Automated clause extraction** -- LLM-powered parsing of policy documents into structured clauses (e.g., "annual leave = 14 days"); v1 stores raw text
4. **Multi-language policy support** -- Mandarin, Malay, Tamil policy documents; requires language detection and multilingual embedding
5. **Policy templates** -- Pre-built policy templates that companies can customise; useful but not required for v1
6. **Full compliance matrix** -- Comparing all policy types (not just leave) against all statutory domains; v1 starts with leave only
7. **Policy approval workflow** -- Multi-step review/approval before a policy becomes active; overkill for SME use case
8. **Collaborative editing** -- Real-time policy editing within the platform; companies upload finished documents

---

## 5. Architecture Decision Records

### ADR-021: Where Company Policy Content Lives

#### Status

Proposed

#### Context

The platform has two content stores today:
1. **Statutory KB** -- `Provision` model with `source_act_id`, `domain_id`, `authority_level`, `embedding` vector. Searchable via `search_provisions()` and `ProvisionSimilaritySearchNode`. Contains ~200 provisions across 6 regulatory domains. Shared across all companies.
2. **Company policies** -- `CompanyPolicy` model with `company_id`, `policy_type`, `title`, `content`, `effective_date`, `is_active`. Per-company. Currently only stores seeded default text. No search capability.

The question: should uploaded company policy content be stored as `Provision` records in the statutory KB, in the existing `CompanyPolicy` model, or in a new hybrid structure?

#### Decision

**Store company policy content in the existing `CompanyPolicy` model, searched separately from statutory provisions.** The advisory engine gains a new tool (`search_company_policies`) that searches only the company's policies. The LLM synthesises both sources in its response.

#### Consequences

##### Positive

- **Clean separation of authority levels.** Statutory provisions (sourced from legislation) remain completely separate from company policies (sourced from HR departments). No risk of a company policy being mistakenly cited as law.
- **Tenant isolation is inherent.** `CompanyPolicy` already filters by `company_id`. Statutory provisions are shared. Mixing them in one table would require adding `company_id` to `Provision` and complicating every query.
- **Minimal model changes.** `CompanyPolicy` already has `content`, `policy_type`, `effective_date`, `is_active`. We add `file_path` (S3 key for the original file), `file_type` (pdf/docx/txt), and `content_hash` (deduplication). No new tables.
- **Independent search tuning.** Company policies are a small corpus (< 20 documents). Keyword search is fast and sufficient. Statutory provisions are larger and benefit from vector similarity. Different search strategies for different data sizes.
- **Advisory engine control.** The LLM decides when to call `search_company_policies` vs `search_kb`. This means it can explain the relationship: "The Employment Act requires a minimum of 7 days annual leave, and your company policy provides 14 days."

##### Negative

- **Two tool calls instead of one.** For a fully comprehensive answer, the LLM may need to call both `search_kb` and `search_company_policies`. This adds one tool-calling round (< 200 ms for keyword search).
- **No unified semantic search.** A single vector search across both statutory and company content would be more elegant. However, the small company policy corpus makes keyword search adequate, and adding embeddings later is straightforward (add `embedding` column to `CompanyPolicy`).

#### Alternatives Considered

##### Option A: Store company policies as Provision records with `authority_level = "company_policy"`

- **Pros**: Unified search, single tool call, reuses embedding pipeline
- **Cons**: Pollutes statutory KB with per-company content; requires adding `company_id` to `Provision` (currently shared); every KB query must filter `company_id` or risk leaking one company's policies to another; `source_act_id` is meaningless for company policies; fundamentally different data ownership model
- **Rejected because**: The tenant isolation risk outweighs the search convenience. Statutory provisions are public/shared; company policies are private/per-tenant. Mixing them invites data leaks.

##### Option B: New `CompanyProvision` model mirroring `Provision` structure

- **Pros**: Same schema for search/embedding, clean separation
- **Cons**: Duplicates the `Provision` model; requires maintaining two parallel search paths anyway; `CompanyPolicy` already exists and is simpler (no `source_act_id`, `domain_id`, etc.)
- **Rejected because**: Over-engineered for the v1 use case. Company policies don't have sections, acts, or domain IDs. The `CompanyPolicy` model's flat structure (`policy_type`, `title`, `content`) is a better fit.

##### Option C: RAG chunks in a shared vector store with metadata filtering

- **Pros**: Best semantic search; single query retrieves both statutory and company content
- **Cons**: Requires chunking pipeline; metadata filtering for tenant isolation is error-prone; need to handle chunk-level deduplication; embedding costs scale with number of companies
- **Rejected for v1 because**: Premature optimisation. The per-company corpus is small enough that keyword search works well. Can migrate to this approach in a future phase when company policy volumes grow.

---

### ADR-022: Advisory Engine Integration Strategy

#### Status

Proposed

#### Context

The `AdvisoryEngine` uses OpenAI-compatible function calling. The LLM currently has 6 tools: `search_kb`, `calculate_cpf`, `calculate_leave`, `calculate_salary`, `calculate_quota_levy`, `get_company_context`. The LLM decides when and in what order to call tools.

How should company policy content be made available to the LLM?

#### Decision

**Add a new `search_company_policies` tool to `TOOL_DEFINITIONS`.** The tool accepts a `query` string and an optional `policy_type` filter. It searches `CompanyPolicy` records for the user's company using keyword matching (same pattern as `_search_python_kb`). Results include the policy title, type, and relevant content excerpt.

The system prompt is updated to instruct the LLM:
- "When the user asks about company-specific policies, benefits, or internal rules, use `search_company_policies` to find relevant company policies."
- "When answering, clearly distinguish between statutory requirements (from `search_kb`) and company-specific policies (from `search_company_policies`)."
- "If company policy appears to conflict with or fall below statutory requirements, explicitly note this."

#### Consequences

##### Positive

- **LLM-driven orchestration.** The LLM decides when company policy is relevant. No hardcoded routing.
- **Citation clarity.** Company policy results include `authority_level: "company_policy"`, clearly distinguishing them from statutory citations.
- **Backward compatible.** Companies without uploaded policies simply get no results from the tool, and the LLM falls back to statutory-only answers (existing behaviour).
- **Conflict detection.** The system prompt explicitly instructs the LLM to flag statutory/policy conflicts. This is a natural language capability, not a code change.

##### Negative

- **Latency.** An additional tool round-trip when the LLM decides to search company policies. Mitigated by the small corpus (< 200 ms for keyword search).
- **Prompt engineering dependency.** The quality of statutory-vs-policy distinction depends on prompt quality. Must be validated via red team testing.

---

### ADR-023: File Parsing Architecture

#### Status

Proposed

#### Context

Company policy documents arrive as PDF, DOCX, or TXT files. The platform needs to extract plain text for storage in the `CompanyPolicy.content` field.

#### Decision

**Server-side synchronous text extraction during the upload request, with a hard timeout and fallback.** The upload endpoint extracts text immediately and returns it to the user for review. If extraction fails or the file is too large to parse quickly, the raw file is still stored in S3 and the policy record is created with `content = ""` and a status indicating extraction failed.

Libraries:
- **PDF**: `pdfplumber` (better than PyPDF2 for complex layouts; pure Python)
- **DOCX**: `python-docx` (standard, lightweight)
- **TXT**: Direct `bytes.decode('utf-8')` with encoding detection fallback via `chardet`

Timeout: 15 seconds for extraction. If exceeded, store the file and return `extraction_status: "timeout"`.

#### Consequences

##### Positive

- **Simple architecture.** No background job queue, no polling for status. User sees extracted text immediately.
- **User verification.** The upload flow includes a "review extracted content" step where the user can confirm or manually edit the text.
- **Graceful degradation.** If extraction fails, the file is still stored. User can manually paste the policy text.

##### Negative

- **Blocking request.** A large PDF (50+ pages) may take up to 15 seconds to extract. This is acceptable given that policy uploads are infrequent (monthly at most) and the user expects to wait.
- **No OCR.** Scanned PDFs will extract empty text. Acceptable for v1; OCR can be added as a future enhancement.

---

## 6. Risk Assessment

### Critical (High Probability, High Impact)

1. **Tenant data leakage -- company policy content visible to wrong company**
   - Probability: Medium (new search path introduces new filtering requirement)
   - Impact: Critical (confidential company data exposed)
   - Mitigation: Every `search_company_policies` call MUST receive `company_id` from the authenticated user context, never from the query. Enforce via `validate_company_access()` middleware. Integration test: upload policy to Company A, verify Company B cannot see it.
   - Prevention: The `CompanyPolicy` model already has `company_id` and the DataFlow ListNode uses filter-based queries. No raw SQL involved.

2. **Advisory engine cites company policy as law**
   - Probability: Low (with proper citation formatting)
   - Impact: High (user makes legal decision based on wrong authority)
   - Mitigation: Company policy search results include `authority_level: "company_policy"` and `source: "Company Policy"` (never "statute"). System prompt explicitly instructs differentiation. Red team test: ask a question that has both statutory and company policy answers, verify citations are correctly attributed.
   - Prevention: Separate tool (`search_company_policies`) with separate result format from `search_kb`.

### Medium Risk (Monitor)

3. **Text extraction produces garbage from complex PDFs**
   - Probability: Medium (depends on document quality)
   - Impact: Medium (advisory engine gives bad answers based on garbled text)
   - Mitigation: User content review step in upload flow; extraction quality score (character-to-word ratio check); manual text entry fallback.
   - Prevention: Test extraction with a corpus of real Singapore HR policy PDFs.

4. **Large file uploads exhaust server memory**
   - Probability: Low (10 MB limit exists)
   - Impact: Medium (temporary degradation for other users)
   - Mitigation: Existing `MAX_FILE_SIZE = 10 MB` limit; `pdfplumber` streams pages incrementally; DOCX extraction is lightweight.

5. **Advisory engine always calls both tools, adding latency**
   - Probability: Medium (LLM may be overly cautious)
   - Impact: Low (< 200 ms additional latency)
   - Mitigation: System prompt instructs the LLM to call `search_company_policies` only when the question is about company-specific topics. Monitor tool call frequency in analytics.

### Low Risk (Accept)

6. **Company policies contradict statutory requirements without detection**
   - Probability: Medium for v1 (compliance comparison is limited to leave)
   - Impact: Low for v1 (advisory engine still cites statutory minimums)
   - Mitigation: The advisory engine's system prompt instructs it to flag conflicts. Structured compliance comparison is scoped to leave for v1, expanding in future phases.

---

## 7. Integration Map

### Components That Need Changes

| Component | File(s) | Change Type | Complexity |
|-----------|---------|-------------|------------|
| `CompanyPolicy` model | `models/company_user.py` | Add fields: `file_path`, `file_type`, `file_size_bytes`, `content_hash`, `extraction_status` | Low |
| Policy upload API | `api/routers/employees.py` (new endpoint) | New `POST /employees/policies/upload` endpoint with file parsing | Medium |
| Policy CRUD API | `api/routers/employees.py` (extend existing) | Add update, deactivate, get-by-id endpoints | Low |
| Text extraction service | New `services/policy_parser.py` | PDF/DOCX/TXT extraction with timeout | Medium |
| Advisory engine tool | `agents/advisory_engine.py` | Add `search_company_policies` tool definition and execution | Medium |
| Advisory system prompt | `agents/advisory_engine.py` | Update `_build_system_prompt()` for company policy awareness | Low |
| Company policy search | New `kb/company_policy_search.py` or extend `kb/admin.py` | Keyword search over `CompanyPolicy.content` scoped by company_id | Low |
| Compliance checker | `workflows/compliance_checker.py` | Add `has_custom_leave_policy` and `leave_entitlement_days` to `ComplianceCheckInput` | Medium |
| Frontend policies page | `apps/web/src/app/(dashboard)/policies/page.tsx` | Add upload button, file picker, content preview, version management | High |
| Frontend API service | `apps/web/src/services/api/employees.ts` | Add `uploadPolicy()`, `updatePolicy()`, `deactivatePolicy()` methods | Low |
| Frontend advisory display | `apps/web/src/components/advisory/ChatContainer.tsx` | Distinguish statutory vs company policy citations visually | Low |

### Components That Stay Unchanged

- **KB content pipeline** (`kb/pipeline.py`, `kb/content/`) -- Statutory content loading is separate
- **Embedding pipeline** (`kb/embeddings.py`) -- Not needed for v1 company policy search
- **Safety chain** (`workflows/guardrails.py`) -- Existing guardrails apply to all advisory responses regardless of source
- **Trust lineage** (`trust/eatp_lineage.py`) -- Existing trust chain wraps the full advisory response

### Dependency Order

```
Phase 1 (Foundation):
  1. CompanyPolicy model changes (add fields)
  2. Text extraction service (policy_parser.py)
  3. Policy upload API endpoint

Phase 2 (Advisory Integration):
  4. Company policy search function
  5. Advisory engine tool + system prompt
  6. Citation differentiation in advisory response

Phase 3 (Frontend + Compliance):
  7. Frontend upload UI
  8. Frontend citation display
  9. Compliance checker integration
 10. Red team testing
```

---

## 8. Implementation Roadmap

### Phase 1: Foundation (3-4 days)

**Goal**: Companies can upload policy documents and the platform extracts + stores the text.

- Add `file_path`, `file_type`, `file_size_bytes`, `content_hash`, `extraction_status` fields to `CompanyPolicy` model
- Build `services/policy_parser.py` with `extract_text_from_pdf()`, `extract_text_from_docx()`, `extract_text_from_txt()`
- Build `POST /employees/policies/upload` endpoint: receive file, validate, extract text, store file in S3, create `CompanyPolicy` record
- Build `PUT /employees/policies/{id}` endpoint: upload new version, deactivate old
- Build `DELETE /employees/policies/{id}` endpoint: soft-deactivate
- Add `pip install pdfplumber python-docx chardet` to dependencies
- Unit tests for text extraction (sample PDF, DOCX, TXT files)
- Integration tests for upload + tenant isolation

### Phase 2: Advisory Integration (3-4 days)

**Goal**: The advisory engine includes company policy in its answers.

- Build `search_company_policies(query, company_id, policy_type=None)` search function
- Add `search_company_policies` tool definition to `TOOL_DEFINITIONS` in `advisory_engine.py`
- Add tool execution handler in `_execute_tool_call()`
- Update `_build_system_prompt()` with company policy awareness instructions
- Update `_extract_citations()` to include `authority_level: "company_policy"` for company policy results
- Integration tests: ask advisory question with and without company policies uploaded
- Red team: verify statutory vs company policy citation accuracy

### Phase 3: Frontend + Compliance (2-4 days)

**Goal**: HR Managers can upload policies through the UI. Compliance checker flags sub-statutory policies.

- Update `PoliciesPage` with upload button (Owner/HR Manager only)
- Build upload modal: file picker, policy type selector, title field, effective date
- Build content preview step: show extracted text, allow manual editing
- Build version history view: show previous versions with effective dates
- Update `ChatContainer` citation display to differentiate statutory vs company policy
- Extend `ComplianceCheckInput` with `has_custom_leave_policy` and `leave_entitlement_days`
- Add leave policy comparison logic to `check_compliance()`
- End-to-end test: upload policy, ask advisory question, verify response includes company policy

---

## 9. Success Criteria

- [ ] HR Manager can upload a PDF/DOCX/TXT policy and see the extracted text within 15 seconds
- [ ] Uploaded policy is visible only to users in the same company (tenant isolation verified)
- [ ] Advisory engine includes company policy in its response when relevant
- [ ] Citations in advisory responses are clearly labelled as "statutory" or "company policy"
- [ ] Advisory engine correctly identifies when company policy exceeds statutory minimums
- [ ] Advisory engine correctly identifies when company policy falls below statutory minimums
- [ ] Compliance checker flags leave policies that are below Employment Act minimums
- [ ] Companies without uploaded policies continue to receive statutory-only answers (no regression)
- [ ] File upload respects 10 MB limit and rejects non-PDF/DOCX/TXT files
- [ ] Policy versioning works: new upload replaces old, old version is preserved but inactive
- [ ] Red team: no case where company policy is cited as statutory law

---

## 10. Open Questions for Product Decision

1. **Should employees be able to see the original uploaded file (download link), or only the extracted text?** Recommendation: extracted text only for v1, as it avoids S3 presigned URL complexity in the employee-facing UI. HR Managers can download the original.

2. **Should there be a maximum number of policies per company?** Recommendation: 50 policies per company for v1. This is generous for any SME and keeps the keyword search fast.

3. **When a company uploads a policy that conflicts with statute, should the platform block the upload or just warn?** Recommendation: warn, not block. Company policies can legitimately differ from statute (e.g., providing more than the statutory minimum). The advisory engine and compliance checker handle the communication.

4. **Should the advisory engine proactively mention company policies, or only when specifically asked?** Recommendation: proactively mention when the query topic has a matching company policy. The system prompt should instruct: "Always check company policies for the topic of the user's question, and include relevant company-specific information in your answer."
