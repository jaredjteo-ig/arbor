"""Employment Act 1968 (Cap 91) — structured content bundle.

Covers:
- Part IV: hours of work, overtime, rest days
- Part X: annual leave
- Sick leave (Section 89)
- Termination and dismissal (Sections 10, 14, 14A)
- Salary provisions (Sections 20A, 21, 22, 27, 96)
- Maternity protection (Part IX, cross-ref to CDCSA)
- Employment records retention (Section 95)

All content reflects the Employment Act as at 1 January 2025,
including the Employment (Amendment) Act 2023 changes.
"""


def get_bundle() -> dict:
    """Return the full Employment Act content bundle.

    This dict is passed directly to ``KBContentPipeline.bulk_load()``.
    """
    return {
        "act": _act(),
        "domains": _domains(),
        "provisions": _provisions(),
        "cross_references": _cross_references(),
        "rate_tables": [],
    }


# ------------------------------------------------------------------
# Act
# ------------------------------------------------------------------


def _act() -> dict:
    return {
        "title": "Employment Act 1968",
        "short_name": "EA",
        "authority_type": "statute",
        "issuing_body": "Ministry of Manpower",
        "official_url": "https://sso.agc.gov.sg/Act/EmplA1968",
        "is_active": True,
    }


# ------------------------------------------------------------------
# Domains
# ------------------------------------------------------------------


def _domains() -> list[dict]:
    return [
        {
            "name": "Working Hours & Overtime",
            "description": (
                "Part IV of the Employment Act: rest days, hours of work, "
                "overtime, and shift work provisions. Applies to workmen "
                "earning up to $4,500/month and non-workmen earning up to "
                "$2,600/month basic salary."
            ),
            "sort_order": 1,
        },
        {
            "name": "Leave Entitlements",
            "description": (
                "Annual leave, sick leave, and other statutory leave "
                "provisions under the Employment Act. Applies to all "
                "employees covered by the EA."
            ),
            "sort_order": 2,
        },
        {
            "name": "Salary & Compensation",
            "description": (
                "Payment of salary, deductions, Key Employment Terms, "
                "itemised payslips, and related provisions."
            ),
            "sort_order": 3,
        },
        {
            "name": "Termination & Dismissal",
            "description": (
                "Notice periods, termination procedures, summary dismissal "
                "for misconduct, and wrongful dismissal remedies."
            ),
            "sort_order": 4,
        },
        {
            "name": "Employment Records",
            "description": (
                "Record-keeping obligations, retention periods, and "
                "documentation requirements for employers."
            ),
            "sort_order": 5,
        },
        {
            "name": "Maternity & Family",
            "description": (
                "Maternity protection under the EA and cross-references "
                "to the Child Development Co-Savings Act for government-paid "
                "maternity, paternity, and childcare leave."
            ),
            "sort_order": 6,
        },
    ]


# ------------------------------------------------------------------
# Provisions
# ------------------------------------------------------------------


