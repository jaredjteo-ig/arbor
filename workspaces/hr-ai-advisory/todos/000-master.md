# HR AI Advisory — Master Todo Index

**Project**: Arbor — Free AI-Powered HR Platform for Singapore (backed by ASME)
**Last Updated**: 2026-03-17
**Total Tasks**: 192 across 21 milestones
**Status**: T001-T140 complete. T141-T192 active (Full HRIS + Shadow Agent Enhancement).

---

## How to Read This Index

- T001-T140 are **done** — completion records are in `completed/`
- T141-T192 are **active** — detailed files are in `active/`
- Core: Compliance + AI Shadow Agent
- Extensions: HRIS features (payroll, leave, claims, attendance) built on the compliance core

---

## Milestones 1-15: COMPLETE

T001-T140 across 15 milestones. Covers:

- Full advisory platform with 14-step safety chain, 6 regulatory domains, 7 calculators
- Shadow agent (command surface, margin, inline annotations, observation layer)
- Enterprise model (admin + employee roles, invitation system, tenant isolation)
- Production deployment at arbor.terrene.foundation
- 8 red team rounds

---

## Milestone 16: Shadow Agent Enhancement (Sprint 1)

**Goal**: The shadow agent becomes truly intelligent — personalised suggestions from observation patterns, proactive attention triggers, and salary encryption at rest.

| Task ID | Task Name                                                                      | Dependencies |
| ------- | ------------------------------------------------------------------------------ | ------------ |
| T141    | Observation-to-suggestion personalisation — feed patterns into command surface | T138         |
| T142    | Shadow widget attention state — trigger ripple on proactive insights           | T140, T141   |
| T143    | Salary field encryption at rest — Fernet wrapper for Employee.salary_monthly   | T129         |
| T144    | Shadow context uses actual company compliance data (not generic defaults)      | T121         |
| T145    | Shadow agent validates payroll before submission (Kaizen agent)                | T143         |

---

## Milestone 17: Payroll Foundation (Sprint 2)

**Goal**: Admins can run monthly payroll for all employees. The system calculates gross-to-net with CPF, SDL, and levies. Payslips are generated and downloadable.

| Task ID | Task Name                                                                           | Dependencies |
| ------- | ----------------------------------------------------------------------------------- | ------------ |
| T146    | Employee model extensions — DOB, NRIC, bank details, allowances, PR year            | T129         |
| T147    | EmployeeBankDetails model with Fernet encryption                                    | T143, T146   |
| T148    | PayrollRun, Payslip, PayslipItem, SalaryHistory data models                         | T146         |
| T149    | PublicHoliday model — seed 2026-2027 Singapore gazetted holidays                    | —            |
| T150    | Payroll calculation workflow — fetch employees, call calculators, generate payslips | T148, T020   |
| T151    | YTD tracking across payroll runs — OW/AW ceiling accumulation                       | T150         |
| T152    | Payslip PDF generation — EA s88A compliant itemisation                              | T150         |
| T153    | Payroll API endpoints — create run, process, review, finalise                       | T150         |
| T154    | Payroll dashboard page — run payroll, review, approve (React)                       | T153         |
| T155    | Payslip view page — employee sees own payslips (React)                              | T152, T154   |
| T156    | Payroll integration with shadow agent — "Run this month's payroll" command          | T153, T113   |

---

## Milestone 18: Leave Management (Sprint 3)

**Goal**: Employees apply for leave. Managers approve or reject. Balances update automatically. Leave calendar shows who's out.

| Task ID | Task Name                                                                | Dependencies |
| ------- | ------------------------------------------------------------------------ | ------------ |
| T157    | LeaveApplication data model with approval state machine                  | T129         |
| T158    | Leave application API endpoints — apply, approve, reject, cancel         | T157         |
| T159    | Leave balance auto-deduction on approval                                 | T157, T134   |
| T160    | Pro-rated leave for mid-year joiners — service year calculation          | T157         |
| T161    | Leave calendar view — who's out this week/month (React)                  | T158         |
| T162    | Leave application page — employee applies, manager queue (React)         | T158         |
| T163    | Leave integration with payroll — no-pay leave deduction                  | T157, T150   |
| T164    | Leave integration with shadow agent — "Apply for 3 days leave next week" | T158, T113   |

---

## Milestone 19: CPF & Tax File Generation (Sprint 4)

**Goal**: Generate CPF Board submission files and IR8A tax data. Admins download and upload to CPF Board/IRAS portals.

