"""Central Provident Fund Act (Cap 36) — structured content bundle.

Covers:
- Section 7: Employer CPF contributions by age band
- Section 9: Employee CPF contributions by age band
- PR Graduated Rates: 1st year, 2nd year, 3rd year+ rates
- Section 13: Ordinary Wage (OW) ceiling
- Section 14: Additional Wage (AW) ceiling
- CPF Account Allocation: OA, SA, MA split by age band
- Section 52: Late payment interest and penalties
- Section 58: Voluntary contributions and tax relief

All content reflects the CPF Act as at 1 January 2026,
including the OW ceiling increase from $7,400 to $8,000.
"""

import json


def get_bundle() -> dict:
    """Return the full CPF Act content bundle.

    This dict is passed directly to ``KBContentPipeline.bulk_load()``.
    """
    return {
        "act": _act(),
        "domains": _domains(),
        "provisions": _provisions(),
        "cross_references": _cross_references(),
        "rate_tables": _rate_tables(),
    }


# ------------------------------------------------------------------
# Act
# ------------------------------------------------------------------


def _act() -> dict:
    return {
        "title": "Central Provident Fund Act",
        "short_name": "CPFA",
        "authority_type": "statute",
        "issuing_body": "Central Provident Fund Board",
        "official_url": "https://sso.agc.gov.sg/Act/CPFA1953",
        "is_active": True,
    }


# ------------------------------------------------------------------
# Domains
# ------------------------------------------------------------------


def _domains() -> list[dict]:
    return [
        {
            "name": "CPF Contribution Rates",
            "description": (
                "CPF contribution rate tables by age band and citizenship "
                "status. Covers Singapore Citizen full rates and Permanent "
                "Resident graduated and full rate schedules."
            ),
            "sort_order": 1,
        },
        {
            "name": "CPF Wage Ceilings",
            "description": (
                "Ordinary Wage (OW) and Additional Wage (AW) ceilings that "
                "cap the amount of wages subject to CPF contributions."
            ),
            "sort_order": 2,
        },
        {
            "name": "CPF Allocation",
            "description": (
                "Allocation of total CPF contributions to the Ordinary "
                "Account (OA), Special Account (SA), and Medisave Account "
                "(MA) by age band."
            ),
            "sort_order": 3,
        },
        {
            "name": "CPF Compliance",
            "description": (
                "Late payment penalties, enforcement actions, voluntary "
                "contributions, Medisave and Retirement Sum top-ups, and "
                "related compliance obligations."
            ),
            "sort_order": 4,
        },
    ]


# ------------------------------------------------------------------
# Provisions
# ------------------------------------------------------------------


