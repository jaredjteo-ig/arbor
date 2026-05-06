---
name: role-aware-ux
description: "Catalog of which surfaces must role-branch (employees vs owner/hr_manager). Codified from round-7 Lily redteam (commit 0cacde4). Use when adding any new shell-level component, employee-facing page, suggested-content list, or shared widget that ships content meaningful to admins but irrelevant or wrong for individual contributors."
---

# Role-Aware UX

The platform serves two principal roles within a single tenant:

| Role         | Primary surfaces                  | Should NOT see                                                                                                |
| ------------ | --------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `owner`      | Everything                        | —                                                                                                             |
| `hr_manager` | Everything except billing         | —                                                                                                             |
| `employee`   | `/my-*`, advisory, settings, help | HR-admin compliance warnings, /alerts admin endpoints, admin getting-started, HR-manager advisory suggestions |

Round-7 found multiple surfaces in the dashboard shell that leaked
HR-admin content to employees — compliance warnings rail, alerts
unread-count, /help getting-started, advisory chat suggestions. Each
has a canonical fix shape.

`AdminGuard` at the route level is **not enough**. Admin pages live
behind it, but the dashboard SHELL renders content (margins, top bar,
alerts) inside ALL authenticated routes — those need their own
per-component role checks.

---

## The role-gating cookbook

### Pattern 1 — gate a shell-level widget

The shadow margin, compliance warnings rail, alerts badge, and any
other component rendered inside `(dashboard)/layout.tsx` or `AppShell`
is shown to every authenticated user by default. To gate:

```tsx
// (dashboard)/layout.tsx
import { useAuth } from "@/contexts/AuthContext";

function RoleGatedShadowMargin() {
  const { user } = useAuth();
  const role = user?.role;
  if (role !== "owner" && role !== "hr_manager") return null;
  return <ShadowMarginWrapper />;
}

// then in the layout:
<ShadowAgentProvider>
  <div className="animate-fade-in">{children}</div>
  <ShadowAgentUI />
  <RoleGatedShadowMargin /> {/* was <ShadowMarginWrapper /> */}
</ShadowAgentProvider>;
```

### Pattern 2 — gate a fetch effect (don't call admin APIs as employee)

```tsx
// AppShell.tsx — round-7 L1: alerts/unread-count was 403'ing every
// page load for employees.
const { user } = useAuth();
const canSeeAlerts = user?.role === "owner" || user?.role === "hr_manager";

useEffect(() => {
  if (!canSeeAlerts) return;
  alertsApi.unreadCount().then(...);
}, [canSeeAlerts]);
```

### Pattern 3 — branch a fixed content list by role

```tsx
// ChatContainer.tsx — round-7 M7
const ADMIN_SUGGESTIONS = [
  "What leave entitlements do my employees have?",
  "How do I calculate CPF contributions?",
  "What are the foreign worker quota limits for my sector?",
  // ... (HR-manager scoped questions)
];

const EMPLOYEE_SUGGESTIONS = [
  "How much annual leave am I entitled to?",
  "Can my employer change my notice period?",
  "What happens to my CPF if I take unpaid leave?",
  "How does maternity leave work in Singapore?",
  "What can I claim under Childcare Leave?",
];

// then:
suggestions={
  isEmpty
    ? hasActiveOnboarding
      ? ONBOARDING_SUGGESTIONS
      : user?.role === "employee"
        ? EMPLOYEE_SUGGESTIONS
        : ADMIN_SUGGESTIONS
    : undefined
}
```

### Pattern 4 — branch a backend response by role

When the backend serves content (FAQ articles, getting-started steps),
inspect the JWT and branch. The endpoint should accept either an
authenticated or anonymous request.

```python
# api/middleware/auth_middleware.py — added in round-7 for /help
async def get_current_user_optional(
    request: Request,
    auth_service: AuthService = Depends(_get_auth_service),
) -> dict | None:
    """Returns None for unauthenticated requests; never raises."""
    if not request.headers.get("Authorization"):
        return None
    try:
        return await get_current_user(request, auth_service=auth_service)
    except HTTPException:
        return None

# api/routers/help.py
@router.get("/getting-started", response_model=GettingStartedResponse)
async def getting_started_guide(
    current_user: dict | None = Depends(get_current_user_optional),
) -> GettingStartedResponse:
    role = (current_user or {}).get("role", "")
    if role == "employee":
        return _GETTING_STARTED_EMPLOYEE
    return _GETTING_STARTED  # admin/owner default
```

