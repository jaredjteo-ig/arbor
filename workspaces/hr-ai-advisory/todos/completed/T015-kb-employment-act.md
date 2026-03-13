# T015 — Knowledge Base Population: Employment Act

## Status: COMPLETED

## What Was Built

### Content Bundle (`src/hr_advisory/kb/content/employment_act.py`)

Structured content bundle for the Employment Act 1968 (Cap 91), covering:

**6 domains**: Working Hours & Overtime, Leave Entitlements, Salary & Compensation, Termination & Dismissal, Employment Records, Maternity & Family

**17 provisions** with full metadata:

| Section    | Title                             | Domain                   |
| ---------- | --------------------------------- | ------------------------ |
| EA-S2      | Application of the Employment Act | Working Hours & Overtime |
| EA-S36     | Hours of Work                     | Working Hours & Overtime |
| EA-S37     | Overtime                          | Working Hours & Overtime |
| EA-S36(4)  | Rest Day                          | Working Hours & Overtime |
| EA-S88A    | Annual Leave                      | Leave Entitlements       |
| EA-S89     | Sick Leave                        | Leave Entitlements       |
| EA-S88     | Public Holidays                   | Leave Entitlements       |
| EA-S10     | Notice of Termination             | Termination & Dismissal  |
| EA-S14     | Summary Dismissal for Misconduct  | Termination & Dismissal  |
| EA-S14A    | Wrongful Dismissal                | Termination & Dismissal  |
| EA-S11     | Salary in Lieu of Notice          | Termination & Dismissal  |
| EA-S20A    | Key Employment Terms              | Salary & Compensation    |
| EA-S21     | Payment of Salary Timeline        | Salary & Compensation    |
| EA-S22     | Deduction Limits                  | Salary & Compensation    |
| EA-S96     | Itemised Payslips                 | Salary & Compensation    |
| EA-S95     | Employment Records Retention      | Employment Records       |
| EA-Part-IX | Maternity Protection              | Maternity & Family       |

Each provision includes: formal_text, plain_summary, interpretation_notes, effective_date, authority_level, applicability_rules, and practical_examples (where applicable).

**9 cross-references** linking related provisions (e.g., S36→S37, S10→S14, S14→S14A).

### Bug Fix: DataFlow ListNode Default Limit

Discovered that DataFlow ListNode has a default result limit (~10 records). Fixed `validator.py` and `admin.py` to pass `limit: 10000` on all ListNode queries that need complete result sets.

## Verification

26 tests passed (0 failures, 0 skips) — bundle structure, loading, data integrity, idempotency, validation.

## Files

- `src/hr_advisory/kb/content/__init__.py`
- `src/hr_advisory/kb/content/employment_act.py`
- `src/hr_advisory/kb/validator.py` (bug fix: added limit param)
- `src/hr_advisory/kb/admin.py` (bug fix: added limit param)
- `tests/integration/test_kb_employment_act.py`