def _provisions() -> list[dict]:
    return [
        # ====== CPF CONTRIBUTION RATES ======
        {
            "section": "CPFA-S7",
            "title": "Employer CPF Contributions",
            "formal_text": (
                "Section 7 of the Central Provident Fund Act. Every employer "
                "shall pay to the Fund, in respect of each month, "
                "contributions at the rates set out in the First Schedule. "
                "For Singapore Citizens earning more than $750/month total "
                "wages, the employer contribution rates by age band are: "
                "age 55 and below — 17%; above 55 to 60 — 14.5%; above 60 "
                "to 65 — 11%; above 65 to 70 — 7.5%; above 70 — 5%. These "
                "rates apply to wages up to the applicable wage ceilings."
            ),
            "plain_summary": (
                "Employers must contribute CPF for every employee who earns "
                "more than $750/month. The employer's share depends on the "
                "employee's age: 17% for age 55 and below, 14.5% for 55-60, "
                "11% for 60-65, 7.5% for 65-70, and 5% for above 70. These "
                "are the full rates for Singapore Citizens."
            ),
            "interpretation_notes": (
                "The $750/month threshold applies to total wages (OW + AW). "
                "For employees earning $50-$500/month, only the employer "
                "contributes (no employee share). For $500-$750/month, "
                "graduated rates apply. The 17% employer rate for age 55 "
                "and below is the highest tier and has been in effect since "
                "1 January 2016. Employer contributions are a tax-deductible "
                "business expense. Employers who fail to pay are liable "
                "under Section 52."
            ),
            "authority_level": "statute",
            "domain_name": "CPF Contribution Rates",
            "effective_date": "2024-01-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {
                        "included": [
                            "singapore_citizen_employees",
                            "permanent_resident_employees",
                        ],
                        "min_monthly_wage": 750,
                    },
                    "notes": (
                        "CPF contributions are mandatory for all Singapore "
                        "Citizen and Permanent Resident employees earning "
                        "more than $750/month in total wages."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "A Singapore Citizen employee aged 30 earns a " "monthly salary of $5,000."
                    ),
                    "calculation": {
                        "age_band": "55 and below",
                        "employer_rate": "17%",
                        "employee_rate": "20%",
                        "employer_contribution": "$5,000 x 17% = $850",
                        "employee_contribution": "$5,000 x 20% = $1,000",
                        "total_cpf": "$850 + $1,000 = $1,850",
                        "take_home": "$5,000 - $1,000 = $4,000",
                    },
                    "outcome": (
                        "The employer pays $850 into the employee's CPF "
                        "account on top of the $5,000 salary. The employee's "
                        "take-home pay is $4,000 after the $1,000 employee "
                        "contribution is deducted. Total CPF credited: $1,850."
                    ),
                },
                {
                    "scenario": (
                        "A Singapore Citizen employee aged 58 earns a " "monthly salary of $4,000."
                    ),
                    "calculation": {
                        "age_band": "above 55 to 60",
                        "employer_rate": "14.5%",
                        "employee_rate": "15%",
                        "employer_contribution": "$4,000 x 14.5% = $580",
                        "employee_contribution": "$4,000 x 15% = $600",
                        "total_cpf": "$580 + $600 = $1,180",
                    },
                    "outcome": (
                        "The employer pays $580 and the employee contributes "
                        "$600, for a total of $1,180 credited to CPF. Both "
                        "rates are lower than the 55-and-below band to "
                        "support continued employment of older workers."
                    ),
                },
            ],
        },
        {
            "section": "CPFA-S9",
            "title": "Employee CPF Contributions",
            "formal_text": (
                "Section 9 of the Central Provident Fund Act. Every employee "
                "who is a citizen or permanent resident of Singapore shall "
                "contribute to the Fund at the rates set out in the First "
                "Schedule. For Singapore Citizens earning more than "
                "$750/month, the employee contribution rates by age band "
                "are: age 55 and below — 20%; above 55 to 60 — 15%; above "
                "60 to 65 — 9.5%; above 65 to 70 — 7%; above 70 — 5%."
            ),
            "plain_summary": (
                "Employees who are Singapore Citizens or PRs must contribute "
                "CPF from their wages. The employee's share depends on age: "
                "20% for age 55 and below, 15% for 55-60, 9.5% for 60-65, "
                "7% for 65-70, and 5% for above 70. The employer deducts "
                "this from the employee's salary."
            ),
            "interpretation_notes": (
                "The employee contribution is deducted from salary — the "
                "employer must not pay the employee's share on their behalf "
                "(doing so is an offence under Section 52A). For employees "
                "earning $500-$750/month, graduated employee rates apply. "
                "Employees earning $500 or less pay no employee "
                "contribution. The 20% rate for age 55 and below is the "
                "highest employee rate. Employee contributions are not "
                "subject to income tax — they are deducted before tax."
            ),
            "authority_level": "statute",
            "domain_name": "CPF Contribution Rates",
            "effective_date": "2024-01-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {
                        "included": [
                            "singapore_citizen_employees",
                            "permanent_resident_employees",
                        ],
                        "min_monthly_wage": 750,
                    },
                    "notes": (
                        "Employee contributions apply to Singapore Citizens "
                        "and PRs earning more than $750/month total wages."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "A Singapore Citizen aged 62 earns $3,000/month. "
                        "What is the employee's CPF contribution?"
                    ),
                    "calculation": {
                        "age_band": "above 60 to 65",
                        "employee_rate": "9.5%",
                        "employee_contribution": "$3,000 x 9.5% = $285",
                        "take_home": "$3,000 - $285 = $2,715",
                    },
                    "outcome": (
                        "The employee contributes $285/month. Combined with "
                        "the employer's 11% ($330), total CPF is $615/month. "
                        "The lower rates for this age band help older workers "
                        "maintain higher take-home pay."
                    ),
                },
            ],
        },
        {
            "section": "CPFA-PR-RATES",
            "title": "PR Graduated Contribution Rates",
            "formal_text": (
                "The CPF Act First Schedule provides graduated contribution "
                "rates for Permanent Residents (PRs). During the 1st year "
                "of PR status, the default rates for employees aged 55 and "
                "below are: employer 4%, employee 5%, total 9% (Full "
                "Employer / Graduated Employee rates). During the 2nd year "
                "of PR status: employer 9%, employee 15%, total 24% "
                "(Graduated Employer / Full Employee rates). From the 3rd "
                "year onwards, PRs pay the same full rates as Singapore "
                "Citizens. Employers and employees may jointly apply to "
                "contribute at full SC rates from the 1st year of PR status."
            ),
            "plain_summary": (
                "New Permanent Residents pay lower CPF rates in their first "
                "two years. In the 1st year: employer 4%, employee 5% "
                "(total 9% for age 55 and below). In the 2nd year: employer "
                "9%, employee 15% (total 24%). From the 3rd year, they pay "
                "the same full rates as Singapore Citizens. Employers and "
                "employees can jointly choose to pay full rates from day one."
            ),
            "interpretation_notes": (
                "The PR year is counted from the date of PR status grant, "
                "not the employment start date. The graduated rates shown "
                "here are the default 'Full Employer / Graduated Employee' "
                "rates for the 1st year. There are also 'Graduated Employer "
                "/ Graduated Employee' rates (even lower). The joint "
                "application for full rates must be made using CPF Board "
                "Form CPF-PR and is irrevocable once approved. Most "
                "employers opt for the graduated rates to reduce initial "
                "costs. The rate differentials apply across all age bands, "
                "not just the 55-and-below band."
            ),
            "authority_level": "statute",
            "domain_name": "CPF Contribution Rates",
            "effective_date": "2024-01-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {
                        "included": ["permanent_resident_employees"],
                        "pr_status_years": "1st_and_2nd_year",
                    },
                    "notes": (
                        "Graduated rates apply to PRs in their 1st and 2nd "
                        "year of PR status. From the 3rd year, full SC rates "
                        "apply automatically."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "An employee obtains PR status on 1 March 2024. "
                        "They earn $5,000/month and are aged 30. What CPF "
                        "does the employer pay in the 1st year?"
                    ),
                    "calculation": {
                        "pr_year": "1st year",
                        "age_band": "55 and below",
                        "employer_rate": "4% (graduated)",
                        "employee_rate": "5% (graduated)",
                        "employer_contribution": "$5,000 x 4% = $200",
                        "employee_contribution": "$5,000 x 5% = $250",
                        "total_cpf": "$200 + $250 = $450",
                        "comparison_sc": "SC total would be $5,000 x 37% = $1,850",
                    },
                    "outcome": (
                        "In the 1st year, total CPF is $450/month compared "
                        "to $1,850 for a Singapore Citizen at the same age "
                        "and salary. This graduated approach helps employers "
                        "manage costs when hiring new PRs."
                    ),
                },
                {
                    "scenario": (
                        "The same PR employee enters their 2nd year of PR "
                        "status. What are the new rates?"
                    ),
                    "calculation": {
                        "pr_year": "2nd year",
                        "age_band": "55 and below",
                        "employer_rate": "9% (graduated)",
                        "employee_rate": "15% (graduated)",
                        "employer_contribution": "$5,000 x 9% = $450",
                        "employee_contribution": "$5,000 x 15% = $750",
                        "total_cpf": "$450 + $750 = $1,200",
                    },
                    "outcome": (
                        "In the 2nd year, the rates step up significantly. "
                        "Total CPF increases from $450 to $1,200/month. By "
                        "the 3rd year, the employee will pay full SC rates "
                        "($1,850/month total)."
                    ),
                },
            ],
        },
        # ====== CPF WAGE CEILINGS ======
        {
            "section": "CPFA-S13",
            "title": "Ordinary Wage Ceiling",
            "formal_text": (
                "Section 13 of the Central Provident Fund Act. CPF "
                "contributions on Ordinary Wages (OW) are subject to an OW "
                "ceiling. Effective 1 January 2026, the OW ceiling is "
                "$8,000 per month (increased from $7,400). Ordinary Wages "
                "are wages due or granted in respect of the employee's "
                "employment in a calendar month, including basic salary and "
                "fixed allowances. Any OW above the ceiling is not subject "
                "to CPF contributions."
            ),
            "plain_summary": (
                "CPF contributions are only calculated on the first $8,000 "
                "of monthly salary (the Ordinary Wage ceiling, effective "
                "1 January 2026, up from $7,400). Any salary above $8,000 "
                "does not attract CPF contributions for that month."
            ),
            "interpretation_notes": (
                "The OW ceiling was raised from $7,400 to $8,000 on "
                "1 January 2026, completing the phased increase from $6,000 "
                "(pre-Sep 2023) to $8,000. OW includes: basic salary, "
                "fixed allowances (e.g., transport, meal allowances paid "
                "monthly), and any other wages payable for the month's "
                "work. OW excludes: bonuses, commission paid quarterly/"
                "annually, and variable payments. The ceiling applies per "
                "employer — an employee with multiple employers has a "
                "separate ceiling for each."
            ),
            "authority_level": "statute",
            "domain_name": "CPF Wage Ceilings",
            "effective_date": "2026-01-01",
            "applicability_rules": [
                {
                    "rule_type": "salary_threshold",
                    "criteria_type": "ceiling",
                    "criteria_value": {
                        "ow_ceiling": 8000,
                        "basis": "ordinary_wages_monthly",
                        "effective_from": "2026-01-01",
                    },
                    "notes": (
                        "The OW ceiling of $8,000/month applies from "
                        "1 January 2026 for all CPF-liable employees."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "A Singapore Citizen aged 35 earns $10,000/month "
                        "basic salary. How much CPF is payable?"
                    ),
                    "calculation": {
                        "gross_salary": 10000,
                        "ow_ceiling": 8000,
                        "cpf_liable_ow": 8000,
                        "employer_rate": "17%",
                        "employee_rate": "20%",
                        "employer_contribution": "$8,000 x 17% = $1,360",
                        "employee_contribution": "$8,000 x 20% = $1,600",
                        "total_cpf": "$1,360 + $1,600 = $2,960",
                        "salary_not_subject_to_cpf": "$10,000 - $8,000 = $2,000",
                    },
                    "outcome": (
                        "CPF is calculated on $8,000 (the OW ceiling), not "
                        "the full $10,000. The employer pays $1,360 and the "
                        "employee contributes $1,600. The remaining $2,000 "
                        "above the ceiling is not subject to CPF."
                    ),
                },
            ],
        },
        {
            "section": "CPFA-S14",
            "title": "Additional Wage Ceiling",
            "formal_text": (
                "Section 14 of the Central Provident Fund Act. CPF "
                "contributions on Additional Wages (AW) are subject to an "
                "AW ceiling. The AW ceiling for a year is calculated as: "
                "$102,000 minus the total Ordinary Wages subject to CPF for "
                "the year. Additional Wages are wages not classified as "
                "Ordinary Wages, including annual bonuses, leave pay, and "
                "incentive payments. If the AW ceiling is exceeded, CPF is "
                "payable only up to the ceiling."
            ),
            "plain_summary": (
                "Bonuses and other non-monthly payments (Additional Wages) "
                "are subject to CPF, but only up to a yearly limit. The "
                "limit is $102,000 minus the total ordinary wages for the "
                "year. For example, if an employee's total OW for the year "
                "is $96,000 ($8,000 x 12), the AW ceiling is $6,000."
            ),
            "interpretation_notes": (
                "The $102,000 annual limit is the total CPF annual limit "
                "(OW + AW combined). The AW ceiling formula ensures that "
                "total CPF-liable wages do not exceed $102,000 in any "
                "calendar year. Common AW items: annual bonus (AWS), "
                "performance bonus, commission paid annually, leave "
                "encashment, ex-gratia payments. If an employee changes "
                "employers mid-year, the AW ceiling is calculated "
                "separately for each employer. The employer must track "
                "cumulative OW to correctly calculate the remaining AW "
                "ceiling."
            ),
            "authority_level": "statute",
            "domain_name": "CPF Wage Ceilings",
            "effective_date": "2026-01-01",
            "applicability_rules": [
                {
                    "rule_type": "salary_threshold",
                    "criteria_type": "ceiling",
                    "criteria_value": {
                        "annual_limit": 102000,
                        "aw_ceiling_formula": "$102,000 - Total OW for the year",
                        "basis": "additional_wages_annual",
                    },
                    "notes": (
                        "The AW ceiling is dynamic — it depends on the "
                        "employee's total OW for the year."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "A Singapore Citizen aged 40 earns $8,000/month OW "
                        "(at the ceiling) and receives a $5,000 annual "
                        "bonus in December."
                    ),
                    "calculation": {
                        "total_ow_for_year": "$8,000 x 12 = $96,000",
                        "aw_ceiling": "$102,000 - $96,000 = $6,000",
                        "bonus": 5000,
                        "cpf_liable_aw": "$5,000 (within ceiling)",
                        "employer_cpf_on_bonus": "$5,000 x 17% = $850",
                        "employee_cpf_on_bonus": "$5,000 x 20% = $1,000",
                    },
                    "outcome": (
                        "The full $5,000 bonus is subject to CPF because "
                        "it is within the $6,000 AW ceiling. The employer "
                        "pays an additional $850 and the employee "
                        "contributes $1,000 on the bonus."
                    ),
                },
                {
                    "scenario": ("Same employee, but the annual bonus is $10,000."),
                    "calculation": {
                        "total_ow_for_year": "$8,000 x 12 = $96,000",
                        "aw_ceiling": "$102,000 - $96,000 = $6,000",
                        "bonus": 10000,
                        "cpf_liable_aw": "$6,000 (capped at AW ceiling)",
                        "excess_not_subject_to_cpf": "$10,000 - $6,000 = $4,000",
                        "employer_cpf_on_bonus": "$6,000 x 17% = $1,020",
                        "employee_cpf_on_bonus": "$6,000 x 20% = $1,200",
                    },
                    "outcome": (
                        "Only $6,000 of the $10,000 bonus is subject to "
                        "CPF (the AW ceiling). The remaining $4,000 is not "
                        "subject to CPF contributions."
                    ),
                },
            ],
        },
        # ====== CPF ALLOCATION ======
        {
            "section": "CPFA-ALLOC",
            "title": "CPF Account Allocation Rates",
            "formal_text": (
                "The total CPF contribution is allocated across three "
                "accounts based on the employee's age. For employees aged "
                "55 and below: Ordinary Account (OA) receives 23% of wages, "
                "Special Account (SA) receives 6% of wages, and Medisave "
                "Account (MA) receives 8% of wages, totalling 37% of wages. "
                "For employees above 55 to 60: OA 11.5%, SA 4.5%, MA 13.5%, "
                "total 29.5%. For employees above 60 to 65: OA 3.5%, SA 3%, "
                "MA 14%, total 20.5%. For employees above 65 to 70: OA 1%, "
                "SA 1%, MA 12.5%, total 14.5%. For employees above 70: "
                "OA 1%, SA 1%, MA 8%, total 10%."
            ),
            "plain_summary": (
                "CPF money goes into three accounts. For workers aged 55 "
                "and below, the split is: 23% to Ordinary Account (housing, "
                "education, investment), 6% to Special Account (retirement), "
                "and 8% to Medisave (healthcare). As workers age, more goes "
                "to Medisave and less to the Ordinary Account."
            ),
            "interpretation_notes": (
                "The allocation percentages are of total wages (not of the "
                "contribution amount). OA can be used for housing, approved "
                "investments, education, and insurance. SA is locked for "
                "retirement and can only be invested in lower-risk products. "
                "MA is for healthcare expenses and MediShield Life premiums. "
                "At age 55, the SA and OA balances (above the Full "
                "Retirement Sum) are merged into a new Retirement Account "
                "(RA). The shift towards Medisave in older age bands "
                "reflects higher expected healthcare needs."
            ),
            "authority_level": "statute",
            "domain_name": "CPF Allocation",
            "effective_date": "2024-01-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {
                        "included": [
                            "singapore_citizen_employees",
                            "permanent_resident_employees",
                        ],
                    },
                    "notes": (
                        "Allocation rates apply to all CPF members. The "
                        "same allocation percentages apply to both SC and "
                        "PR employees (after full rates kick in)."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "A Singapore Citizen aged 45 earns $5,000/month. "
                        "How is the CPF allocated across accounts?"
                    ),
                    "calculation": {
                        "age_band": "55 and below",
                        "oa_rate": "23%",
                        "sa_rate": "6%",
                        "ma_rate": "8%",
                        "oa_amount": "$5,000 x 23% = $1,150",
                        "sa_amount": "$5,000 x 6% = $300",
                        "ma_amount": "$5,000 x 8% = $400",
                        "total": "$1,150 + $300 + $400 = $1,850",
                    },
                    "outcome": (
                        "Of the $1,850 total CPF: $1,150 goes to OA "
                        "(can be used for housing), $300 to SA (for "
                        "retirement), and $400 to MA (for healthcare)."
                    ),
                },
            ],
        },
        # ====== CPF COMPLIANCE ======
        {
            "section": "CPFA-S52",
            "title": "Late Payment Interest",
            "formal_text": (
                "Section 52 of the Central Provident Fund Act. Where any "
                "amount of contributions due from an employer under this "
                "Act is not paid within such period as may be prescribed, "
                "the employer shall be liable to pay interest at the rate "
                "of 18% per annum (or such other rate as the Minister may "
                "prescribe) on the amount of contributions due. In addition, "
                "the Board may impose a composition fine not exceeding "
                "$5,000 per offence. Persistent non-payment may result in "
                "prosecution, with penalties including fines up to $10,000 "
                "and/or imprisonment up to 7 years."
            ),
            "plain_summary": (
                "Employers who pay CPF late are charged 18% per annum "
                "interest on the overdue amount. The CPF Board can also "
                "impose fines of up to $5,000 per offence. Repeated "
                "non-payment can lead to criminal prosecution with heavier "
                "fines and possible imprisonment."
            ),
            "interpretation_notes": (
                "CPF contributions are due by the 14th of the following "
                "month (e.g., January contributions due by 14 February). "
                "The 18% interest rate is significantly higher than "
                "commercial rates, serving as a strong deterrent. Interest "
                "is calculated from the first day of the month following "
                "the contribution month. The CPF Board may also take civil "
                "recovery action. Directors of companies that persistently "
                "default may be held personally liable. Composition fines "
                "can be offered in lieu of prosecution for first-time or "
                "minor offences."
            ),
            "authority_level": "statute",
            "domain_name": "CPF Compliance",
            "effective_date": "1953-07-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {
                        "included": ["all_employers_of_cpf_liable_employees"],
                    },
                    "notes": (
                        "Late payment penalties apply to all employers who "
                        "are required to make CPF contributions."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "An employer with 10 employees fails to pay January "
                        "CPF contributions totalling $18,500 until 15 March "
                        "(1 month late)."
                    ),
                    "calculation": {
                        "contributions_due": 18500,
                        "days_late": 30,
                        "annual_rate": "18%",
                        "monthly_interest": "$18,500 x 18% / 12 = $277.50",
                        "composition_fine": "Up to $5,000 per offence",
                    },
                    "outcome": (
                        "The employer must pay the $18,500 in overdue "
                        "contributions plus $277.50 in interest for the "
                        "one-month delay. The CPF Board may also impose "
                        "a composition fine. Prompt payment avoids these "
                        "penalties entirely."
                    ),
                },
            ],
        },
        {
            "section": "CPFA-S58",
            "title": "Voluntary Contributions",
            "formal_text": (
                "Section 58 of the Central Provident Fund Act. Members may "
                "make voluntary contributions to their own or their family "
                "members' CPF accounts. Types of voluntary contributions "
                "include: (a) Medisave Account top-ups under the Voluntary "
                "MediSave Contribution Scheme; (b) Retirement Sum Top-Up "
                "Scheme (RSTU) — cash top-ups to own or family members' SA "
                "(below 55) or RA (55 and above); (c) Voluntary "
                "contributions to SA/MA. Tax relief of up to $8,000 per "
                "calendar year is available for cash top-ups to one's own "
                "SA/RA, and an additional $8,000 for top-ups to family "
                "members' SA/RA, for a maximum of $16,000 total tax relief."
            ),
            "plain_summary": (
                "CPF members can voluntarily top up their own or family "
                "members' CPF accounts. Cash top-ups to the Special or "
                "Retirement Account qualify for tax relief: up to $8,000 "
                "for topping up your own account, and another $8,000 for "
                "topping up family members' accounts, for a total of "
                "$16,000 in annual tax relief."
            ),
            "interpretation_notes": (
                "Voluntary contributions are separate from mandatory "
                "employer/employee contributions and do not count towards "
                "the OW or AW ceilings. The $8,000 tax relief for self "
                "top-up is a personal income tax deduction (not a refund). "
                "Family members eligible for the additional $8,000 relief: "
                "spouse, parents, parents-in-law, grandparents, "
                "grandparents-in-law, and siblings. The top-up amount is "
                "limited to the difference between the member's current "
                "SA/RA balance and the Full Retirement Sum (FRS). Voluntary "
                "MediSave contributions are subject to the Basic Healthcare "
                "Sum (BHS) limit."
            ),
            "authority_level": "statute",
            "domain_name": "CPF Compliance",
            "effective_date": "2024-01-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {
                        "included": ["all_cpf_members"],
                    },
                    "notes": (
                        "Voluntary contributions are available to all CPF "
                        "members, including self-employed persons."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "A CPF member aged 40 with a taxable income of "
                        "$80,000 makes a $8,000 cash top-up to their own SA "
                        "and a $8,000 top-up to their mother's RA."
                    ),
                    "calculation": {
                        "self_top_up": 8000,
                        "family_top_up": 8000,
                        "total_top_up": 16000,
                        "tax_relief_self": "$8,000",
                        "tax_relief_family": "$8,000",
                        "total_tax_relief": "$16,000",
                        "estimated_tax_saving": (
                            "At marginal rate of 11.5%, " "$16,000 x 11.5% = $1,840"
                        ),
                    },
                    "outcome": (
                        "The member receives $16,000 in total tax relief, "
                        "saving approximately $1,840 in income tax. The "
                        "top-ups also earn attractive CPF interest rates: "
                        "4% p.a. on SA/RA balances."
                    ),
                },
            ],
        },
    ]


