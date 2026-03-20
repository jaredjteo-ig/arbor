# PACT Restructuring: Arbor HRIS Platform

## What This Is

Arbor is the Terrene Foundation's open-source HRIS platform for Singapore SMEs. It currently operates as an HR advisory agent with payroll, leave, attendance, claims, and compliance modules. With PACT, Arbor becomes a governed organizational platform where every HR action flows through accountable delegation chains with classified knowledge access and calibrated human oversight.

## Why PACT Transforms Arbor

Today Arbor has role-based access (owner, hr_manager, consultant) and approval workflows. But these are flat. A payroll officer and an HR manager have different roles but no compositional authority structure. There is no formal relationship between "the CFO approved payroll" and "the HR manager approved leave that feeds into payroll." PACT provides that structure.

With PACT:
- Every company deployed on Arbor gets a D/T/R organizational tree reflecting its actual structure
- Operating envelopes constrain what each role's agent can do (payroll officer cannot approve terminations)
- Knowledge clearance separates employee data access from organizational rank (payroll officer sees salary; does not see medical records)
- The verification gradient calibrates when humans must intervene (routine leave = auto-approve; termination = expert review + legal)
- Cross-department bridges model how leave approval triggers payroll recalculation

## The Organizational Grammar Applied to HRIS

### D/T/R Structure for a Typical SME

```
BOD (Company Board)
D1 (Company Operations)
  D1-R1 (Managing Director / CEO)
    D1-R1-D1 (HR Department)
      D1-R1-D1-R1 (HR Director)
        D1-R1-D1-R1-T1 (Recruitment Team)
          D1-R1-D1-R1-T1-R1 (Recruitment Lead)
        D1-R1-D1-R1-T2 (People Operations)
          D1-R1-D1-R1-T2-R1 (HR Manager)
            D1-R1-D1-R1-T2-R1-R2 (HR Executive)
    D1-R1-D2 (Finance Department)
      D1-R1-D2-R1 (CFO / Finance Director)
        D1-R1-D2-R1-T1 (Payroll Team)
          D1-R1-D2-R1-T1-R1 (Payroll Officer)
    D1-R1-D3 (Operations Department)
      D1-R1-D3-R1 (COO / Operations Director)
        D1-R1-D3-R1-T1 (Shift Supervisors)
          D1-R1-D3-R1-T1-R1 (Shift Supervisor A)
```

### Employee Data Clearance Mapping

| PACT Level | HR Data Type | Who Accesses | Arbor Module |
|---|---|---|---|
| OFFICIAL | Org chart, job titles, department names, public policies | All employees | Company directory |
| SENSITIVE | Leave balances (own + team), shift schedules, attendance summaries, project allocations | Employee (own) + Manager (team) + HR | Leave, Attendance |
| CONFIDENTIAL | Salary/wages, payroll data, performance reviews, disciplinary records, claims | Employee (own) + HR + Payroll + Manager (team) | Payroll, Performance |
| SECRET | Medical records, banking details, CPF breakdowns, tax information | Employee + HR + Payroll (encrypted) + Statutory agencies | PDPA-protected, Payroll |

### Operating Envelopes by Role

**HR Manager Envelope** (defined by HR Director):
```
Financial: approve claims up to $500; above requires HR Director
Operational: approve leave (own team), create discipline records,
             manage attendance overrides, view performance reviews
             BLOCKED: modify statutory rates, delete audit records,
             override TAFEP fair hiring, approve discrimination claims
Data Access: CONFIDENTIAL for own team; SENSITIVE for other teams
Communication: internal autonomous; external (MOM, TADM) held for HR Director
Temporal: business hours for approvals; urgent matters 24/7
```

**Payroll Officer Envelope** (defined by CFO):
```
Financial: calculate and process payroll; cannot approve expenses above $200
Operational: generate CPF e-Submit, IR8A/IR21, bank GIRO files
             BLOCKED: approve leave, terminate employees, access salary
             history beyond 3 years (PDPA retention limit)
Data Access: CONFIDENTIAL for payroll data; no access to medical records,
             performance reviews, or disciplinary records
Communication: internal only; statutory submissions (CPF Board, IRAS) held for CFO
Temporal: payroll processing windows; cut-off enforcement
```

**Employee Self-Service Envelope** (defined by HR Manager):
```
Financial: submit claims up to policy limit; view own payslip
Operational: apply leave, clock in/out, view own records
             BLOCKED: view other employees' data, modify any records,
             approve anything, access KB provisions above OFFICIAL
Data Access: SENSITIVE for own records only
Communication: internal self-service only
Temporal: business hours for applications; emergency contact 24/7
```

### Verification Gradient for HR Workflows

| Zone | Trigger | Arbor Examples |
|---|---|---|
| Auto-approved | Routine, within envelope | View own payslip, check leave balance, clock in/out |
| Flagged | Near boundary, unusual pattern | Leave request during notice period, overtime above threshold |
| Held | At boundary, judgment needed | Termination, wrongful dismissal claim, salary adjustment above band |
| Blocked | Outside envelope, hard constraint | Delete employee record, cancel completed payroll, override TAFEP rules |

### Cross-Department Bridges

**Leave to Payroll Bridge**:
- Leave approval (HR Manager) triggers payroll recalculation (Payroll Officer)
- Off-in-lieu encashment creates pay item
- Scoped: leave data flows to payroll; payroll data does not flow to HR Manager

**Recruitment to Onboarding Bridge**:
- Offer letter approved (Recruitment Lead) triggers employee creation (HR Manager)
- CPF enrollment initiated (Payroll Officer)
- Work pass application if foreign worker (HR + MOM submission)

**Compliance to Advisory Bridge**:
- KB provision updated (expert review required per CARE governance)
- Advisory engine automatically uses updated provision
- Trust chain records which expert approved the update

## Implementation Priority

1. **Organization Builder** — D/T/R tree creation when company onboards to Arbor
2. **Envelope Enforcement** — Constrain existing role-based access through envelope validation
3. **Knowledge Clearance** — Classify all 60+ DataFlow models by clearance level
4. **Verification Gradient** — Map existing approval workflows to four-zone gradient
5. **Bridge Modeling** — Formalize cross-module data flows as PACT bridges
6. **EATP Integration** — Extend trust lineage to include PACT context (which envelope, which clearance)

## Key Files to Modify

| Current File | PACT Change |
|---|---|
| `src/hr_advisory/models/company_user.py` | Add D/T/R node types and positional addressing |
| `src/hr_advisory/security/pdpa.py` | Integrate with PACT clearance framework |
| `src/hr_advisory/trust/eatp_lineage.py` | Add envelope and clearance context to trust records |
| `src/hr_advisory/workflows/guardrails.py` | Replace flat guardrails with envelope validation |
| `src/hr_advisory/shadow/observation.py` | Add envelope boundary detection |
| `src/hr_advisory/agents/orchestration/` | Route based on D/T/R addressing and clearance |
| All API routers | Add envelope check middleware |

## What Success Looks Like

When a shift supervisor at a logistics SME tries to view an employee's medical records through their Arbor shadow agent, the system:
1. Checks the supervisor's positional address (D1-R1-D3-R1-T1-R1)
2. Computes effective clearance: min(SENSITIVE role clearance, Shared Planning posture ceiling) = SENSITIVE
3. Checks medical records classification: SECRET
4. Result: BLOCKED. "Insufficient clearance for medical records. Contact HR Director."
5. Logs the access attempt as an Audit Anchor with the blocking reason

No configuration needed beyond the initial D/T/R setup. The architecture enforces it.