def _provisions() -> list[dict]:
    return [
        # ====== WORKING HOURS & OVERTIME ======
        {
            "section": "EA-S36",
            "title": "Hours of Work",
            "formal_text": (
                "Section 36 of the Employment Act. An employee shall not be "
                "required under the contract of service to work more than "
                "8 hours in a day or 44 hours in a week. Where an employee "
                "is required to work on any day in excess of the limits "
                "prescribed, the employee shall be paid at the rate of not "
                "less than 1.5 times the hourly basic rate of pay. An "
                "employee shall not be permitted to work more than 12 hours "
                "in any one day except in specified circumstances."
            ),
            "plain_summary": (
                "Staff cannot be asked to work more than 8 hours a day or "
                "44 hours a week. If they work beyond this, they must be "
                "paid overtime at 1.5 times their hourly rate. Maximum "
                "working hours in any single day is 12 hours."
            ),
            "interpretation_notes": (
                "The 44-hour weekly limit can be averaged over a continuous "
                "period of 2 weeks (i.e. 88 hours over 2 weeks) if agreed "
                "by both parties. Meal breaks of at least 45 minutes must "
                "be given after 6 consecutive hours of work. For shift "
                "workers, the 44-hour limit can be averaged over a "
                "continuous period of 3 weeks."
            ),
            "authority_level": "statute",
            "domain_name": "Working Hours & Overtime",
            "effective_date": "1968-08-01",
            "applicability_rules": [
                {
                    "rule_type": "salary_threshold",
                    "criteria_type": "maximum",
                    "criteria_value": {
                        "workman_limit": 4500,
                        "non_workman_limit": 2600,
                        "basis": "basic_monthly_salary",
                    },
                    "notes": (
                        "Part IV applies only to workmen earning up to "
                        "$4,500/month and non-workmen earning up to "
                        "$2,600/month basic salary."
                    ),
                },
                {
                    "rule_type": "worker_type",
                    "criteria_type": "exclusion",
                    "criteria_value": {
                        "excluded": [
                            "domestic_worker",
                            "seafarer",
                            "statutory_board_employee",
                            "government_employee",
                        ]
                    },
                    "notes": "Domestic workers, seafarers, and public servants are excluded from the EA.",
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "A non-workman office employee earning $2,400/month basic "
                        "salary is asked to work 10 hours on a Monday."
                    ),
                    "calculation": {
                        "regular_hours": 8,
                        "overtime_hours": 2,
                        "hourly_rate": "2400 / (26 x 8) = $11.54",
                        "ot_rate": "$11.54 x 1.5 = $17.31",
                        "ot_pay": "$17.31 x 2 = $34.62",
                    },
                    "outcome": (
                        "The employee is entitled to $34.62 in overtime pay for "
                        "the 2 hours of overtime. The employer must pay this on "
                        "top of the normal day's salary."
                    ),
                },
                {
                    "scenario": (
                        "A manager earning $5,000/month basic salary works 10 "
                        "hours on a weekday."
                    ),
                    "calculation": {
                        "note": "Part IV does not apply as salary exceeds $2,600 for non-workmen.",
                    },
                    "outcome": (
                        "Part IV does not apply. The manager is not entitled to "
                        "statutory overtime pay. However, any overtime "
                        "compensation would depend on the employment contract."
                    ),
                },
            ],
        },
        {
            "section": "EA-S37",
            "title": "Overtime",
            "formal_text": (
                "Section 37 of the Employment Act. An employee shall not be "
                "required to work overtime for more than 72 hours in a month. "
                "The Minister may by notification in the Gazette vary the "
                "maximum permissible overtime hours. For the avoidance of doubt, "
                "the overtime rate of pay is not less than 1.5 times the hourly "
                "basic rate of pay regardless of the basis of calculation of the "
                "employee's rate of pay."
            ),
            "plain_summary": (
                "The maximum overtime allowed is 72 hours per month. Overtime "
                "must always be paid at least 1.5 times the normal hourly rate, "
                "no matter how the employee's salary is calculated (monthly, "
                "daily, or hourly)."
            ),
            "interpretation_notes": (
                "The 72-hour monthly cap on overtime is a hard statutory limit. "
                "Employers who require more must apply to MOM for an overtime "
                "exemption. For salary calculations: hourly rate = "
                "(monthly basic salary) / (26 days x 8 hours) for monthly-rated "
                "employees. The overtime rate applies from the first hour beyond "
                "the contractual or 8-hour daily limit."
            ),
            "authority_level": "statute",
            "domain_name": "Working Hours & Overtime",
            "effective_date": "1968-08-01",
            "applicability_rules": [
                {
                    "rule_type": "salary_threshold",
                    "criteria_type": "maximum",
                    "criteria_value": {
                        "workman_limit": 4500,
                        "non_workman_limit": 2600,
                        "basis": "basic_monthly_salary",
                    },
                    "notes": "Same Part IV salary cap as Section 36.",
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "A factory workman earning $3,000/month basic salary "
                        "works 80 hours of overtime in March."
                    ),
                    "calculation": {
                        "hourly_rate": "3000 / (26 x 8) = $14.42",
                        "ot_rate": "$14.42 x 1.5 = $21.63",
                        "max_claimable_ot_hours": 72,
                        "ot_pay": "$21.63 x 72 = $1,557.36",
                    },
                    "outcome": (
                        "The employer is in breach for requiring more than 72 "
                        "hours of overtime. The employee is entitled to OT pay "
                        "for all 80 hours worked, but the employer faces "
                        "penalties for exceeding the statutory cap."
                    ),
                },
            ],
        },
        {
            "section": "EA-S36(4)",
            "title": "Rest Day",
            "formal_text": (
                "Section 36(4)-(6) of the Employment Act. Every employee shall "
                "be allowed in each week a rest day without pay. The rest day "
                "shall be a Sunday or such other day as is specified in the "
                "contract of service or as mutually agreed. Work done on a rest "
                "day: at the request of the employer — at 2 times the basic rate "
                "of pay if the work exceeds half the normal daily hours, or 1 "
                "day's pay if half or less. At the request of the employee — at "
                "1.5 times the basic rate."
            ),
            "plain_summary": (
                "Every employee must get at least 1 rest day per week. If the "
                "employer asks the employee to work on a rest day, the pay rates "
                "are: up to half day = 1 day's pay, more than half day = 2 days' "
                "pay. If the employee requests to work, the rate is 1.5 times "
                "the basic rate."
            ),
            "interpretation_notes": (
                "The rest day is without pay for daily-rated workers but "
                "monthly-rated workers' salary already includes rest days. "
                "The rest day does not have to be Sunday — it can be any day "
                "agreed in the contract. Employers must give at least 48 hours' "
                "notice before requiring work on a rest day."
            ),
            "authority_level": "statute",
            "domain_name": "Working Hours & Overtime",
            "effective_date": "1968-08-01",
            "applicability_rules": [
                {
                    "rule_type": "salary_threshold",
                    "criteria_type": "maximum",
                    "criteria_value": {
                        "workman_limit": 4500,
                        "non_workman_limit": 2600,
                        "basis": "basic_monthly_salary",
                    },
                    "notes": "Rest day pay rates under Part IV apply to the same salary-capped group.",
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "A shop assistant earning $2,200/month is asked by the "
                        "employer to work 9 hours on her Sunday rest day."
                    ),
                    "calculation": {
                        "daily_rate": "2200 / 26 = $84.62",
                        "hours_worked": 9,
                        "normal_hours": 8,
                        "pay_for_rest_day": "$84.62 x 2 = $169.24 (more than half day)",
                        "overtime_hours": 1,
                        "ot_rate": "(2200 / (26 x 8)) x 1.5 = $15.87",
                        "total": "$169.24 + $15.87 = $185.11",
                    },
                    "outcome": (
                        "The employee gets 2 days' pay ($169.24) for working "
                        "more than half a day on a rest day at the employer's "
                        "request, plus 1 hour of overtime at 1.5x rate ($15.87). "
                        "Total additional pay: $185.11."
                    ),
                },
            ],
        },
        # ====== LEAVE ENTITLEMENTS ======
        {
            "section": "EA-S88A",
            "title": "Annual Leave",
            "formal_text": (
                "Section 88A of the Employment Act. An employee who has served "
                "an employer for not less than 3 months shall be entitled to "
                "annual leave of 7 days for the first 12 months of continuous "
                "service, with an additional 1 day for every subsequent 12 months "
                "of continuous service, up to a maximum of 14 days. An employee "
                "who has not completed 12 months of continuous service is entitled "
                "to annual leave on a pro-rata basis."
            ),
            "plain_summary": (
                "After 3 months of service, employees are entitled to paid "
                "annual leave: 7 days in the first year, increasing by 1 day "
                "each year up to a maximum of 14 days. If an employee has not "
                "completed a full year, leave is calculated proportionally."
            ),
            "interpretation_notes": (
                "Annual leave entitlement by year: Year 1 = 7 days, Year 2 = 8, "
                "Year 3 = 9, Year 4 = 10, Year 5 = 11, Year 6 = 12, Year 7 = 13, "
                "Year 8+ = 14 days. Pro-ration formula: (months completed / 12) x "
                "annual entitlement, rounded to nearest half-day. Employers may "
                "grant more than the statutory minimum. Unused annual leave may "
                "be carried forward or encashed, subject to the employment "
                "contract. Annual leave cannot be forfeited by the employer."
            ),
            "authority_level": "statute",
            "domain_name": "Leave Entitlements",
            "effective_date": "1968-08-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {
                        "included": ["all_ea_covered_employees"],
                        "min_service": "3_months",
                    },
                    "notes": (
                        "Annual leave applies to all employees covered by the EA "
                        "with at least 3 months of service. No salary cap."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "A new employee joins on 1 March and wants to know their "
                        "annual leave entitlement as of 31 December (10 months)."
                    ),
                    "calculation": {
                        "months_completed": 10,
                        "annual_entitlement": 7,
                        "pro_rated": "(10 / 12) x 7 = 5.83, rounded to 6 days",
                    },
                    "outcome": (
                        "The employee is entitled to 6 days of annual leave "
                        "(pro-rated for 10 months of service in the first year)."
                    ),
                },
                {
                    "scenario": (
                        "An employee in their 5th year of service wants to know "
                        "their annual leave."
                    ),
                    "calculation": {
                        "year_of_service": 5,
                        "entitlement": "7 + (5-1) = 11 days",
                    },
                    "outcome": "The employee is entitled to 11 days of annual leave.",
                },
            ],
        },
        {
            "section": "EA-S89",
            "title": "Sick Leave",
            "formal_text": (
                "Section 89 of the Employment Act. An employee who has served an "
                "employer for not less than 6 months shall be entitled to paid "
                "sick leave as follows: (a) 14 days in each year if no "
                "hospitalisation is necessary; or (b) the aggregate of 14 days "
                "plus 60 days if hospitalisation is necessary, totalling up to "
                "60 days of paid hospitalisation leave (inclusive of the 14 "
                "outpatient days). The employee must be examined by a medical "
                "practitioner within 48 hours and must inform or attempt to "
                "inform the employer of the sick leave within 48 hours."
            ),
            "plain_summary": (
                "After 6 months of service, employees get 14 days of paid "
                "outpatient sick leave per year. If hospitalisation is needed, "
                "they get up to 60 days total (including the 14 outpatient days). "
                "A valid medical certificate is required."
            ),
            "interpretation_notes": (
                "Sick leave entitlement is pro-rated for employees with less than "
                "6 months service: 3 months = 5 outpatient + 15 hospital days, "
                "4 months = 8 + 30, 5 months = 11 + 45. The MC must be from a "
                "company-approved doctor, government doctor, or dentist (dental "
                "only). If the employee sees a non-approved doctor, the employer "
                "is not obliged to accept the MC. Sick leave pay is at the "
                "employee's gross rate of pay."
            ),
            "authority_level": "statute",
            "domain_name": "Leave Entitlements",
            "effective_date": "1968-08-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {
                        "included": ["all_ea_covered_employees"],
                        "min_service": "6_months_for_full",
                        "pro_rated_from": "3_months",
                    },
                    "notes": (
                        "Sick leave applies to all EA-covered employees. Full "
                        "entitlement after 6 months, pro-rated from 3 months."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "An employee with 4 months of service falls ill and "
                        "needs 10 days of outpatient sick leave."
                    ),
                    "calculation": {
                        "months_of_service": 4,
                        "outpatient_entitlement": 8,
                        "days_requested": 10,
                        "paid_days": 8,
                        "unpaid_days": 2,
                    },
                    "outcome": (
                        "The employee is entitled to 8 days of paid outpatient "
                        "sick leave (pro-rated for 4 months). The remaining 2 "
                        "days may be unpaid unless the employer has a more "
                        "generous policy."
                    ),
                },
            ],
        },
        # ====== TERMINATION & DISMISSAL ======
        {
            "section": "EA-S10",
            "title": "Notice of Termination",
            "formal_text": (
                "Section 10 of the Employment Act. Either party may terminate a "
                "contract of service at any time by giving notice. The length of "
                "notice shall be the same for both employer and employee and "
                "shall be determined by any provision in the contract or, in the "
                "absence of such provision: (a) 1 day's notice if employed for "
                "less than 26 weeks; (b) 1 week's notice if employed for 26 "
                "weeks or more but less than 2 years; (c) 2 weeks' notice if "
                "employed for 2 years or more but less than 5 years; (d) 4 "
                "weeks' notice if employed for 5 years or more."
            ),
            "plain_summary": (
                "Either party can end the employment by giving notice. The notice "
                "period depends on how long the employee has worked: less than 26 "
                "weeks = 1 day, 26 weeks to 2 years = 1 week, 2 to 5 years = 2 "
                "weeks, 5 years or more = 4 weeks. The contract can specify a "
                "different period but it must be the same for both sides."
            ),
            "interpretation_notes": (
                "The contractual notice period overrides statutory minimums — "
                "many employers specify 1 month notice in the contract. The "
                "notice period must be the same for both employer and employee. "
                "Notice must start on the day it is given and includes all "
                "calendar days. Either party can pay salary in lieu of notice "
                "(Section 11)."
            ),
            "authority_level": "statute",
            "domain_name": "Termination & Dismissal",
            "effective_date": "1968-08-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {"included": ["all_ea_covered_employees"]},
                    "notes": "Applies to all EA-covered employees regardless of salary.",
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "An employee has worked for 3 years. The contract is "
                        "silent on the notice period. The employer wants to "
                        "terminate the employment."
                    ),
                    "calculation": {
                        "years_of_service": 3,
                        "statutory_notice": "2 weeks (2-5 years band)",
                        "contractual_notice": "None specified",
                        "applicable_notice": "2 weeks",
                    },
                    "outcome": (
                        "The employer must give 2 weeks' notice or pay 2 weeks' "
                        "salary in lieu of notice. The employee also needs to "
                        "give 2 weeks' notice if they resign."
                    ),
                },
            ],
        },
        {
            "section": "EA-S14",
            "title": "Summary Dismissal for Misconduct",
            "formal_text": (
                "Section 14 of the Employment Act. An employer may dismiss an "
                "employee without notice on the grounds of misconduct after due "
                "inquiry. The employer must conduct an inquiry before making the "
                "decision. If an employee considers that the dismissal is without "
                "just cause or excuse, the employee may within one month of the "
                "dismissal make representations in writing to the Minister. The "
                "employer may, instead of dismissing the employee, instantly "
                "downgrade the employee or suspend without pay for a period not "
                "exceeding 1 week."
            ),
            "plain_summary": (
                "An employer can dismiss an employee immediately (without notice) "
                "for serious misconduct, but only after conducting a fair "
                "investigation. Alternatives to dismissal include a downgrade or "
                "suspension without pay for up to 1 week."
            ),
            "interpretation_notes": (
                "Due inquiry means a proper internal investigation. MOM recommends: "
                "(1) inform the employee of the allegation in writing, (2) give "
                "the employee a chance to respond, (3) consider the response "
                "fairly before deciding. During the investigation the employee "
                "may be suspended with at least half pay for up to 1 week. If "
                "the inquiry is not concluded within 1 week, the employee must "
                "be reinstated with full pay pending the outcome. Misconduct "
                "examples: theft, dishonesty, fighting, substance abuse at work, "
                "wilful insubordination."
            ),
            "authority_level": "statute",
            "domain_name": "Termination & Dismissal",
            "effective_date": "1968-08-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {"included": ["all_ea_covered_employees"]},
                    "notes": "Applies to all EA-covered employees.",
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "An SME owner catches an employee stealing cash from the "
                        "register on CCTV."
                    ),
                    "calculation": {
                        "step_1": "Suspend employee with at least half pay",
                        "step_2": "Conduct inquiry within 1 week",
                        "step_3": "Present evidence and give employee chance to respond",
                        "step_4": "If misconduct confirmed, may dismiss without notice",
                    },
                    "outcome": (
                        "The employer can dismiss the employee without notice "
                        "after conducting the inquiry. If the employer skips the "
                        "inquiry, the dismissal may be challenged as wrongful."
                    ),
                },
            ],
        },
        {
            "section": "EA-S14A",
            "title": "Wrongful Dismissal",
            "formal_text": (
                "Section 14A of the Employment Act (as amended). An employee who "
                "considers that he has been dismissed without just cause or "
                "excuse by his employer may, within one month of the dismissal, "
                "make a claim to the Employment Claims Tribunals. The Tribunal "
                "may order reinstatement or compensation. Wrongful dismissal "
                "includes dismissal with notice but without valid reason, "
                "constructive dismissal, and dismissal on discriminatory grounds."
            ),
            "plain_summary": (
                "Employees who believe they were unfairly fired can file a claim "
                "with the Employment Claims Tribunals within 1 month. The "
                "Tribunal can order the employer to take the employee back or "
                "pay compensation."
            ),
            "interpretation_notes": (
                "Wrongful dismissal claims are available to all EA-covered "
                "employees (since April 2019 amendments). Constructive dismissal "
                "— where the employer's conduct forces the employee to resign — "
                "is also covered. Employees must first attempt mediation at TADM "
                "(Tripartite Alliance for Dispute Management). The claim must be "
                "filed within 1 month of the last day of employment, or 1 month "
                "of the constructive dismissal being known. Maximum compensation: "
                "ECT may order up to $20,000 (union members up to $30,000)."
            ),
            "authority_level": "statute",
            "domain_name": "Termination & Dismissal",
            "effective_date": "2019-04-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {"included": ["all_ea_covered_employees"]},
                    "notes": (
                        "Available to all EA-covered employees since April 2019. "
                        "Previously limited to non-PMEs."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "An employee earning $8,000/month is dismissed with 1 "
                        "month notice but believes the real reason is her "
                        "pregnancy announcement."
                    ),
                    "calculation": {
                        "claim_deadline": "1 month from last day of employment",
                        "process": "TADM mediation first, then ECT if unresolved",
                        "max_compensation": "$20,000 (or $30,000 for union members)",
                    },
                    "outcome": (
                        "The employee can file a wrongful dismissal claim. "
                        "Dismissal related to pregnancy is prohibited under the "
                        "EA (Section 81) and may constitute discriminatory "
                        "dismissal. She should file within 1 month."
                    ),
                },
            ],
        },
        # ====== SALARY & COMPENSATION ======
        {
            "section": "EA-S20A",
            "title": "Key Employment Terms",
            "formal_text": (
                "Section 20A of the Employment Act. An employer shall, within 14 "
                "days of employing an employee, provide the employee with a "
                "written document containing the Key Employment Terms. The KET "
                "must include: (a) full name of the employer; (b) full name of "
                "the employee; (c) job title and main duties; (d) start date; "
                "(e) duration of employment (if fixed-term); (f) working "
                "arrangements (days, hours); (g) salary period and basic salary; "
                "(h) fixed allowances; (i) fixed deductions; (j) overtime rate; "
                "(k) other salary-related components; (l) type of leave and "
                "entitlement; (m) other medical benefits; (n) probation period; "
                "(o) notice period."
            ),
            "plain_summary": (
                "Employers must give new employees a written document listing "
                "all key employment terms within 14 days of starting work. This "
                "must cover salary, working hours, leave, notice period, and "
                "other essential conditions."
            ),
            "interpretation_notes": (
                "The KET requirement applies to all employees covered by the EA "
                "who are employed for 14 days or more. The KET does not need to "
                "be a separate document — it can be part of the employment "
                "contract. Changes to any KET must be notified in writing. "
                "Failure to provide KET: fine up to $5,000 (first offence), "
                "$10,000 (subsequent). The KET obligation started 1 April 2016."
            ),
            "authority_level": "statute",
            "domain_name": "Salary & Compensation",
            "effective_date": "2016-04-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {
                        "included": ["all_ea_covered_employees"],
                        "min_duration": "14_days",
                    },
                    "notes": (
                        "Applies to all EA-covered employees employed for 14 "
                        "days or more. No salary cap."
                    ),
                },
            ],
        },
        {
            "section": "EA-S21",
            "title": "Payment of Salary Timeline",
            "formal_text": (
                "Section 21 of the Employment Act. Salary shall be paid before "
                "the expiry of the 7th day after the last day of the salary "
                "period. Overtime pay shall be paid within 14 days after the "
                "last day of the salary period."
            ),
            "plain_summary": (
                "Employers must pay salaries within 7 days after the end of the "
                "salary period (e.g., by 7 February for January salary). "
                "Overtime pay must be paid within 14 days."
            ),
            "interpretation_notes": (
                "The salary period is usually one month. If the salary period is "
                "not specified, it defaults to one month. Upon termination: all "
                "outstanding salary must be paid on the last day of work (if "
                "employee is terminated) or within 7 days (if employee resigns "
                "with due notice). Penalties for late payment: fine up to $5,000 "
                "per offence, and MOM may prosecute."
            ),
            "authority_level": "statute",
            "domain_name": "Salary & Compensation",
            "effective_date": "1968-08-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {"included": ["all_ea_covered_employees"]},
                    "notes": "Applies to all EA-covered employees.",
                },
            ],
        },
        {
            "section": "EA-S22",
            "title": "Deduction Limits",
            "formal_text": (
                "Section 22 of the Employment Act. No deduction shall be made "
                "from the salary of an employee other than those authorised by "
                "this Act, and the total deductions shall not exceed 50% of the "
                "salary payable to the employee in any one salary period. "
                "Authorised deductions include: absence from work, damage or "
                "loss of goods/money (with the employee's written consent and "
                "subject to limits), accommodation and amenities, recovery of "
                "advances or loans, income tax, and CPF contributions."
            ),
            "plain_summary": (
                "Employers can only deduct from salary what the law allows, and "
                "the total deductions cannot exceed 50% of the employee's pay "
                "in any salary period. Common allowed deductions: CPF, income "
                "tax, approved absences, and agreed loan repayments."
            ),
            "interpretation_notes": (
                "Deductions for damage or loss require: (1) the employee's "
                "written consent, (2) a limit per incident (the lesser of one "
                "day's salary or the actual damage/loss), (3) proper inquiry "
                "into the employee's responsibility. The 50% cap does not "
                "include CPF contributions or income tax deductions. Illegal "
                "deductions: penalties, fines not authorised by contract, "
                "deductions for tools or uniforms required for the job."
            ),
            "authority_level": "statute",
            "domain_name": "Salary & Compensation",
            "effective_date": "1968-08-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {"included": ["all_ea_covered_employees"]},
                    "notes": "Applies to all EA-covered employees.",
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "An employee earning $2,000/month accidentally breaks "
                        "company equipment worth $500. Can the employer deduct "
                        "the full $500?"
                    ),
                    "calculation": {
                        "one_days_salary": "2000 / 26 = $76.92",
                        "actual_damage": 500,
                        "max_deduction_per_incident": "$76.92 (lesser of one day's salary or actual damage)",
                        "total_max_deduction": "50% of $2000 = $1000 (cap)",
                    },
                    "outcome": (
                        "No. The employer can only deduct $76.92 (one day's "
                        "salary, being less than the $500 damage) with the "
                        "employee's written consent. Even if the employee "
                        "agrees, the total deductions cannot exceed $1,000 "
                        "(50% of salary) in any pay period."
                    ),
                },
            ],
        },
        {
            "section": "EA-S11",
            "title": "Salary in Lieu of Notice",
            "formal_text": (
                "Section 11 of the Employment Act. Either party to a contract "
                "of service may at any time give notice of termination and "
                "either party may waive the right to notice by paying the "
                "other party an amount equal to the salary at the gross rate "
                "of pay for the period of the notice. For the purposes of "
                "this section, salary shall be calculated at the gross rate "
                "of pay."
            ),
            "plain_summary": (
                "Instead of serving the notice period, either the employer or "
                "employee can pay salary equivalent to the notice period. The "
                "payment is based on gross salary, not just basic salary."
            ),
            "interpretation_notes": (
                "Salary in lieu of notice is calculated at the gross rate — "
                "this includes basic salary plus all fixed allowances. For "
                "employees who resign without serving notice, the employer may "
                "recover the amount from any outstanding salary. Salary in lieu "
                "of notice is not subject to CPF contributions. Tax treatment: "
                "generally taxable for the recipient."
            ),
            "authority_level": "statute",
            "domain_name": "Termination & Dismissal",
            "effective_date": "1968-08-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {"included": ["all_ea_covered_employees"]},
                    "notes": "Applies to all EA-covered employees.",
                },
            ],
        },
        {
            "section": "EA-S96",
            "title": "Itemised Payslips",
            "formal_text": (
                "Section 96 of the Employment Act. An employer shall, at the "
                "time of payment of salary, give to the employee an itemised "
                "pay slip for each salary period. The pay slip must contain: "
                "(a) name of employer; (b) name of employee; (c) date of "
                "payment; (d) basic salary, for the salary period; (e) start "
                "and end date of the salary period; (f) allowances paid; "
                "(g) any additional payment (overtime, bonus, rest day, public "
                "holiday pay); (h) deductions made; (i) net salary paid."
            ),
            "plain_summary": (
                "Employers must give employees a detailed payslip every time "
                "they are paid. The payslip must show the breakdown of salary, "
                "allowances, overtime, deductions, and net pay."
            ),
            "interpretation_notes": (
                "Payslips can be in electronic form (email, online portal). "
                "They must be given at the time of salary payment or within 3 "
                "working days. Employers must keep records of payslips for 2 "
                "years after the employee leaves. Penalties for non-compliance: "
                "fine up to $5,000 (first offence). The requirement has been in "
                "effect since 1 April 2016."
            ),
            "authority_level": "statute",
            "domain_name": "Salary & Compensation",
            "effective_date": "2016-04-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {"included": ["all_ea_covered_employees"]},
                    "notes": "Applies to all EA-covered employees.",
                },
            ],
        },
        # ====== EMPLOYMENT RECORDS ======
        {
            "section": "EA-S95",
            "title": "Employment Records Retention",
            "formal_text": (
                "Section 95 of the Employment Act. Every employer shall keep "
                "a register of employees containing: (a) the employee's name, "
                "sex, date of birth, NRIC number or FIN; (b) date of "
                "commencement; (c) date of cessation (if applicable); "
                "(d) occupation; (e) terms and conditions of employment; "
                "(f) salary records; (g) leave records. The records must be "
                "kept for a period of at least 2 years after the employee "
                "ceases employment."
            ),
            "plain_summary": (
                "Employers must keep records of all employees' personal details, "
                "employment terms, salary, and leave. These records must be kept "
                "for at least 2 years after the employee leaves the company."
            ),
            "interpretation_notes": (
                "Records can be in electronic or paper form. Current employees' "
                "records: must be kept and available for inspection at all times. "
                "Former employees: retain for at least 2 years. MOM may request "
                "access during inspections. In practice, employers should "
                "retain records for at least 5 years to cover potential claims "
                "and tax audits. Penalty for failure to keep records: fine up "
                "to $5,000."
            ),
            "authority_level": "statute",
            "domain_name": "Employment Records",
            "effective_date": "1968-08-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {"included": ["all_ea_covered_employees"]},
                    "notes": "Applies to all employers of EA-covered employees.",
                },
            ],
        },
        # ====== MATERNITY & FAMILY ======
        {
            "section": "EA-Part-IX",
            "title": "Maternity Protection",
            "formal_text": (
                "Part IX (Sections 76-84) of the Employment Act. A female "
                "employee is entitled to maternity leave of 8 weeks (including "
                "the day of delivery). The employer shall not dismiss a female "
                "employee during her absence on maternity leave or give notice "
                "of dismissal on a date that falls within the maternity leave "
                "period. An employer who contravenes this commits an offence. "
                "For eligibility for government-paid maternity leave (16 weeks), "
                "see the Child Development Co-Savings Act."
            ),
            "plain_summary": (
                "Female employees get at least 8 weeks of employer-paid maternity "
                "leave under the EA. They cannot be fired during maternity leave. "
                "Eligible mothers can get up to 16 weeks of government-paid "
                "maternity leave under a separate law (CDCSA)."
            ),
            "interpretation_notes": (
                "EA maternity leave (8 weeks): paid by employer for all "
                "EA-covered employees. CDCSA maternity leave (16 weeks): first "
                "8 weeks paid by employer, last 8 weeks paid by government. "
                "Eligibility for government-paid portion: (1) child must be a "
                "Singapore citizen, (2) employee must have served employer for "
                "at least 3 months. The employee must notify the employer at "
                "least 1 week before commencing maternity leave. Dismissal "
                "during maternity leave is an offence with fine up to $5,000 "
                "and/or imprisonment up to 6 months."
            ),
            "authority_level": "statute",
            "domain_name": "Maternity & Family",
            "effective_date": "1968-08-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {
                        "included": ["female_ea_covered_employees"],
                        "min_service": "3_months_for_paid_leave",
                    },
                    "notes": (
                        "EA maternity protection applies to all female EA-covered "
                        "employees. Minimum 3 months service for paid maternity "
                        "leave."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "A female employee earning $3,500/month has worked for "
                        "the company for 2 years. She is expecting her first "
                        "child who will be a Singapore citizen."
                    ),
                    "calculation": {
                        "ea_maternity_leave": "8 weeks employer-paid",
                        "cdcsa_gov_paid": "8 weeks government-paid",
                        "total": "16 weeks",
                        "gov_cap": "Government reimburses up to $10,000 per 4-week period",
                        "employer_cost": "8 weeks x $3,500/4.33 = approximately $6,466",
                    },
                    "outcome": (
                        "The employee is entitled to 16 weeks of maternity leave. "
                        "First 8 weeks: paid by the employer. Last 8 weeks: paid "
                        "by the government (employer pays first, then claims back). "
                        "The employer cannot dismiss her during this period."
                    ),
                },
            ],
        },
        # ====== PUBLIC HOLIDAYS ======
        {
            "section": "EA-S88",
            "title": "Public Holidays",
            "formal_text": (
                "Section 88 of the Employment Act. Every employee shall be "
                "entitled to a paid holiday on each of the 11 gazetted public "
                "holidays: New Year's Day, Chinese New Year (2 days), Good "
                "Friday, Hari Raya Puasa, Labour Day, Vesak Day, Hari Raya "
                "Haji, National Day, Deepavali, Christmas Day. If the employee "
                "is required to work on a public holiday, the employee shall "
                "be paid an extra day's salary at the basic rate of pay for "
                "that day, in addition to the gross rate of pay payable for "
                "that day."
            ),
            "plain_summary": (
                "All employees are entitled to 11 paid public holidays per year. "
                "If they work on a public holiday, they get an extra day's pay "
                "on top of their normal salary for that day."
            ),
            "interpretation_notes": (
                "If a public holiday falls on a rest day, the next working day "
                "becomes a paid holiday. For monthly-rated employees, the "
                "public holiday is already included in their monthly salary — "
                "if they work, they get 1 extra day's pay. For daily-rated "
                "employees, they get paid for the public holiday even though "
                "they do not work (gross rate). Working on a public holiday "
                "is at the employer's request unless otherwise agreed in the "
                "contract. Part IV employees working on a PH also get OT "
                "rates (1.5x) for hours exceeding normal daily working hours."
            ),
            "authority_level": "statute",
            "domain_name": "Leave Entitlements",
            "effective_date": "1968-08-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {"included": ["all_ea_covered_employees"]},
                    "notes": "All EA-covered employees are entitled to 11 gazetted public holidays.",
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "A monthly-rated employee earning $2,600/month works on "
                        "National Day (a public holiday)."
                    ),
                    "calculation": {
                        "daily_rate": "2600 / 26 = $100",
                        "normal_ph_pay": "already included in monthly salary",
                        "extra_day_pay": "$100",
                        "total_additional": "$100",
                    },
                    "outcome": (
                        "The employee receives their normal monthly salary plus "
                        "an extra $100 (one day's basic pay) for working on the "
                        "public holiday."
                    ),
                },
            ],
        },
        # ====== EA COVERAGE ======
        {
            "section": "EA-S2",
            "title": "Application of the Employment Act",
            "formal_text": (
                "Section 2 of the Employment Act. The Act applies to all "
                "employees (including managers and executives, since the "
                "Employment (Amendment) Act 2018 effective 1 April 2019) "
                "except: (a) any person employed in a managerial or executive "
                "position with a monthly basic salary exceeding $4,500 (for "
                "Part IV only); (b) domestic workers; (c) seafarers; (d) "
                "employees of the Government or any statutory body."
            ),
            "plain_summary": (
                "The Employment Act covers almost all employees in Singapore, "
                "including managers and executives (since April 2019). The main "
                "exceptions are domestic workers, seafarers, and government "
                "employees. Some provisions (working hours, overtime) only apply "
                "to lower-salary workers."
            ),
            "interpretation_notes": (
                "Since April 2019, the EA covers all employees regardless of "
                "salary for core protections: salary payment, notice period, "
                "wrongful dismissal, public holidays, sick leave, and annual "
                "leave. Part IV (hours/overtime/rest days) still has salary "
                "caps: workmen up to $4,500, non-workmen up to $2,600. "
                '"Employee" does not include independent contractors — the '
                "test is control over how, when, and where work is done, not "
                "just labelling."
            ),
            "authority_level": "statute",
            "domain_name": "Working Hours & Overtime",
            "effective_date": "2019-04-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "general_coverage",
                    "criteria_value": {
                        "covered": [
                            "all_employees",
                            "managers_and_executives",
                            "part_time_employees",
                            "contract_employees",
                            "foreign_employees_with_valid_pass",
                        ],
                        "excluded": [
                            "domestic_workers",
                            "seafarers",
                            "government_employees",
                            "statutory_board_employees",
                        ],
                    },
                    "notes": "Comprehensive coverage since April 2019 amendments.",
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
            "source_section": "EA-S36",
            "target_section": "EA-S37",
            "relationship_type": "supplements",
            "notes": "Section 36 sets working hour limits; Section 37 governs overtime beyond those limits.",
        },
        {
            "source_section": "EA-S36",
            "target_section": "EA-S36(4)",
            "relationship_type": "supplements",
            "notes": "Section 36(4) specifies rest day provisions within the working hours framework.",
        },
        {
            "source_section": "EA-S10",
            "target_section": "EA-S11",
            "relationship_type": "supplements",
            "notes": "Section 10 sets notice periods; Section 11 allows salary in lieu of notice.",
        },
        {
            "source_section": "EA-S14",
            "target_section": "EA-S14A",
            "relationship_type": "supplements",
            "notes": "Section 14 covers summary dismissal; Section 14A provides wrongful dismissal remedies.",
        },
        {
            "source_section": "EA-S10",
            "target_section": "EA-S14",
            "relationship_type": "related",
            "notes": "Notice termination vs. summary dismissal — two different termination paths.",
        },
        {
            "source_section": "EA-S21",
            "target_section": "EA-S96",
            "relationship_type": "supplements",
            "notes": "Section 21 requires timely payment; Section 96 requires itemised documentation of that payment.",
        },
        {
            "source_section": "EA-S20A",
            "target_section": "EA-S21",
            "relationship_type": "supplements",
            "notes": "KET specifies salary terms; Section 21 enforces payment timelines.",
        },
        {
            "source_section": "EA-Part-IX",
            "target_section": "EA-S14A",
            "relationship_type": "related",
            "notes": "Dismissal during maternity leave is an offence and may constitute wrongful dismissal.",
        },
        {
            "source_section": "EA-S88A",
            "target_section": "EA-S89",
            "relationship_type": "related",
            "notes": "Annual leave and sick leave are separate statutory entitlements that cannot be used interchangeably.",
        },
    ]
