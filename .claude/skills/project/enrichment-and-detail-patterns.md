---
name: enrichment-and-detail-patterns
description: "Two interlocking anti-patterns and their canonical fixes: (1) raw-ID leakage — backend list endpoints return employee_id / candidate_id / created_by but the frontend has no name to render, falling back to 'Employee #N'; (2) hidden-detail — backend stores rich JSON columns (responses, scores, sections, payload) but the frontend renders only summary numbers. Codified from rounds 3, 4, 5, 6 (commits 0da4dda, 5938e06, 5e07a00, d734d3d). Use when adding any new list endpoint, expanding a card, or auditing for either anti-pattern."
---

# Enrichment & Detail Patterns

Two related anti-patterns surfaced repeatedly in rounds 3–6 of the
obayashi redteam. Together they account for ~30 of the issues fixed
across 7 endpoints and 17+ frontend surfaces. They share a common shape:
**the backend has the data, but the contract between backend and
frontend leaves it locked away from the user.**

This skill is the canonical playbook for both.

---

## A. Raw-ID leakage (`Employee #N`, `Candidate #N`, `#${id}`)

### A.1 The anti-pattern

```python
# Backend: returns raw rows
@router.get("/appraisals/my")
async def list_my_appraisals(...):
    appraisals = dataflow_crud.list_records("Appraisal", filters)
    return {"appraisals": appraisals, "count": len(appraisals)}
```

```tsx
// Frontend: falls back to the only thing it has
{
  a.employee_name || `Employee #${a.employee_id}`;
}
```

The `Employee.name` field doesn't exist (name lives on `User.name`),
so `a.employee_name` is undefined, so HR sees "Employee #6 / Employee
#5 / Employee #4". The user reads "the system doesn't know who works
here" and trust collapses.

This bug class has hit, at minimum: **policies/[id] acknowledgments
(28 rows live), appraisals My Appraisals (3 rows live), exit-interviews,
goals, recognition, retention, training records / mandatory /
certifications, projects allocations + timesheets, shifts assignments,
inventory requests, employee notes (created_by), payroll components,
recruitment interviews + scorecards, employees onboarding row.**

### A.2 The canonical fix — three layers

**Layer 1 — shared backend helper** (`api/routers/_helpers.py`):

```python
def _resolve_employee_names(
    employee_ids: set[int], company_id: int
) -> dict[int, str]:
    """Bulk-resolve employee_id → User.name.

    Employee has no name column; the canonical display name lives on
    the linked User row. Returns dict keyed by employee_id; missing
    entries map to "" so callers can fall back gracefully.
    """
    if not employee_ids:
        return {}
    employees = dataflow_crud.list_records(
        "Employee", {"company_id": company_id}
    )
    uid_to_eids: dict[int, list[int]] = {}
    for emp in employees:
        eid = emp.get("id")
        if eid not in employee_ids:
            continue
        uid = emp.get("user_id")
        if uid:
            uid_to_eids.setdefault(uid, []).append(eid)
    if not uid_to_eids:
        return {}
    name_map: dict[int, str] = {}
    users = dataflow_crud.list_records("User", {"company_id": company_id})
    for user in users:
        uid = user.get("id")
        if uid in uid_to_eids:
            name = user.get("name", "")
            for eid in uid_to_eids[uid]:
                name_map[eid] = name
    return name_map


def _resolve_user_names(
    user_ids: set[int], company_id: int
) -> dict[int, str]:
    """Bulk-resolve user_id → User.name.

    Used for `created_by`, `approved_by`, `actor_id` columns whose
    value is a raw User.id (not an Employee.id).
    """
    if not user_ids:
        return {}
    users = dataflow_crud.list_records("User", {"company_id": company_id})
    return {
        u.get("id"): u.get("name", "")
        for u in users
        if u.get("id") in user_ids
    }
```

**Layer 2 — call the helper in every list endpoint that returns IDs**:

```python
@router.get("/projects/{project_id}/assignments")
async def list_assignments(...):
    assignments = dataflow_crud.list_records("ProjectAssignment", {...})
    name_map = _resolve_employee_names(
        {a.get("employee_id") for a in assignments if a.get("employee_id")},
        company_id,
    )
    for a in assignments:
        a["employee_name"] = name_map.get(a.get("employee_id"), "")
    return {"assignments": assignments, "count": len(assignments)}
