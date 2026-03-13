"""Deterministic calculator workflows for Singapore HR computations.

All calculators are pure functions with frozen dataclass I/O.
No LLM calls — deterministic, auditable, testable.
"""

from hr_advisory.workflows.calculators.cpf_calculator import (
    calculate_cpf_contributions,
    CPF_RATE_TABLE,
)
from hr_advisory.workflows.calculators.quota_levy_calculator import (
    calculate_quota_levy,
    SECTOR_DRC,
)
from hr_advisory.workflows.calculators.leave_calculator import (
    calculate_leave_entitlement,
    LEAVE_CALCULATORS,
)
from hr_advisory.workflows.calculators.notice_period_calculator import (
    calculate_notice_period,
)
from hr_advisory.workflows.calculators.overtime_calculator import (
    calculate_overtime,
)
from hr_advisory.workflows.calculators.retrenchment_calculator import (
    calculate_retrenchment,
)
from hr_advisory.workflows.calculators.cost_to_company_calculator import (
    calculate_cost_to_company,
)

__all__ = [
    "calculate_cpf_contributions",
    "CPF_RATE_TABLE",
    "calculate_quota_levy",
    "SECTOR_DRC",
    "calculate_leave_entitlement",
    "LEAVE_CALCULATORS",
    "calculate_notice_period",
    "calculate_overtime",
    "calculate_retrenchment",
    "calculate_cost_to_company",
]
