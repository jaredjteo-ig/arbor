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

    # Address (structured — exceeds Payboy)
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
    with versioning via effective_date.
    """

    company_id: int
    policy_type: str
    title: str = ""
    content: str = ""
    effective_date: str = ""
    is_active: bool = True

    __dataflow__ = {
        "indexes": [
            {"name": "idx_policy_company", "fields": ["company_id"]},
            {"name": "idx_policy_type", "fields": ["policy_type"]},
            {"name": "idx_policy_active", "fields": ["is_active"]},
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
