"""DataFlow models for companies, users, conversations, and advisory sessions.

These models handle the transactional side of the platform: who is asking,
what company context they're in, what conversations they've had, and
what advisory responses were generated.
"""

from datetime import datetime
from typing import Optional

from hr_advisory.models.database import db
from hr_advisory.models.enums import RiskTier


# ---------------------------------------------------------------------------
# Enums (string-based for DataFlow compatibility)
# ---------------------------------------------------------------------------


class UserRole:
    OWNER = "owner"
    HR_MANAGER = "hr_manager"
    CONSULTANT = "consultant"
    EMPLOYEE = "employee"


class EmploymentType:
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"


class LeaveTypeCode:
    ANNUAL = "annual"
    SICK = "sick"
    HOSPITALIZATION = "hospitalization"
    MATERNITY = "maternity"
    PATERNITY = "paternity"
    CHILDCARE = "childcare"
    INFANT_CARE = "infant_care"
    ADOPTION = "adoption"
    SHARED_PARENTAL = "shared_parental"
    UNPAID_INFANT_CARE = "unpaid_infant_care"
    NS = "ns"
    COMPASSIONATE = "compassionate"
    MARRIAGE = "marriage"
    UNPAID = "unpaid"


class LeaveApplicationStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    WITHDRAWN = "withdrawn"


class LeaveCategory:
    STATUTORY = "statutory"
    COMPANY = "company"
    CUSTOM = "custom"


class Gender:
    MALE = "male"
    FEMALE = "female"


class Race:
    CHINESE = "chinese"
    MALAY = "malay"
    INDIAN = "indian"
    EURASIAN = "eurasian"
    OTHER = "other"


class ImmigrationStatus:
    CITIZEN = "citizen"
    PR_YEAR1 = "pr_year1"
    PR_YEAR2 = "pr_year2"
    PR_YEAR3_PLUS = "pr_year3_plus"
    FOREIGNER = "foreigner"


class PassType:
    EP = "ep"
    SP = "sp"
    WP = "wp"
    S_PASS = "s_pass"
    LTVP = "ltvp"
    DP = "dp"
    CITIZEN = "citizen"
    PR = "pr"


class ConfirmationStatus:
    ON_PROBATION = "on_probation"
    CONFIRMED = "confirmed"
    EXTENDED = "extended"
    TERMINATED = "terminated"


class SalaryComponentType:
    BASIC_SALARY = "basic_salary"
    FIXED_ALLOWANCE = "fixed_allowance"
    VARIABLE_ALLOWANCE = "variable_allowance"
    FIXED_DEDUCTION = "fixed_deduction"
    VARIABLE_DEDUCTION = "variable_deduction"
    COMMISSION = "commission"
    BONUS = "bonus"


class ComponentFrequency:
    MONTHLY = "monthly"
    WEEKLY = "weekly"
    DAILY = "daily"
    ONE_TIME = "one_time"
    PER_PAYROLL_RUN = "per_payroll_run"


class EmploymentEventType:
    HIRED = "hired"
    PROMOTED = "promoted"
    TRANSFERRED = "transferred"
    SALARY_REVISION = "salary_revision"
    CONFIRMED = "confirmed"
    RESIGNED = "resigned"
    TERMINATED = "terminated"
    RETRENCHED = "retrenched"
    CONTRACT_RENEWED = "contract_renewed"


class DocumentType:
    CONTRACT = "contract"
    OFFER_LETTER = "offer_letter"
    KET = "ket"
    CERTIFICATION = "certification"
    WARNING_LETTER = "warning_letter"
    TERMINATION_LETTER = "termination_letter"
    NRIC_COPY = "nric_copy"
    WORK_PASS_COPY = "work_pass_copy"
    MEDICAL_CERT = "medical_cert"
    OTHER = "other"


class PayrollRunStatus:
    DRAFT = "draft"
    CALCULATING = "calculating"
    REVIEW = "review"
    APPROVED = "approved"
    PAID = "paid"
    CANCELLED = "cancelled"


class ClaimStatus:
    DRAFT = "draft"
    SUBMITTED = "submitted"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"
    CANCELLED = "cancelled"


class AttendanceStatus:
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    HALF_DAY = "half_day"
    ON_LEAVE = "on_leave"
    HOLIDAY = "holiday"


class TimesheetStatus:
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PayrollType:
    MONTHLY = "monthly"
    BONUS = "bonus"
    BACK_PAY = "back_pay"
    FINAL = "final"


class PayslipStatus:
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    PAID = "paid"


class PayslipItemType:
    BASIC_SALARY = "basic_salary"
    ALLOWANCE = "allowance"
    DEDUCTION = "deduction"
    OVERTIME = "overtime"
    BONUS = "bonus"
    COMMISSION = "commission"
    BACK_PAY = "back_pay"
    NO_PAY_LEAVE_DEDUCTION = "no_pay_leave_deduction"
    EMPLOYER_CPF = "employer_cpf"
    EMPLOYEE_CPF = "employee_cpf"
    SDL = "sdl"
    FWL = "fwl"
    SHG = "shg"
    CLAIM_REIMBURSEMENT = "claim_reimbursement"


class TaxFilingType:
    IR8A = "ir8a"
    APPENDIX_8A = "appendix_8a"
    IR21 = "ir21"


class ShiftAssignmentStatus:
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class PolicyType:
    LEAVE = "leave"
    FWA = "fwa"
    HANDBOOK = "handbook"
    SAFETY = "safety"
    BENEFITS = "benefits"


class ContentUpdateStatus:
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class ContentUrgency:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


@db.model
class Company:
    """A Singapore SME company profile.

    Stores workforce composition used for provision applicability filtering.
    Multi-tenant enabled for consultant access to multiple clients.
    """

    name: str
    uen: Optional[str] = None
    sector: Optional[str] = None
    sub_sector: Optional[str] = None
    headcount_local: int = 0
    headcount_pr: int = 0
    headcount_ep: int = 0
    headcount_sp: int = 0
    headcount_wp: int = 0
    salary_ranges: Optional[dict] = None
    profile_completeness_score: float = 0.0
    monthly_llm_budget_usd: float = 5.00
    is_active: bool = True

    __dataflow__ = {
        "multi_tenant": True,
        "indexes": [
            {"name": "idx_company_uen", "fields": ["uen"]},
            {"name": "idx_company_sector", "fields": ["sector"]},
        ],
    }


@db.model
class User:
    """A platform user linked to a company.

    Stores preferences (text size, notifications, language) as JSON.
    """

    email: str
    name: str
    company_id: Optional[int] = None
    role: str = UserRole.OWNER
    preferences: Optional[dict] = None
    password_hash: Optional[str] = None
    is_active: bool = True
    last_login_at: Optional[datetime] = None

    __dataflow__ = {
        "indexes": [
            {"name": "idx_user_email", "fields": ["email"]},
            {"name": "idx_user_company", "fields": ["company_id"]},
        ],
    }


@db.model
class Conversation:
    """A conversation thread grouping related advisory sessions.

    Each conversation belongs to a user+company context and may
    contain multiple back-and-forth advisory exchanges.
    """

    user_id: int
    company_id: Optional[int] = None
    title: str = ""
    is_active: bool = True

    __dataflow__ = {
        "indexes": [
            {"name": "idx_conversation_user", "fields": ["user_id"]},
            {"name": "idx_conversation_company", "fields": ["company_id"]},
        ],
    }


@db.model
class AdvisorySession:
    """A single query-response exchange within a conversation.

    Stores the full audit trail: which provisions were cited,
    which agents were involved, confidence score, risk tier,
    trust lineage (EATP), and genesis record (COC).
    """

    conversation_id: int
    user_id: int
    company_id: Optional[int] = None
    query_text: str
    response_text: str = ""
    provisions_cited: Optional[dict] = None
    agents_involved: Optional[dict] = None
    confidence_score: float = 0.0
    risk_tier: str = RiskTier.GREEN.value
    trust_lineage: Optional[dict] = None
    genesis_record: Optional[dict] = None
    feedback_rating: Optional[str] = None
    feedback_text: Optional[str] = None

    __dataflow__ = {
        "indexes": [
            {"name": "idx_session_conversation", "fields": ["conversation_id"]},
            {"name": "idx_session_user", "fields": ["user_id"]},
            {"name": "idx_session_company", "fields": ["company_id"]},
            {"name": "idx_session_risk_tier", "fields": ["risk_tier"]},
        ],
    }


