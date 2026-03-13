"""CPF Contribution Calculator Workflow — Kailash Core SDK workflow factory.

Wraps the pure CPF calculator functions into a Kailash workflow
that can be executed via LocalRuntime. Each node in the pipeline
handles one step of the calculation.

Pipeline steps:
    validate_input -> lookup_rates -> apply_ceilings -> calculate -> allocate -> summarize
"""

from __future__ import annotations

import json
import textwrap

from kailash.workflow.builder import WorkflowBuilder


def create_cpf_calculator_workflow(
    *,
    citizenship_status: str,
    age: int,
    monthly_ow: float,
    monthly_aw: float = 0.0,
    pr_year: int | None = None,
    ytd_ow: float = 0.0,
) -> object:
    """Create a Kailash workflow for CPF contribution calculation.

    Args:
        citizenship_status: "SC", "PR", or "foreigner"
        age: Employee's age in years
        monthly_ow: Monthly Ordinary Wages
        monthly_aw: Monthly Additional Wages (bonus, etc.)
        pr_year: PR year (1, 2, or 3+) — required for PR employees
        ytd_ow: Year-to-date OW already contributed on

    Returns:
        A built Workflow object ready for runtime.execute().
    """
    wf = WorkflowBuilder()

    input_dict = {
        "citizenship_status": citizenship_status,
        "age": age,
        "monthly_ow": monthly_ow,
        "monthly_aw": monthly_aw,
        "pr_year": pr_year,
        "ytd_ow": ytd_ow,
    }
    input_json = json.dumps(input_dict)

    # Node 1: validate and prepare input
    wf.add_node(
        "PythonCodeNode",
        "validate_input",
        {
            "code": textwrap.dedent(
                f"""\
                import json

                data = json.loads('''{input_json}''')

                errors = []
                if data["citizenship_status"] not in ("SC", "PR", "foreigner"):
                    errors.append("citizenship_status must be SC, PR, or foreigner")
                if data["citizenship_status"] == "PR" and data.get("pr_year") is None:
                    errors.append("pr_year is required for PR employees")
                if not isinstance(data["age"], int) or data["age"] < 0:
                    errors.append("age must be a non-negative integer")
                if data["monthly_ow"] < 0:
                    errors.append("monthly_ow must be non-negative")
                if data["monthly_aw"] < 0:
                    errors.append("monthly_aw must be non-negative")

                if errors:
                    raise ValueError("CPF input validation failed: " + "; ".join(errors))

                result = data
            """
            ),
        },
    )

    # Node 2: determine tier and rates
    wf.add_node(
        "PythonCodeNode",
        "lookup_rates",
        {
            "code": textwrap.dedent(
                """\
                data = result
                citizenship = data["citizenship_status"]
                pr_year = data.get("pr_year")
                age = data["age"]

                # Determine tier
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

                # Determine age band
                if age < 55:
                    age_band = "55_below"
                elif age < 60:
                    age_band = "55_60"
                elif age < 65:
                    age_band = "60_65"
                elif age < 70:
                    age_band = "65_70"
                else:
                    age_band = "above_70"

                # Rate table
                RATES = {
                    ("sc_full", "55_below"): (0.17, 0.20),
                    ("sc_full", "55_60"): (0.145, 0.15),
                    ("sc_full", "60_65"): (0.11, 0.095),
                    ("sc_full", "65_70"): (0.075, 0.07),
                    ("sc_full", "above_70"): (0.05, 0.05),
                    ("pr_year1", "55_below"): (0.04, 0.05),
                    ("pr_year1", "55_60"): (0.04, 0.05),
                    ("pr_year1", "60_65"): (0.035, 0.05),
                    ("pr_year1", "65_70"): (0.035, 0.05),
                    ("pr_year1", "above_70"): (0.035, 0.05),
                    ("pr_year2", "55_below"): (0.09, 0.15),
                    ("pr_year2", "55_60"): (0.09, 0.15),
                    ("pr_year2", "60_65"): (0.065, 0.095),
                    ("pr_year2", "65_70"): (0.065, 0.07),
                    ("pr_year2", "above_70"): (0.065, 0.05),
                    ("pr_year3_plus", "55_below"): (0.17, 0.20),
                    ("pr_year3_plus", "55_60"): (0.145, 0.15),
                    ("pr_year3_plus", "60_65"): (0.11, 0.095),
                    ("pr_year3_plus", "65_70"): (0.075, 0.07),
                    ("pr_year3_plus", "above_70"): (0.05, 0.05),
                }

                employer_rate = 0.0
                employee_rate = 0.0
                if cpf_applicable:
                    key = (cpf_tier, age_band)
                    employer_rate, employee_rate = RATES.get(key, (0.0, 0.0))

                result = {
                    **data,
                    "cpf_applicable": cpf_applicable,
                    "cpf_tier": cpf_tier,
                    "age_band": age_band,
                    "employer_rate": employer_rate,
                    "employee_rate": employee_rate,
                    "total_rate": employer_rate + employee_rate,
                }
            """
            ),
        },
    )

    # Node 3: apply wage ceilings
    wf.add_node(
        "PythonCodeNode",
        "apply_ceilings",
        {
            "code": textwrap.dedent(
                """\
                data = result
                OW_CEILING = 8000.0
                AW_CEILING_ANNUAL = 102000.0

                monthly_ow = data["monthly_ow"]
                monthly_aw = data["monthly_aw"]
                ytd_ow = data.get("ytd_ow", 0.0)

                ow_subject = min(monthly_ow, OW_CEILING)
                ow_capped = monthly_ow > OW_CEILING

                total_ytd_ow = ytd_ow + ow_subject
                aw_ceiling_remaining = max(0.0, AW_CEILING_ANNUAL - total_ytd_ow)
                aw_subject = min(monthly_aw, aw_ceiling_remaining)
                aw_capped = monthly_aw > aw_ceiling_remaining

                result = {
                    **data,
                    "ow_subject": ow_subject,
                    "ow_capped": ow_capped,
                    "aw_subject": aw_subject,
                    "aw_capped": aw_capped,
                    "total_wages": ow_subject + aw_subject,
                    "aw_ceiling_remaining": aw_ceiling_remaining,
                }
            """
            ),
        },
    )

    # Node 4: calculate contributions
    wf.add_node(
        "PythonCodeNode",
        "calculate",
        {
            "code": textwrap.dedent(
                """\
                data = result
                total_wages = data["total_wages"]
                employer_rate = data["employer_rate"]
                employee_rate = data["employee_rate"]

                if not data["cpf_applicable"] or total_wages == 0:
                    employer_cpf = 0.0
                    employee_cpf = 0.0
                else:
                    employer_cpf = round(total_wages * employer_rate)
                    employee_cpf = round(total_wages * employee_rate)

                total_cpf = employer_cpf + employee_cpf

                result = {
                    **data,
                    "employer_contribution": employer_cpf,
                    "employee_contribution": employee_cpf,
                    "total_contribution": total_cpf,
                }
            """
            ),
        },
    )

    # Node 5: allocate to OA/SA/MA
    wf.add_node(
        "PythonCodeNode",
        "allocate",
        {
            "code": textwrap.dedent(
                """\
                data = result
                total_wages = data["total_wages"]
                total_cpf = data["total_contribution"]
                age_band = data["age_band"]

                ALLOC = {
                    "55_below": (0.2308, 0.0616, 0.0811),
                    "55_60": (0.1282, 0.0350, 0.1068),
                    "60_65": (0.0357, 0.0175, 0.1468),
                    "65_70": (0.0100, 0.0100, 0.1250),
                    "above_70": (0.0100, 0.0100, 0.0800),
                }

                if data["cpf_applicable"] and total_wages > 0:
                    oa_r, sa_r, ma_r = ALLOC.get(age_band, (0.0, 0.0, 0.0))
                    alloc_oa = round(total_wages * oa_r)
                    alloc_sa = round(total_wages * sa_r)
                    alloc_ma = total_cpf - alloc_oa - alloc_sa
                else:
                    alloc_oa = 0.0
                    alloc_sa = 0.0
                    alloc_ma = 0.0

                result = {
                    **data,
                    "allocation_oa": alloc_oa,
                    "allocation_sa": alloc_sa,
                    "allocation_ma": alloc_ma,
                }
            """
            ),
        },
    )

    # Node 6: build summary
    wf.add_node(
        "PythonCodeNode",
        "summarize",
        {
            "code": textwrap.dedent(
                """\
                data = result

                result = {
                    "cpf_applicable": data["cpf_applicable"],
                    "cpf_tier": data["cpf_tier"],
                    "age_band": data["age_band"],
                    "employer_rate": data["employer_rate"],
                    "employee_rate": data["employee_rate"],
                    "total_rate": data["total_rate"],
                    "employer_contribution": data["employer_contribution"],
                    "employee_contribution": data["employee_contribution"],
                    "total_contribution": data["total_contribution"],
                    "ow_subject_to_cpf": data["ow_subject"],
                    "aw_subject_to_cpf": data["aw_subject"],
                    "ow_capped": data["ow_capped"],
                    "aw_capped": data["aw_capped"],
                    "allocation_oa": data["allocation_oa"],
                    "allocation_sa": data["allocation_sa"],
                    "allocation_ma": data["allocation_ma"],
                    "input": {
                        "citizenship_status": data["citizenship_status"],
                        "age": data["age"],
                        "monthly_ow": data["monthly_ow"],
                        "monthly_aw": data["monthly_aw"],
                        "pr_year": data.get("pr_year"),
                    },
                }
            """
            ),
        },
    )

    # Connections
    wf.add_connection("validate_input", "result", "lookup_rates", "result")
    wf.add_connection("lookup_rates", "result", "apply_ceilings", "result")
    wf.add_connection("apply_ceilings", "result", "calculate", "result")
    wf.add_connection("calculate", "result", "allocate", "result")
    wf.add_connection("allocate", "result", "summarize", "result")

    return wf.build()