# ------------------------------------------------------------------
# Cross-references
# ------------------------------------------------------------------


def _cross_references() -> list[dict]:
    return [
        {
            "source_section": "CPFA-S7",
            "target_section": "CPFA-S9",
            "relationship_type": "supplements",
            "notes": (
                "Employer contributions (Section 7) and employee "
                "contributions (Section 9) together make up the total "
                "CPF contribution for each employee."
            ),
        },
        {
            "source_section": "CPFA-S13",
            "target_section": "CPFA-S14",
            "relationship_type": "supplements",
            "notes": (
                "The OW ceiling (Section 13) and AW ceiling (Section 14) "
                "work together to cap total CPF-liable wages at $102,000 "
                "per year."
            ),
        },
        {
            "source_section": "CPFA-S7",
            "target_section": "CPFA-ALLOC",
            "relationship_type": "supplements",
            "notes": (
                "Employer and employee contributions (Section 7) are "
                "then allocated to OA, SA, and MA according to the "
                "allocation rates."
            ),
        },
        {
            "source_section": "CPFA-S7",
            "target_section": "CPFA-PR-RATES",
            "relationship_type": "related",
            "notes": (
                "PR employees have different (graduated) rate schedules "
                "in their 1st and 2nd year of PR status, distinct from "
                "the full SC rates in Section 7."
            ),
        },
        {
            "source_section": "CPFA-S7",
            "target_section": "CPFA-S52",
            "relationship_type": "related",
            "notes": (
                "Late payment penalties (Section 52) apply to mandatory "
                "employer contributions under Section 7."
            ),
        },
    ]


