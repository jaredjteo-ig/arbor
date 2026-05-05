# Red-team findings — Arbor as a real HR platform

**Date:** 2026-05-05
**Method:** Live walk through prod (`http://136.110.51.61`) as the
seeded demo owner, with backend log inspection.
**Tester perspective:** SG-SME HR manager exploring Arbor for the first
time. No insider knowledge.

**Headline:** the platform's core mechanics work end-to-end. **The
flagship AI advisory is unreliable for a buyer demo** because the prod
LLM is on Gemini's free tier (5 req/min) and the engine's own
multi-tool ReAct loop blows that quota. Several visible data /
arithmetic / routing bugs would erode trust in the first 2 minutes of a
demo.

---

## 🔴 BLOCKERS (3) — fix before next pilot demo

### B1 — AI advisory degrades on its own suggested questions

**Where:** `/advisory` → click any of the platform-suggested chips.
**What happens:** "I'm having trouble processing your question right
now. Please try again in a moment." with a "High Risk — Action
Required / Connect to Employment Law Specialist" banner.

**Root cause (from backend log):**

```
ERROR:hr_advisory.agents.advisory_engine: Advisory engine failed:
Error code: 429 — Quota exceeded for metric:
generativelanguage.googleapis.com/generate_content_free_tier_requests,
limit: 5, model: gemini-2.5-flash
```

The advisory engine's ReAct loop made 4 `search_kb` tool calls in one
question. Each call hits the LLM. Gemini free tier = 5 req/min. The
4-tool query alone was tight against the limit; subsequent queries
within the minute were guaranteed to fail.

**Why this is a blocker:** the Advisory chat IS the headline feature
("AI Compliance Advisor"). Demoing this with a built-in suggested
question that produces "I'm having trouble" makes the platform look
broken. The escalation banner and "Connect to Employment Law
Specialist" CTA reinforce the impression that something went wrong.

**Fixes (pick one or stack):**

1. Move prod off free tier — paid Gemini ($X/M tokens) OR switch
   `DEFAULT_LLM_MODEL` to `gpt-4o-mini` / `claude-3-5-haiku-latest`
   (both keys are already set in env).
2. Reduce ReAct tool-call budget per query (currently 4× search_kb
   for one CPF question is excessive — most can be answered with 1).
3. Cache `search_kb` responses inside a single query — the engine ran
   the same KB search 4 times sequentially.
4. On 429, retry with exponential backoff up to 30s (Gemini's own
   retry-info says 16s) before degrading.

**Recommendation:** swap to OpenAI as default tonight (5-line change in
`.env.prod`); keep the upstream rate-limit handling as a Phase 2 fix.

---

### B2 — "Onboarding" sidebar link routes to the new-user signup wizard

**Where:** any logged-in owner clicks "Onboarding" in the left sidebar.
**What happens:** browser navigates to `/onboarding` which renders the
"Welcome to Central / Set Up Company Profile" 4-step signup wizard
(Welcome → Company → Snapshot → Ask).

This is the page a brand-new signup uses to set up their company. An
already-onboarded owner who has 28 employees should not see it.

**Why this is a blocker:** the sidebar is the primary nav surface. If
the most-used HR feature (Employee Onboarding) takes the user to a
"set up your company" wizard, the demo loses credibility instantly.

**Likely fix:** the sidebar link's `href` should be
`/employees?tab=onboarding` (which renders the proper Employees ▸
Onboarding admin view, verified working). One-line change in
`apps/web/src/components/shell/NavigationSidebar.tsx`.

---

### B3 — Claim totals are arithmetically wrong

**Where:** `/claims` → the "Pending Claims" cards.
**Specific examples seen:**

- **David Lee** — 3 line items: $65.00 + $38.00 + $45.50 = $148.50
  expected. **Displayed total: $45.50.**
- **Muhammad Rizwan** — 2 line items: $28.50 + $32.00 = $60.50
  expected. **Displayed total: $32.00.**

The pattern looks like the displayed "total" is the **last item** or
**max item**, not the sum.

**Why this is a blocker:** an HR manager who can't trust the dollar
totals on the claims page won't approve through the platform. This is
a finance-grade bug.

**Likely fix:** check `_recalculate_claim_total` in `claims.py` —
total = sum(items.amount). Likely a backend computation bug or a
frontend rendering of `claim.total_amount` that's stale after item
changes.

---

## 🟠 HIGH (4) — visible to a real customer in the first month

### H1 — Attendance shows every employee "Absent" (no clock-ins)

`/attendance` lists 27 of 28 employees as "Absent" today (the 28th is
on leave). All clock-in/out cells show `--:--`.

**Real cause:** no employee has clocked in today, AND the system has
no concept of "salaried — does not clock in." Most SG SME staff are
salaried and don't punch a clock. Marking them all "Absent" is wrong
data.

