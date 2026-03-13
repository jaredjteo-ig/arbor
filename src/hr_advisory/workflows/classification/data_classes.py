"""Data classes for Employee Classification Engine input and output."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EmployeeClassificationInput:
    """Input parameters for employee classification.

    Attributes:
        monthly_basic_salary: Monthly basic salary in SGD.
        citizenship_status: "SC" (Singapore Citizen), "PR" (Permanent Resident),
            or "foreigner".
        employment_type: "full_time", "part_time", or "contract".
        sector: e.g. "services", "manufacturing", "construction",
            "marine_shipyard", "process".
        age: Employee age in years.
        is_workman: Whether the employee performs manual labor.
        is_manager_executive: Whether the employee is classified as a
            manager or executive.
        pr_year: PR year (1, 2, or 3+) if citizenship_status is "PR".
        pass_type: Work pass type ("ep", "sp", "wp") if foreigner.
        job_role_description: Optional free-text description.
        is_domestic_worker: True if employee is a domestic worker.
        is_seafarer: True if employee is a seafarer.
        is_government: True if employee is a government/statutory board employee.
    """

    monthly_basic_salary: float
    citizenship_status: str  # "SC", "PR", "foreigner"
    employment_type: str  # "full_time", "part_time", "contract"
    sector: str  # e.g., "services", "manufacturing", "construction"
    age: int = 30
    is_workman: bool = False
    is_manager_executive: bool = False
    pr_year: int | None = None
    pass_type: str | None = None
    job_role_description: str = ""
    is_domestic_worker: bool = False
    is_seafarer: bool = False
    is_government: bool = False


@dataclass
class EmployeeClassificationResult:
    """Output of the employee classification workflow.

    Attributes:
        ea_covered: Whether the Employment Act covers this employee.
        ea_exclusion_reason: Reason for EA exclusion, if any.
        part_iv_applicable: Whether EA Part IV (rest days, hours, overtime) applies.
        part_iv_reason: Explanation for Part IV determination.
        cpf_applicable: Whether CPF contributions apply.
        cpf_tier: CPF tier string (sc_full, pr_year1, pr_year2, pr_year3_plus, none).
        cpf_age_band: CPF age band (55_below, 55_60, 60_65, 65_70, above_70).
        pass_valid: Whether the work pass type is valid for the given salary.
        pass_validation_message: Details of pass validation.
        applicable_leave_types: List of applicable statutory leave types.
        classification_summary: Human-readable summary of the classification.
        warnings: List of warning messages.
    """

    ea_covered: bool
    ea_exclusion_reason: str | None = None
    part_iv_applicable: bool = False
    part_iv_reason: str = ""
    cpf_applicable: bool = False
    cpf_tier: str = ""
    cpf_age_band: str = ""
    pass_valid: bool = True
    pass_validation_message: str = ""
    applicable_leave_types: list[str] = field(default_factory=list)
    classification_summary: str = ""
    warnings: list[str] = field(default_factory=list)
