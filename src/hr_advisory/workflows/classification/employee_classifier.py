"""Employee Classification Workflow -- Kailash Core SDK workflow factory.

Builds a deterministic, multi-step classification pipeline using
PythonCodeNode. Each node applies one set of Singapore employment rules.
The workflow is 100% deterministic -- no LLM involvement.

Pipeline steps:
    validate_input -> classify_ea -> classify_part_iv -> classify_cpf
    -> validate_pass -> determine_leave -> summarize
"""

from __future__ import annotations

import json
import textwrap

from kailash.workflow.builder import WorkflowBuilder

from hr_advisory.workflows.classification.data_classes import (
    EmployeeClassificationInput,
)


def create_employee_classification_workflow(
    input_data: EmployeeClassificationInput,
) -> object:
    """Create and build a Kailash Core SDK workflow for employee classification.

    Args:
        input_data: Employee classification input parameters.

    Returns:
        A built Workflow object ready for runtime.execute().
    """
    wf = WorkflowBuilder()

    # ------------------------------------------------------------------
    # Node 1: validate_input
    # Packages the input data into a dict for downstream nodes.
    # ------------------------------------------------------------------
    input_dict = {
        "monthly_basic_salary": input_data.monthly_basic_salary,
        "citizenship_status": input_data.citizenship_status,
        "employment_type": input_data.employment_type,
        "sector": input_data.sector,
        "age": input_data.age,
        "is_workman": input_data.is_workman,
        "is_manager_executive": input_data.is_manager_executive,
        "pr_year": input_data.pr_year,
        "pass_type": input_data.pass_type,
        "job_role_description": input_data.job_role_description,
        "is_domestic_worker": input_data.is_domestic_worker,
        "is_seafarer": input_data.is_seafarer,
        "is_government": input_data.is_government,
    }
    input_json = json.dumps(input_dict)

    wf.add_node(
        "PythonCodeNode",
        "validate_input",
        {
            "code": textwrap.dedent(
                f"""\
                import json

                data = json.loads('''{input_json}''')

                # Validate required fields
                errors = []
                if not isinstance(data.get("monthly_basic_salary"), (int, float)):
                    errors.append("monthly_basic_salary must be a number")
                if data.get("monthly_basic_salary", 0) < 0:
                    errors.append("monthly_basic_salary must be non-negative")
                if data.get("citizenship_status") not in ("SC", "PR", "foreigner"):
                    errors.append("citizenship_status must be SC, PR, or foreigner")
                if data.get("employment_type") not in ("full_time", "part_time", "contract"):
                    errors.append("employment_type must be full_time, part_time, or contract")
                if not isinstance(data.get("age"), int) or data.get("age", 0) < 0:
                    errors.append("age must be a non-negative integer")

                if errors:
                    raise ValueError("Input validation failed: " + "; ".join(errors))

                result = data
            """
            ),
        },
    )

    # ------------------------------------------------------------------
    # Node 2: classify_ea
    # Determines Employment Act coverage.
    # ------------------------------------------------------------------
    wf.add_node(
        "PythonCodeNode",
        "classify_ea",
        {
            "code": textwrap.dedent(
                """\
                data = result

                is_domestic = data.get("is_domestic_worker", False)
                is_seafarer = data.get("is_seafarer", False)
                is_govt = data.get("is_government", False)

                ea_covered = True
                ea_exclusion_reason = None

                if is_domestic:
                    ea_covered = False
                    ea_exclusion_reason = "Domestic workers are excluded from the Employment Act"
                elif is_seafarer:
                    ea_covered = False
                    ea_exclusion_reason = "Seafarers are excluded from the Employment Act"
                elif is_govt:
                    ea_covered = False
                    ea_exclusion_reason = "Government employees (statutory board/civil service) are excluded from the Employment Act"

                result = {**data, "ea_covered": ea_covered, "ea_exclusion_reason": ea_exclusion_reason}
            """
            ),
        },
    )

    # ------------------------------------------------------------------
    # Node 3: classify_part_iv
    # Determines EA Part IV applicability.
    # ------------------------------------------------------------------
    wf.add_node(
        "PythonCodeNode",
        "classify_part_iv",
        {
            "code": textwrap.dedent(
                """\
                data = result
                ea_covered = data["ea_covered"]
                is_manager = data.get("is_manager_executive", False)
                is_workman = data.get("is_workman", False)
                salary = data["monthly_basic_salary"]

                WORKMAN_THRESHOLD = 4500.0
                NON_WORKMAN_THRESHOLD = 2600.0

                part_iv = False
                reason = ""

                if not ea_covered:
                    reason = "Part IV does not apply: employee is not covered by the Employment Act"
                elif is_manager:
                    reason = "Part IV does not apply to managers/executives regardless of salary"
                elif is_workman:
                    if salary <= WORKMAN_THRESHOLD:
                        part_iv = True
                        reason = f"Part IV applies: workman earning ${salary:,.2f}/month (<= ${WORKMAN_THRESHOLD:,.2f} threshold)"
                    else:
                        reason = f"Part IV does not apply: workman earning ${salary:,.2f}/month exceeds the $4,500 threshold for workmen"
                else:
                    if salary <= NON_WORKMAN_THRESHOLD:
                        part_iv = True
                        reason = f"Part IV applies: non-workman employee earning ${salary:,.2f}/month (<= ${NON_WORKMAN_THRESHOLD:,.2f} threshold)"
                    else:
                        reason = f"Part IV does not apply: non-workman employee earning ${salary:,.2f}/month exceeds the $2,600 threshold for non-workman employees"

                result = {**data, "part_iv_applicable": part_iv, "part_iv_reason": reason}
            """
            ),
        },
    )

    # ------------------------------------------------------------------
    # Node 4: classify_cpf
    # Determines CPF applicability, tier, and age band.
    # ------------------------------------------------------------------
    wf.add_node(
        "PythonCodeNode",
        "classify_cpf",
        {
            "code": textwrap.dedent(
                """\
                data = result
                citizenship = data["citizenship_status"]
                pr_year = data.get("pr_year")
                age = data["age"]

                cpf_applicable = False
                cpf_tier = "none"

                if citizenship == "SC":
                    cpf_applicable = True
                    cpf_tier = "sc_full"
                elif citizenship == "PR":
                    cpf_applicable = True
                    if pr_year == 1:
                        cpf_tier = "pr_year1"
                    elif pr_year == 2:
                        cpf_tier = "pr_year2"
                    else:
                        cpf_tier = "pr_year3_plus"
                else:
                    cpf_applicable = False
                    cpf_tier = "none"

                # Age band
                if age < 55:
                    cpf_age_band = "55_below"
                elif age < 60:
                    cpf_age_band = "55_60"
                elif age < 65:
                    cpf_age_band = "60_65"
                elif age < 70:
                    cpf_age_band = "65_70"
                else:
                    cpf_age_band = "above_70"

                result = {
                    **data,
                    "cpf_applicable": cpf_applicable,
                    "cpf_tier": cpf_tier,
                    "cpf_age_band": cpf_age_band,
                }
            """
            ),
        },
    )

    # ------------------------------------------------------------------
    # Node 5: validate_pass
    # Validates work pass type against salary thresholds.
    # ------------------------------------------------------------------
    wf.add_node(
        "PythonCodeNode",
        "validate_pass",
        {
            "code": textwrap.dedent(
                """\
                data = result
                citizenship = data["citizenship_status"]
                pass_type = data.get("pass_type")
                salary = data["monthly_basic_salary"]
                sector = data.get("sector", "services")
                warnings = []

                EP_MIN = 5000.0
                SP_MIN = 3150.0

                pass_valid = True
                pass_msg = ""

                if citizenship in ("SC", "PR"):
                    pass_valid = True
                    pass_msg = ""
                elif pass_type == "ep":
                    if salary >= EP_MIN:
                        pass_valid = True
                        pass_msg = f"EP valid: salary ${salary:,.2f} meets minimum ${EP_MIN:,.2f}"
                    else:
                        pass_valid = False
                        pass_msg = f"EP invalid: salary ${salary:,.2f} is below the minimum ${EP_MIN:,.2f}/month required for Employment Pass"
                        warnings.append(f"Employment Pass salary requirement not met: ${salary:,.2f} < ${EP_MIN:,.2f}")
                elif pass_type == "sp":
                    if salary >= SP_MIN:
                        pass_valid = True
                        pass_msg = f"S-Pass valid: salary ${salary:,.2f} meets minimum ${SP_MIN:,.2f}"
                    else:
                        pass_valid = False
                        pass_msg = f"S-Pass invalid: salary ${salary:,.2f} is below the minimum ${SP_MIN:,.2f}/month required for S-Pass"
                        warnings.append(f"S-Pass salary requirement not met: ${salary:,.2f} < ${SP_MIN:,.2f}")
                elif pass_type == "wp":
                    pass_valid = True
                    pass_msg = "Work Permit: no minimum salary threshold (quota/levy applies)"
                else:
                    pass_valid = False
                    pass_msg = f"Unknown pass type: {pass_type}"
                    warnings.append(f"Invalid or missing pass type for foreigner: {pass_type}")

                result = {
                    **data,
                    "pass_valid": pass_valid,
                    "pass_validation_message": pass_msg,
                    "warnings": warnings,
                }
            """
            ),
        },
    )

    # ------------------------------------------------------------------
    # Node 6: determine_leave
    # Determines applicable statutory leave types.
    # ------------------------------------------------------------------
    wf.add_node(
        "PythonCodeNode",
        "determine_leave",
        {
            "code": textwrap.dedent(
                """\
                data = result
                ea_covered = data["ea_covered"]
                citizenship = data["citizenship_status"]
                emp_type = data.get("employment_type", "full_time")

                leaves = []

                if ea_covered:
                    # EA-mandated leave for all EA-covered employees
                    leaves.append("annual_leave")
                    leaves.append("sick_leave")
                    leaves.append("maternity_leave")

                    # CCDA-based leave -- SC and PR only
                    if citizenship in ("SC", "PR"):
                        leaves.append("paternity_leave")
                        leaves.append("childcare_leave")
                        leaves.append("shared_parental_leave")
                        leaves.append("adoption_leave")
                        leaves.append("unpaid_infant_care_leave")

                result = {**data, "applicable_leave_types": leaves}
            """
            ),
        },
    )

    # ------------------------------------------------------------------
    # Node 7: summarize
    # Produces the final classification result dict.
    # ------------------------------------------------------------------
    wf.add_node(
        "PythonCodeNode",
        "summarize",
        {
            "code": textwrap.dedent(
                """\
                data = result
                warnings = data.get("warnings", [])

                # Build classification summary
                parts = []
                if data["ea_covered"]:
                    parts.append("Employment Act covered")
                else:
                    parts.append(f"Employment Act excluded ({data.get('ea_exclusion_reason', 'unknown reason')})")

                if data.get("part_iv_applicable"):
                    parts.append("Part IV (rest days/hours/overtime) applies")
                else:
                    parts.append("Part IV does not apply")

                if data.get("cpf_applicable"):
                    parts.append(f"CPF applicable (tier: {data.get('cpf_tier', 'unknown')}, age band: {data.get('cpf_age_band', 'unknown')})")
                else:
                    parts.append("CPF not applicable (foreigner)")

                if data.get("pass_valid"):
                    if data.get("pass_validation_message"):
                        parts.append(data["pass_validation_message"])
                else:
                    parts.append(f"Pass INVALID: {data.get('pass_validation_message', 'unknown')}")

                leave_count = len(data.get("applicable_leave_types", []))
                parts.append(f"{leave_count} statutory leave type(s) applicable")

                summary = ". ".join(parts) + "."

                result = {
                    "ea_covered": data["ea_covered"],
                    "ea_exclusion_reason": data.get("ea_exclusion_reason"),
                    "part_iv_applicable": data.get("part_iv_applicable", False),
                    "part_iv_reason": data.get("part_iv_reason", ""),
                    "cpf_applicable": data.get("cpf_applicable", False),
                    "cpf_tier": data.get("cpf_tier", ""),
                    "cpf_age_band": data.get("cpf_age_band", ""),
                    "pass_valid": data.get("pass_valid", True),
                    "pass_validation_message": data.get("pass_validation_message", ""),
                    "applicable_leave_types": data.get("applicable_leave_types", []),
                    "classification_summary": summary,
                    "warnings": warnings,
                }
            """
            ),
        },
    )

    # ------------------------------------------------------------------
    # Connections: linear pipeline
    # ------------------------------------------------------------------
    wf.add_connection("validate_input", "result", "classify_ea", "result")
    wf.add_connection("classify_ea", "result", "classify_part_iv", "result")
    wf.add_connection("classify_part_iv", "result", "classify_cpf", "result")
    wf.add_connection("classify_cpf", "result", "validate_pass", "result")
    wf.add_connection("validate_pass", "result", "determine_leave", "result")
    wf.add_connection("determine_leave", "result", "summarize", "result")

    return wf.build()