**Suggested fix:** `Employee.tracks_attendance: bool = False` (default
off). Employees opted-in show on the dashboard; everyone else is
hidden. OR a "Not tracked" status pill instead of "Absent" for
non-tracked employees.

---

### H2 — Stale leave requests linger as "Pending" past their dates

`/leave` shows 4 pending leave applications. **3 of them have dates
already in the past** (Mar 24; Apr 7-9; Apr 14-18). It's now 5 May.

**Cause:** no auto-handling when a pending leave goes past its end
date. Real HR teams expect a daily sweep that either auto-rejects,
flags as overdue-decision, or escalates to the next approver.

**Suggested fix:** daily cron — for any `LeaveApplication.status =
'pending' AND end_date < today - 24h`, set status = `expired_pending`
and send a reminder.

---

### H3 — Payroll "Next pay date" is in the past

`/payroll` shows "Next pay date: 07 Apr 2026 (Draft)". It's now 5 May.
The May payroll has not been calculated.

The Mar 2026 run also still shows "Draft" while Apr 2026 shows "Paid"
— payroll runs are not strictly sequential, which is a real workflow
problem (you shouldn't be able to mark April paid before March is
finalized).

**Suggested fixes:**

- "Next pay date" should resolve to the upcoming month's pay date
  (May 2026 with status "Not yet calculated").
- Out-of-order finalisation should warn the operator: "March 2026 is
  still Draft. Approving April will not back-fill Mar." Or block
  entirely and force chronological closure.

---

### H4 — Onboarding has 3 templates with the same name

`/employees?tab=onboarding`:

- HR Technology / SaaS Onboarding (id=2)
- HR Technology / SaaS Onboarding **(Copy)** (id=3)
- HR Technology / SaaS Onboarding (id=4)
- Singapore Standard Onboarding (default)

Two of those have the identical name (id=2 and id=4), the third is
labelled "(Copy)". An admin doesn't know which to pick.

**Suggested fix:** unique-name constraint per company (or auto-rename
on duplicate-detect: "(Copy)", "(Copy 2)"). Cleanup of the existing
duplicates on prod via SQL.

---

## 🟡 MEDIUM (8) — UX gaps + value-flow breaks

| ID  | Where                             | Issue                                                                                                                                                                                                                               |
| --- | --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| M1  | `/dashboard` Total Headcount tile | "Unknown 1" — one employee has no `pass_type`. Likely Demo Admin. Either auto-flag for owner to fix, or default to `citizen`.                                                                                                       |
| M2  | `/compliance`                     | "4/5 domains covered" is ambiguous — there are 5 cards visible, one at "Medium Risk". Phrase as "5 domains covered, 1 at medium risk" to avoid the implicit "1 missing entirely" reading.                                           |
| M3  | `/compliance`                     | TAFEP / Workplace Fairness Act is missing from the 5-domain set despite being a regulatory area.                                                                                                                                    |
| M4  | `/payroll` Jan 2026               | $0.00 gross/net but status "Draft" with 28 employees. Looks like an empty draft was created and abandoned.                                                                                                                          |
| M5  | `/appraisals`                     | 1 template only ("Annual Performance Review"), no Periods, no in-flight appraisals. Whole stage looks dead. Seed a current period + 3 in-progress reviews for demo realism.                                                         |
| M6  | Advisory chat history             | One past conversation ends with "I'm having trouble processing your question right now…" — same B1 cause. Showing degraded responses in history advertises the failure.                                                             |
| M7  | `/recruitment` Interviews tab     | 4 of 5 interviews still show "Scheduled" with future dates, but Alex Tan's 10 Apr 2026 interview is correctly flagged Overdue. **Expected — all 5 at "Scheduled" gives a flat demo.** Seed 1-2 Completed + 1 Cancelled for variety. |
| M8  | Sidebar                           | "Onboarding" + "Employees" both exist as top-level entries despite the user-facing onboarding being IN the Employees page. Either merge or rename.                                                                                  |

---

## 🟢 LOW (5) — polish + future improvements

| ID  | Where                             | Issue                                                                                                                                           |
| --- | --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| L1  | `/dashboard`                      | "Pending Actions: 1 / No critical items" — slight self-contradiction. Either "1 pending action" or "No critical items," not both.               |
| L2  | `/dashboard` Headcount            | The pass-class sub-bars (Local 64% / PR 7% / EP 7% / SP 11% / WP 7% / Unknown 1) — Unknown shown as raw count not %. Inconsistent.              |
| L3  | `/payroll` CPF Due                | "14 May 2026, $42,929 total CPF" — correct. Could link directly to the CPF e-Submit file generator for one-click flow.                          |
| L4  | `/leave` "Approved This Month: 0" | The metric is right but visually empty for May. Consider showing last 30 days rolling instead of calendar-month for new-month dead-zone effect. |
| L5  | All pages                         | Persistent "8 unread notifications" badge throughout — clicking nowhere shows a clear notifications panel for the demo to walk through.         |

---

## Cross-cutting backend health observations

