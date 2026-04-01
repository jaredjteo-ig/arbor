# Company Policy Upload & Integration -- Implementation Plan

**Date**: 2026-03-31
**Status**: Proposed
**Estimated Effort**: 8-12 days across 4 phases
**Prerequisites**: None (all referenced infrastructure exists)

---

## Architecture Decisions Summary

These decisions were made during analysis and confirmed by stakeholder input:

1. Company policies stored in the existing `CompanyPolicy` DataFlow model (NOT in the KB `Provision` table)
2. New `search_company_policies` tool added to the advisory engine (LLM decides when to call it)
3. New `"company-policy"` authority level (purple) for citations, distinct from statutory/guideline/best-practice
4. Synchronous PDF/DOCX extraction during upload with `pdfplumber`/`python-docx`
5. 9 predefined categories + custom categories
6. Warn (not block) when company policy is below statutory minimums
7. Employee acknowledgment required, integrated into onboarding
8. Version history from the start
9. Dedicated `/api/policies/` router (not buried in the employees router)

---

## Phase 1: Data Model & Backend Foundation

**Goal**: The `CompanyPolicy` model supports all required fields, a new dedicated router handles CRUD, and text extraction from uploaded files works end-to-end via API.

**Delivers**: Admin users can create, read, update, version, and deactivate company policies via API. File uploads extract text from PDF/DOCX/TXT. All operations are tenant-isolated.

### Task 1.1: Extend the CompanyPolicy DataFlow Model

**Files to modify**:
- `/Users/jaredteo/Documents/GitHub/arbor/src/hr_advisory/models/company_user.py`

**What to implement**:

Add fields to the existing `CompanyPolicy` model (currently at line 1040):

```
category: str = ""                # One of the 9 predefined categories or a custom string
version_number: int = 1           # Integer version, incremented on each new version
superseded_by_id: Optional[int] = None  # Points to the newer version's record ID
uploaded_by: Optional[int] = None  # User ID of the uploader
file_name: str = ""               # Original filename (e.g., "leave-policy-2026.pdf")
file_path: str = ""               # Storage path (local or S3 key)
file_type: str = ""               # "pdf", "docx", "txt", or "text" (manual entry)
file_size_bytes: int = 0          # Original file size in bytes
content_hash: str = ""            # SHA-256 of extracted content (deduplication)
extraction_status: str = ""       # "success", "partial", "failed", "timeout", or "" (manual entry)
requires_acknowledgment: bool = False
status: str = "active"            # "draft", "active", "archived"
```

Add a new `PolicyAcknowledgment` model:

```python
@db.model
class PolicyAcknowledgment:
    """Tracks employee acknowledgment of company policies."""
    company_id: int
    policy_id: int
    employee_id: int
    version_acknowledged: int = 1
    acknowledged_at: str = ""
    ip_address: str = ""
```

Add indexes for the new model on `company_id`, `policy_id`, and `employee_id`.

**Dependencies**: None
**Complexity**: S (model field additions + one new model)

---

### Task 1.2: Build the Text Extraction Service

**Files to create**:
- `/Users/jaredteo/Documents/GitHub/arbor/src/hr_advisory/services/policy_parser.py`

**What to implement**:

Three extraction functions plus a dispatcher:

- `extract_text_from_pdf(file_bytes: bytes, timeout_seconds: int = 15) -> tuple[str, str]`
  Returns `(extracted_text, extraction_status)`. Uses `pdfplumber` to iterate pages, concatenating text. Strips headers/footers heuristically (first/last line per page if repeated across 3+ pages). Returns `("", "failed")` if pdfplumber raises. Returns `("", "timeout")` if exceeds timeout.

- `extract_text_from_docx(file_bytes: bytes) -> tuple[str, str]`
  Returns `(extracted_text, extraction_status)`. Uses `python-docx` to walk paragraphs and table cells. Preserves paragraph breaks. Returns `("", "failed")` on error.

- `extract_text_from_txt(file_bytes: bytes) -> tuple[str, str]`
  Tries UTF-8 decode. Falls back to `chardet` for encoding detection. Returns `("", "failed")` on decode failure.

- `extract_text(file_bytes: bytes, file_type: str) -> tuple[str, str]`
  Dispatcher. Maps `"pdf"` / `"docx"` / `"txt"` to the appropriate function. Raises `ValueError` for unsupported types.

- `compute_content_hash(content: str) -> str`
  SHA-256 hex digest of the content string.