@db.model
class ContentUpdate:
    """Tracks regulatory content changes (e.g. new MOM circular, CPF rate change).

    Used to alert companies about changes affecting them and to
    trigger knowledge base updates.
    """

    source_url: Optional[str] = None
    change_summary: str = ""
    affected_domains: Optional[dict] = None
    urgency: str = ContentUrgency.MEDIUM
    status: str = ContentUpdateStatus.DRAFT
    author_id: Optional[int] = None
    published_at: Optional[datetime] = None

    __dataflow__ = {
        "indexes": [
            {"name": "idx_content_update_status", "fields": ["status"]},
            {"name": "idx_content_update_urgency", "fields": ["urgency"]},
        ],
    }


@db.model
class Template:
    """Reusable document templates linked to provisions.

    Examples: Employment contract template, FWA request form,
    performance review template.
    """

    name: str
    template_type: str = ""
    content: str = ""
    template_version: int = 1
    linked_provision_ids: Optional[dict] = None

    __dataflow__ = {
        "indexes": [
            {"name": "idx_template_type", "fields": ["template_type"]},
        ],
    }


# ---------------------------------------------------------------------------
# Employee & Multi-Tenant Models (M15)
# ---------------------------------------------------------------------------


@db.model
class Employee:
    """Employee record linked to a User and Company.

    Tracks employment details including department, designation,
    nationality/pass type (for Singapore MOM compliance), salary,
    personal details (DOB, NRIC, bank), and lifecycle (probation, reporting).
    """

    user_id: int
    company_id: int
    employee_id_internal: str = ""
    department: str = ""
    designation: str = ""
    employment_type: str = EmploymentType.FULL_TIME
    start_date: str = ""
    end_date: str = ""
    nationality: str = ""
    pass_type: str = ""
    salary_monthly: float = 0.0
    notice_period_days: int = 0
    is_active: bool = True

    # Personal details (T141)
    date_of_birth: str = ""
    gender: str = ""
    marital_status: str = ""
    race: str = ""

    # Identity documents — stored as plaintext for now, encrypted in T191
    nric_fin: str = ""
    nric_fin_last4: str = ""

    # Work pass details
    work_pass_number: str = ""
    work_pass_expiry: str = ""
    immigration_status: str = ImmigrationStatus.CITIZEN
    immigration_effective_date: str = ""

    # Banking details
    bank_name: str = ""
    bank_account_number: str = ""
    bank_account_last4: str = ""
    bank_code: str = ""

    # Address
    residential_address: str = ""
    postal_code: str = ""

    # Organisational hierarchy
    reporting_manager_id: Optional[int] = None

    # Leave policy
    leave_policy_id: Optional[int] = None

    # Probation & confirmation
    probation_months: int = 3
    probation_end_date: str = ""
    confirmation_status: str = ConfirmationStatus.ON_PROBATION

    # --- M39: Employee Profile Extensions (T298) ---

    # Personal (extended)
    religion: str = ""  # buddhist/christian/hindu/islam/sikh/taoist/none/other
    phone: str = ""
    alias: str = ""  # display name
    photo_url: str = ""

    # Employment (extended)
    salary_type: str = "monthly"  # monthly/daily/hourly
    hourly_rate: float = 0.0
    daily_rate: float = 0.0
    payment_method: str = "giro"  # giro/fast/cheque/cash
    payment_frequency: str = "monthly"  # monthly/bi_weekly/weekly
    overtime_eligible: bool = True
    working_hours_type: str = "fixed"  # fixed/shift/flexible

    # Bank (extended)
    branch_code: str = ""

    # Tax
    iras_auto_inclusion: bool = True
    tax_reference: str = ""

    # Tags (JSON string — DataFlow doesn't support native JSON arrays)
    tags: str = ""

    # Statutory (extended)
    cpf_status: str = "include"  # include/exclude/full_employer
    amcs_enabled: bool = False
    pmbs_enabled: bool = False
    community_chest_amount: float = 0.0
    shg_override_amount: float = 0.0

    # Address (structured)
    address_block: str = ""
    address_street: str = ""
    address_unit: str = ""  # e.g., "#05-123"
    address_building: str = ""
    address_postal_code: str = ""  # 6-digit SG postal

    # Organization
    organization_id: Optional[int] = None
    branch_id: Optional[int] = None
    cost_centre_id: Optional[int] = None
    pay_scheme_id: Optional[int] = None

    __dataflow__ = {
        "indexes": [
            {"name": "idx_employee_user", "fields": ["user_id"]},
            {"name": "idx_employee_company", "fields": ["company_id"]},
            {"name": "idx_employee_department", "fields": ["department"]},
            {"name": "idx_employee_active", "fields": ["is_active"]},
            {"name": "idx_employee_manager", "fields": ["reporting_manager_id"]},
        ],
    }


@db.model
class SalaryComponent:
    """Salary component (allowance, deduction, commission, bonus) for an employee.

    Replaces the single salary_monthly field with a structured breakdown
    that supports multiple component types for payroll processing.
    """

    employee_id: int
    company_id: int
    component_type: str = SalaryComponentType.FIXED_ALLOWANCE
    name: str = ""
    amount: float = 0.0
    frequency: str = ComponentFrequency.MONTHLY
    is_taxable: bool = True
    is_cpf_applicable: bool = True
    effective_from: str = ""
    effective_to: str = ""
    is_active: bool = True

    __dataflow__ = {
        "indexes": [
            {"name": "idx_salcomp_employee", "fields": ["employee_id"]},
            {"name": "idx_salcomp_company", "fields": ["company_id"]},
            {"name": "idx_salcomp_active", "fields": ["is_active"]},
        ],
    }


@db.model
class EmergencyContact:
    """Emergency contact / next-of-kin for an employee.

    Up to 3 contacts per employee, ordered by priority.
    """

    employee_id: int
    company_id: int
    name: str = ""
    relationship: str = ""  # spouse/parent/sibling/child/friend/other
    phone: str = ""
    phone_primary: str = ""
    phone_secondary: str = ""
    email: str = ""
    is_primary: bool = False
    is_next_of_kin: bool = False
    priority: int = 1

    __dataflow__ = {
        "indexes": [
            {"name": "idx_emgcontact_employee", "fields": ["employee_id"]},
            {"name": "idx_emergency_company", "fields": ["company_id"]},
        ],
    }


@db.model
class EmploymentEvent:
    """Employment event tracking (promotion, salary revision, transfer, etc.).

    Auto-generated when key employee fields change. Provides an audit trail
    of the employee's journey within the company.
    """

    employee_id: int
    company_id: int
    event_type: str = EmploymentEventType.HIRED
    event_date: str = ""
    description: str = ""
    old_value: Optional[dict] = None
    new_value: Optional[dict] = None
    effective_date: str = ""
    approved_by: Optional[int] = None
    notes: str = ""

    __dataflow__ = {
        "indexes": [
            {"name": "idx_empevent_employee", "fields": ["employee_id"]},
            {"name": "idx_empevent_company", "fields": ["company_id"]},
            {"name": "idx_empevent_type", "fields": ["event_type"]},
        ],
    }


@db.model
class EmployeeDocument:
    """Document stored for an employee (contract, NRIC copy, MC, etc.).

    Files stored on local filesystem (dev) or S3 (production).
    """

    employee_id: int
    company_id: int
    document_type: str = DocumentType.OTHER
    file_name: str = ""
    file_path: str = ""
    file_url: str = ""
    file_size: int = 0
    mime_type: str = ""
    uploaded_by: int = 0
    upload_date: str = ""
    description: str = ""
    expiry_date: str = ""
    notification_days_before: int = 30
    notes: str = ""
    is_confidential: bool = False
    is_active: bool = True

    __dataflow__ = {
        "indexes": [
            {"name": "idx_empdoc_employee", "fields": ["employee_id"]},
            {"name": "idx_empdoc_company", "fields": ["company_id"]},
            {"name": "idx_empdoc_type", "fields": ["document_type"]},
            {"name": "idx_empdoc_expiry", "fields": ["expiry_date"]},
        ],
    }


@db.model
class PdpaAccessLog:
    """Audit log for access to PDPA-protected personal data.

    Records every read/export/modify of encrypted fields (NRIC, bank account,
    salary, work pass) for regulatory compliance.
    """

    accessed_by: int  # User ID of accessor
    company_id: int
    data_subject_id: int  # Employee ID whose data was accessed
    data_category: str = ""  # nric/bank_account/salary/work_pass/medical
    action: str = ""  # view/export/modify
    ip_address: str = ""
    justification: str = ""

    __dataflow__ = {
        "indexes": [
            {"name": "idx_pdpa_accessed_by", "fields": ["accessed_by"]},
            {"name": "idx_pdpa_subject", "fields": ["data_subject_id"]},
            {"name": "idx_pdpa_company", "fields": ["company_id"]},
        ],
    }


# ---------------------------------------------------------------------------
# Payroll Models
# ---------------------------------------------------------------------------


