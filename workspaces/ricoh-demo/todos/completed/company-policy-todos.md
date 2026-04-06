# Company Policy Upload & Integration — Todo List

**Feature**: Company Policy Upload, Advisory Integration, Compliance Checking
**Workspace**: `workspaces/ricoh-demo/`
**Plan**: `02-plans/01-company-policy-implementation-plan.md`
**Decisions**: `briefs/02-company-policy-decisions.md`
**Red Team**: `01-analysis/01-research/24-company-policy-red-team.md`

---

## M1: Data Model & Dependencies

### T001: Extend CompanyPolicy DataFlow model with new fields

**File**: `src/hr_advisory/models/company_user.py` (line ~1040)

**Current fields**: `company_id`, `policy_type`, `title`, `content`, `effective_date`, `is_active`

**Add fields**:

```
category: str = ""
version_number: int = 1
superseded_by_id: Optional[int] = None
uploaded_by: Optional[int] = None
file_name: str = ""
file_path: str = ""
file_type: str = ""
file_size_bytes: int = 0
content_hash: str = ""
extraction_status: str = ""
requires_acknowledgment: bool = False
status: str = "active"
```

All fields have defaults so existing records won't break.

**Complexity**: S

---

### T002: Create PolicyAcknowledgment DataFlow model

**File**: `src/hr_advisory/models/company_user.py`

**New model**:

```python
@db.model
class PolicyAcknowledgment:
    company_id: int
    policy_id: int
    employee_id: int
    version_acknowledged: int = 1
    acknowledged_at: str = ""
    ip_address: str = ""
```

Add indexes on `company_id`, `policy_id`, `employee_id`.

**Complexity**: S

---

### T003: Add pdfplumber and chardet to pyproject.toml

**File**: `pyproject.toml`

Add:

- `pdfplumber>=0.10.0`
- `chardet>=5.0.0`

(`python-docx>=1.1.0` already present at line 39.)

**Complexity**: S

---

### T004: Update company seeding for new fields

**File**: `src/hr_advisory/services/company_seeding.py` (line 79, `DEFAULT_POLICIES`)

Populate the NEW `category` field using the 9-category taxonomy. **Do NOT change the existing `policy_type` field** — it must retain its original values (`leave`, `fwa`, `handbook`, `wsh`) for backward compatibility with the mobile app and deprecated endpoint.

Mapping for `category` field only:

- `leave` -> `category: "leave_absence"`
- `fwa` -> `category: "employment_terms"`
- `handbook` -> `category: "general_hr"`
- `wsh` -> `category: "workplace_safety"`

Add to each seeded policy: `category` (mapped above), `version_number: 1`, `file_type: "text"`, `status: "active"`, `extraction_status: ""`.

Update `_seed_policies()` to include new fields in CreateNode params.

**Complexity**: S

---

## M2: Text Extraction & File Handling

### T005: Build text extraction service

**New file**: `src/hr_advisory/services/policy_parser.py`

Implement:

- `extract_text_from_pdf(file_bytes, timeout_seconds=15) -> (text, status)` — uses pdfplumber, strips repeated headers/footers
- `extract_text_from_docx(file_bytes) -> (text, status)` — uses python-docx, walks paragraphs + tables
- `extract_text_from_txt(file_bytes) -> (text, status)` — UTF-8 with chardet fallback
- `extract_text(file_bytes, file_type) -> (text, status)` — dispatcher
- `compute_content_hash(content) -> str` — SHA-256 hex digest

Content limit: truncate at 500,000 characters.

**Complexity**: M

---

### T006: Add extracted text quality validation

**File**: `src/hr_advisory/services/policy_parser.py`

Add `validate_extraction_quality(text: str) -> tuple[str, list[str]]` that checks:

- Minimum word count (< 10 words = likely garbage)
- Character-to-word ratio (> 20 chars/word average = likely binary garbage)
- Excessive special characters (> 30% non-alphanumeric = likely OCR noise)

Returns `(quality_status, warnings)` where status is `"good"`, `"low_quality"`, or `"empty"`.

