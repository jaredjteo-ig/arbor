"""CalculatorAgent -- deterministic HR calculation dispatcher.

This is a thin wrapper that dispatches to deterministic calculator
functions.  There is NO LLM involvement -- all calculations are
purely arithmetic.

Supported calculators:
  - cpf:        CPF contribution calculation by age band and wage
  - leave:      Annual/sick/maternity leave entitlement calculation
  - salary:     Salary proration, overtime, and deduction calculation
  - quota_levy: Foreign worker quota and levy calculation
"""

import logging
from typing import Any, Dict, Optional

from hr_advisory.workflows.calculators.quota_levy_calculator import (
    QuotaLevyInput,
    calculate_quota_levy,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CPF rate tables (simplified -- production would load from KB)
# ---------------------------------------------------------------------------

# Rates for Singapore Citizens, wages > $750/month
_CPF_RATES_SC = {
    "55_and_below": {"employer": 0.17, "employee": 0.20},
    "above_55_to_60": {"employer": 0.15, "employee": 0.16},
    "above_60_to_65": {"employer": 0.115, "employee": 0.105},
    "above_65_to_70": {"employer": 0.09, "employee": 0.075},
    "above_70": {"employer": 0.075, "employee": 0.05},
}

_OW_CEILING = 8000  # Monthly OW ceiling (2026)
_AW_CEILING = 102000  # Annual AW ceiling (2024)


# ---------------------------------------------------------------------------
# Leave entitlement tables
# ---------------------------------------------------------------------------


def _annual_leave_days(years_of_service: int) -> int:
    """EA minimum annual leave: 7 days in year 1, +1 per year, max 14."""
    if years_of_service < 1:
        return 0
    return min(7 + (years_of_service - 1), 14)


def _sick_leave_days(years_of_service: int) -> Dict[str, int]:
    """EA minimum sick leave entitlement by service months."""
    if years_of_service < 1:
        # Pro-rated based on months of service in first year
        months = max(1, int(years_of_service * 12))
        table = {3: 5, 4: 8, 5: 11, 6: 14}
        outpatient = 14
        hospitalisation = 60
        for threshold, days in sorted(table.items()):
            if months <= threshold:
                outpatient = days
                hospitalisation = days * 4
                break
        return {"outpatient": outpatient, "hospitalisation": hospitalisation}
    return {"outpatient": 14, "hospitalisation": 60}


# ---------------------------------------------------------------------------
# Calculator dispatch
# ---------------------------------------------------------------------------


class CalculatorAgent:
    """Deterministic calculator dispatcher.

    No LLM, no BaseAgent -- purely arithmetic.  Instantiated like an
    agent for API consistency but executes synchronous calculations.
    """

    domain = "calculator"
    domain_label = "Calculator"
    agent_id = "calculator"

    # Available calculator types
    CALCULATOR_TYPES = frozenset(["cpf", "leave", "salary", "quota_levy"])

    def calculate(
        self,
        calculator_type: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Dispatch to the appropriate deterministic calculator.

        Args:
            calculator_type: One of "cpf", "leave", "salary".
            params: Calculator-specific input parameters.

        Returns:
            Dict with keys: calculator_type, result, breakdown.

        Raises:
            ValueError: If calculator_type is not supported.
        """
        if calculator_type not in self.CALCULATOR_TYPES:
            raise ValueError(
                f"Unknown calculator_type '{calculator_type}'. "
                f"Supported: {sorted(self.CALCULATOR_TYPES)}"
            )

        dispatch = {
            "cpf": self._calculate_cpf,
            "leave": self._calculate_leave,
            "salary": self._calculate_salary,
            "quota_levy": self._calculate_quota_levy,
        }

        result = dispatch[calculator_type](params)
        return {
            "calculator_type": calculator_type,
            **result,
        }

    # ------------------------------------------------------------------
    # CPF calculator
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_cpf(params: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate CPF contributions.

        Params:
            monthly_wage: float -- gross monthly ordinary wages
            age_band: str -- one of the _CPF_RATES_SC keys
            bonus: float (optional) -- additional wages
        """
        wage = float(params.get("monthly_wage", 0))
        age_band = params.get("age_band", "55_and_below")
        bonus = float(params.get("bonus", 0))

        rates = _CPF_RATES_SC.get(age_band, _CPF_RATES_SC["55_and_below"])

        # Apply OW ceiling
        capped_wage = min(wage, _OW_CEILING)

        employer_ow = round(capped_wage * rates["employer"], 2)
        employee_ow = round(capped_wage * rates["employee"], 2)

        # Additional wages (bonus)
        employer_aw = round(bonus * rates["employer"], 2) if bonus else 0
        employee_aw = round(bonus * rates["employee"], 2) if bonus else 0

        total_employer = employer_ow + employer_aw
        total_employee = employee_ow + employee_aw

        return {
            "result": {
                "employer_contribution": total_employer,
                "employee_contribution": total_employee,
                "total_contribution": round(total_employer + total_employee, 2),
            },
            "breakdown": {
                "ordinary_wages": {
                    "gross": wage,
                    "capped": capped_wage,
                    "ow_ceiling": _OW_CEILING,
                    "employer_rate": rates["employer"],
                    "employee_rate": rates["employee"],
                    "employer_amount": employer_ow,
                    "employee_amount": employee_ow,
                },
                "additional_wages": {
                    "bonus": bonus,
                    "employer_amount": employer_aw,
                    "employee_amount": employee_aw,
                },
                "age_band": age_band,
            },
        }

    # ------------------------------------------------------------------
    # Leave calculator
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_leave(params: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate leave entitlements.

        Params:
            years_of_service: float -- completed years of service
            leave_type: str -- "annual", "sick", or "all"
        """
        years = float(params.get("years_of_service", 0))
        leave_type = params.get("leave_type", "all")

        result = {}
        breakdown = {}

        if leave_type in ("annual", "all"):
            annual_days = _annual_leave_days(int(years))
            result["annual_leave_days"] = annual_days
            breakdown["annual_leave"] = {
                "years_of_service": years,
                "entitlement_days": annual_days,
                "basis": "Employment Act s.43A",
            }

        if leave_type in ("sick", "all"):
            sick = _sick_leave_days(years)
            result["outpatient_sick_leave_days"] = sick["outpatient"]
            result["hospitalisation_leave_days"] = sick["hospitalisation"]
            breakdown["sick_leave"] = {
                "years_of_service": years,
                "outpatient_days": sick["outpatient"],
                "hospitalisation_days": sick["hospitalisation"],
                "basis": "Employment Act s.89",
            }

        return {"result": result, "breakdown": breakdown}

    # ------------------------------------------------------------------
    # Salary calculator
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_salary(params: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate salary proration or overtime.

        Params:
            monthly_salary: float -- gross monthly salary
            calculation_type: str -- "proration" or "overtime"
            days_worked: int (for proration) -- days worked in partial month
            total_working_days: int (for proration) -- total working days in month
            overtime_hours: float (for overtime) -- OT hours in the month
            hourly_rate: float (optional, for overtime) -- if not given, derived from salary
        """
        salary = float(params.get("monthly_salary", 0))
        calc_type = params.get("calculation_type", "proration")

        if calc_type == "proration":
            days_worked = int(params.get("days_worked", 0))
            total_days = int(params.get("total_working_days", 22))

            if total_days <= 0:
                return {
                    "result": {"prorated_salary": 0},
                    "breakdown": {"error": "total_working_days must be > 0"},
                }

            prorated = round(salary * days_worked / total_days, 2)
            return {
                "result": {"prorated_salary": prorated},
                "breakdown": {
                    "monthly_salary": salary,
                    "days_worked": days_worked,
                    "total_working_days": total_days,
                    "formula": "monthly_salary * days_worked / total_working_days",
                },
            }

        elif calc_type == "overtime":
            ot_hours = float(params.get("overtime_hours", 0))
            # EA: hourly rate = monthly salary / (26 * 8) for Part IV employees
            hourly_rate = float(params.get("hourly_rate", 0))
            if hourly_rate == 0:
                hourly_rate = round(salary / (26 * 8), 2)

            ot_rate = round(hourly_rate * 1.5, 2)  # EA mandates 1.5x
            ot_pay = round(ot_rate * ot_hours, 2)

            return {
                "result": {"overtime_pay": ot_pay},
                "breakdown": {
                    "monthly_salary": salary,
                    "hourly_rate": hourly_rate,
                    "ot_multiplier": 1.5,
                    "ot_rate": ot_rate,
                    "overtime_hours": ot_hours,
                    "formula": "hourly_rate * 1.5 * overtime_hours",
                    "basis": "Employment Act s.38",
                },
            }

        else:
            return {
                "result": {},
                "breakdown": {
                    "error": f"Unknown calculation_type: {calc_type}. Use 'proration' or 'overtime'."
                },
            }

    # ------------------------------------------------------------------
    # Quota & levy calculator
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_quota_levy(params: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate foreign worker quota utilisation and levy costs.

        Params:
            sector: str -- "services", "manufacturing", "construction", "process", "marine"
            headcount_local: int -- local (SC + PR) headcount
            headcount_ep: int (optional) -- EP headcount
            headcount_sp: int (optional) -- S Pass headcount
            headcount_wp: int (optional) -- Work Permit headcount
            scenario_hire_sp: int (optional) -- proposed SP hires
            scenario_hire_wp: int (optional) -- proposed WP hires
        """
        input_data = QuotaLevyInput(
            sector=params.get("sector", "services"),
            headcount_local=int(params.get("headcount_local", 0)),
            headcount_ep=int(params.get("headcount_ep", 0)),
            headcount_sp=int(params.get("headcount_sp", 0)),
            headcount_wp=int(params.get("headcount_wp", 0)),
            scenario_hire_sp=int(params.get("scenario_hire_sp", 0)),
            scenario_hire_wp=int(params.get("scenario_hire_wp", 0)),
        )

        result = calculate_quota_levy(input_data)

        return {
            "result": {
                "sector": result.sector,
                "current_ratio": result.current_ratio,
                "drc_limit": result.drc_limit,
                "within_limit": result.within_limit,
                "headroom_foreign": result.headroom_foreign,
                "scenario_feasible": result.scenario_feasible,
                "current_total_monthly_levy": result.current_total_monthly_levy,
                "projected_total_monthly_levy": result.projected_total_monthly_levy,
            },
            "breakdown": {
                "total_workforce": result.total_workforce,
                "local_count": result.local_count,
                "foreign_count": result.foreign_count,
                "drc_utilisation": result.drc_utilisation,
                "projected_ratio": result.projected_ratio,
                "projected_within_limit": result.projected_within_limit,
                "levy_increase": result.levy_increase,
                "warnings": result.warnings,
            },
        }