@db.model
class PayrollRun:
    """A payroll run for a company covering a specific pay period.

    Tracks the lifecycle from draft through calculation, review,
    approval, and payment. Aggregates totals for all employees
    in the run.
    """

    company_id: int
    period_start: str = ""
    period_end: str = ""
    pay_date: str = ""
    status: str = PayrollRunStatus.DRAFT
    payroll_type: str = PayrollType.MONTHLY
    total_gross: float = 0.0
    total_net: float = 0.0
    total_employer_cpf: float = 0.0
    total_employee_cpf: float = 0.0
    total_sdl: float = 0.0
    total_fwl: float = 0.0
    total_shg: float = 0.0
    employee_count: int = 0
    created_by: int = 0
    approved_by: Optional[int] = None
    approved_at: str = ""
    notes: str = ""

    __dataflow__ = {
        "indexes": [
            {"name": "idx_payrollrun_company", "fields": ["company_id"]},
            {"name": "idx_payrollrun_status", "fields": ["status"]},
            {"name": "idx_payrollrun_company_period", "fields": ["company_id", "period_start"]},
        ],
    }


@db.model
class Payslip:
    """Individual payslip for an employee within a payroll run.

    Contains the computed gross-to-net breakdown including CPF,
    SDL, FWL, and SHG contributions.
    """

    payroll_run_id: int
    employee_id: int
    company_id: int
    period_start: str = ""
    period_end: str = ""
    basic_salary: float = 0.0
    gross_salary: float = 0.0
    net_salary: float = 0.0
    employer_cpf: float = 0.0
    employee_cpf: float = 0.0
    sdl: float = 0.0
    fwl: float = 0.0
    shg_fund: str = ""
    shg_amount: float = 0.0
    cpf_ow_used: float = 0.0
    cpf_aw_used: float = 0.0
    status: str = PayslipStatus.DRAFT

    __dataflow__ = {
        "indexes": [
            {"name": "idx_payslip_run", "fields": ["payroll_run_id"]},
            {"name": "idx_payslip_employee", "fields": ["employee_id"]},
            {"name": "idx_payslip_employee_period", "fields": ["employee_id", "period_start"]},
        ],
    }


@db.model
class PayslipItem:
    """Line item on a payslip (earnings, deductions, statutory contributions).

    Each payslip has multiple items that sum to the gross and net totals.
    """

    payslip_id: int
    company_id: int
    item_type: str = ""
    name: str = ""
    amount: float = 0.0
    is_taxable: bool = True
    is_cpf_applicable: bool = True
    notes: str = ""

    __dataflow__ = {
        "indexes": [
            {"name": "idx_payslipitem_payslip", "fields": ["payslip_id"]},
        ],
    }


@db.model
class CpfYtdRecord:
    """Year-to-date CPF contribution record per employee per month.

    Tracks cumulative OW and AW subject to CPF for annual ceiling
    calculations. One record per employee per month.
    """

    employee_id: int
    company_id: int
    year: int
    month: int
    ow_subject_to_cpf: float = 0.0
    aw_subject_to_cpf: float = 0.0
    ytd_ow_total: float = 0.0
    ytd_aw_total: float = 0.0
    employer_cpf: float = 0.0
    employee_cpf: float = 0.0
    payslip_id: int = 0

    __dataflow__ = {
        "indexes": [
            {"name": "idx_cpfytd_employee_year", "fields": ["employee_id", "year"]},
        ],
    }


@db.model
class TaxFiling:
    """Tax filing record for IR8A / Appendix 8A / IR21 submissions.

    Stores structured data for IRAS filings per employee per tax year.
    """

    company_id: int
    employee_id: int
    tax_year: int
    filing_type: str = TaxFilingType.IR8A
    data: Optional[dict] = None
    status: str = "draft"
    submitted_date: str = ""

    __dataflow__ = {
        "indexes": [
            {"name": "idx_taxfiling_company_year", "fields": ["company_id", "tax_year"]},
            {"name": "idx_taxfiling_employee_year", "fields": ["employee_id", "tax_year"]},
        ],
    }


@db.model
class ShiftTemplate:
    """Reusable shift template defining working hours for scheduling.

    Stores start/end times, break duration, total work hours, and
    a display colour for the schedule grid.
    """

    company_id: int
    name: str = ""
    start_time: str = "09:00"
    end_time: str = "17:00"
    break_minutes: int = 60
    work_hours: float = 8.0
    colour: str = "#4A90C4"
    is_active: bool = True

    __dataflow__ = {
        "indexes": [
            {"name": "idx_shifttemplate_company", "fields": ["company_id"]},
        ],
    }


@db.model
class ShiftAssignment:
    """An employee's scheduled shift on a specific date.

    Links an employee to a shift template for a given day, tracking
    actual start/end times and status through the lifecycle.
    """

    employee_id: int
    company_id: int
    shift_template_id: int
    date: str = ""
    status: str = ShiftAssignmentStatus.SCHEDULED
    actual_start: str = ""
    actual_end: str = ""
    notes: str = ""

    __dataflow__ = {
        "indexes": [
            {"name": "idx_shiftassign_emp_date", "fields": ["employee_id", "date"]},
            {"name": "idx_shiftassign_company_date", "fields": ["company_id", "date"]},
        ],
    }


@db.model
class ShiftPublish:
    """Audit record for when a weekly schedule was published.

    Records who published the schedule and when, for compliance
    and communication tracking.
    """

    company_id: int
    week_start: str = ""
    published_at: str = ""
    published_by: int = 0

    __dataflow__ = {
        "indexes": [
            {"name": "idx_shiftpublish_company", "fields": ["company_id"]},
        ],
    }


@db.model
class LeaveTypeConfig:
    """Configurable leave type for a company.

    Defines entitlement rules, carry-forward policy, attachment requirements,
    and applicability filters (gender, minimum service) for each leave type.
    """

    company_id: int
    name: str = ""
    code: str = ""
    category: str = LeaveCategory.STATUTORY
    is_paid: bool = True
    is_pro_ratable: bool = True
    default_days: float = 0.0
    max_carry_forward: float = 0.0
    carry_forward_expiry_months: int = 0
    requires_attachment: bool = False
    min_service_months: int = 0
    applicable_gender: str = ""  # all/male/female
    is_active: bool = True

    __dataflow__ = {
        "indexes": [
            {"name": "idx_leavetypeconfig_company", "fields": ["company_id"]},
        ],
    }


@db.model
class LeaveApplication:
    """Employee leave application with approval workflow.

    Tracks the full lifecycle from submission through approval/rejection,
    including half-day support, attachment paths, and reviewer audit trail.
    """

    employee_id: int
    company_id: int
    leave_type_id: int
    leave_type_code: str = ""
    start_date: str = ""
    end_date: str = ""
    start_half: str = "full_day"  # full_day/first_half/second_half
    end_half: str = "full_day"
    total_days: float = 0.0
    reason: str = ""
    attachment_path: str = ""
    status: str = LeaveApplicationStatus.PENDING
    applied_at: str = ""
    reviewed_by: Optional[int] = None
    reviewed_at: str = ""
    reviewer_remarks: str = ""

    __dataflow__ = {
        "indexes": [
            {"name": "idx_leaveapp_employee", "fields": ["employee_id"]},
            {"name": "idx_leaveapp_company", "fields": ["company_id"]},
            {"name": "idx_leaveapp_status", "fields": ["status"]},
        ],
    }


@db.model
class PublicHoliday:
    """Public holiday entry for leave calculation.

    Supports both national (company_id=0) and company-specific holidays.
    Used by the leave calculator to exclude non-working days.
    """

    company_id: int = 0  # 0 = national, >0 = company-specific
    name: str = ""
    date: str = ""
    year: int = 0
    is_gazetted: bool = True

    __dataflow__ = {
        "indexes": [
            {"name": "idx_pubhol_year", "fields": ["year"]},
        ],
    }


@db.model
class LeavePolicy:
    """Leave policy grouping (e.g. Full-time, Part-time, Management).

    Links to LeavePolicyEntitlement records that define per-leave-type
    entitlements within this policy.
    """

    company_id: int
    name: str = ""
    is_default: bool = False
    is_active: bool = True

    __dataflow__ = {
        "indexes": [
            {"name": "idx_leavepolicy_company", "fields": ["company_id"]},
        ],
    }


@db.model
class LeavePolicyEntitlement:
    """Entitlement for a specific leave type within a policy.

    Defines how many days an employee under this policy gets for a
    given leave type, plus carry-forward allowance.
    """

    policy_id: int
    company_id: int
    leave_type_id: int
    days: float = 0.0
    carry_forward_days: float = 0.0

    __dataflow__ = {
        "indexes": [
            {"name": "idx_lpentitle_policy", "fields": ["policy_id"]},
        ],
    }