Called after extraction, result stored in `extraction_status`. Does NOT block save — informational only.

**Source**: Red team F4 (extracted text quality validation).

**Complexity**: S

---

## M3: Policies Router (Backend API)

### T007: Create dedicated policies router with full CRUD

**New file**: `src/hr_advisory/api/routers/policies.py`

Endpoints:

- `GET /policies/` — List policies for current company (filters: category, status). Employees see only `status="active"`.
- `GET /policies/{id}` — Single policy with full content. Tenant-isolated.
- `POST /policies/` — Create from manual text entry (owner/hr_manager only). Validate category.
- `POST /policies/upload` — Upload file (PDF/DOCX/TXT, max 10MB). Extract text. Store file.
- `PUT /policies/{id}` — Update. Content change = new version (deactivate old, create new). Metadata change = in-place update.
- `PUT /policies/{id}/content` — Edit extracted text after upload review.
- `DELETE /policies/{id}` — Soft delete (archive). Sets `status="archived"`, `is_active=False`.
- `GET /policies/{id}/versions` — Version history for a policy.
- `POST /policies/{id}/acknowledge` — Employee acknowledges policy. Idempotent.
- `GET /policies/{id}/acknowledgments` — Acknowledgment status (owner/hr_manager only).

Predefined categories constant:

```python
POLICY_CATEGORIES = [
    "employment_terms", "leave_absence", "compensation_benefits",
    "workplace_safety", "fair_employment", "foreign_worker",
    "tax_filing", "general_hr", "code_of_conduct",
]
```

Custom categories: any non-empty string accepted. Free-text field with predefined suggestions in UI.

**File upload validation**: Validate file extension against allowlist (`[".pdf", ".docx", ".txt"]`), validate MIME type header, reject with 400 + descriptive error for disallowed types. Follow the existing upload pattern from `employees.py` line 38 / `claims.py` line 23.

**File storage**: Use `UPLOAD_DIR` pattern from existing document uploads. Store with UUID-based filenames to avoid collisions. Create `policies/` subdirectory under `UPLOAD_DIR`. Ensure directory creation on startup.

**Register**: Add to `src/hr_advisory/api/platform.py` following existing router pattern.

**Complexity**: L

---

### T008: Add version creation race condition protection

**File**: `src/hr_advisory/api/routers/policies.py`

In the PUT endpoint when creating a new version:

- Use a database transaction wrapping the deactivate-old + create-new sequence
- Check for existing active version of same policy_type+company_id within the transaction
- If another active version was created concurrently, return 409 Conflict

**Source**: Red team F3.

**Complexity**: S

---

### T009: Deprecate old policies endpoint in employees router

**File**: `src/hr_advisory/api/routers/employees.py` (line ~1901)

Add deprecation comment to `list_policies()` indicating canonical endpoint is `GET /policies/`. Keep functional for backward compatibility until frontend migrates.

**Complexity**: S

---

## M4: Advisory Engine Integration

### T010: Build company policy search function

**New file**: `src/hr_advisory/services/company_policy_search.py`

```python
def search_company_policies(
    query: str,
    company_id: int,
    category: str | None = None,
    limit: int = 5,
) -> list[dict]:
```

- Queries CompanyPolicyListNode for active policies
- Keyword relevance scoring (stopword removal, word overlap — same pattern as `_search_python_kb`)
- Returns top results with: `title`, `category`, `content_excerpt` (first 2000 chars), `effective_date`, `version_number`, `authority_level` (always `"company_policy"`)

**Zero-result format** (red team F2): When no results match, return:

```json
{
  "results": [],
  "total_company_policies": 5,
  "message": "No company policies matched this query. The company has 5 policies but none are relevant to this topic."
}
```

This prevents LLM from confusing "no match" with "no policies exist."

**Complexity**: M

---

### T011: Thread company_id through advisory engine to tool execution

**File**: `src/hr_advisory/agents/advisory_engine.py`

Current `_execute_tool_call(name, arguments)` has no `company_id` parameter.