Content limits: truncate extracted text at 500,000 characters (about 100,000 words -- generous for any SME policy document).

**Dependencies**: Task 1.1 (for model understanding, but parser is independent)
**Complexity**: M

**Dependencies to install**:
- `pdfplumber` (add to `pyproject.toml`)
- `chardet` (add to `pyproject.toml`)
- `python-docx` already in `pyproject.toml`

---

### Task 1.3: Create the Dedicated Policies Router

**Files to create**:
- `/Users/jaredteo/Documents/GitHub/arbor/src/hr_advisory/api/routers/policies.py`

**Files to modify**:
- `/Users/jaredteo/Documents/GitHub/arbor/src/hr_advisory/api/platform.py` (register the new router)

**What to implement**:

A new FastAPI router at prefix `/policies` with these endpoints:

**GET /policies/** -- List all policies for the current user's company
- Filters: `category`, `status`, `is_active`
- Employees see only `status="active"` policies
- Returns: list of policy summaries (no full content -- too large)

**GET /policies/{policy_id}** -- Get a single policy with full content
- Tenant-isolated: verify `company_id` matches
- Returns: full policy record including content text

**POST /policies/** -- Create a new policy (Owner/HR Manager only)
- Accepts JSON body for manual text entry: `{ title, category, content, effective_date, requires_acknowledgment, status }`
- Sets `file_type = "text"`, `extraction_status = ""`
- Validates category is one of the 9 predefined values or a non-empty custom string
- Returns: created policy record

**POST /policies/upload** -- Upload a policy file (Owner/HR Manager only)
- Accepts multipart form: `file` + `title` + `category` + `effective_date` + `requires_acknowledgment`
- Validates: file size (10 MB max), MIME type (PDF, DOCX, TXT), extension
- Calls `policy_parser.extract_text()` synchronously
- Stores file to disk (same `UPLOAD_DIR` pattern as employee documents)
- Creates `CompanyPolicy` record with extracted text and file metadata
- Returns: policy record with extraction_status for UI feedback

**PUT /policies/{policy_id}** -- Update a policy (creates new version)
- When content changes: deactivates old record (`is_active = False`, `status = "archived"`, sets `superseded_by_id`), creates new record with `version_number + 1`
- When only metadata changes (title, category, effective_date): updates in place
- Returns: the new/updated policy record

**PUT /policies/{policy_id}/content** -- Update extracted content (Owner/HR Manager only)
- For manual editing of extracted text after upload review
- Updates `content` and `content_hash` fields
- Returns: updated policy record

**DELETE /policies/{policy_id}** -- Archive a policy (soft delete)
- Sets `status = "archived"`, `is_active = False`
- Does NOT delete the record or the file
- Returns: confirmation

**GET /policies/{policy_id}/versions** -- List version history
- Returns all records with the same `company_id` + `policy_type` + `category`, ordered by `version_number` desc
- Includes superseded records (archived versions)

**POST /policies/{policy_id}/acknowledge** -- Employee acknowledges a policy
- Creates a `PolicyAcknowledgment` record
- Any authenticated user can acknowledge (not role-restricted)
- Idempotent: re-acknowledging the same version is a no-op

**GET /policies/{policy_id}/acknowledgments** -- List acknowledgment status (Owner/HR Manager only)
- Returns which employees have acknowledged and which have not
- Includes acknowledgment timestamps

Helper functions (internal):
- `_list_policies(company_id, filters)` -- DataFlow ListNode query
- `_get_policy(policy_id, company_id)` -- single-record fetch with tenant check
- `_create_policy(params)` -- DataFlow CreateNode wrapper
- `_update_policy(policy_id, fields)` -- DataFlow UpdateNode wrapper
- `_deactivate_policy(policy_id)` -- set `is_active=False`, `status="archived"`

**Predefined categories** (constant list):
```python
POLICY_CATEGORIES = [
    "employment_terms",
    "leave_absence",
    "compensation_benefits",
    "workplace_safety",
    "fair_employment",
    "foreign_worker",
    "tax_filing",
    "general_hr",
    "code_of_conduct",
]
```

Custom categories: any non-empty string not in the predefined list is accepted. The category field is free-text, with the 9 predefined values offered as suggestions in the UI.

**Dependencies**: Task 1.1 (model fields), Task 1.2 (text extraction)
**Complexity**: L

---

### Task 1.4: Migrate Existing Policy Endpoint

**Files to modify**:
- `/Users/jaredteo/Documents/GitHub/arbor/src/hr_advisory/api/routers/employees.py`

**What to implement**:

The existing `GET /employees/policies` endpoint (line 1901) continues to work for backward compatibility with the current frontend. Internally, it delegates to the same DataFlow query. No code change needed in this file for now -- the new router serves the new endpoints, and the old one stays until the frontend migrates.

Add a deprecation comment to `list_policies()` in employees.py indicating the canonical endpoint is now `GET /policies/`.

**Dependencies**: Task 1.3
**Complexity**: S

---

### Task 1.5: Update Company Seeding for New Fields

**Files to modify**:
- `/Users/jaredteo/Documents/GitHub/arbor/src/hr_advisory/services/company_seeding.py`

**What to implement**:

Update `DEFAULT_POLICIES` (line 79) to include the new fields:
- Add `category` to each seeded policy (map existing `policy_type` values: `"leave"` -> `"leave_absence"`, `"fwa"` -> `"employment_terms"`, `"handbook"` -> `"general_hr"`, `"wsh"` -> `"workplace_safety"`)
- Add `version_number: 1`
- Add `file_type: "text"` (these are manual-entry policies, not uploads)
- Add `status: "active"`
- Add `extraction_status: ""`

Update `_seed_policies()` to include these fields in the CreateNode params.

**Dependencies**: Task 1.1
**Complexity**: S

---

### Task 1.6: Add Dependencies to pyproject.toml

**Files to modify**:
- `/Users/jaredteo/Documents/GitHub/arbor/pyproject.toml`

**What to implement**:

Add to dependencies:
- `pdfplumber>=0.10.0`
- `chardet>=5.0.0`

(`python-docx>=1.1.0` is already present at line 39.)

**Dependencies**: None
**Complexity**: S

---

## Phase 2: Advisory Engine Integration

**Goal**: The advisory engine searches company policies alongside statutory provisions and produces responses with clear authority-level separation in citations.

**Delivers**: When a user asks an HR question, the advisory engine checks their company's policies and references them alongside statutory provisions, with correct citation labelling.

### Task 2.1: Build the Company Policy Search Function

**Files to create**:
- `/Users/jaredteo/Documents/GitHub/arbor/src/hr_advisory/services/company_policy_search.py`

**What to implement**:

```python
def search_company_policies(
    query: str,
    company_id: int,
    category: str | None = None,
    limit: int = 5,
) -> list[dict]:
```

This function:
1. Queries `CompanyPolicyListNode` for all active policies belonging to `company_id`, optionally filtered by `category`
2. Scores each policy by keyword relevance against the `query` (same pattern as `_search_python_kb` in `advisory_engine.py` -- stopword removal, word overlap scoring)
3. Returns the top `limit` results as dicts with keys: `title`, `category`, `content_excerpt` (first 2000 chars of matching content), `effective_date`, `version_number`, `authority_level` (always `"company_policy"`)

The search is keyword-based for v1. The per-company corpus is small (typically under 20 documents, under 100 KB total text), so this is fast and adequate.

**Dependencies**: Task 1.1
**Complexity**: M

---

### Task 2.2: Add search_company_policies Tool to Advisory Engine

**Files to modify**:
- `/Users/jaredteo/Documents/GitHub/arbor/src/hr_advisory/agents/advisory_engine.py`

**What to implement**:

**A. New tool definition** -- Add to `TOOL_DEFINITIONS` list (after `get_company_context`):

```python
{
    "type": "function",
    "function": {
        "name": "search_company_policies",
        "description": (
            "Search the user's company-specific internal policies. Use this "
            "when the question relates to company benefits, entitlements, or "
            "internal procedures that may differ from statutory minimums. "
            "Returns matching company policies with titles, categories, and "
            "content excerpts. ALWAYS also call search_kb for the statutory "
            "position when company policy relates to a regulated area."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query about company policies",
                },
                "category": {
                    "type": "string",
                    "description": "Optional category filter",
                    "enum": [
                        "employment_terms",
                        "leave_absence",
                        "compensation_benefits",
                        "workplace_safety",
                        "fair_employment",
                        "foreign_worker",
                        "tax_filing",
                        "general_hr",
                        "code_of_conduct",
                    ],
                },
            },
            "required": ["query"],
        },
    },
}
```

**B. Tool execution handler** -- Add to `_execute_tool_call()` (after the `get_company_context` elif block):

```python
elif name == "search_company_policies":
    from hr_advisory.services.company_policy_search import search_company_policies
    # company_id is passed through the engine context, not the tool arguments
    results = search_company_policies(
        query=arguments.get("query", ""),
        company_id=company_id,  # from engine context
        category=arguments.get("category"),
        limit=5,
    )
    return json.dumps(results, default=str)
```

Note: `_execute_tool_call` currently does not receive `company_id`. The function signature needs to be extended to accept it, and `AdvisoryEngine.run()` must pass it through. Currently `company_id` is available in `run()` as a parameter.

**C. Update `_execute_tool_call` signature** from `(name, arguments)` to `(name, arguments, company_id=None)` and thread `company_id` through from `AdvisoryEngine.run()`.

**Dependencies**: Task 2.1
**Complexity**: M

---

### Task 2.3: Update the Advisory Engine System Prompt

**Files to modify**:
- `/Users/jaredteo/Documents/GitHub/arbor/src/hr_advisory/agents/advisory_engine.py`

**What to implement**:

Update `_build_system_prompt()` to add company policy awareness. Add these sections to the base prompt:

In the TOOLS section, add:
```
- search_company_policies: The user's company-specific internal policies.
  Use when the question involves company benefits, entitlements, or
  internal rules. ALWAYS also check the statutory position (search_kb)
  when answering about regulated areas like leave, CPF, or employment
  terms. This ensures you can tell the user whether their company exceeds,
  meets, or falls below statutory minimums.
```

Add a new COMPANY POLICY RULES section:
```
COMPANY POLICY RULES:
- ALWAYS state the statutory position first, then the company position.
- Use "Under the Employment Act..." for statutory. Use "Your company
  policy provides..." for company-specific rules.
- If a company policy appears to fall BELOW a statutory minimum, say so
  explicitly: "Note: your company policy states X, but the statutory
  minimum is Y. The statutory minimum applies regardless of the company
  policy."
- If a company policy EXCEEDS the statutory minimum, note this positively:
  "Your company provides X, which is above the statutory minimum of Y."
- If the company has no policy on a topic, say: "Your company does not
  have a specific policy on this. The statutory requirements apply."
- NEVER present company policy as having the force of law.
```

**Dependencies**: Task 2.2
**Complexity**: S

---

### Task 2.4: Add Citation Differentiation for Company Policies

**Files to modify**:
- `/Users/jaredteo/Documents/GitHub/arbor/src/hr_advisory/agents/advisory_engine.py`

**What to implement**:

When the advisory engine returns results from `search_company_policies`, the tool response already includes `authority_level: "company_policy"`. The LLM response may naturally include citations.

Check the existing citation extraction logic (if any `_extract_citations` function exists in the engine or the streaming endpoint). Ensure that when citations are parsed from the LLM response, the "company-policy" authority level is recognized and passed through to the frontend.

The streaming advisory endpoint (`/advisory/stream` or similar) must include `authority_level` in any citation metadata it sends to the frontend.

**Dependencies**: Task 2.2
**Complexity**: S

---

## Phase 3: Frontend -- Policy Management UI

**Goal**: HR Managers can upload, create, edit, version, and archive policies through the web UI. Employees can view active policies and acknowledge them.

**Delivers**: The policies page transforms from a read-only accordion into a full policy management interface with upload capability, content preview, and version history.

### Task 3.1: Update Frontend API Service

**Files to modify**:
- `/Users/jaredteo/Documents/GitHub/arbor/apps/web/src/services/api/employees.ts`

**What to implement**:

Add new TypeScript types:

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
```

Add new API methods (can be in the same file or a new `policies.ts` service file):

```typescript
const policiesApi = {
  list(filters?: { category?: string; status?: string }): Promise<{ policies: PolicyRecord[]; count: number }>;
  get(policyId: number): Promise<PolicyRecord>;
  create(data: { title: string; category: string; content: string; effective_date: string; requires_acknowledgment: boolean; status: string }): Promise<PolicyRecord>;
  upload(formData: FormData): Promise<PolicyRecord>;
  update(policyId: number, data: Partial<PolicyRecord>): Promise<PolicyRecord>;
  updateContent(policyId: number, content: string): Promise<PolicyRecord>;
  archive(policyId: number): Promise<{ message: string }>;
  versions(policyId: number): Promise<{ versions: PolicyRecord[] }>;
  acknowledge(policyId: number): Promise<{ message: string }>;
  acknowledgments(policyId: number): Promise<{ acknowledgments: PolicyAcknowledgmentRecord[]; pending_count: number }>;
};
```

**Dependencies**: Phase 1 complete (API endpoints exist)
**Complexity**: S

---

### Task 3.2: Build the Policy List Page (Admin View)

**Files to modify**:
- `/Users/jaredteo/Documents/GitHub/arbor/apps/web/src/app/(dashboard)/policies/page.tsx`

**What to implement**:

Complete rewrite of the current page. The new page has:

**Header section**:
- Title "Company Policies" with `FileText` icon (existing pattern)
- Subtitle: "Manage, version, and distribute company policies."
- "Add Policy" button (visible only for owner/hr_manager roles) -- opens creation modal

**Filter bar**:
- Status tabs: All / Active / Draft / Archived (with counts)
- Search input (debounced, searches titles and content)
- Category filter dropdown (multi-select, the 9 predefined categories + any custom ones found in the data)

**Policy list**:
- Grouped by category (collapsible sections)
- Each policy row is an `AppCard variant="flat"` showing:
  - Title, version badge (`v1.0`), status badge (Active/Draft/Archived)
  - Effective date, file type icon (PDF/DOCX/text)
  - Pending acknowledgment count (if `requires_acknowledgment` is true)
- Click navigates to detail page (or opens detail panel)

**Empty state**:
- "No company policies yet. Add your first policy to get started."
- Primary CTA button to add first policy

**Employee view** (same route, role-gated):
- No "Add Policy" button
- Only active policies shown (no Draft/Archived tabs)
- Acknowledgment banner at top when policies need signing
- "[NEW]" badge on policies updated since last acknowledgment

**Dependencies**: Task 3.1
**Complexity**: L

---

### Task 3.3: Build the Policy Creation/Upload Modal

**Files to create**:
- `/Users/jaredteo/Documents/GitHub/arbor/apps/web/src/components/policies/PolicyCreateModal.tsx`

**What to implement**:

A modal dialog (following existing modal patterns in the codebase) with two tabs:

**Tab 1: "Write Policy"** (manual text entry)
- Title field (required)
- Category dropdown (9 predefined options + "Other" with free-text input)
- Content textarea (rich text not required for v1 -- plain text with paragraph breaks)
- Effective date picker (required)
- "Requires employee acknowledgment" checkbox
- "Save as Draft" / "Publish" buttons

**Tab 2: "Upload Document"** (file upload)
- File picker: accepts `.pdf`, `.docx`, `.txt` (max 10 MB)
- Title field (auto-populated from filename, editable)
- Category dropdown (same as Tab 1)
- Effective date picker
- "Requires employee acknowledgment" checkbox
- Upload button

**After upload**: show content preview step:
- Display extracted text in a scrollable container
- Show extraction status badge (success / partial / failed)
- "Edit" button to allow manual correction of extracted text
- If extraction failed: warning message + manual text entry area
- "Save as Draft" / "Publish" buttons

**Validation**:
- Title: required, max 200 characters
- Category: required (from predefined list or non-empty custom)
- Content: required for publish (can be empty for draft)
- Effective date: required, must be a valid date
- File: max 10 MB, allowed extensions only

**Dependencies**: Task 3.1
**Complexity**: M

---

### Task 3.4: Build the Policy Detail View

**Files to create**:
- `/Users/jaredteo/Documents/GitHub/arbor/apps/web/src/app/(dashboard)/policies/[id]/page.tsx`

**What to implement**:

Detail page with tabs (following the pattern from `/employees/[id]` which uses horizontal tabs):

**Header**:
- Back link to `/policies`
- Policy title, category badge, version badge, status badge
- Action buttons (admin only): "Edit", "Archive", "Upload New Version"

**Tab: Overview**
- Summary card: title, category, effective date, version, status, uploaded by, file details (name, size, type)
- Statutory domain mapping: which regulatory domains this policy category maps to
- Acknowledgment summary: X of Y employees acknowledged (admin only)

**Tab: Content**
- Full policy text in a readable format
- "Edit Content" button (admin only) -- inline editing of text content

**Tab: Versions**
- List of all versions (current + archived), ordered newest first
- Each row: version number, effective date, status, uploaded by, date
- "View" link to see the content of any previous version

**Tab: Acknowledgments** (admin only)
- Table of employees: name, role, acknowledged (yes/no), date
- Filter: pending / completed
- "Send Reminder" button for pending employees (future -- log the intent for now)

**Employee view**: same page without admin tabs (no Acknowledgments tab), no action buttons, but with an "I Acknowledge" button if acknowledgment is required and the employee has not yet acknowledged this version.

**Dependencies**: Task 3.2, Task 3.3
**Complexity**: L

---

### Task 3.5: Add "company-policy" Authority Level to Design System

**Files to modify**:
- `/Users/jaredteo/Documents/GitHub/arbor/apps/web/src/app/globals.css`
- `/Users/jaredteo/Documents/GitHub/arbor/apps/web/src/components/design-system/SourceCitation.tsx`

**What to implement**:

**A. CSS variables** (add after the existing authority badge variables at line 45):

```css
--color-authority-company-policy: #7C3AED;      /* Purple */
--color-authority-company-policy-bg: #F5F3FF;    /* Light purple */
```

**B. SourceCitation component** -- extend `AuthorityLevel` type:

Change from:
```typescript
export type AuthorityLevel = "statutory" | "guideline" | "best-practice";
```
To:
```typescript
export type AuthorityLevel = "statutory" | "guideline" | "best-practice" | "company-policy";
```

Add to `authorityStyles`:
```typescript
"company-policy":
  "bg-[var(--color-authority-company-policy-bg)] text-[var(--color-authority-company-policy)] border-[var(--color-authority-company-policy)]",
