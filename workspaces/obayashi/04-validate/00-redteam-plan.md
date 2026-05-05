# Red-team plan — Arbor as a real HR platform

**Date:** 2026-05-05
**Tester perspective:** SG-SME HR manager who just signed up. Not the
person who built the product. No insider knowledge.
**Method:** Playwright MCP against the LIVE prod site
(http://136.110.51.61) using the seeded demo company (Central Solutions
Pte Ltd, demo@central.kailash.ai / CentralDemo2026!).

## Lens

For each surface I check three things:

1. **Does it work?** No 500s, no console errors, no orphaned states.
2. **Is there value?** Does the buyer / user get something they couldn't
   easily replicate in a spreadsheet?
3. **Does it connect to the lifecycle story?** If a stage of the Cox
   lifecycle is implicated, does Arbor cover it usefully?

## Stages walked (and the routes I'll exercise)

| Cox stage     | Routes / actions to verify                                        |
| ------------- | ----------------------------------------------------------------- |
| 1 Strategy    | Dashboard, headcount metric, owner-level summary                  |
| 2 Attract     | Public careers page (if rendered), settings → company brand       |
| 3 Recruit     | Job listings, candidates kanban, interviews list, hire flow       |
| 4 Onboard     | Templates, my-onboarding, assignment progress                     |
| 5 L&D         | /training/skillsfuture                                            |
| 6 Reward      | Payroll dashboard, payslip flow, leave, claims                    |
| 7 Progression | Appraisals                                                        |
| 8 Retain/Exit | Employee termination flow, churn data                             |
| Cross         | Compliance, advisory chat (the AI flagship), shadow agent overlay |

## Severity scale (per finding)

- **🔴 BLOCKER** — page errors out, feature unusable, demo would crash here
- **🟠 HIGH** — works but produces wrong / missing data, looks broken
- **🟡 MEDIUM** — works but UX gap, polish issue, or value-flow break
- **🟢 LOW** — minor cosmetic or future-improvement

## Output

`04-validate/01-redteam-findings.md` (gets written as I go).