@db.model
class LeaveBalance:
    """Leave balance for an employee.

    Tracks entitlement, used, and pending days per leave type per year.
    Leave types follow Singapore Employment Act categories.
    """

    employee_id: int
    company_id: int
    leave_type: str
    year: int
    entitlement_days: float = 0.0
    used_days: float = 0.0
    pending_days: float = 0.0

    __dataflow__ = {
        "indexes": [
            {"name": "idx_leave_employee", "fields": ["employee_id"]},
            {"name": "idx_leave_company", "fields": ["company_id"]},
            {"name": "idx_leave_type_year", "fields": ["leave_type", "year"]},
        ],
    }


@db.model
class CompanyPolicy:
    """Company policy document.

    Stores policy content (leave, FWA, handbook, safety, benefits)
    with versioning via effective_date and version_number.
    Categories use a 9-value taxonomy (+ custom strings).
    Supports file uploads (PDF/DOCX/TXT) with text extraction.
    """

    company_id: int
    policy_type: str
    title: str = ""
    content: str = ""
    effective_date: str = ""
    is_active: bool = True
    # --- New fields for company policy upload feature ---
    category: str = ""
    version_number: int = 1
    superseded_by_id: int = 0
    uploaded_by: int = 0
    file_name: str = ""
    file_path: str = ""
    file_type: str = ""
    file_size_bytes: int = 0
    content_hash: str = ""
    extraction_status: str = ""
    requires_acknowledgment: bool = False
    status: str = "active"

    __dataflow__ = {
        "indexes": [
            {"name": "idx_policy_company", "fields": ["company_id"]},
            {"name": "idx_policy_type", "fields": ["policy_type"]},
            {"name": "idx_policy_active", "fields": ["is_active"]},
            {"name": "idx_policy_category", "fields": ["category"]},
            {"name": "idx_policy_status", "fields": ["status"]},
        ],
    }


@db.model
class PolicyAcknowledgment:
    """Tracks employee acknowledgment of company policies.

    Created when an employee acknowledges a specific version of a policy.
    Idempotent: re-acknowledging the same version is a no-op.
    """

    company_id: int
    policy_id: int
    employee_id: int
    version_acknowledged: int = 1
    acknowledged_at: str = ""
    ip_address: str = ""

    __dataflow__ = {
        "indexes": [
            {"name": "idx_ack_company", "fields": ["company_id"]},
            {"name": "idx_ack_policy", "fields": ["policy_id"]},
            {"name": "idx_ack_employee", "fields": ["employee_id"]},
        ],
    }


@db.model
class Invitation:
    """Employee invitation to join a company on the platform.

    Created by admins (owner/hr_manager) to invite employees.
    Token-based with expiry for secure onboarding.
    """

    company_id: int
    inviter_id: int
    email: str
    role: str = UserRole.EMPLOYEE
    token: str = ""
    expires_at: str = ""
    accepted_at: str = ""
    is_active: bool = True

    __dataflow__ = {
        "indexes": [
            {"name": "idx_invitation_company", "fields": ["company_id"]},
            {"name": "idx_invitation_email", "fields": ["email"]},
            {"name": "idx_invitation_token", "fields": ["token"]},
        ],
    }


# ---------------------------------------------------------------------------
# Claims / Expenses Models
# ---------------------------------------------------------------------------


@db.model
class ClaimCategory:
    """Expense claim category for a company.

    Defines limits and receipt requirements for each category of claimable
    expense (e.g. transport, meals, medical).
    """

    company_id: int
    name: str
    monthly_limit: float = 0.0  # 0 = unlimited
    per_claim_limit: float = 0.0  # 0 = unlimited
    requires_receipt: bool = True
    is_active: bool = True

    __dataflow__ = {
        "indexes": [
            {"name": "idx_claimcat_company", "fields": ["company_id"]},
            {"name": "idx_claimcat_active", "fields": ["is_active"]},
        ],
    }


@db.model
class Claim:
    """An expense claim submitted by an employee.

    Groups one or more ClaimItems under a single submission for a given
    month. Follows a draft -> submitted -> pending_approval -> approved/rejected
    -> paid lifecycle.
    """

    employee_id: int
    company_id: int
    claim_month: str = ""
    status: str = ClaimStatus.DRAFT
    total_amount: float = 0.0
    submitted_at: str = ""
    reviewed_by: Optional[int] = None
    reviewed_at: str = ""
    reviewer_remarks: str = ""
    paid_in_payroll_run_id: Optional[int] = None

    __dataflow__ = {
        "indexes": [
            {"name": "idx_claim_employee", "fields": ["employee_id"]},
            {"name": "idx_claim_company", "fields": ["company_id"]},
            {"name": "idx_claim_status", "fields": ["status"]},
            {"name": "idx_claim_month", "fields": ["claim_month"]},
        ],
    }


@db.model
class ClaimItem:
    """A single line item within an expense claim.

    Each item is linked to a ClaimCategory and may have receipt attachments.
    """

    claim_id: int
    company_id: int
    category_id: int
    description: str = ""
    amount: float = 0.0
    receipt_date: str = ""
    receipt_paths: Optional[dict] = None  # JSON array of file paths
    notes: str = ""

    __dataflow__ = {
        "indexes": [
            {"name": "idx_claimitem_claim", "fields": ["claim_id"]},
            {"name": "idx_claimitem_category", "fields": ["category_id"]},
        ],
    }


@db.model
class ClaimAuditEntry:
    """Audit trail entry for a claim status change or action.

    Auto-created whenever a claim's status changes (submit, approve,
    reject, cancel, pay).
    """

    claim_id: int
    company_id: int
    action: str = ""
    actor_id: int = 0
    details: Optional[dict] = None

    __dataflow__ = {
        "indexes": [
            {"name": "idx_claimaudit_claim", "fields": ["claim_id"]},
        ],
    }


# ---------------------------------------------------------------------------
# Attendance / Time-Tracking Models
# ---------------------------------------------------------------------------


@db.model
class AttendanceSettings:
    """Company-level attendance configuration.

    Defines working hours, grace period for lateness, overtime threshold,
    and optional GPS/photo verification requirements.
    """

    company_id: int
    work_start_time: str = "09:00"
    work_end_time: str = "18:00"
    grace_period_minutes: int = 15
    overtime_threshold_minutes: int = 30
    require_gps: bool = False
    require_photo: bool = False
    allowed_locations: Optional[dict] = None

    __dataflow__ = {
        "indexes": [
            {"name": "idx_attsettings_company", "fields": ["company_id"]},
        ],
    }


@db.model
class AttendanceRecord:
    """Daily attendance record for an employee.

    Tracks clock-in/out times, optional location and photo proof,
    computed work hours and overtime.
    """

    employee_id: int
    company_id: int
    date: str = ""
    clock_in: str = ""
    clock_out: str = ""
    clock_in_location: Optional[dict] = None
    clock_out_location: Optional[dict] = None
    clock_in_photo: str = ""
    clock_out_photo: str = ""
    status: str = AttendanceStatus.PRESENT
    work_hours: float = 0.0
    overtime_hours: float = 0.0
    remarks: str = ""
    is_manual: bool = False

    __dataflow__ = {
        "indexes": [
            {"name": "idx_attrec_employee", "fields": ["employee_id"]},
            {"name": "idx_attrec_company", "fields": ["company_id"]},
            {"name": "idx_attrec_date", "fields": ["date"]},
            {"name": "idx_attrec_employee_date", "fields": ["employee_id", "date"]},
        ],
    }


@db.model
class TimesheetApproval:
    """Monthly timesheet approval record.

    Aggregates an employee's attendance for a given month and tracks
    the submission and approval lifecycle.
    """

    employee_id: int
    company_id: int
    month: str = ""
    status: str = TimesheetStatus.PENDING
    total_work_hours: float = 0.0
    total_ot_hours: float = 0.0
    submitted_at: str = ""
    approved_by: Optional[int] = None
    approved_at: str = ""

    __dataflow__ = {
        "indexes": [
            {"name": "idx_timesheet_employee", "fields": ["employee_id"]},
            {"name": "idx_timesheet_company", "fields": ["company_id"]},
            {"name": "idx_timesheet_status", "fields": ["status"]},
            {"name": "idx_timesheet_month", "fields": ["month"]},
        ],
    }


# ---------------------------------------------------------------------------
# M39: Employee Profile Models (T300-T307)
# ---------------------------------------------------------------------------