- Extend signature: `_execute_tool_call(name, arguments, company_id=None)`
- In `AdvisoryEngine.run()`, pass `company_id` through to `_execute_tool_call()`
- Existing tool handlers unchanged (they ignore the new param)

**Source**: Red team B1, plan Task 2.2 note.

**Complexity**: S

---

### T012: Add search_company_policies tool to advisory engine

**File**: `src/hr_advisory/agents/advisory_engine.py`

A. Add tool definition to `TOOL_DEFINITIONS` list (after `get_company_context`):

- Name: `search_company_policies`
- Description: instructs LLM to search company-specific policies, ALWAYS also call `search_kb` for statutory position
- Parameters: `query` (required), `category` (optional, enum of 9 predefined)

B. Add handler in `_execute_tool_call()`:

```python
elif name == "search_company_policies":
    from hr_advisory.services.company_policy_search import search_company_policies
    results = search_company_policies(
        query=arguments.get("query", ""),
        company_id=company_id,
        category=arguments.get("category"),
        limit=5,
    )
    return json.dumps(results, default=str)
```

**Depends on**: T010, T011

**Complexity**: M

---

### T013: Screen company policy search results for prompt injection

**File**: `src/hr_advisory/agents/advisory_engine.py`

Before returning tool results to LLM context, run content screening on `search_company_policies` results. Reuse existing `screen_injection()` pattern from `advisory.py:264` but applied to tool result text (content excerpts).

If injection detected in policy content:

- Strip the flagged content from the result
- Log the detection
- Return remaining clean results (do not block the entire search)
- If ALL results are stripped, return `{"results": [], "results_screened": true, "message": "Relevant company policies were found but their content could not be included."}` — prevents LLM from saying "no policies exist" when they were screened

**Source**: Red team F1 (CRITICAL — prompt injection via PDF policy content).

**Complexity**: M

---

### T014: Update advisory engine system prompt for company policy awareness

**File**: `src/hr_advisory/agents/advisory_engine.py` (`_build_system_prompt()`)

Add to TOOLS section: description of `search_company_policies` tool.

Add COMPANY POLICY RULES section:

- ALWAYS state statutory position first, then company position
- Use "Under the Employment Act..." for statutory, "Your company policy provides..." for company
- If company policy below statutory minimum: say so explicitly
- If company policy exceeds statutory minimum: note positively
- If no company policy: say so and fall back to statutory
- NEVER present company policy as having force of law

**Depends on**: T012

**Complexity**: S

---

### T015: Update advisory engine steering logic for statutory primacy

**File**: `src/hr_advisory/agents/advisory_engine.py` (line ~723)

Current steering: after 5+ `search_kb` calls, nudge model to synthesize.

Update to account for `search_company_policies`:

- If model calls `search_company_policies` but has NOT called `search_kb` for a regulated topic, inject a nudge: "You must also check the statutory position via search_kb before synthesizing."
- Track both tool calls in the loop counter

**Source**: Red team F7 (statutory primacy enforcement).

**Complexity**: M

---

### T016: Add company policy citation accumulator and extraction

**File**: `src/hr_advisory/agents/advisory_engine.py`

Currently `_extract_citations()` (line ~886) only handles KB results via `kb_results_seen`.

A. Add `company_policy_results_seen: list[dict]` accumulator alongside `kb_results_seen`
B. Populate it when `search_company_policies` tool results are received (same place kb_results_seen is populated, ~line 709-713)
C. Extend `_extract_citations()` to:

- Include company policy results with `authority_level: "company_policy"`
- Use `policy_id` (not `section`) as the deduplication key
- Return citation format: `{ provision_id: "policy-{id}", title: "Leave Policy, v3", authority_level: "company_policy" }`

**Source**: Red team B1/F5 (CRITICAL — citation pipeline only handles KB results).

**Complexity**: M

---

### T017: Update citation validator to handle company policy citations

**File**: `src/hr_advisory/trust/citation_validator.py` (`validate_citations()`, line ~449)