```

Add to `authorityLabels`:
```typescript
"company-policy": "Company Policy",
```

**C. Update ProvisionViewer** (`/Users/jaredteo/Documents/GitHub/arbor/apps/web/src/components/advisory/ProvisionViewer.tsx`) to include the new authority style mapping.

**Dependencies**: None (can be done in parallel with other frontend tasks)
**Complexity**: S

---

### Task 3.6: Update Advisory Chat to Show Company Policy Citations

**Files to modify**:
- `/Users/jaredteo/Documents/GitHub/arbor/apps/web/src/components/advisory/ChatContainer.tsx` (or wherever citations are rendered in the advisory response)
- `/Users/jaredteo/Documents/GitHub/arbor/apps/web/src/components/shadow-agent/InlineAnnotation.tsx` (if applicable)

**What to implement**:

When the advisory response includes citations with `authority_level: "company_policy"`, render them using the purple `SourceCitation` badge. The citation label should show the policy title (e.g., "[Annual Leave Policy, v3.0]") rather than a statutory section number.

Ensure the existing rendering logic handles the new authority level without errors (it should fall through to a default style if the level is unrecognized, but explicitly supporting it is better).

**Dependencies**: Task 3.5, Task 2.4
**Complexity**: S

---

## Phase 4: Compliance Integration & Statutory Floor Warnings

**Goal**: The compliance engine flags company policies that fall below statutory minimums. The upload flow warns admins when this is detected.

**Delivers**: When an HR manager uploads a leave policy with entitlements below the statutory minimum, the system warns (but does not block). The compliance dashboard shows company policy coverage status.

### Task 4.1: Build the Statutory Floor Check Service

**Files to create**:
- `/Users/jaredteo/Documents/GitHub/arbor/src/hr_advisory/services/statutory_floor_check.py`

**What to implement**:

```python
def check_policy_against_statutory_floor(
    policy_content: str,
    category: str,
) -> list[dict]:
```

For v1, this only checks leave-related policies (`category == "leave_absence"`). It:

1. Searches the policy content for numeric values near keywords like "annual leave", "sick leave", "hospitalisation" using regex patterns
2. Compares extracted values against known statutory minimums:
   - Annual leave: 7 days minimum (EA s.88, first year of service)
   - Outpatient sick leave: 14 days minimum (EA s.89)
   - Hospitalisation leave: 60 days maximum entitlement (inclusive of sick leave)
3. Returns a list of findings, each with:
   - `field`: which entitlement was checked (e.g., "annual_leave")
   - `company_value`: the value found in the policy (or `null` if not detected)
   - `statutory_minimum`: the statutory floor
   - `status`: "above_minimum", "meets_minimum", "below_minimum", "not_detected"
   - `message`: human-readable description

This is a best-effort extraction. If the policy text is ambiguous or the values cannot be found, the status is `"not_detected"` with a message explaining that manual verification is recommended.

Returns an empty list for non-leave categories (no statutory floor checks defined yet).

**Dependencies**: None
**Complexity**: M

---

### Task 4.2: Integrate Statutory Floor Check into Upload Flow

**Files to modify**:
- `/Users/jaredteo/Documents/GitHub/arbor/src/hr_advisory/api/routers/policies.py`

**What to implement**:

In the `POST /policies/` and `POST /policies/upload` endpoints, after content is available:
1. Call `check_policy_against_statutory_floor(content, category)`
2. Include the findings in the response under a `statutory_floor_warnings` key
3. Do NOT block the upload -- always allow the policy to be saved

The response shape becomes:
```json
{
  "policy": { ... },
  "statutory_floor_warnings": [
    {
      "field": "annual_leave",
      "company_value": 5,
      "statutory_minimum": 7,
      "status": "below_minimum",
      "message": "Your policy states 5 days annual leave. The statutory minimum under the Employment Act is 7 days for the first year of service."
    }
  ]
}
```

Also add a `GET /policies/{policy_id}/compliance-check` endpoint that runs the floor check on demand.

**Dependencies**: Task 4.1, Task 1.3
**Complexity**: S

---

### Task 4.3: Show Statutory Floor Warnings in Frontend

**Files to modify**:
- `/Users/jaredteo/Documents/GitHub/arbor/apps/web/src/components/policies/PolicyCreateModal.tsx`
- `/Users/jaredteo/Documents/GitHub/arbor/apps/web/src/app/(dashboard)/policies/[id]/page.tsx`

**What to implement**:

In the upload/create flow: after the API returns, if `statutory_floor_warnings` contains any `"below_minimum"` findings:
- Show a warning banner (amber, using existing color variables) above the Save/Publish buttons
- The banner shows each below-minimum finding in plain language
- Include a "Publish Anyway" button (the warning does not block)

In the policy detail view (Overview tab): if the policy has below-minimum findings:
- Show a persistent warning card with the compliance details
- Link to the relevant statutory provision for reference

**Dependencies**: Task 4.2, Task 3.3, Task 3.4
**Complexity**: S

---

### Task 4.4: Extend Compliance Dashboard with Company Policy Status

**Files to modify**:
- `/Users/jaredteo/Documents/GitHub/arbor/src/hr_advisory/api/routers/compliance.py`

**What to implement**:

In the `GET /compliance/status/{company_id}` endpoint, add a `company_policies` section to the response:

```json
{
  "company_id": 1,
  "overall_status": "review_needed",
  "domains": { ... },
  "company_policies": {
    "total_policies": 5,
    "categories_covered": ["leave_absence", "workplace_safety", "general_hr"],
    "categories_missing": ["employment_terms", "compensation_benefits", "fair_employment", "foreign_worker", "tax_filing", "code_of_conduct"],
    "below_minimum_warnings": 1,
    "acknowledgment_pending": 12
  }
}
```

This queries the `CompanyPolicy` table for the company and summarizes coverage. No changes to the existing statutory domain checks.

**Dependencies**: Task 1.1
**Complexity**: S

---

## Dependency Graph

```
Phase 1 (Foundation):
  1.1 Model changes ─────┬──> 1.3 Policies router ──> 1.4 Migrate old endpoint
  1.2 Text extraction ───┘              │
  1.5 Update seeding <── 1.1            │
  1.6 Add pyproject deps                │
                                        v