| Task ID | Task Name                                                                                            | Dependencies |
| ------- | ---------------------------------------------------------------------------------------------------- | ------------ |
| T165    | CPF submission file generator — CPF Board prescribed format                                          | T150, T146   |
| T166    | CPF reconciliation report — monthly summary by employee                                              | T165         |
| T167    | IR8A data aggregation — annual payslip items mapped to IRAS fields                                   | T150, T148   |
| T168    | IR8A export — CSV format for AIS upload                                                              | T167         |
| T169    | Appendix 8A (benefits in kind) basic support                                                         | T167         |
| T170    | CPF/IR8A file generation page — download files (React)                                               | T165, T168   |
| T171    | Shadow agent CPF validation — "Your total CPF this month is X — Y% higher than last month because Z" | T165, T145   |

---

## Milestone 20: Claims, Attendance & Employee Lifecycle (Sprint 5)

**Goal**: Employees submit expense claims with receipts. Clock in/out for attendance. Full employee lifecycle from onboarding to exit.

| Task ID | Task Name                                                                                 | Dependencies |
| ------- | ----------------------------------------------------------------------------------------- | ------------ |
| T172    | Claim and ClaimItem data models                                                           | T129         |
| T173    | Claims API endpoints — submit, approve, reject, pay                                       | T172         |
| T174    | Claims page — submit with receipt upload, manager approval queue (React)                  | T173         |
| T175    | Claims integration with payroll — approved claims paid in next run                        | T173, T150   |
| T176    | Attendance data model — clock in/out, overtime hours                                      | T129         |
| T177    | Attendance API endpoints — clock in, clock out, timesheet                                 | T176         |
| T178    | Attendance page — clock in/out, weekly timesheet view (React)                             | T177         |
| T179    | Overtime auto-calculation from attendance — feed into payroll                             | T177, T150   |
| T180    | Exit processing — final salary calculation using notice period + retrenchment calculators | T150         |
| T181    | Probation tracking with auto-reminders                                                    | T129, T140   |
| T182    | Employee lifecycle page — onboarding checklist, confirmation, exit (React)                | T180, T181   |

---

## Milestone 21: HRIS Hardening & Compliance (Sprint 6)

**Goal**: Payroll accuracy verified against CPF Board rate tables. Security audited. PDPA compliance for salary and bank data. Red team validated.

| Task ID | Task Name                                                                  | Dependencies |
| ------- | -------------------------------------------------------------------------- | ------------ |
| T183    | Payroll accuracy test suite — against CPF Board published rate examples    | T150         |
| T184    | PDPA data category extensions — SALARY_DATA, BANK_DETAILS categories       | T143, T147   |
| T185    | Audit trail for all payroll data access                                    | T153, T184   |
| T186    | Payroll run performance test — 200 employees under 30 seconds              | T150         |
| T187    | Employee data import — CSV upload for bulk onboarding                      | T146         |
| T188    | Parallel run support — run Arbor alongside existing HRIS, compare payslips | T152         |
| T189    | Payroll data export — full history CSV for migration                       | T148         |
| T190    | Red team — payroll accuracy, PDPA compliance, security                     | T183-T189    |
| T191    | COC codification — update project agents and skills for HRIS domain        | T190         |
| T192    | Deploy HRIS to production                                                  | T190         |

---

## Summary

### Completed (T001-T140)

- **140/140 tasks** across 15 milestones
- Full advisory + shadow agent + enterprise model

### Completed (T141-T185) — HRIS Expansion (2026-04-06)

- **45/52 tasks complete** across M16-M20 + partial M21
- M16: Shadow enhancement — personalisation (T141), encryption (T143), HRIS integration (T145)
- M17: Payroll engine — all 11 tasks complete (models, calc, YTD, CPF file, PDF, API, dashboard)
- M18: Leave management — all 8 tasks complete (model, API, balance, pro-ration, calendar, UI)
- M19: CPF/Tax — all 7 tasks complete (CPF eSubmit, reconciliation, IR8A CSV, Appendix 8A)
- M20: Claims/attendance/lifecycle — all 11 tasks complete (models, API, UI, exit processing)
- Red Team Round 8: 70 findings, 30 fixed (all CRITICAL/HIGH resolved)

### Remaining (7 tasks)

- T142: Shadow widget attention state (ripple on proactive insights) — frontend UX
- T144: Shadow context uses actual company compliance data — partial
- T152: Payslip PDF rendering (HTML exists, PDF generation pending)
- T186: Payroll performance test (200 employees under 30 seconds)
- T188: Parallel run support (run Arbor alongside existing HRIS)
- T190: Final red team for HRIS
- T191-T192: COC codification + deploy (in progress)