The two response variants live next to each other in the file. The
employee version walks: profile → leave → claims → payslips → advisor
→ settings. The admin version walks: company profile → advisor →
compliance → calculators → alerts → emergency hub.

### Pattern 5 — gate a button by data-availability _plus_ role context

```tsx
// my-timesheets — round-7 M5
<AppButton
  onClick={() => setShowModal(true)}
  disabled={projects.length === 0}
  title={
    projects.length === 0
      ? "You need to be assigned to a project before you can log time. Ask your manager to add you."
      : undefined
  }
>
  <Plus className="h-4 w-4 mr-1" /> Log Time
</AppButton>;

{
  projects.length === 0 && !isLoading && (
    <AppCard variant="flat">
      <p className="text-sm text-[var(--color-gray-700)]">
        You aren't assigned to any project yet, so there's nothing to log time
        against. Ask your manager to add you to a project — once you're on one,
        the <strong>Log Time</strong> button will activate.
      </p>
    </AppCard>
  );
}
```

---

## Inventory — what's currently role-gated

This is the catalog after round-7. Use it as the checklist when adding
any new shell-level component or shared content list.

| Surface                                    | Gating mechanism                              | Reference                                      |
| ------------------------------------------ | --------------------------------------------- | ---------------------------------------------- |
| `(dashboard)/layout.tsx` ShadowMargin      | `RoleGatedShadowMargin` wrapper               | round-7 M9                                     |
| `AppShell` alerts unread-count fetch       | `canSeeAlerts` useEffect skip                 | round-7 L1                                     |
| `ChatContainer` suggestions                | EMPLOYEE / ADMIN / ONBOARDING branches        | round-7 M7                                     |
| `/help` getting-started                    | backend `_GETTING_STARTED_EMPLOYEE` branch    | round-7 M8                                     |
| `/appraisals` page (admin tabs)            | `AdminGuard` — ALSO blocks employees          | open issue: employees can't view OWN appraisal |
| `/employees`, `/payroll`, `/policies` etc. | `AdminGuard` route-level                      | working                                        |
| `/my-*` employee-facing pages              | `ProtectedRoute` only (any auth user)         | working                                        |
| `compliance warnings rail content`         | hidden for employees via shadow-margin gating | round-7 M9                                     |

## Anti-patterns

### Don't rely solely on AdminGuard at the route level

The shell renders `<ShadowMargin>`, `<TopBar>`, `<NavigationSidebar>`
INSIDE `(dashboard)/layout.tsx`, which wraps every authenticated route
including `/my-*`. Anything inside the shell that fires API calls or
displays admin content needs its own role check.

### Don't show employees endpoints they can't call

`/api/alerts/unread-count` is admin-only. Calling it from `AppShell`
unconditionally produces a 403 in the console on every page load for
employees. Gate the fetch.

### Don't pretend admin content is irrelevant to employees

"Foreign workers employed — ensure all passes are valid and conditions
are met" is a real compliance finding, but it's directed at HR. An
employee reading their own dashboard cannot act on it. Hide, don't
just demote.

### Don't hardcode HR-manager-style suggestions for everyone

"What are my obligations when terminating an employee?" is a Grace
question. "Can I encash unused annual leave on resignation?" is a
Lily question. Same KB, different framing.

### Don't AdminGuard `/my-appraisals` if employees should see their own

The current `/appraisals` page wraps the entire component in
`AdminGuard`, so Lily gets "Access Denied" even for the My Appraisals
tab that the page advertises. Open follow-up: split the route so
admins manage templates/periods at `/appraisals` and employees view
their own at `/my-appraisals`, OR change the guard to allow
authenticated users into the My Appraisals tab while keeping the
admin tabs admin-only.

---

## Cross-references

- `auth-security.md` — RBAC role-page matrix (the high-level mapping)
- `enrichment-and-detail-patterns.md` — when role gating intersects
  with name enrichment (e.g., who sees `created_by_name` at all)
- `security-patterns.md` P46 — canonical pattern for "role-aware UX
  gating" (the post-audit closure form)
- `tests/regression/test_redteam2_polish.py` —
  `test_appraisals_my_resolves_employee_names` exercises Grace's
  permission scope; round-7 lacks an analogous Lily-scope regression
  test, worth adding