@db.model
class FamilyMember:
    """Family member record for an employee (T300).

    Tracks dependants for benefits, tax relief, and emergency contact purposes.
    Supports spouse, children, and parents.
    """

    employee_id: int
    company_id: int
    name: str = ""
    relationship: str = ""  # spouse/child/parent
    date_of_birth: str = ""
    gender: str = ""
    citizenship_status: str = ""  # citizen/pr/foreigner
    nric_fin: str = ""  # encrypted

    __dataflow__ = {
        "indexes": [
            {"name": "idx_family_employee", "fields": ["employee_id"]},
            {"name": "idx_family_company", "fields": ["company_id"]},
        ],
    }


@db.model
class EmployeeNote:
    """Internal note on an employee record (T302).

    Supports general, performance, disciplinary, and confidential notes.
    Confidential notes are restricted to HR managers and owners.
    """

    employee_id: int
    company_id: int
    note_type: str = "general"  # general/performance/disciplinary/confidential
    content: str = ""
    created_by: int = 0
    is_confidential: bool = False

    __dataflow__ = {
        "indexes": [
            {"name": "idx_empnote_employee", "fields": ["employee_id"]},
            {"name": "idx_empnote_company", "fields": ["company_id"]},
        ],
    }


@db.model
class EmployeeEvent:
    """Timeline event for an employee (T304).

    Captures the full audit trail of changes to an employee's profile,
    salary, department, and status. Each event stores old/new values
    as JSON strings for diffing.
    """

    employee_id: int
    company_id: int
    event_type: str = (
        ""  # created/profile_updated/salary_changed/promoted/department_changed/probation_confirmed/leave_approved/terminated/document_uploaded/note_added
    )
    description: str = ""
    changed_by: int = 0
    old_value: str = ""  # JSON string
    new_value: str = ""  # JSON string
    event_date: str = ""

    __dataflow__ = {
        "indexes": [
            {"name": "idx_event_employee", "fields": ["employee_id"]},
            {"name": "idx_event_company", "fields": ["company_id"]},
            {"name": "idx_event_date", "fields": ["event_date"]},
        ],
    }


@db.model
class EmployeeSkill:
    """Skill or certification record for an employee (T307).

    Tracks professional skills, certifications, and their expiry dates
    for compliance and workforce planning.
    """

    employee_id: int
    company_id: int
    skill_name: str = ""
    proficiency_level: str = ""  # basic/intermediate/advanced/expert
    certification_name: str = ""
    certification_number: str = ""
    certified_date: str = ""
    expiry_date: str = ""
    issuing_body: str = ""

    __dataflow__ = {
        "indexes": [
            {"name": "idx_skill_employee", "fields": ["employee_id"]},
            {"name": "idx_skill_company", "fields": ["company_id"]},
            {"name": "idx_skill_expiry", "fields": ["expiry_date"]},
        ],
    }


@db.model
class CustomFieldDefinition:
    """Custom field definition for a company (T303).

    Allows companies to define their own fields for employees, leave,
    or claims without schema changes. Supports text, number, date,
    dropdown, and checkbox types.
    """

    company_id: int
    field_name: str = ""
    field_label: str = ""
    field_type: str = "text"  # text/number/date/dropdown/checkbox
    dropdown_options: str = ""  # JSON array string
    is_required: bool = False
    display_order: int = 0
    applies_to: str = "employee"  # employee/leave/claim

    __dataflow__ = {
        "indexes": [
            {"name": "idx_customdef_company", "fields": ["company_id"]},
        ],
    }


@db.model
class CustomFieldValue:
    """Custom field value for an entity (T303).

    Stores the actual value for a custom field on a specific entity
    (employee, leave application, or claim). Values stored as JSON
    strings to support any type.
    """

    entity_type: str = "employee"  # employee/leave/claim
    entity_id: int = 0
    field_definition_id: int = 0
    company_id: int = 0
    value: str = ""  # JSON — supports any type

    __dataflow__ = {
        "indexes": [
            {"name": "idx_customval_entity", "fields": ["entity_type", "entity_id"]},
            {"name": "idx_customval_field", "fields": ["field_definition_id"]},
        ],
    }


# ---------------------------------------------------------------------------
# M45: Payroll Enhancements
# ---------------------------------------------------------------------------


@db.model
class PayItem:
    """Pay item definition for a company (T336)."""

    company_id: int
    name: str = ""
    category: str = "salary"  # salary/overtime/allowance/deduction/reimbursement/bonus/commission
    cpf_type: str = "ow"  # ow/aw/exempt
    ir8a_code: str = ""
    unit_type: str = "fixed_amount"  # fixed_amount/hours/days
    default_amount: float = 0.0
    is_recurring: bool = False
    is_taxable: bool = True
    is_cpf_applicable: bool = True
    display_on_shift: bool = False
    allow_adhoc_request: bool = False
    allow_project_costing: bool = True
    exclude_from_project_costing: bool = False
    is_archived: bool = False

    __dataflow__ = {
        "indexes": [
            {"name": "idx_payitem_company", "fields": ["company_id"]},
        ],
    }


@db.model
class PayScheme:
    """Pay scheme template (T337)."""

    company_id: int
    name: str = ""
    pay_type: str = "monthly"  # monthly/daily/hourly
    currency: str = "SGD"
    base_amount: float = 0.0
    has_overtime: bool = False
    ot_base_hourly_rate: float = 0.0
    ot_rate_normal: float = 1.5
    ot_rate_rest_day: float = 2.0
    ot_rate_holiday: float = 2.0
    ot_recording_method: str = "after_working_hours"  # after_working_hours/after_fixed_hours
    ot_threshold_weekly: float = 44.0
    ot_threshold_monthly: float = 0.0
    work_hours_type: str = "fixed_days"  # fixed_days/fixed_timing/shift/flexible
    holiday_group_id: int = 0
    prorate_by_attendance: bool = False
    recurring_pay_items: str = ""  # JSON array of {pay_item_id, amount}
    is_archived: bool = False

    __dataflow__ = {
        "indexes": [
            {"name": "idx_payscheme_company", "fields": ["company_id"]},
        ],
    }


@db.model
class PayrollLineItem:
    """Editable line item during payroll generation (T342)."""

    payroll_run_id: int
    employee_id: int
    company_id: int
    pay_item_id: int = 0
    description: str = ""
    amount: float = 0.0
    unit_type: str = "fixed_amount"
    units: float = 0.0
    cpf_type: str = "ow"
    is_manual_override: bool = False

    __dataflow__ = {
        "indexes": [
            {"name": "idx_pli_payroll", "fields": ["payroll_run_id"]},
            {"name": "idx_pli_employee", "fields": ["employee_id"]},
        ],
    }


@db.model
class PayslipSettings:
    """Payslip display settings per company (T340)."""

    company_id: int
    show_employee_address: bool = False
    show_paid_days: bool = True
    show_leave_balance: bool = True
    show_payslip_id: bool = True
    combine_pay_items_by_type: bool = False
    password_protect_pdf: bool = False
    password_format: str = "nric_last4"  # nric_last4/custom
    enable_payslip_module: bool = True
    enable_payday_countdown: bool = False

    __dataflow__ = {
        "indexes": [
            {"name": "idx_paysettings_company", "fields": ["company_id"]},
        ],
    }


# ---------------------------------------------------------------------------
# M47: Claims Enhancements
# ---------------------------------------------------------------------------


@db.model
class ClaimGroup:
    """Group claims under a single submission (T350)."""

    employee_id: int
    company_id: int
    name: str = ""
    status: str = "draft"  # draft/submitted/approved/partially_approved/rejected
    total_amount: float = 0.0
    submitted_at: str = ""

    __dataflow__ = {
        "indexes": [
            {"name": "idx_claimgrp_employee", "fields": ["employee_id"]},
            {"name": "idx_claimgrp_company", "fields": ["company_id"]},
        ],
    }


# ---------------------------------------------------------------------------
# M48: Attendance Enhancements
# ---------------------------------------------------------------------------


@db.model
class LatenessSettings:
    """Lateness deduction configuration per company (T354)."""

    company_id: int
    enable_lateness_deduction: bool = False
    display_lateness: bool = True
    grace_period_minutes: int = 15
    deduction_brackets: str = ""  # JSON: [{from_min, to_min, amount}]

    __dataflow__ = {
        "indexes": [
            {"name": "idx_lateness_company", "fields": ["company_id"]},
        ],
    }


@db.model
class EarlyDepartureSettings:
    """Early departure deduction configuration per company (T354)."""

    company_id: int
    enable_early_departure_deduction: bool = False
    display_early_departure: bool = True
    grace_period_minutes: int = 0
    deduction_brackets: str = ""  # JSON

    __dataflow__ = {
        "indexes": [
            {"name": "idx_earlydep_company", "fields": ["company_id"]},
        ],
    }


# ---------------------------------------------------------------------------
# M49: Shift Enhancements
# ---------------------------------------------------------------------------