Currently validates provision IDs against KB. Company policy citations have format `policy-{id}` not `EA s88`.

Update to:

- Recognize `authority_level: "company_policy"` citations
- Skip KB provision lookup for company policy citations (they don't exist in the KB)
- Validate that the referenced policy_id exists and belongs to the user's company
- Do NOT mark company policy citations as invalid

**Source**: Red team F5 (citation validator breaks on company policy citations).

**Complexity**: M

---

## M5: Frontend — API Service & Design System

### T018: Create policies API service with TypeScript types

**New file**: `apps/web/src/services/api/policies.ts`

Types:

```typescript
interface PolicyRecord {
  id: number;
  company_id: number;
  policy_type: string;
  category: string;
  title: string;
  content: string;
  effective_date: string;
  is_active: boolean;
  version_number: number;
  status: "draft" | "active" | "archived";
  file_name: string;
  file_type: string;
  file_size_bytes: number;
  extraction_status: string;
  requires_acknowledgment: boolean;
  created_at: string;
  updated_at: string;
}

interface PolicyAcknowledgmentRecord {
  id: number;
  policy_id: number;
  employee_id: number;
  version_acknowledged: number;
  acknowledged_at: string;
}

interface StatutoryFloorWarning {
  field: string;
  company_value: number | null;
  statutory_minimum: number;
  status: "above_minimum" | "meets_minimum" | "below_minimum" | "not_detected";
  message: string;
}
```

API methods:

- `list`, `get`, `create`, `upload`, `update`, `updateContent`, `archive`
- `versions`, `acknowledge`, `acknowledgments`
- `complianceCheck`

Follow the existing pattern from `employees.ts` for Nexus gateway envelope handling.

**Complexity**: S

---

### T019: Add company-policy authority level to design system

**Files**:

- `apps/web/src/app/globals.css` — Add CSS variables:
  ```css
  --color-authority-company-policy: #7c3aed;
  --color-authority-company-policy-bg: #f5f3ff;
  ```
- `apps/web/src/components/design-system/SourceCitation.tsx` — Extend `AuthorityLevel` type to include `"company-policy"`, add styles and label
- `apps/web/src/components/advisory/ProvisionViewer.tsx` — Extend its `AuthorityLevel` type and `authorityStyles` to include `"company-policy"`

**Complexity**: S

---

### T020: Update ProvisionCited type for company policy support

**File**: `apps/web/src/types/api.ts` (line ~19)

Current:

```typescript
interface ProvisionCited {
  provision_id: string;
  title: string;
  relevance: number;
  authority_level?: string;
}
```

Add optional fields for company policy citations:

```typescript
  policy_id?: number;
  policy_version?: number;
  source_type?: "statutory" | "company_policy";
```

**Complexity**: S

---

### T021: Move Policies to top-level admin navigation

**File**: `apps/web/src/components/shell/NavigationSidebar.tsx`

Currently policies is buried as a submenu item under "Leave" (line ~129-133). For company policy management, it needs to be a top-level item in admin navigation.

- Add "Policies" with `FileText` icon to `adminCoreNavItems` (after Compliance or in its own group)
- Keep the employee-facing policies link in `employeeCoreNavItems` as well
- Remove from Leave submenu

**Complexity**: S

---

## M6: Frontend — Policy Management UI

### T022: Rewrite policy list page (admin + employee views)

**File**: `apps/web/src/app/(dashboard)/policies/page.tsx`

Complete rewrite of current page. New page has:

**Admin view**:

- Header: "Company Policies" with FileText icon, "Add Policy" button (owner/hr_manager only)
- Filter bar: Status tabs (All/Active/Draft/Archived with counts), search input (debounced), category filter dropdown
- Policy list: Grouped by category (collapsible). Each row = AppCard with title, version badge, status badge, effective date, file type icon, pending acknowledgment count
- Empty state with CTA

**Employee view** (same route, role-gated):

- No "Add Policy" button
- Only active policies (no Draft/Archived tabs)
- Acknowledgment banner when policies need signing
- "[NEW]" badge on policies updated since last acknowledgment

Replace current `STANDARD_POLICIES` fallback with proper empty state.

**Depends on**: T018

**Complexity**: L

---

### T023: Build policy creation/upload modal

**New file**: `apps/web/src/components/policies/PolicyCreateModal.tsx`

Two-tab modal:

**Tab 1: "Write Policy"** — Title, category dropdown (9 predefined + "Other" with free-text), content textarea, effective date (DatePicker), requires_acknowledgment checkbox, Save Draft / Publish buttons

**Tab 2: "Upload Document"** — File picker (.pdf/.docx/.txt, max 10MB), title (auto from filename, editable), category, effective date, requires_acknowledgment checkbox, Upload button

**After upload**: Content preview step — scrollable extracted text, extraction status badge, Edit button for corrections, warning if extraction failed + manual entry area

**Validation**: Title required (max 200 chars), category required, content required for publish, effective date required, file max 10MB + allowed extensions only

**Depends on**: T018

**Complexity**: M

---

### T024: Build policy detail page with tabs

**New file**: `apps/web/src/app/(dashboard)/policies/[id]/page.tsx`

Horizontal tabs (follow employees/[id] pattern):

**Tab: Overview** — Summary card (title, category, effective date, version, status, uploaded by, file details), statutory domain mapping, acknowledgment summary (admin only)

**Tab: Content** — Full policy text in readable format, "Edit Content" button (admin only) for inline editing

**Tab: Versions** — All versions (current + archived), ordered newest first. Each: version number, effective date, status, uploaded by, date. "View" link for previous versions.

**Tab: Acknowledgments** (admin only) — Employee table (name, role, acknowledged yes/no, date), filter pending/completed, "Send Reminder" button (logs intent for now)

**Employee view**: Same page without admin tabs, no action buttons, but "I Acknowledge" button if required and not yet acknowledged for this version.

**Depends on**: T018, T022

**Complexity**: L

---

### T025: Update advisory chat to show company policy citations

**Files**:

- `apps/web/src/components/advisory/ChatContainer.tsx` — Ensure citations with `authority_level: "company_policy"` render correctly
- `apps/web/src/components/advisory/SystemMessage.tsx` — Update `resolveAuthority()` to recognize `"company_policy"` level
- Citation click handler: company policy citations open policy detail page (or inline viewer), NOT ProvisionViewer

**Depends on**: T019, T020

**Complexity**: S

---

## M7: Acknowledgment & Onboarding Integration

### T026: Build employee policy acknowledgment flow

**Files**:

- `apps/web/src/app/(dashboard)/policies/[id]/page.tsx` — "I Acknowledge" button for employees
- `apps/web/src/app/(dashboard)/policies/page.tsx` — Acknowledgment banner at top listing pending policies

When employee clicks "I Acknowledge":

- Call `POST /policies/{id}/acknowledge`
- Update UI to show acknowledged state
- Idempotent — re-acknowledging same version is no-op

**Depends on**: T024, T007

**Complexity**: S

---

### T027: Add policy acknowledgment to employee onboarding checklist

**File**: `apps/web/src/app/(dashboard)/employees/[id]/page.tsx` (`OnboardingTab`, line ~3057)

Currently has 6 hard-coded checklist items. Add a 7th:

- "Company policies acknowledged" — shows how many of the `requires_acknowledgment=true` policies the employee has acknowledged
- Links to policies page filtered for pending acknowledgments

**Backend**: Add a `GET /policies/pending-acknowledgments?employee_id=X` endpoint to policies router that returns policies requiring acknowledgment that this employee hasn't acknowledged.

**Depends on**: T007, T026

**Complexity**: M

---

### T028: Show pending policy acknowledgments on employee dashboard

**File**: `apps/web/src/app/(dashboard)/my-dashboard/page.tsx`

After first login or when new policies are published:

- Show a prominent card/banner: "You have X policies to review and acknowledge"
- Each policy listed with title, category, "Review" link
- Card dismisses when all acknowledged

This is a soft nudge (not a blocker). Employees can use the platform without acknowledging.

**Depends on**: T027

**Complexity**: S

---

## M8: Compliance Integration

### T029: Build statutory floor check service

**New file**: `src/hr_advisory/services/statutory_floor_check.py`

```python
def check_policy_against_statutory_floor(
    policy_content: str,
    category: str,
) -> list[dict]:
```

For v1, only checks `category == "leave_absence"`:

- Regex patterns for numeric values near "annual leave", "sick leave", "hospitalisation"
- Compare against: annual leave 7 days min (EA s.88), outpatient sick 14 days min (EA s.89), hospitalisation 60 days max
- Returns list of findings: `field`, `company_value`, `statutory_minimum`, `status` ("above/meets/below_minimum" or "not_detected"), `message`

Returns empty list for non-leave categories.

**Complexity**: M

---

### T030: Integrate statutory floor check into upload flow

**File**: `src/hr_advisory/api/routers/policies.py`

In `POST /policies/` and `POST /policies/upload`, after content is available:

- Call `check_policy_against_statutory_floor(content, category)`
- Include findings in response under `statutory_floor_warnings` key
- Do NOT block upload

Add `GET /policies/{id}/compliance-check` endpoint for on-demand checking.

**Depends on**: T007, T029

**Complexity**: S

---

### T031: Show statutory floor warnings in frontend

**Files**:

- `apps/web/src/components/policies/PolicyCreateModal.tsx` — After API returns with `statutory_floor_warnings` containing `below_minimum` findings, show amber warning banner above Save/Publish buttons with each finding in plain language + "Publish Anyway" button
- `apps/web/src/app/(dashboard)/policies/[id]/page.tsx` — Overview tab: persistent warning card if policy has below-minimum findings

**Depends on**: T023, T024, T030

**Complexity**: S

---

### T032: Extend compliance dashboard with company policy status (DEFERRED — v2)

**File**: `src/hr_advisory/api/routers/compliance.py`

In `GET /compliance/status/{company_id}`, add `company_policies` section:

```json
{
  "company_policies": {
    "total_policies": 5,
    "categories_covered": ["leave_absence", "workplace_safety"],
    "categories_missing": ["employment_terms", ...],
    "below_minimum_warnings": 1,
    "acknowledgment_pending": 12
  }
}
```

**Note**: Red team recommended deferring to v2. Not tied to any stakeholder decision. Implement after core feature ships if time permits.

**Depends on**: T001

**Complexity**: S

---

## M9: Testing

### T033: Unit tests for text extraction service

**New file**: `tests/unit/test_policy_parser.py`

Test cases:

- Extract from valid PDF, DOCX, TXT
- Empty file returns `("", "failed")`
- Corrupted PDF returns `("", "failed")`
- Non-UTF8 text with chardet fallback
- Content exceeding 500K chars is truncated
- Quality validation: garbage detection, minimum word count
- Content hash computation

**Complexity**: M

---

### T034: Integration tests for policies router

**New file**: `tests/integration/test_policies_api.py`

Test cases:

- CRUD lifecycle: create, read, update (new version), archive
- Tenant isolation: Company A cannot see Company B policies
- File upload with size/type validation (reject > 10MB, reject .exe)
- Version creation: old version archived when new version created
- Acknowledgment: create, idempotent re-acknowledgment, list status
- Role-based access: employees can't create/update/archive, can acknowledge
- Custom category accepted alongside predefined categories

**Complexity**: L

---

### T035: Integration tests for advisory engine with company policies

**New file**: `tests/integration/test_advisory_company_policies.py`

Test cases:

- Advisory query with company policies uploaded: both statutory and company citations appear
- Advisory query without company policies: no regression (statutory-only answers)
- Company policy contradicts statute: response identifies conflict, cites both
- Zero company policy matches: response falls back to statutory only, no hallucination
- Company policy citation passes through citation validator without error
- Prompt injection in policy content is screened (does not reach LLM)

**Complexity**: L

---

### T036: Mobile app regression verification

**Files**: `apps/mobile/lib/features/compliance/screens/compliance_screen.dart` and any other mobile files referencing policies.

Verify:

- Deprecated `GET /employees/policies` endpoint still returns the same response shape
- `policy_type` values in seeded data are unchanged (mobile compliance screen matches on `wsh`, `fwa`, etc.)
- No runtime errors when mobile fetches policies from updated backend

This is a manual check or a lightweight script. The mobile app is not being modified but must not break.

**Complexity**: S

---

### T037: Unit tests for statutory floor check

**New file**: `tests/unit/test_statutory_floor_check.py`

Test cases:

- Leave policy with below-minimum annual leave (5 days) → `below_minimum`
- Leave policy meeting minimum (7 days) → `meets_minimum`
- Leave policy exceeding minimum (14 days) → `above_minimum`
- Policy with ambiguous text → `not_detected`
- Non-leave category → empty results
- Multiple entitlements checked in one policy

**Complexity**: S

---

## Summary

| Milestone | Todos     | Description                            | Effort  |
| --------- | --------- | -------------------------------------- | ------- |
| **M1**    | T001-T004 | Data model & dependencies              | 0.5 day |
| **M2**    | T005-T006 | Text extraction & validation           | 1 day   |
| **M3**    | T007-T009 | Policies router (full CRUD)            | 2 days  |
| **M4**    | T010-T017 | Advisory engine integration            | 3 days  |
| **M5**    | T018-T021 | Frontend API & design system           | 0.5 day |
| **M6**    | T022-T025 | Policy management UI                   | 3 days  |
| **M7**    | T026-T028 | Acknowledgment & onboarding            | 1 day   |
| **M8**    | T029-T032 | Compliance integration (T032 deferred) | 1 day   |
| **M9**    | T033-T037 | Testing + mobile regression            | 2 days  |

**Total: 37 todos across 9 milestones (~14 days)** (T032 deferred to v2)

### Dependency Graph

```
M1 (Model + Deps)
  ├── T001 ──┬──> T004 (seeding)
  │          ├──> T007 (router) ──> T008 (race protection)
  │          ├──> T010 (search) ──> T012 (advisory tool)
  │          └──> T032 (compliance dashboard)
  ├── T002 ──┘
  └── T003 ──> T005 (extraction) ──> T006 (quality)

M3 (Router) ──> T009 (deprecate old endpoint)

M4 (Advisory)
  T011 (thread company_id) ──> T012 (add tool) ──> T013 (injection screen)
  T012 ──> T014 (system prompt) ──> T015 (steering)
  T012 ──> T016 (citation accumulator) ──> T017 (citation validator)

M5 (Frontend foundation)
  T019 (design system) ──> T025 (chat citations)
  T018 (API types) ──> T022 (list page) ──> T024 (detail page)
  T018 ──> T023 (create modal) ──> T024

M7 (Acknowledgment)
  T026 ──> T027 (onboarding) ──> T028 (dashboard)

M8 (Compliance)
  T029 (floor check) ──> T030 (integrate) ──> T031 (frontend warnings)
```

### Red Team Findings Coverage

| Finding                                   | Severity    | Todo             |
| ----------------------------------------- | ----------- | ---------------- |
| F1: Prompt injection via PDF content      | CRITICAL    | T013             |
| F2: Zero-result hallucination             | MAJOR       | T010             |
| F3: Version creation race condition       | MAJOR       | T008             |
| F4: Extracted text quality                | MAJOR       | T006             |
| F5: Citation validator breaks             | SIGNIFICANT | T016, T017       |
| F7: Tool steering for statutory primacy   | SIGNIFICANT | T015             |
| B1: \_extract_citations() only handles KB | CRITICAL    | T016             |
| B2: Frontend type mismatch                | MAJOR       | T018             |
| B3: Dual endpoint confusion               | MAJOR       | T009             |
| C1: Advisory integration day 1            | CRITICAL    | All M4 tasks     |
| G1: Onboarding integration                | MAJOR       | T027, T028       |
| G2: Custom category management            | MAJOR       | T007 (free-text) |