# ------------------------------------------------------------------
# Rate tables
# ------------------------------------------------------------------


_CPF_SOURCE_URL = (
    "https://www.cpf.gov.sg/employer/employer-obligations/" "how-much-cpf-contributions-to-pay"
)


def _rate_tables() -> list[dict]:
    return [
        # SC age 55 and below
        {
            "table_type": "cpf_contribution_rate",
            "effective_date": "2024-01-01",
            "criteria": {
                "age_band": "55_and_below",
                "citizenship_status": "SC",
            },
            "rate_value": json.dumps(
                {
                    "employer_rate": 17.0,
                    "employee_rate": 20.0,
                    "total_rate": 37.0,
                }
            ),
            "source_url": _CPF_SOURCE_URL,
        },
        # SC age 55-60
        {
            "table_type": "cpf_contribution_rate",
            "effective_date": "2024-01-01",
            "criteria": {
                "age_band": "above_55_to_60",
                "citizenship_status": "SC",
            },
            "rate_value": json.dumps(
                {
                    "employer_rate": 14.5,
                    "employee_rate": 15.0,
                    "total_rate": 29.5,
                }
            ),
            "source_url": _CPF_SOURCE_URL,
        },
        # SC age 60-65
        {
            "table_type": "cpf_contribution_rate",
            "effective_date": "2024-01-01",
            "criteria": {
                "age_band": "above_60_to_65",
                "citizenship_status": "SC",
            },
            "rate_value": json.dumps(
                {
                    "employer_rate": 11.0,
                    "employee_rate": 9.5,
                    "total_rate": 20.5,
                }
            ),
            "source_url": _CPF_SOURCE_URL,
        },
        # SC age 65-70
        {
            "table_type": "cpf_contribution_rate",
            "effective_date": "2024-01-01",
            "criteria": {
                "age_band": "above_65_to_70",
                "citizenship_status": "SC",
            },
            "rate_value": json.dumps(
                {
                    "employer_rate": 7.5,
                    "employee_rate": 7.0,
                    "total_rate": 14.5,
                }
            ),
            "source_url": _CPF_SOURCE_URL,
        },
        # SC age above 70
        {
            "table_type": "cpf_contribution_rate",
            "effective_date": "2024-01-01",
            "criteria": {
                "age_band": "above_70",
                "citizenship_status": "SC",
            },
            "rate_value": json.dumps(
                {
                    "employer_rate": 5.0,
                    "employee_rate": 5.0,
                    "total_rate": 10.0,
                }
            ),
            "source_url": _CPF_SOURCE_URL,
        },
        # PR 1st year age 55 and below (Full Employer / Graduated Employee)
        {
            "table_type": "cpf_contribution_rate",
            "effective_date": "2024-01-01",
            "criteria": {
                "age_band": "55_and_below",
                "citizenship_status": "PR",
                "pr_year": "1st_year",
            },
            "rate_value": json.dumps(
                {
                    "employer_rate": 4.0,
                    "employee_rate": 5.0,
                    "total_rate": 9.0,
                }
            ),
            "source_url": _CPF_SOURCE_URL,
        },
        # PR 2nd year age 55 and below (Graduated Employer / Graduated Employee)
        {
            "table_type": "cpf_contribution_rate",
            "effective_date": "2024-01-01",
            "criteria": {
                "age_band": "55_and_below",
                "citizenship_status": "PR",
                "pr_year": "2nd_year",
            },
            "rate_value": json.dumps(
                {
                    "employer_rate": 9.0,
                    "employee_rate": 15.0,
                    "total_rate": 24.0,
                }
            ),
            "source_url": _CPF_SOURCE_URL,
        },
        # PR 3rd year+ age 55 and below (same as SC)
        {
            "table_type": "cpf_contribution_rate",
            "effective_date": "2024-01-01",
            "criteria": {
                "age_band": "55_and_below",
                "citizenship_status": "PR",
                "pr_year": "3rd_year_onwards",
            },
            "rate_value": json.dumps(
                {
                    "employer_rate": 17.0,
                    "employee_rate": 20.0,
                    "total_rate": 37.0,
                }
            ),
            "source_url": _CPF_SOURCE_URL,
        },
    ]