@db.model
class ShiftHourlyRate:
    """Shift hourly rate definition (T357)."""

    company_id: int
    name: str = ""
    branch_id: int = 0
    hourly_rate: float = 0.0
    overtime_amount: float = 0.0

    __dataflow__ = {
        "indexes": [
            {"name": "idx_shiftrate_company", "fields": ["company_id"]},
        ],
    }


@db.model
class ShiftMultiplier:
    """Shift pay multiplier (T357)."""

    company_id: int
    name: str = ""
    branch_id: int = 0
    multiplier_value: float = 1.0

    __dataflow__ = {
        "indexes": [
            {"name": "idx_shiftmult_company", "fields": ["company_id"]},
        ],
    }


# ---------------------------------------------------------------------------
# M50: Appraisal Module
# ---------------------------------------------------------------------------


@db.model
class AppraisalTemplate:
    """Appraisal template with sections and questions (T359)."""

    company_id: int
    name: str = ""
    sections: str = ""  # JSON: [{title, weight, questions: [{text, type, filled_by, options}]}]
    enable_weightage: bool = True
    require_employee_signoff: bool = True
    is_archived: bool = False

    __dataflow__ = {
        "indexes": [
            {"name": "idx_apptpl_company", "fields": ["company_id"]},
        ],
    }


@db.model
class AppraisalPeriod:
    """Appraisal period for batch reviews (T359)."""

    company_id: int
    template_id: int
    name: str = ""
    start_date: str = ""
    end_date: str = ""
    status: str = "draft"  # draft/active/closed

    __dataflow__ = {
        "indexes": [
            {"name": "idx_appperiod_company", "fields": ["company_id"]},
        ],
    }


@db.model
class Appraisal:
    """Individual employee appraisal (T359)."""

    period_id: int = 0
    employee_id: int
    reviewer_id: int = 0
    template_id: int
    company_id: int
    status: str = "pending"  # pending/in_progress/submitted/signed_off
    responses: str = ""  # JSON
    scores: str = ""  # JSON
    overall_score: float = 0.0
    reviewer_comments: str = ""
    employee_comments: str = ""
    submitted_at: str = ""
    signed_off_at: str = ""

    __dataflow__ = {
        "indexes": [
            {"name": "idx_appraisal_employee", "fields": ["employee_id"]},
            {"name": "idx_appraisal_period", "fields": ["period_id"]},
            {"name": "idx_appraisal_company", "fields": ["company_id"]},
        ],
    }


# ---------------------------------------------------------------------------
# M51: Org Structure
# ---------------------------------------------------------------------------


@db.model
class Organization:
    """Sub-organization within a company (T361)."""

    company_id: int
    parent_org_id: int = 0
    name: str = ""
    code: str = ""

    __dataflow__ = {
        "indexes": [
            {"name": "idx_org_company", "fields": ["company_id"]},
        ],
    }


@db.model
class Branch:
    """Physical branch location (T361)."""

    company_id: int
    name: str = ""
    address: str = ""
    postal_code: str = ""
    geofence_radius_meters: int = 100
    latitude: float = 0.0
    longitude: float = 0.0
    is_archived: bool = False

    __dataflow__ = {
        "indexes": [
            {"name": "idx_branch_company", "fields": ["company_id"]},
        ],
    }


@db.model
class ApprovalGroup:
    """Approval routing configuration (T362)."""

    company_id: int
    name: str = ""
    approval_type: str = "no_rules"  # no_rules/one_tier/two_tier
    rules: str = ""  # JSON

    __dataflow__ = {
        "indexes": [
            {"name": "idx_approvalgrp_company", "fields": ["company_id"]},
        ],
    }


@db.model
class AdminPermission:
    """Granular admin permissions (T363)."""

    user_id: int
    company_id: int
    permissions: str = ""  # JSON with module-level booleans

    __dataflow__ = {
        "indexes": [
            {"name": "idx_adminperm_user", "fields": ["user_id"]},
            {"name": "idx_adminperm_company", "fields": ["company_id"]},
        ],
    }


@db.model
class HolidayGroup:
    """Holiday calendar group (T364)."""

    company_id: int
    name: str = ""
    holidays: str = ""  # JSON array of {date, name, is_gazetted}

    __dataflow__ = {
        "indexes": [
            {"name": "idx_holidaygrp_company", "fields": ["company_id"]},
        ],
    }


@db.model
class CostCentre:
    """Cost centre for expense tracking (T370)."""

    company_id: int
    name: str = ""
    code: str = ""
    is_active: bool = True

    __dataflow__ = {
        "indexes": [
            {"name": "idx_costcentre_company", "fields": ["company_id"]},
        ],
    }


# ---------------------------------------------------------------------------
# M56: Project Costing
# ---------------------------------------------------------------------------


@db.model
class Project:
    """Project for cost tracking (T386)."""

    company_id: int
    name: str = ""
    description: str = ""
    start_date: str = ""
    end_date: str = ""
    branch_id: int = 0
    auto_assign_new_employees: bool = False
    budget_amount: float = 0.0
    is_archived: bool = False

    __dataflow__ = {
        "indexes": [
            {"name": "idx_project_company", "fields": ["company_id"]},
        ],
    }


@db.model
class ProjectAssignment:
    """Employee assignment to project (T386)."""

    project_id: int
    employee_id: int
    company_id: int
    assignment_type: str = "timesheet"  # timesheet/attendance/allocation
    role_id: int = 0
    is_active: bool = True

    __dataflow__ = {
        "indexes": [
            {"name": "idx_projassign_project", "fields": ["project_id"]},
            {"name": "idx_projassign_employee", "fields": ["employee_id"]},
        ],
    }


@db.model
class ProjectRole:
    """Role with hourly rate for project costing (T386)."""

    company_id: int
    name: str = ""
    hourly_rate: float = 0.0
    remarks: str = ""
    is_archived: bool = False

    __dataflow__ = {
        "indexes": [
            {"name": "idx_projrole_company", "fields": ["company_id"]},
        ],
    }


@db.model
class ProjectOverhead:
    """Overhead cost for a project (T386)."""

    project_id: int
    company_id: int
    overhead_type: str = "project_based"  # project_based/employee_based
    name: str = ""
    description: str = ""
    months: str = ""  # JSON array
    amount_per_month: float = 0.0
    remarks: str = ""

    __dataflow__ = {
        "indexes": [
            {"name": "idx_projoverhead_project", "fields": ["project_id"]},
        ],
    }


@db.model
class TimesheetEntry:
    """Timesheet entry for project costing (T387)."""

    employee_id: int
    company_id: int
    project_id: int
    entry_date: str = ""
    hours: float = 0.0
    minutes: int = 0
    description: str = ""
    task: str = ""
    rate_type: str = "normal"  # normal/overtime/holiday
    billable: bool = True
    notes: str = ""
    status: str = "draft"  # draft/submitted/approved/rejected
    approved_by: int = 0
    rejection_reason: str = ""
    created_by: int = 0
    created_by_type: str = "employee"  # admin/manager/employee

    __dataflow__ = {
        "indexes": [
            {"name": "idx_timesheet_employee", "fields": ["employee_id"]},
            {"name": "idx_timesheet_project", "fields": ["project_id"]},
            {"name": "idx_timesheet_date", "fields": ["entry_date"]},
            {"name": "idx_timesheet_status", "fields": ["status"]},
        ],
    }


@db.model
class ProjectAllocation:
    """Salary allocation to projects (T388)."""

    employee_id: int
    company_id: int
    month: str = ""  # YYYY-MM
    allocation_type: str = "percentage"  # percentage/nominal/equal
    base_amount_type: str = "salary"  # salary/custom
    custom_base_amount: float = 0.0
    allocations: str = ""  # JSON: [{project_id, percentage_or_amount}]
    remarks: str = ""

    __dataflow__ = {
        "indexes": [
            {"name": "idx_projalloc_employee", "fields": ["employee_id"]},
            {"name": "idx_projalloc_month", "fields": ["month"]},
        ],
    }


# ---------------------------------------------------------------------------
# M57: Inventory
# ---------------------------------------------------------------------------


@db.model
class InventoryLocation:
    """Storage location for inventory items (T390)."""

    company_id: int
    name: str = ""
    organization_scope: str = "all"  # all/specific
    organization_id: int = 0

    __dataflow__ = {
        "indexes": [
            {"name": "idx_invloc_company", "fields": ["company_id"]},
        ],
    }