From the live backend log:

- **Async pool errors recurring** — multiple
  `WARNING: AsyncSQLDatabaseNode: Error disconnecting pool ... attached
to a different loop` lines after each request. Doesn't fail requests
  but produces log noise + suggests asyncpg lifecycle is fragile under
  the current connection-pool config.
- **Connection-pool saturation** still latent — DataFlow `pool_size=70 +
max_overflow=35 = 105` vs Postgres `max_connections=100`. Already
  documented in `dataflow-specialist.md`. Not blocking demo.
- **LLM cost per query is reasonable** —
  `19,596 input + 73 output tokens = $0.0052 per advisory query`. The
  rate-limit issue is the bottleneck, not cost.

---

## Lifecycle stage value verdict

For each Cox lifecycle stage, "if I were demoing this to an SG-SME HR
manager today, would they see real value?":

| Stage         | Verdict                                | One-liner                                                              |
| ------------- | -------------------------------------- | ---------------------------------------------------------------------- |
| 1 Strategy    | ❌ no surface                          | The dashboard headcount tile is the only "strategy" today.             |
| 2 Attract     | 🟡 partial                             | Public careers API works. No employer-brand surface.                   |
| 3 Recruit     | ✅ strong                              | Drag-drop kanban, 20 candidates, 5 interviews, AI scorecards.          |
| 4 Onboard     | ✅ strong                              | Templates work, assignments tracked. **Sidebar broken (B2).**          |
| 5 L&D         | ❌ near-empty                          | Just SkillsFuture lookup. No internal training records.                |
| 6 Reward      | 🟡 strong on payroll, broken on claims | Payroll engine real. **Claim totals broken (B3).** Recognition absent. |
| 7 Progression | ❌ thin                                | 1 template, 0 periods, 0 active reviews.                               |
| 8 Retain/Exit | 🟡 mechanics work, no analytics        | Termination + IR21 work. No churn dashboard, no exit interview.        |

Two ❌ stages (Strategy, L&D) match the gap analysis in
`01-analysis/03-gap-analysis.md`. The single most impactful "looks
broken" issue is **B1 (AI advisory rate-limited)** because the demo
narrative leads with it.

---

## Recommended fix order before next pilot demo

1. **B1 — Switch prod LLM off Gemini free tier.** (env-var change, 1
   min). Suggested: `DEFAULT_LLM_MODEL=gpt-4o-mini` or `claude-3-5-
haiku-latest`. Smoke-test the advisory chat after.
2. **B2 — Fix Onboarding sidebar route.** 1-line change in
   `NavigationSidebar.tsx`. Verify in Playwright.
3. **B3 — Fix claim total computation.** Backend grep
   `_recalculate_claim_total` + frontend rendering of
   `claim.total_amount`. ~30 min.
4. **H4 — Clean up duplicate onboarding templates.** SQL on prod +
   add unique constraint going forward.
5. **H1 — Add `tracks_attendance` flag.** Default off, opt-in per
   employee. Cleans up the "everyone Absent" demo failure.
6. **H2 — Daily cron for stale pending leave.** Modeled on the
   existing reminders cron infrastructure.
7. **H3 — "Next pay date" + out-of-order block.** Logic fix in
   `payroll.py`.
8. **M5 — Seed an active appraisal period + 3 in-flight reviews.**
   Demo realism.
9. **M7 — Seed 1 Completed + 1 Cancelled interview.** Demo variety.

This list is ~1.5–2 days of focused work and converts the demo from
"3 visible bugs in 2 minutes" to "clean walkthrough of 8 stages."

---

## What WORKS well (not all bad news)

- Login + auth + sidebar nav (apart from B2)
- Recruitment end-to-end: jobs, drag-drop kanban, interviews enriched
  with names + types + overdue flag, AI scorecards
- Onboarding admin view: templates, assignments, completion %, drag-drop
- Payroll engine: 4 historical runs, gross/net/CPF totals
- Leave: approve/reject UI, on-leave-today widget
- Compliance: 80% score, 5 domain cards, checklist
- Advisory chat infrastructure (history, citations, suggested
  questions, escalation banner) — only the LLM connection is broken
- The full data model + 26+ working routers + the lifecycle scaffold
  for the obayashi initiative

The platform's bones are good. The flagship AI is rate-limited; the
finance arithmetic is broken; the sidebar has a wrong link. None of
those are architectural; all are 1–2 hours each.

---

## Severity totals

- 🔴 BLOCKER × 3 (B1 LLM rate-limit, B2 sidebar route, B3 claim totals)
- 🟠 HIGH × 4 (H1 attendance, H2 stale leave, H3 payroll dates, H4 duplicate templates)
- 🟡 MEDIUM × 8
- 🟢 LOW × 5

**Total findings: 20.** Fixing the 3 blockers + 4 highs = ~1.5 days
of work and removes every "trust-killer" issue a buyer would notice
in their first 5 minutes.
