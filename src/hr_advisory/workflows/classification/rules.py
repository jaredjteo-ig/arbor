"""Pure functions for Singapore employee classification rules.

Every function in this module is deterministic and side-effect-free.
No LLM, no external calls, no database access. Each function encodes
a specific piece of Singapore employment legislation.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Constants -- Singapore regulatory thresholds
# ---------------------------------------------------------------------------

# Part IV salary thresholds (EA Part IV: rest days, hours of work, overtime)
PART_IV_WORKMAN_SALARY_THRESHOLD = 4500.0  # Workman Part IV cap
PART_IV_NON_WORKMAN_SALARY_THRESHOLD = 2600.0  # Non-workman Part IV cap

# Work pass minimum salary thresholds (as of 2024)
EP_MIN_SALARY = 5000.0  # Employment Pass
SP_MIN_SALARY = 3150.0  # S-Pass (base; varies by sector)

# Valid pass types for foreigners
VALID_PASS_TYPES = {"ep", "sp", "wp"}

# Valid citizenship statuses
VALID_CITIZENSHIP_STATUSES = {"SC", "PR", "foreigner"}


# ---------------------------------------------------------------------------
# EA Coverage
# ---------------------------------------------------------------------------


def classify_ea_coverage(
    *,
    is_domestic_worker: bool,
    is_seafarer: bool,
    is_government: bool,
) -> tuple[bool, str | None]:
    """Determine if an employee is covered by the Employment Act.

    The EA covers ALL employees EXCEPT:
    - Domestic workers
    - Seafarers
    - Government employees (statutory board / civil service)

    Returns:
        (covered: bool, exclusion_reason: str | None)
    """
    if is_domestic_worker:
        return False, "Domestic workers are excluded from the Employment Act"
    if is_seafarer:
        return False, "Seafarers are excluded from the Employment Act"
    if is_government:
        return (
            False,
            "Government employees (statutory board/civil service) are excluded from the Employment Act",
        )
    return True, None


# ---------------------------------------------------------------------------
# Part IV Applicability
# ---------------------------------------------------------------------------


def classify_part_iv(
    *,
    ea_covered: bool,
    is_manager_executive: bool,
    is_workman: bool,
    monthly_basic_salary: float,
) -> tuple[bool, str]:
    """Determine if EA Part IV (rest days, hours of work, overtime) applies.

    Part IV rules:
    - Does NOT apply if employee is not EA covered
    - Does NOT apply to managers/executives (regardless of salary)
    - Applies to ALL workmen earning <= $4,500/month basic salary
    - Applies to ALL non-workman employees earning <= $2,600/month basic salary
    - Does NOT apply to workmen earning > $4,500/month
    - Does NOT apply to non-workmen earning > $2,600/month

    Returns:
        (applicable: bool, reason: str)
    """
    if not ea_covered:
        return False, "Part IV does not apply: employee is not covered by the Employment Act"

    if is_manager_executive:
        return False, "Part IV does not apply to managers/executives regardless of salary"

    if is_workman:
        if monthly_basic_salary <= PART_IV_WORKMAN_SALARY_THRESHOLD:
            return True, (
                f"Part IV applies: workman earning ${monthly_basic_salary:,.2f}/month "
                f"(<= ${PART_IV_WORKMAN_SALARY_THRESHOLD:,.2f} threshold)"
            )
        else:
            return False, (
                f"Part IV does not apply: workman earning ${monthly_basic_salary:,.2f}/month "
                f"exceeds the $4,500 threshold for workmen"
            )
    else:
        # Non-workman, non-manager
        if monthly_basic_salary <= PART_IV_NON_WORKMAN_SALARY_THRESHOLD:
            return True, (
                f"Part IV applies: non-workman employee earning ${monthly_basic_salary:,.2f}/month "
                f"(<= ${PART_IV_NON_WORKMAN_SALARY_THRESHOLD:,.2f} threshold)"
            )
        else:
            return False, (
                f"Part IV does not apply: non-workman employee earning ${monthly_basic_salary:,.2f}/month "
                f"exceeds the $2,600 threshold for non-workman employees"
            )


# ---------------------------------------------------------------------------
# CPF Status
# ---------------------------------------------------------------------------


def classify_cpf_status(
    *,
    citizenship_status: str,
    pr_year: int | None,
) -> tuple[bool, str]:
    """Determine CPF applicability and tier.

    CPF rules:
    - Singapore Citizens (SC): Full CPF from day one
    - Permanent Residents (PR): Graduated rates based on PR year (1, 2, 3+)
    - Foreigners (EP, S-Pass, WP): No CPF

    Returns:
        (applicable: bool, tier: str)
        tier is one of: "sc_full", "pr_year1", "pr_year2", "pr_year3_plus", "none"

    Raises:
        ValueError: If citizenship_status is invalid or PR without pr_year
    """
    if citizenship_status not in VALID_CITIZENSHIP_STATUSES:
        raise ValueError(
            f"Invalid citizenship_status '{citizenship_status}'. "
            f"Must be one of: {sorted(VALID_CITIZENSHIP_STATUSES)}"
        )

    if citizenship_status == "SC":
        return True, "sc_full"

    if citizenship_status == "PR":
        if pr_year is None:
            raise ValueError(
                "pr_year is required for PR citizenship status. "
                "Provide the PR year (1, 2, or 3+) to determine CPF tier."
            )
        if pr_year == 1:
            return True, "pr_year1"
        elif pr_year == 2:
            return True, "pr_year2"
        else:
            return True, "pr_year3_plus"

    # Foreigner
    return False, "none"


# ---------------------------------------------------------------------------
# CPF Age Band
# ---------------------------------------------------------------------------


def determine_cpf_age_band(age: int) -> str:
    """Determine CPF contribution age band.

    CPF age tiers:
    - <= 55: "55_below"
    - 55-59: "55_60"
    - 60-64: "60_65"
    - 65-69: "65_70"
    - >= 70: "above_70"

    Returns:
        Age band string
    """
    if age < 55:
        return "55_below"
    elif age < 60:
        return "55_60"
    elif age < 65:
        return "60_65"
    elif age < 70:
        return "65_70"
    else:
        return "above_70"


# ---------------------------------------------------------------------------
# Pass Type Validation
# ---------------------------------------------------------------------------


def validate_pass_type(
    *,
    citizenship_status: str,
    pass_type: str | None,
    monthly_basic_salary: float,
    sector: str,
) -> tuple[bool, str]:
    """Validate work pass type against salary thresholds.

    Pass rules:
    - SC/PR: No pass type needed
    - Employment Pass (EP): Minimum $5,000/month
    - S-Pass: Minimum $3,150/month (base; varies by sector)
    - Work Permit (WP): No minimum salary threshold (quota/levy applies)

    Returns:
        (valid: bool, message: str)

    Raises:
        ValueError: If foreigner without pass_type or invalid pass_type
    """
    # SC and PR do not need a pass
    if citizenship_status in ("SC", "PR"):
        return True, ""

    # Foreigners must have a pass type
    if pass_type is None:
        raise ValueError(
            "pass_type is required for foreigner citizenship status. " "Provide one of: ep, sp, wp"
        )

    if pass_type not in VALID_PASS_TYPES:
        raise ValueError(
            f"Invalid pass_type '{pass_type}'. Must be one of: {sorted(VALID_PASS_TYPES)}"
        )

    if pass_type == "ep":
        if monthly_basic_salary >= EP_MIN_SALARY:
            return (
                True,
                f"EP valid: salary ${monthly_basic_salary:,.2f} meets minimum ${EP_MIN_SALARY:,.2f}",
            )
        else:
            return False, (
                f"EP invalid: salary ${monthly_basic_salary:,.2f} is below the "
                f"minimum ${EP_MIN_SALARY:,.2f}/month required for Employment Pass"
            )

    if pass_type == "sp":
        if monthly_basic_salary >= SP_MIN_SALARY:
            return (
                True,
                f"S-Pass valid: salary ${monthly_basic_salary:,.2f} meets minimum ${SP_MIN_SALARY:,.2f}",
            )
        else:
            return False, (
                f"S-Pass invalid: salary ${monthly_basic_salary:,.2f} is below the "
                f"minimum ${SP_MIN_SALARY:,.2f}/month required for S-Pass"
            )

    if pass_type == "wp":
        return True, "Work Permit: no minimum salary threshold (quota/levy applies)"

    # Should not reach here given the validation above
    return False, f"Unhandled pass type: {pass_type}"


# ---------------------------------------------------------------------------
# Leave Entitlements
# ---------------------------------------------------------------------------


def determine_leave_entitlements(
    *,
    ea_covered: bool,
    citizenship_status: str,
    employment_type: str,
) -> list[str]:
    """Determine applicable statutory leave types.

    Leave rules:
    - Annual leave: 7 days minimum (EA covered, >3 months service)
    - Sick leave: 14 days outpatient + 60 days hospitalisation (EA covered)
    - Maternity leave: 16 weeks (EA covered, working woman)
    - Paternity leave: 4 weeks (CDCSA, married father, since 1 Jan 2025) -- SC/PR only
    - Childcare leave: 6 days/year (child <7, EA covered) -- SC/PR only
    - Shared parental leave: up to 4 weeks (from mother's maternity) -- SC/PR only
    - Adoption leave: 12 weeks (qualifying adoption) -- SC/PR only
    - Unpaid infant care leave: 6 days/year (child <2, EA covered) -- SC/PR only

    Returns:
        List of applicable leave type strings
    """
    if not ea_covered:
        return []

    leaves = []

    # EA-mandated leave -- applies to ALL EA-covered employees
    leaves.append("annual_leave")
    leaves.append("sick_leave")
    leaves.append("maternity_leave")

    # CCDA-based leave -- applies to SC and PR only (not foreigners)
    if citizenship_status in ("SC", "PR"):
        leaves.append("paternity_leave")
        leaves.append("childcare_leave")
        leaves.append("shared_parental_leave")
        leaves.append("adoption_leave")
        leaves.append("unpaid_infant_care_leave")

    return leaves