```

**Layer 3 — frontend never falls back to `#${id}`**:

```tsx
// Right
{
  a.employee_name || "—";
}

// Wrong (leaks the raw ID when name is missing)
{
  a.employee_name || `Employee #${a.employee_id}`;
}
{
  a.employee_name || a.employee_id;
} // even worse — raw int
{
  `Created by #${note.created_by}`;
} // hardcoded leak
```

### A.3 Special case — names live on User, not Employee

The `Employee` model has NO `name`, `email`, or `full_name` columns.
Every place that previously read `emp.get("full_name")` got an empty
string. Specific known offenders the helper should hide:

```python
# DO NOT do this — `full_name` doesn't exist on Employee
not_acknowledged = [
    {"employee_id": emp.get("id"),
     "full_name": emp.get("full_name", ""),  # always ""
     "email": emp.get("email", "")}          # always ""
    for emp in all_employees
]

# DO this
eid_to_name: dict[int, str] = {}
eid_to_email: dict[int, str] = {}
uid_to_eids: dict[int, list[int]] = {}
for emp in all_employees:
    eid, uid = emp.get("id"), emp.get("user_id")
    if eid and uid:
        uid_to_eids.setdefault(uid, []).append(eid)
if uid_to_eids:
    users = dataflow_crud.list_records("User", {"company_id": company_id})
    for user in users:
        uid = user.get("id")
        if uid in uid_to_eids:
            for eid in uid_to_eids[uid]:
                eid_to_name[eid] = user.get("name", "")
                eid_to_email[eid] = user.get("email", "")
```

### A.4 The audit method

**Static scan first** (cheap, finds every theoretical leak):

```bash
# Find every #${...id} fallback pattern in JSX
grep -rEn '#\$\{[^}]+_id\}' apps/web/src --include='*.tsx' --include='*.ts'

# Find raw integer fallbacks (`comp.employee_name || comp.employee_id`)
grep -rEn '_name\s*\|\|\s*[a-z]+\.[a-z_]+_id\b' apps/web/src --include='*.tsx'

# Find hardcoded #N renders with no fallback at all
grep -rEn '>#\{[^}]+_id\}<|`#\$\{[^}]+_id\}`' apps/web/src --include='*.tsx'

# Sanity: which backend list endpoints emit *_name fields already
grep -rEn '"employee_name"|"candidate_name"|"reviewer_name"|"created_by_name"' \
  src/hr_advisory/api/routers/ --include='*.py'
