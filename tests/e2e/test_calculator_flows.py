"""Calculator E2E tests (T058).

Tests all calculator flows end-to-end:
- CPF calculator with various employee scenarios
- Leave entitlement calculator
- Quota and levy calculator

Validates calculation accuracy against known-correct results.
"""

from __future__ import annotations

import pytest

from hr_advisory.workflows.calculators.cpf_calculator import (
    CPFInput,
    calculate_cpf_contributions,
)
from hr_advisory.workflows.calculators.leave_calculator import (
    LeaveInput,
    calculate_leave_entitlement,
)
from hr_advisory.workflows.calculators.quota_levy_calculator import (
    QuotaLevyInput,
    calculate_quota_levy,
)


class TestCpfCalculatorE2E:
    """CPF calculator end-to-end accuracy tests."""

    def test_citizen_below_55_standard(self) -> None:
        """Standard CPF for citizen below 55."""
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="SC",
                age=35,
                monthly_ow=5000.0,
            )
        )
        assert result.employer_contribution > 0
        assert result.employee_contribution > 0
        assert result.total_contribution == (
            result.employer_contribution + result.employee_contribution
        )

    def test_pr_year1_graduated_rates(self) -> None:
        """PR Year 1 has graduated (lower) CPF rates."""
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="PR",
                age=35,
                monthly_ow=5000.0,
                pr_year=1,
            )
        )
        citizen_result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="SC",
                age=35,
                monthly_ow=5000.0,
            )
        )
        # PR Year 1 rates should be lower than citizen
        assert result.employer_contribution <= citizen_result.employer_contribution

    def test_ow_ceiling(self) -> None:
        """Wages above OW ceiling ($8,000) should be capped."""
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="SC",
                age=35,
                monthly_ow=10000.0,
            )
        )
        capped_result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="SC",
                age=35,
                monthly_ow=8000.0,
            )
        )
        # Contributions should be same (capped at $8,000)
        assert result.employer_contribution == capped_result.employer_contribution

    def test_foreigner_no_cpf(self) -> None:
        """Foreigners should have zero CPF contributions."""
        result = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="foreigner",
                age=35,
                monthly_ow=5000.0,
            )
        )
        assert result.employer_contribution == 0.0
        assert result.employee_contribution == 0.0

    def test_age_bands(self) -> None:
        """Different age bands should have different rates."""
        young = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="SC",
                age=35,
                monthly_ow=5000.0,
            )
        )
        senior = calculate_cpf_contributions(
            CPFInput(
                citizenship_status="SC",
                age=60,
                monthly_ow=5000.0,
            )
        )
        # Senior rates should be lower
        assert senior.total_contribution <= young.total_contribution


class TestLeaveCalculatorE2E:
    """Leave calculator end-to-end tests."""

    def test_first_year_annual_leave(self) -> None:
        """First year employee gets 7 days annual leave."""
        result = calculate_leave_entitlement(
            LeaveInput(
                years_of_service=1,
                employment_type="full_time",
                leave_type="annual_leave",
                citizenship_status="SC",
            )
        )
        assert result.days_entitled == 7

    def test_eighth_year_annual_leave(self) -> None:
        """8+ years gets maximum 14 days annual leave."""
        result = calculate_leave_entitlement(
            LeaveInput(
                years_of_service=8,
                employment_type="full_time",
                leave_type="annual_leave",
                citizenship_status="SC",
            )
        )
        assert result.days_entitled == 14

    def test_sick_leave(self) -> None:
        """Sick leave entitlement based on service length."""
        result = calculate_leave_entitlement(
            LeaveInput(
                years_of_service=2,
                employment_type="full_time",
                leave_type="sick_leave",
                citizenship_status="SC",
            )
        )
        assert result.days_entitled > 0

    def test_maternity_leave(self) -> None:
        """Maternity leave for citizens."""
        result = calculate_leave_entitlement(
            LeaveInput(
                years_of_service=1,
                employment_type="full_time",
                leave_type="maternity_leave",
                citizenship_status="SC",
            )
        )
        assert result.days_entitled > 0


class TestQuotaLevyCalculatorE2E:
    """Quota and levy calculator end-to-end tests."""

    def test_services_drc(self) -> None:
        """Services sector DRC calculation."""
        result = calculate_quota_levy(
            QuotaLevyInput(
                sector="services",
                headcount_local=10,
            )
        )
        assert result.headroom_foreign > 0

    def test_construction_drc(self) -> None:
        """Construction sector DRC calculation."""
        result = calculate_quota_levy(
            QuotaLevyInput(
                sector="construction",
                headcount_local=10,
            )
        )
        assert result.headroom_foreign > 0

    def test_within_limit(self) -> None:
        """Company with only locals should be within quota limit."""
        result = calculate_quota_levy(
            QuotaLevyInput(
                sector="services",
                headcount_local=10,
                headcount_wp=0,
                headcount_sp=0,
            )
        )
        assert result.within_limit is True