Phase 2 (Advisory):                     
  2.1 Policy search <── 1.1             
  2.2 Advisory tool <── 2.1             
  2.3 System prompt <── 2.2             
  2.4 Citation differentiation <── 2.2  
                                        
Phase 3 (Frontend):                     
  3.1 API service types <── Phase 1     
  3.2 Policy list page <── 3.1         
  3.3 Create/upload modal <── 3.1      
  3.4 Detail view <── 3.2, 3.3        
  3.5 Design system authority level (independent)
  3.6 Chat citations <── 3.5, 2.4     
                                        
Phase 4 (Compliance):                   
  4.1 Statutory floor check (independent)
  4.2 Integrate into upload <── 4.1, 1.3
  4.3 Frontend warnings <── 4.2, 3.3   
  4.4 Compliance dashboard <── 1.1     
```

---

## Task Summary

| Task | Description | Files | Complexity | Phase |
|------|-------------|-------|------------|-------|
| 1.1 | Extend CompanyPolicy model + add PolicyAcknowledgment | models/company_user.py | S | 1 |
| 1.2 | Build text extraction service | services/policy_parser.py (new) | M | 1 |
| 1.3 | Create dedicated policies router | api/routers/policies.py (new), api/platform.py | L | 1 |
| 1.4 | Migrate/deprecate old endpoint | api/routers/employees.py | S | 1 |
| 1.5 | Update company seeding | services/company_seeding.py | S | 1 |
| 1.6 | Add pyproject dependencies | pyproject.toml | S | 1 |
| 2.1 | Build company policy search | services/company_policy_search.py (new) | M | 2 |
| 2.2 | Add tool to advisory engine | agents/advisory_engine.py | M | 2 |
| 2.3 | Update system prompt | agents/advisory_engine.py | S | 2 |
| 2.4 | Citation differentiation | agents/advisory_engine.py | S | 2 |
| 3.1 | Update frontend API service | services/api/employees.ts | S | 3 |
| 3.2 | Build policy list page | policies/page.tsx | L | 3 |
| 3.3 | Build create/upload modal | components/policies/PolicyCreateModal.tsx (new) | M | 3 |
| 3.4 | Build detail view | policies/[id]/page.tsx (new) | L | 3 |
| 3.5 | Add company-policy authority level | globals.css, SourceCitation.tsx | S | 3 |
| 3.6 | Update chat citations | ChatContainer.tsx, ProvisionViewer.tsx | S | 3 |
| 4.1 | Build statutory floor check | services/statutory_floor_check.py (new) | M | 4 |
| 4.2 | Integrate into upload flow | api/routers/policies.py | S | 4 |
| 4.3 | Show warnings in frontend | PolicyCreateModal.tsx, policies/[id]/page.tsx | S | 4 |
| 4.4 | Extend compliance dashboard | api/routers/compliance.py | S | 4 |

**Totals**: 20 tasks, 4 new files, 10 modified files
- Phase 1: 3-4 days (model + parser + router + seeding)
- Phase 2: 2-3 days (search + advisory tool + prompt + citations)
- Phase 3: 3-4 days (API types + list page + modal + detail view + design system)
- Phase 4: 1-2 days (floor check + warnings + compliance)

---

## Testing Strategy

### Phase 1 Tests
- **Unit**: Text extraction from sample PDF, DOCX, TXT files (include edge cases: empty file, corrupted PDF, non-UTF8 text)
- **Unit**: Content hash computation
- **Integration**: CRUD endpoints with tenant isolation (Company A cannot see Company B policies)
- **Integration**: File upload with size and type validation
- **Integration**: Version creation (upload new version, verify old is archived)

### Phase 2 Tests
- **Unit**: Company policy search scoring and filtering
- **Integration**: Advisory engine with company policies uploaded -- verify both statutory and company citations appear
- **Integration**: Advisory engine without company policies -- verify no regression (statutory-only answers)
- **Red team**: Ask a question where company policy contradicts statute -- verify the response correctly identifies the conflict

### Phase 3 Tests
- **Manual**: Full upload flow (file picker, extraction preview, edit, save)
- **Manual**: Employee acknowledgment flow
- **Manual**: Version history navigation
- **Manual**: Role-based visibility (admin vs employee views)

### Phase 4 Tests
- **Unit**: Statutory floor extraction from sample policy texts
- **Integration**: Upload a below-minimum leave policy, verify warning is returned
- **Integration**: Compliance status endpoint includes company policy summary
- **Manual**: Warning display in upload flow and detail view

---

## Risk Mitigations (from Analysis)

| Risk | Mitigation Built Into Plan |
|------|---------------------------|
| Tenant data leakage | All queries filter by `company_id` from auth context (Task 1.3). Integration tests verify isolation. |
| Trust contamination (company policy cited as law) | Separate tool, separate authority level, explicit system prompt instructions (Tasks 2.2, 2.3, 3.5). |
| Below-minimum policies accepted silently | Statutory floor check warns but does not block (Tasks 4.1-4.3). Advisory engine explicitly flags conflicts (Task 2.3). |
| PDF extraction garbage | Content preview step allows manual editing (Task 3.3). Extraction status communicated to user. |
| Advisory latency increase | Company policy search is keyword-based over small corpus (< 200 ms). LLM decides when to call (not always). |
| Version conflicts | Automatic deactivation of old version when new version is created (Task 1.3). Only active versions are searchable. |