@db.model
class InventoryCategory:
    """Inventory category within a location (T390)."""

    company_id: int
    name: str = ""
    location_id: int
    tracking_mode: str = "quantity"  # quantity/individual
    permitted_issuers: str = ""  # JSON
    permitted_requesters: str = ""  # JSON
    require_acknowledgment: bool = True

    __dataflow__ = {
        "indexes": [
            {"name": "idx_invcat_company", "fields": ["company_id"]},
            {"name": "idx_invcat_location", "fields": ["location_id"]},
        ],
    }


@db.model
class InventoryItem:
    """Individual inventory item or quantity-based stock (T390)."""

    category_id: int
    company_id: int
    location_id: int
    name: str = ""
    quantity: int = 0
    serial_number: str = ""
    purchase_date: str = ""
    purchase_price: float = 0.0
    warranty_expiry: str = ""
    condition: str = "new"  # new/good/fair/damaged/disposed
    status: str = "available"  # available/reserved/issued/pending_acknowledgment/returned/disposed
    assigned_to_employee_id: int = 0
    assigned_at: str = ""
    notes: str = ""
    photo_url: str = ""

    __dataflow__ = {
        "indexes": [
            {"name": "idx_invitem_category", "fields": ["category_id"]},
            {"name": "idx_invitem_company", "fields": ["company_id"]},
            {"name": "idx_invitem_assigned", "fields": ["assigned_to_employee_id"]},
        ],
    }


@db.model
class InventoryMovement:
    """Audit trail for inventory movements (T391)."""

    item_id: int
    company_id: int
    action: str = ""  # created/reserved/issued/acknowledged/returned/disposed/transferred
    from_employee_id: int = 0
    to_employee_id: int = 0
    performed_by: int = 0
    notes: str = ""
    movement_date: str = ""

    __dataflow__ = {
        "indexes": [
            {"name": "idx_invmove_item", "fields": ["item_id"]},
            {"name": "idx_invmove_company", "fields": ["company_id"]},
        ],
    }


@db.model
class InventoryRequest:
    """Employee request for inventory item (T391)."""

    employee_id: int
    company_id: int
    category_id: int
    item_id: int = 0
    reason: str = ""
    status: str = "pending"  # pending/approved/denied
    approved_by: int = 0
    denial_reason: str = ""
    requested_at: str = ""

    __dataflow__ = {
        "indexes": [
            {"name": "idx_invreq_employee", "fields": ["employee_id"]},
            {"name": "idx_invreq_company", "fields": ["company_id"]},
        ],
    }


# ---------------------------------------------------------------------------
# M58: ATS (Applicant Tracking System)
# ---------------------------------------------------------------------------


@db.model
class JobListing:
    """Job listing for recruitment (T393)."""

    company_id: int
    organization_id: int = 0
    department: str = ""
    position_title: str = ""
    employment_type: str = "full_time"  # full_time/part_time/contract/internship
    location: str = ""
    description: str = ""
    requirements: str = ""
    salary_range_min: float = 0.0
    salary_range_max: float = 0.0
    is_published: bool = False
    unique_slug: str = ""
    application_form_config: str = ""  # JSON
    created_by: int = 0
    published_at: str = ""
    closed_at: str = ""

    __dataflow__ = {
        "indexes": [
            {"name": "idx_joblisting_company", "fields": ["company_id"]},
            {"name": "idx_joblisting_slug", "fields": ["unique_slug"]},
        ],
    }


@db.model
class Candidate:
    """Job candidate/applicant (T393)."""

    company_id: int
    job_listing_id: int
    name: str = ""
    email: str = ""
    phone: str = ""
    nric_fin: str = ""  # encrypted
    gender: str = ""
    date_of_birth: str = ""
    race: str = ""
    nationality: str = ""
    citizenship_status: str = ""
    address: str = ""
    resume_url: str = ""
    cover_letter_url: str = ""
    application_data: str = ""  # JSON
    source: str = "direct"  # direct/linkedin/indeed/jobstreet/referral/other
    stage: str = "new"  # new/screening/shortlisted/interview/offered/hired/rejected/withdrawn
    overall_score: float = 0.0
    rejection_reason: str = ""
    pdpa_consent: bool = False
    pdpa_consent_date: str = ""
    notes: str = ""

    __dataflow__ = {
        "indexes": [
            {"name": "idx_candidate_company", "fields": ["company_id"]},
            {"name": "idx_candidate_job", "fields": ["job_listing_id"]},
            {"name": "idx_candidate_stage", "fields": ["stage"]},
        ],
    }


@db.model
class InterviewSchedule:
    """Interview schedule for a candidate (T393)."""

    candidate_id: int
    company_id: int
    interview_type: str = "in_person"  # phone/video/in_person/panel
    scheduled_at: str = ""
    duration_minutes: int = 60
    location_or_link: str = ""
    interviewer_ids: str = ""  # JSON array
    status: str = "scheduled"  # scheduled/completed/cancelled/no_show
    notes: str = ""

    __dataflow__ = {
        "indexes": [
            {"name": "idx_interview_candidate", "fields": ["candidate_id"]},
            {"name": "idx_interview_company", "fields": ["company_id"]},
        ],
    }


@db.model
class InterviewFeedback:
    """Interviewer feedback for a candidate (T393)."""

    interview_id: int
    interviewer_id: int
    company_id: int
    candidate_id: int
    scores: str = ""  # JSON: {criteria: score}
    overall_rating: float = 0.0
    recommendation: str = ""  # strong_hire/hire/neutral/no_hire/strong_no_hire
    strengths: str = ""
    weaknesses: str = ""
    notes: str = ""

    __dataflow__ = {
        "indexes": [
            {"name": "idx_feedback_interview", "fields": ["interview_id"]},
            {"name": "idx_feedback_candidate", "fields": ["candidate_id"]},
        ],
    }


# ---------------------------------------------------------------------------
# BYOK / LLM Configuration Models (T405-T406)
# ---------------------------------------------------------------------------


class LLMConfigStatus:
    ACTIVE = "active"
    INVALID = "invalid"
    REVOKED = "revoked"


class LLMProvider:
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"
    MISTRAL = "mistral"
    OLLAMA = "ollama"
    CUSTOM = "custom"


@db.model
class CompanyLLMConfig:
    """Company-level LLM provider configuration (BYOK / Ollama).

    Stores an encrypted API key, model preference, and optional base URL
    for companies that bring their own key or run a local Ollama instance.
    """

    company_id: int
    provider: str = LLMProvider.OPENAI
    encrypted_key: Optional[str] = None
    model_pref: Optional[str] = None
    base_url: Optional[str] = None
    status: str = LLMConfigStatus.ACTIVE
    updated_by: Optional[int] = None
    is_active: bool = True

    __dataflow__ = {
        "indexes": [
            {"name": "idx_companyllm_company", "fields": ["company_id"]},
            {"name": "idx_companyllm_provider", "fields": ["provider"]},
            {"name": "idx_companyllm_active", "fields": ["is_active"]},
        ],
    }


@db.model
class CompanyLLMUsage:
    """Per-company monthly LLM usage tracking for budget enforcement.

    One record per company per month. Accumulates token counts and
    estimated cost throughout the billing period.
    """

    company_id: int
    month: str = ""  # YYYY-MM-01 format
    query_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: float = 0.0  # USD

    __dataflow__ = {
        "indexes": [
            {"name": "idx_llmusage_company", "fields": ["company_id"]},
            {"name": "idx_llmusage_month", "fields": ["month"]},
            {"name": "idx_llmusage_company_month", "fields": ["company_id", "month"]},
        ],
    }


@db.model
class UserLLMConfig:
    """Per-user LLM provider configuration (optional personal key override).

    Allows individual users to override their company's LLM config with
    a personal API key.  User config takes priority over company config.
    """

    user_id: int
    company_id: int
    provider: str = LLMProvider.OPENAI
    encrypted_key: Optional[str] = None
    model_pref: Optional[str] = None
    base_url: Optional[str] = None
    status: str = LLMConfigStatus.ACTIVE
    is_active: bool = True

    __dataflow__ = {
        "indexes": [
            {"name": "idx_userllm_user", "fields": ["user_id"]},
            {"name": "idx_userllm_company", "fields": ["company_id"]},
            {"name": "idx_userllm_active", "fields": ["is_active"]},
        ],
    }


# ---------------------------------------------------------------------------
# Production persistence models (replacing in-memory stores)
# ---------------------------------------------------------------------------


@db.model
class ConversationThread:
    """Persistent advisory conversation thread."""

    user_id: int
    company_id: int
    session_id: str = ""
    subject: str = ""
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    turn_count: int = 0
    is_active: bool = True

    __dataflow__ = {
        "indexes": [
            {"name": "idx_convthread_user", "fields": ["user_id"]},
            {"name": "idx_convthread_session", "fields": ["session_id"]},
            {"name": "idx_convthread_company", "fields": ["company_id"]},
        ],
    }


