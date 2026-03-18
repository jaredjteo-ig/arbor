# Analysis: Project Costing, Inventory & ATS Modules

## Date: 2026-03-18

## Current State

| Module          | Codebase Status                                             | Models | Endpoints | Frontend |
| --------------- | ----------------------------------------------------------- | ------ | --------- | -------- |
| Project Costing | Stub only — `TimesheetApproval` model exists, nothing wired | 1 stub | 0         | 0        |
| Inventory       | Completely missing                                          | 0      | 0         | 0        |
| ATS             | Completely missing                                          | 0      | 0         | 0        |

## Payboy Feature Analysis

### Project Costing (Payboy Module 10)

- 8-step workflow: create project → assign employees → track time → calculate → report
- 3 assignment types: Timesheet (manual hours), Attendance (clock-in import), Allocations (percentage/nominal/equal)
- Project Roles with per-role hourly rates
- Project Overheads: project-based (flat) or employee-based (conditional)
- Allocations: percentage, nominal (fixed), or equal split of salary across projects
- Base amount = gross salary + pay items + employer CPF + SDL
- Project Calculations with approval workflow (unapproved → approved, irreversible)
- Excel report with org/dept/position/employee/project filters
- **Payboy gaps**: no budget vs actual, no profitability analysis, no billable/non-billable hours

### Inventory (Payboy Module 11)

- 3-tier hierarchy: Locations → Inventories (named containers) → Items
- Quantity-based (NOT individual asset tracking — no serial numbers)
- 4 statuses: Available, Reserved, Issued, Pending Acknowledgment
- Reserve → Issue → Acknowledge workflow
- Employee request workflow with admin approve/deny
- Position-based and employee-based permissions for issuers/requesters
- Movement audit log
- **Payboy gaps**: no serial numbers, no purchase price/depreciation, no categories, no return workflow, no condition tracking, no barcode/QR

### ATS (Payboy Module 14)

- Job listings with auto-generated unique URL
- Customizable application form (drag-and-drop builder, 16+ personal fields, custom questions)
- Kanban pipeline: New → Screening → Shortlisted → Interview → Offered → Hired → Rejected
- Direct onboarding: "Onboard" button pre-fills employee form from candidate data
- **Payboy gaps**: no API job board integration, no interview scheduling, no offer letter templates, no scoring/rating, no career page, no PDPA consent, no reports

## Our Competitive Advantages

All three modules can leverage existing AITE infrastructure:

1. **AI Shadow Agent** — can surface project cost overruns, asset expiry alerts, hiring pipeline bottlenecks
2. **PDPA Compliance** — audit trails on candidate PII, which Payboy lacks
3. **Custom Fields** — already planned (T303), can extend to all three modules
4. **Approval Groups** — already planned (T362), can apply to project calculations, inventory requests, job requisitions
5. **Existing TimesheetApproval model** — stub ready for project costing

## Design Decisions

### Project Costing

- Exceed Payboy: add budget vs actual tracking, billable/non-billable hours, project profitability dashboard
- Integrate with existing attendance and payroll (natural connection)
- Self-service timesheets for employees (Payboy has this)

### Inventory

- Exceed Payboy: individual asset tracking with serial numbers, purchase/depreciation, condition tracking, return workflow, barcode support
- Two modes: quantity-based (consumables like stationery) AND individual-tracked (laptops, keys, phones)
- Integrate with onboarding checklist (T308): auto-create asset assignment tasks for new hires

### ATS

- Exceed Payboy: interview scheduling with calendar, offer letter templates, candidate scoring, AI-powered screening, PDPA consent management, career page, recruitment reports
- Direct onboarding: candidate → employee conversion (pre-fill all fields)
- Talent pool: persistent candidate database for future hiring