```

**Live verification second** (Playwright; finds which leaks are
actually reachable in seeded data):

```js
// Generic page-grep evaluator — paste into mcp__playwright__browser_evaluate
() => {
  const text = (document.querySelector("main") || document.body).innerText;
  const patterns = [
    /Employee #\d+/g,
    /Candidate #\d+/g,
    /Manager #\d+/g,
    /Reviewer #\d+/g,
    /User #\d+/g,
    /Emp #\d+/g,
    /Created by #\d+/g,
    /Template #\d+/g,
    /Project #\d+/g,
    /Question #\d+/g,
    /Assignment #\d+/g,
  ];
  const hits = [];
  for (const p of patterns) {
    const m = text.match(p);
    if (m) hits.push(...m);
  }
  const bare = (text.match(/(?:^|\s|\t|>)#\d+(?:$|\s|\t|<)/g) || []).map((s) =>
    s.trim(),
  );
  return {
    url: location.pathname,
    hits: [...new Set(hits)],
    bareIds: [...new Set(bare)],
  };
};
```

Walk every authenticated page as both an HR-manager (Grace Koh,
`grace.koh@central-solutions.sg`) and an employee (Lily Phang,
`lily.phang@central-solutions.sg`); password is `Employee2026!`.

### A.5 What is NOT a leak (don't over-eagerly fix these)

- `(#${skill.certification_number})` — `certification_number` is a real
  cert serial like "PMP #12345", not an internal DB id
- `key={emp.employee_id}` — React key, never rendered
- `value={newAssignment.employee_id}` — form select state
- ID fields in API request bodies / Zod schemas

The static-grep predicate worth filtering on: `#${...}` literals that
appear inside JSX text content, not inside attributes or hooks.

### A.6 Regression coverage

`tests/regression/test_redteam3_id_leak.py` pins:

- `test_policy_acknowledgments_resolve_names_and_emails`
- `test_project_assignments_resolve_employee_name`
- `test_project_timesheets_resolve_employee_and_project_name`
- `test_shifts_schedule_returns_flat_assignments_with_names`
- `test_inventory_requests_resolve_employee_name`
- `test_employee_notes_resolve_created_by_name`
- `test_resolve_employee_names_handles_missing_user`

`tests/regression/test_redteam2_polish.py::test_appraisals_my_resolves_employee_names`
also covers the appraisal case from round-3a.

When you add a new list endpoint that exposes employee_id, ADD A
PINNING TEST in the same shape.

---

## B. Hidden-detail anti-pattern (rich JSON column never rendered)

### B.1 The anti-pattern

The DB stores rich structured data in JSON-as-text columns:

```python
class ExitInterview:
    survey_payload: str = ""  # JSON, 6 questions worth of answers
    themes: str = ""          # JSON list, derived theme tally

class Appraisal:
    responses: str = ""       # JSON {q1: "...", q2: "..."}
    scores: str = ""          # JSON {delivery: 4, collaboration: 5}

class AppraisalTemplate:
    sections: str = ""        # JSON [{title, weight, questions: [...]}]

class CompanyPolicy:
    content: str = ""         # full policy body markdown

class ComplianceGap:  # response shape, not a model
    provisions_found: int     # but the actual provisions list is loaded server-side
```

The backend does the heavy lifting (search KB, derive themes, run
`_query_domain_provisions`, load templates), then returns ONLY the
summary number to the frontend. The list view shows a one-line card.
There's no way to drill in.

This was the exit-interview UX bug ("themes only, can't read what they
wrote"), the appraisal bug ("score only, can't see per-criterion"), the
goals bug ("progress %, can't see check-in history"), the activity feed
bug ("Appraisal submitted: Priya Nair" — dead text, can't navigate to
the appraisal), and the compliance bug ("8 provisions found, can't see
which ones").

### B.2 The canonical fix — expand-in-place pattern

For tables/cards: add a chevron toggle that reveals the full payload
parsed and rendered semantically.

```tsx
// State
const [expandedId, setExpandedId] = useState<number | null>(null);

// Helper — parse JSON-as-text without throwing
function parseJsonObject(
  raw: string | null | undefined,
): Record<string, unknown> | null {
  if (!raw) return null;
  try {
    const obj = JSON.parse(raw);
    return obj && typeof obj === "object" && !Array.isArray(obj)
      ? (obj as Record<string, unknown>)
      : null;
  } catch {
    return null;
  }
}

// Reusable Likert / score bar (mirrors what we shipped in
// exit-interviews/page.tsx + appraisals/page.tsx)
function ScoreBar({ score }: { score: number }) {
  return (
    <div className="flex items-center gap-1">
      {[1, 2, 3, 4, 5].map((n) => (
        <div
          key={n}
          className={`h-2 w-6 rounded-full ${
            n <= score
              ? "bg-[var(--color-primary)]"
              : "bg-[var(--color-gray-200)]"
          }`}
        />
      ))}
      <span className="ml-1 text-xs tabular-nums text-[var(--color-gray-600)]">
        {score}/5
      </span>
    </div>
  );
}

// Render
<tr onClick={() => setExpandedId(isExpanded ? null : iv.id)}>
  <td>{isExpanded ? <ChevronUp /> : <ChevronDown />}</td>
  <td>{iv.employee_name}</td>
  ...
</tr>;
{
  isExpanded && (
    <tr>
      <td colSpan={6}>
        <ResponseDetail
          interview={iv}
          payload={parseJsonObject(iv.survey_payload)}
        />
      </td>
    </tr>
  );
}
```

### B.3 Specific shipped cases (use these as the templates)

| Surface                     | Hidden field                               | Now renders                                            |
| --------------------------- | ------------------------------------------ | ------------------------------------------------------ |
| `/exit-interviews`          | `survey_payload`                           | Q1+Q2 Likert bars + Q3 reason chips + Q4/5/6 free text |
| `/appraisals` My Appraisals | `responses`, `scores`, template `sections` | per-criterion bars + per-question Q&A                  |
| `/goals`                    | `GET /goals/{id}/checkins`                 | Past check-in history, dated, with `actor_name`        |
| `/strategy/lifecycle` feed  | `entity_type` + `entity_id`                | Each row is now a Next `Link` to the relevant page     |
| `/compliance/{category}`    | `provisions_sample` (top 10)               | Inline section + title + plain_summary per gap         |
| `/dashboard` metric tiles   | (no JSON column — drill-in)                | Tiles wrap in `Link` to /compliance, /advisory         |

### B.4 Where it does NOT apply

- Aggregate-by-design surfaces (workforce composition pie, headcount
  count) — the rolled-up number IS the value
- Performance-critical tables that already deep-link via row click to
  a separate detail page (the row click IS the drill-in)
- Audit-log entries that intentionally summarize for compactness (the
  full record lives on the entity that was modified)

### B.5 The audit method

**Static scan** (find JSON-as-text columns the frontend reads but
doesn't expand):

```bash
# Backend: find string-typed structured columns
grep -rEn 'sections: str|responses: str|scores: str|payload: str|content: str' \
  src/hr_advisory/models/ --include='*.py'

# Frontend: find every JSON.parse to see what's already being unpacked
grep -rn 'JSON.parse' apps/web/src/app --include='*.tsx'

# API types: find string-typed structured fields the type system warns about
grep -rEn '\b(payload|responses|sections|content|raw|details)\b\s*:\s*string' \
  apps/web/src/services/api --include='*.ts'
```

**Heuristic — "if the backend returns N tokens of JSON and the UI
shows one number, that's the bug shape":** trace the model field
through `serialize_*` / API response types / frontend renderers. If
nothing parses or renders the structured part, you have a hidden-detail
case.

### B.6 Regression coverage

The frontend changes don't have unit tests but ARE exercised by live
Playwright walks (rounds 5/6/7). Backend changes have:

- `tests/regression/test_redteam2_polish.py::test_appraisal_period_close_marks_completed`
- `tests/regression/test_redteam3_id_leak.py` (the activity-feed
  click-through `entity_type/entity_id` shape is implicitly tested via
  the full-suite green; future work could pin it explicitly).

When adding a new expand surface, write at least one Playwright test
that clicks the chevron and asserts the parsed-detail markers are
visible.

---

## C. Audit-method protocol (use this for any future round)

The shape of every redteam round in this project converges on:

1. **Static catalog first** — grep both layers (`apps/web/src/**`
   for render patterns, `src/hr_advisory/api/routers/**` for response
   shapes). Build a candidate-fix list before booting the browser.
2. **Live walk via Playwright MCP, both roles** — login as Grace and
   Lily, hit every page in the sidebar, evaluate the leak-detector
   regex on `document.body.innerText`. Live data may not reach every
   theoretical leak — those become "defensive" not "user-visible"
   findings.
3. **Triage by severity** — H = user-visible broken core flow; M =
   either hidden by demo data emptiness OR cosmetic-but-real; L =
   polish.
4. **Ship in batches** — H tier first (highest user impact), then M,
   then L. One bundled commit + one rebuild per batch. Local-validate
   before commit (`npx tsc --noEmit`, regression tests for the
   touched routers).
5. **Re-walk after deploy** — same Playwright script confirms the
   live leak count is zero. Screenshots into
   `workspaces/<workspace>/04-validate/r<n>-fixed-*.png` as
   audit-trail artefacts.

This protocol is what closed rounds 3 → 7 in this session.

---

## Cross-references

- `security-patterns.md` P40-P48 — the matching shape for several of
  these issues (e.g. P45 hidden-detail pattern lives in security-patterns
  too)
- `auth-security.md` — RBAC role-page matrix (related to "what should be
  visible to whom")
- `lifecycle-dashboard.md` — the activity feed click-through is a
  Strategy Hub artefact
- `tests/regression/test_redteam3_id_leak.py` + `test_redteam2_polish.py`
  — the canonical regression pins