@db.model
class ConversationMessage:
    """Individual message within a conversation thread."""

    thread_id: int
    sender: str = "user"  # "user" or "agent"
    text: str = ""
    entities: str = ""  # JSON
    domains: str = ""  # JSON list
    risk_tier: str = "green"
    confidence_score: Optional[float] = None
    provisions_cited: str = ""  # JSON list
    timestamp: Optional[datetime] = None

    __dataflow__ = {
        "indexes": [
            {"name": "idx_convmsg_thread", "fields": ["thread_id"]},
            {"name": "idx_convmsg_timestamp", "fields": ["timestamp"]},
        ],
    }


@db.model
class TrustLineageRecord:
    """Persistent trust chain record for advisory sessions."""

    session_id: str = ""
    company_id: int = 0
    user_id: int = 0
    genesis_fingerprint: str = ""
    user_verification_level: str = "standard"
    company_completeness: float = 0.0
    kb_currency_status: str = ""  # JSON
    attestations: str = ""  # JSON list of agent attestations
    attestation_count: int = 0
    verification_depth: str = "green"
    human_review_required: bool = False
    human_review_completed: bool = False
    human_reviewer: Optional[str] = None
    created_at: Optional[datetime] = None

    __dataflow__ = {
        "indexes": [
            {"name": "idx_trustlineage_session", "fields": ["session_id"]},
            {"name": "idx_trustlineage_company", "fields": ["company_id"]},
            {"name": "idx_trustlineage_created", "fields": ["created_at"]},
        ],
    }


@db.model
class FlaggedQueryRecord:
    """Persistent record of flagged advisory queries for compliance review."""

    query_hash: str = ""
    user_id: Optional[int] = None
    company_id: int = 0
    query_text: str = ""
    screening_result: str = ""  # ScreeningResult value
    reason: str = ""
    matched_patterns: str = ""  # JSON list
    reviewed: bool = False
    reviewer_notes: str = ""
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    flagged_at: Optional[datetime] = None

    __dataflow__ = {
        "indexes": [
            {"name": "idx_flaggedquery_hash", "fields": ["query_hash"]},
            {"name": "idx_flaggedquery_reviewed", "fields": ["reviewed"]},
            {"name": "idx_flaggedquery_company", "fields": ["company_id"]},
            {"name": "idx_flaggedquery_flagged", "fields": ["flagged_at"]},
        ],
    }


@db.model
class UserObservation:
    """Shadow agent observation of user behavior."""

    user_id: int
    company_id: int = 0
    session_id: str = ""
    page: str = ""
    action_type: str = ""  # "page_visit", "click", "form_submit", etc.
    details: str = ""  # JSON
    timestamp: Optional[datetime] = None

    __dataflow__ = {
        "indexes": [
            {"name": "idx_obs_user", "fields": ["user_id"]},
            {"name": "idx_obs_session", "fields": ["session_id"]},
            {"name": "idx_obs_timestamp", "fields": ["timestamp"]},
        ],
    }


@db.model
class UserMemory:
    """Distilled shadow agent memory per user (themes, patterns, preferences)."""

    user_id: int
    company_id: int = 0
    themes: str = ""  # JSON list
    patterns: str = ""  # JSON list
    preferences: str = ""  # JSON dict
    observation_count: int = 0
    last_distilled: Optional[datetime] = None

    __dataflow__ = {
        "indexes": [
            {"name": "idx_usermem_user", "fields": ["user_id"]},
            {"name": "idx_usermem_company", "fields": ["company_id"]},
        ],
    }


@db.model
class ActionHistoryRecord:
    """Shadow agent action execution history."""

    user_id: int
    company_id: int = 0
    session_id: str = ""
    module: str = ""
    action: str = ""
    parameters: str = ""  # JSON
    success: bool = True
    error_message: str = ""
    timestamp: Optional[datetime] = None

    __dataflow__ = {
        "indexes": [
            {"name": "idx_actionhist_user", "fields": ["user_id"]},
            {"name": "idx_actionhist_module", "fields": ["module"]},
            {"name": "idx_actionhist_timestamp", "fields": ["timestamp"]},
        ],
    }


# ---------------------------------------------------------------------------
# Onboarding models
# ---------------------------------------------------------------------------


@db.model
class OnboardingTemplate:
    """Reusable onboarding configuration for a company."""

    company_id: int = 0
    name: str = ""
    description: str = ""
    is_default: bool = False
    version: int = 1
    is_active: bool = True
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    __dataflow__ = {
        "indexes": [
            {"name": "idx_onbtemplate_company", "fields": ["company_id"]},
            {"name": "idx_onbtemplate_default", "fields": ["is_default"]},
        ],
    }


@db.model
class OnboardingModule:
    """A group of related onboarding steps within a template."""

    template_id: int = 0
    company_id: int = 0
    name: str = ""
    description: str = ""
    phase: str = "custom"  # orientation, compliance, benefits, probation, custom
    order: int = 0
    estimated_duration_minutes: int = 0
    is_mandatory: bool = True
    is_role_specific: bool = False
    role_filter: str = ""  # JSON array of designations/departments, empty = all roles

    __dataflow__ = {
        "indexes": [
            {"name": "idx_onbmodule_template", "fields": ["template_id"]},
            {"name": "idx_onbmodule_company", "fields": ["company_id"]},
            {"name": "idx_onbmodule_order", "fields": ["order"]},
        ],
    }


@db.model
class OnboardingStep:
    """A single action or content item within an onboarding module."""

    module_id: int = 0
    title: str = ""
    description: str = ""
    order: int = 0
    step_type: str = "content"  # content, checklist, document_upload, policy_acknowledgment, form, approval
    body_content: str = ""  # markdown/HTML content for content steps
    checklist_items: str = ""  # JSON array of checklist items
    media_url: str = ""
    requires_completion: bool = True
    policy_id: Optional[int] = None  # FK to CompanyPolicy for acknowledgment steps
    requires_previous_completion: bool = False  # sequential enforcement

    __dataflow__ = {
        "indexes": [
            {"name": "idx_onbstep_module", "fields": ["module_id"]},
            {"name": "idx_onbstep_order", "fields": ["order"]},
        ],
    }


@db.model
class OnboardingAssignment:
    """Tracks an employee's assignment to an onboarding template."""

    employee_id: int = 0
    template_id: int = 0
    template_version: int = 1  # snapshot at assignment time
    company_id: int = 0
    assigned_by: Optional[int] = None
    assigned_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    status: str = "in_progress"  # in_progress, completed, overdue
    completed_at: Optional[datetime] = None
    completion_percentage: float = 0.0

    __dataflow__ = {
        "indexes": [
            {"name": "idx_onbassign_employee", "fields": ["employee_id"]},
            {"name": "idx_onbassign_company", "fields": ["company_id"]},
            {"name": "idx_onbassign_status", "fields": ["status"]},
            {"name": "idx_onbassign_template", "fields": ["template_id"]},
        ],
    }


@db.model
class OnboardingStepProgress:
    """Tracks an employee's progress on a specific onboarding step."""

    assignment_id: int = 0
    step_id: int = 0
    employee_id: int = 0
    status: str = "pending"  # pending, in_progress, completed, skipped
    completed_at: Optional[datetime] = None
    completed_by: Optional[int] = None  # for approval steps (manager/HR)
    document_url: str = ""  # for document_upload steps
    form_data: str = ""  # JSON for form steps
    notes: str = ""
    acknowledged_at: Optional[datetime] = None  # for policy acknowledgment steps

    __dataflow__ = {
        "indexes": [
            {"name": "idx_onbprog_assignment", "fields": ["assignment_id"]},
            {"name": "idx_onbprog_step", "fields": ["step_id"]},
            {"name": "idx_onbprog_employee", "fields": ["employee_id"]},
            {"name": "idx_onbprog_status", "fields": ["status"]},
        ],
    }


@db.model
class PreboardingTaskInstance:
    """Tracks a specific pre-boarding task for an incoming employee."""

    company_id: int = 0
    template_id: int = 0
    employee_id: int = 0
    task_name: str = ""
    owner_role: str = "hr"  # hr, manager, it, office_manager
    trigger: str = ""  # e.g. "offer_accepted", "7_days_before_start"
    deadline_date: Optional[datetime] = None  # absolute, calculated from start_date
    status: str = "pending"  # pending, done
    completed_at: Optional[datetime] = None
    completed_by: Optional[int] = None
    notes: str = ""

    __dataflow__ = {
        "indexes": [
            {"name": "idx_preboard_company", "fields": ["company_id"]},
            {"name": "idx_preboard_employee", "fields": ["employee_id"]},
            {"name": "idx_preboard_status", "fields": ["status"]},
        ],
    }
