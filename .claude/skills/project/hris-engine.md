# HRIS Engine Skill

Full HRIS operations: payroll, leave, claims, attendance, shifts, employee lifecycle.

## Module Map

| Module     | Router                      | Models                                                                                                     | Service                                                         | Frontend                                    |
| ---------- | --------------------------- | ---------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- | ------------------------------------------- |
| Payroll    | `api/routers/payroll.py`    | PayrollRun, Payslip, PayslipItem, CpfYtdRecord, TaxFiling                                                  | `services/payroll_calculator.py`, `services/statutory_files.py` | `/payroll`, `/payroll/[id]`, `/my-payslips` |
| Leave      | `api/routers/leave.py`      | LeaveTypeConfig, LeaveApplication, PublicHoliday, LeavePolicy, LeavePolicyEntitlement                      | —                                                               | `/leave`                                    |
| Claims     | `api/routers/claims.py`     | ClaimCategory, Claim, ClaimItem, ClaimAuditEntry                                                           | —                                                               | `/claims`                                   |
| Attendance | `api/routers/attendance.py` | AttendanceSettings, AttendanceRecord, TimesheetApproval                                                    | —                                                               | `/attendance`                               |
| Shifts     | `api/routers/shifts.py`     | ShiftTemplate, ShiftAssignment, ShiftPublish                                                               | —                                                               | `/shifts`                                   |
| Employee   | `api/routers/employees.py`  | Employee (30+ fields), SalaryComponent, EmergencyContact, EmploymentEvent, EmployeeDocument, PdpaAccessLog | —                                                               | `/employees`, `/employees/[id]`             |

## DataFlow Helper Pattern

Every router uses four identical helpers. This is the canonical pattern:

```python
def _dataflow_create(node_type: str, data: dict) -> dict:
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder
    import hr_advisory.models  # noqa: F401 — ensures models registered
    wf = WorkflowBuilder()
    wf.add_node(node_type, "create", data)
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["create"]

def _dataflow_list(node_type: str, filter_dict: dict, limit: int = 10000) -> list:
    # CRITICAL: enable_cache=False on ALL queries (prevents stale reads)
    # CRITICAL: limit=10000 (DataFlow default is ~10 — silently truncates)
    wf.add_node(node_type, "list", {"filter": filter_dict, "limit": limit, "enable_cache": False})
    # Result is {"records": [...], "count": N} — unwrap to list
```

## Router Endpoint Template

Every endpoint follows: auth → tenant → validate → execute → respond.

```python
@router.post("/endpoint")
async def handler(request: Request, current_user: dict = Depends(require_role("owner", "hr_manager"))) -> dict:
    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")
    # ... validate inputs (NaN check, length check)
    # ... execute business logic
    # ... return result
```

## Status Machines

| Entity            | States                                                          | Key Transition Rules                                                          |
| ----------------- | --------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| PayrollRun        | draft → approved → paid (+ cancelled)                           | Approve: owner only. Cancel approved: owner only.                             |
| LeaveApplication  | pending → approved/rejected/withdrawn/cancelled                 | Approve deducts balance. Cancel restores balance. Remarks required on reject. |
| Claim             | draft → submitted → pending_approval → approved/rejected → paid | Audit entry on every transition. Paid only via payroll mark-paid.             |
| TimesheetApproval | pending → approved/rejected                                     | Approved OT feeds into payroll.                                               |
| ShiftAssignment   | scheduled → confirmed → completed/cancelled/no_show             | No-show: no pay for that shift.                                               |

## Security Checklist (Every New Endpoint)

1. Auth decorator present (`Depends(get_current_user)` or `require_role`)
2. Company_id from JWT, never from request body
3. Ownership check after every record read (`record.company_id == company_id`)
4. Role-appropriate access (employees see own, admins see company)
5. Input validation (required fields, types, `math.isfinite()` on amounts, length limits)
6. Generic error messages (log details server-side, never `str(exc)` to client)
7. Status transition guard (verify current state before allowing change)
8. PDPA audit logging for encrypted fields (NRIC, bank, salary, work pass)
9. Balance coupling (leave/claims status changes must update balances atomically)

## PII Encryption

```python
from hr_advisory.security.encryption import encrypt_field, decrypt_field, mask_nric, mask_bank_account

# On write: encrypt before storing
updates["nric_fin"] = encrypt_field(nric_value)
updates["nric_fin_last4"] = nric_value[-4:]  # Derive BEFORE encrypting

# On read: decrypt for internal use, mask for display
full_nric = decrypt_field(emp.get("nric_fin", ""))
display_nric = mask_nric(full_nric)  # S****567D

# PDPA audit: log every access
_log_pdpa_access(accessed_by=user_id, company_id=company_id,
                 data_subject_id=emp_id, categories=["nric", "salary"], action="view")
```

## Cross-Module Integration

Payroll pulls from leave, attendance, and claims during calculation:

```
POST /payroll/calculate
  ├── For each employee:
  │   ├── Fetch unpaid leave → leave_deduction_days
  │   ├── Fetch approved timesheet → overtime_hours
  │   ├── Fetch approved claims → approved_claims_total
  │   └── calculate_employee_payslip(emp, components, period, ...)
  └── On mark-paid: update claims with paid_in_payroll_run_id
```

## Statutory Files

| File         | Format                     | Generator                     |
| ------------ | -------------------------- | ----------------------------- |
| CPF e-Submit | CSV: HEADER/DETAIL/TRAILER | `generate_cpf_esubmit()`      |
| Bank GIRO    | CSV or DBS fixed-width     | `generate_bank_giro(format=)` |
| IR8A         | JSON data structure        | `generate_ir8a_data()`        |
| IR21         | JSON data structure        | `generate_ir21_data()`        |
| Payslip      | HTML (EA s88A compliant)   | `generate_payslip_html()`     |

## Related Docs

- `docs/01-architecture.md` — System architecture with HRIS modules
- `docs/02-api-reference.md` — Complete API reference (payroll, leave, claims, attendance, shifts)
- `docs/03-security.md` — Security architecture
