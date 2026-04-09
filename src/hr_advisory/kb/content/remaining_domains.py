"""Remaining regulatory domains -- structured content bundle.

Covers:
- Family Leave (CDCSA): Government-paid maternity, paternity, shared parental,
  childcare, infant care, adoption leave
- Workplace Safety & Health (WSHA): WSH Act obligations, incident reporting,
  bizSAFE programme
- Retirement & Re-employment (RRA): Retirement age, re-employment obligations,
  Employment Assistance Payment
- Work Injury Compensation (WICA): Employer liability, compulsory insurance
- Tax Obligations (IRAS): IR8A, IR8S, tax clearance, benefits-in-kind
- Data Protection (PDPA): Employee data obligations

The primary act is the Child Development Co-Savings Act (CDCSA).
Provisions from other acts are loaded under this act with clear section
prefixes (CDCSA-, WSHA-, RRA-, WICA-, IRAS-, PDPA-).

All content reflects legislation as at 1 January 2025.
"""


def get_bundle() -> dict:
    """Return the full remaining domains content bundle.

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
        "title": "Child Development Co-Savings Act",
        "short_name": "CDCSA",
        "authority_type": "statute",
        "issuing_body": "Ministry of Social and Family Development",
        "official_url": "https://sso.agc.gov.sg/Act/CDCSA2001",
        "is_active": True,
    }


# ------------------------------------------------------------------
# Domains
# ------------------------------------------------------------------


def _domains() -> list[dict]:
    return [
        {
            "name": "Family Leave",
            "description": (
                "Government-paid maternity, paternity, shared parental, "
                "childcare, infant care, and adoption leave under the "
                "Child Development Co-Savings Act (CDCSA)."
            ),
            "sort_order": 1,
        },
        {
            "name": "Workplace Safety & Health",
            "description": (
                "Workplace Safety and Health Act obligations including "
                "employer general duties, incident reporting requirements, "
                "and the bizSAFE programme."
            ),
            "sort_order": 2,
        },
        {
            "name": "Retirement & Re-employment",
            "description": (
                "Retirement and Re-employment Act provisions covering "
                "minimum retirement age, re-employment obligations, and "
                "Employment Assistance Payment."
            ),
            "sort_order": 3,
        },
        {
            "name": "Work Injury Compensation",
            "description": (
                "Work Injury Compensation Act (WICA) employer liability "
                "for work injuries, commuting accidents, occupational "
                "diseases, and compulsory insurance requirements."
            ),
            "sort_order": 4,
        },
        {
            "name": "Tax Obligations",
            "description": (
                "Employer tax filing obligations under IRAS including "
                "employment income tax, IR8A/IR8S filing, tax clearance "
                "for foreign employees, and benefits-in-kind reporting."
            ),
            "sort_order": 5,
        },
        {
            "name": "Data Protection",
            "description": (
                "Personal Data Protection Act (PDPA) obligations for "
                "employee personal data including consent requirements, "
                "purpose limitation, access and correction rights, and "
                "data breach notification."
            ),
            "sort_order": 6,
        },
    ]


# ------------------------------------------------------------------
# Provisions
# ------------------------------------------------------------------


def _provisions() -> list[dict]:
    return [
        *_family_leave_provisions(),
        *_wsh_provisions(),
        *_retirement_provisions(),
        *_wica_provisions(),
        *_tax_provisions(),
        *_pdpa_provisions(),
    ]


# ------------------------------------------------------------------
# Family Leave (CDCSA)
# ------------------------------------------------------------------


def _family_leave_provisions() -> list[dict]:
    return [
        {
            "section": "CDCSA-ML",
            "title": "Government-Paid Maternity Leave",
            "formal_text": (
                "Under the Child Development Co-Savings Act, eligible "
                "working mothers are entitled to 16 weeks of maternity "
                "leave. The first 8 weeks are employer-paid. The last 8 "
                "weeks are government-paid, capped at $10,000 per 4-week "
                "period. Eligibility: the child must be a Singapore citizen "
                "and the employee must have served the employer for at "
                "least 3 months before the birth. For the third and "
                "subsequent child, all 16 weeks are government-paid."
            ),
            "plain_summary": (
                "Working mothers get 16 weeks of maternity leave. The "
                "employer pays for the first 8 weeks and the government "
                "pays for the last 8 weeks (up to $10,000 per 4-week "
                "period). The child must be a Singapore citizen and the "
                "mother must have worked for the employer for at least 3 "
                "months. From the third child onwards, the government pays "
                "all 16 weeks."
            ),
            "interpretation_notes": (
                "The government reimbursement cap of $10,000 per 4-week "
                "period means employers of higher-earning mothers bear the "
                "difference. For the first and second child, weeks 1-8 are "
                "employer-funded; for the third child onwards, the "
                "government funds all 16 weeks (employer pays first, then "
                "claims reimbursement). The employee must notify the "
                "employer at least 1 week before commencing leave. "
                "Maternity leave can be taken flexibly: the last 8 weeks "
                "can be taken within 12 months of the birth."
            ),
            "authority_level": "statute",
            "domain_name": "Family Leave",
            "effective_date": "2001-04-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {
                        "included": ["female_employees"],
                        "child_citizenship": "singapore_citizen",
                        "min_service": "3_months",
                    },
                    "notes": (
                        "Child must be a Singapore citizen. Mother must "
                        "have served employer for at least 3 months."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "A female employee earning $6,000/month is "
                        "expecting her first child (Singapore citizen). "
                        "She has worked for 2 years."
                    ),
                    "calculation": {
                        "total_leave": "16 weeks",
                        "weeks_1_to_8": "Employer-paid at $6,000/month",
                        "weeks_9_to_16": "Government-paid, capped at $10,000 per 4 weeks",
                        "monthly_salary_exceeds_cap": True,
                        "employer_top_up_per_4_weeks": "$6,000 - $10,000 = no top-up needed (4 weeks < 1 month)",
                    },
                    "outcome": (
                        "The employee receives 16 weeks of paid maternity "
                        "leave. The employer pays weeks 1-8. For weeks "
                        "9-16, the government reimburses up to $10,000 per "
                        "4-week period."
                    ),
                },
            ],
        },
        {
            "section": "CDCSA-ML-RESIGN",
            "title": "Maternity Leave and Resignation",
            "formal_text": (
                "Under the CDCSA and Employment Act, there is no statutory "
                "requirement for employers to pay out unused flexible "
                "maternity leave upon resignation. Flexible maternity leave "
                "(the last 8 weeks, which can be taken within 12 months of "
                "birth) is a leave entitlement, not a cash benefit. If the "
                "employee resigns before taking all flexible maternity leave, "
                "the unused portion is forfeited."
            ),
            "plain_summary": (
                "If an employee resigns during or after maternity leave, "
                "unused flexible maternity leave is forfeited — you do not "
                "have to pay it out in cash. You only need to pay: salary "
                "up to the last working day, unused annual leave, and any "
                "notice period obligations."
            ),
            "interpretation_notes": (
                "RESIGNATION DURING MATERNITY / FLEXIBLE MATERNITY LEAVE:\n\n"
                "1. Flexible maternity leave (last 8 weeks within 12 months) "
                "is TIME OFF, not a cash benefit. If not taken before "
                "resignation, it lapses.\n\n"
                "2. Government reimbursement only applies to leave ACTUALLY "
                "TAKEN. If leave is not taken, no reimbursement, no obligation.\n\n"
                "3. What you MUST pay on resignation:\n"
                "   - Salary up to last working day\n"
                "   - Unused annual leave encashment\n"
                "   - Payment in lieu of notice (if applicable)\n"
                "   - CPF contributions on final salary\n"
                "   - Any earned commissions or bonuses\n\n"
                "4. What you do NOT pay:\n"
                "   - Unused flexible maternity leave (not encashable)\n"
                "   - Future maternity leave entitlement\n\n"
                "5. EXCEPTION — Check your contract/policy:\n"
                "   - If your company policy explicitly states maternity "
                "leave is encashable (rare), you may be contractually bound\n"
                "   - If specific leave dates were already approved AND fall "
                "before the last day of employment, she is still entitled "
                "to take (and be paid for) those approved days\n\n"
                "6. Notice period overlap:\n"
                "   - Employee can take approved maternity leave during "
                "notice period (if mutually agreed)\n"
                "   - Do NOT cancel already-approved maternity leave just "
                "because she resigned\n"
                "   - Do NOT convert maternity leave to unpaid leave\n"
                "   - Do NOT offset maternity leave against notice period "
                "(unless mutually agreed)\n\n"
                "PRACTICAL RECOMMENDATION:\n"
                "To avoid ambiguity, your HR policy should state:\n"
                "- 'Flexible maternity leave is non-encashable and forfeited "
                "upon resignation'\n"
                "- 'Approval of flexible maternity leave is subject to "
                "continued employment'"
            ),
            "authority_level": "statute",
            "domain_name": "Family Leave",
            "effective_date": "2001-04-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {"values": ["female_employees"]},
                }
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "Employee returns from 8 weeks compulsory maternity "
                        "leave and starts taking flexible maternity leave. "
                        "She resigns with 4 weeks of flexible maternity "
                        "leave remaining."
                    ),
                    "calculation": {
                        "flexible_ml_remaining": "4 weeks",
                        "encashable": False,
                        "payment_required": "Salary to last day + unused annual leave + notice",
                        "flexible_ml_payout": "$0 (forfeited)",
                    },
                    "outcome": (
                        "The 4 weeks of unused flexible maternity leave "
                        "are forfeited. You only pay salary up to her last "
                        "day, unused annual leave, and any notice period "
                        "obligations."
                    ),
                },
            ],
        },
        {
            "section": "CDCSA-PL",
            "title": "Government-Paid Paternity Leave",
            "formal_text": (
                "Under the CDCSA, eligible working fathers are entitled "
                "to 4 weeks of government-paid paternity leave (increased "
                "from 2 weeks, effective 1 January 2025). Government "
                "reimbursement is capped at $2,500 per week (including "
                "CPF contributions). Eligibility: the child must be a "
                "Singapore citizen, the employee must have served the "
                "employer for at least 3 months, and the father must be "
                "lawfully married to the child's mother."
            ),
            "plain_summary": (
                "Working fathers get 4 weeks of government-paid paternity "
                "leave (for births from 1 January 2025). The government "
                "reimburses up to $2,500 per week. The child must be a "
                "Singapore citizen, the father must have worked for the "
                "employer for at least 3 months, and the parents must "
                "be legally married."
            ),
            "interpretation_notes": (
                "The increase from 2 weeks to 4 weeks applies to births "
                "on or after 1 January 2025. The $2,500/week cap includes "
                "CPF contributions. Paternity leave must be taken within "
                "16 weeks of the birth (or within 12 months if employer "
                "agrees). The leave can be taken as a continuous block or "
                "flexibly in days, subject to employer agreement."
            ),
            "authority_level": "statute",
            "domain_name": "Family Leave",
            "effective_date": "2025-01-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {
                        "included": ["male_employees"],
                        "child_citizenship": "singapore_citizen",
                        "min_service": "3_months",
                        "married_to_mother": True,
                    },
                    "notes": (
                        "Father must be lawfully married to the child's "
                        "mother. Child must be SC. 3 months service."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "A male employee earning $4,000/month is expecting "
                        "his first child (Singapore citizen) in March 2025. "
                        "He is married and has worked for 1 year."
                    ),
                    "calculation": {
                        "paternity_leave": "4 weeks",
                        "weekly_salary": "$4,000 / 4.33 = ~$923",
                        "government_cap": "$2,500/week",
                        "salary_below_cap": True,
                        "government_pays": "full salary for 4 weeks",
                    },
                    "outcome": (
                        "The employee gets 4 weeks of paternity leave, "
                        "fully funded by the government as his weekly "
                        "salary is below the $2,500 cap."
                    ),
                },
            ],
        },
        {
            "section": "CDCSA-SPL",
            "title": "Shared Parental Leave",
            "formal_text": (
                "Under the CDCSA, a working father may share up to 4 "
                "weeks of the mother's 16-week government-paid maternity "
                "leave. The shared leave is government-paid. The father "
                "must take the shared parental leave within 12 months of "
                "the child's birth. The mother's consent is required for "
                "the father to take shared parental leave."
            ),
            "plain_summary": (
                "Fathers can share up to 4 weeks of the mother's 16-week "
                "maternity leave. This is paid by the government. The "
                "father must use the shared leave within 12 months of the "
                "birth and the mother must agree to share her leave."
            ),
            "interpretation_notes": (
                "Shared parental leave is taken from the mother's "
                "entitlement, reducing her remaining maternity leave by "
                "the corresponding number of weeks. The mother must "
                "consent in writing. The father's employer can require "
                "reasonable notice. Government reimbursement caps apply "
                "based on the mother's salary, not the father's."
            ),
            "authority_level": "statute",
            "domain_name": "Family Leave",
            "effective_date": "2013-05-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {
                        "included": ["male_employees"],
                        "child_citizenship": "singapore_citizen",
                        "min_service": "3_months",
                        "married_to_mother": True,
                        "mother_consent_required": True,
                    },
                    "notes": (
                        "Same eligibility as paternity leave, plus "
                        "written consent from the mother is required."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "A father wants to take 4 weeks of shared parental "
                        "leave. The mother has taken 12 weeks of her 16 "
                        "weeks of maternity leave."
                    ),
                    "calculation": {
                        "mother_total_entitlement": "16 weeks",
                        "mother_used": "12 weeks",
                        "mother_remaining": "4 weeks",
                        "father_shared_request": "4 weeks",
                        "result": "Father takes 4 weeks, mother has 0 remaining",
                    },
                    "outcome": (
                        "The father can take all 4 weeks. The mother will "
                        "have used her full 16-week entitlement (12 taken "
                        "herself + 4 shared with father)."
                    ),
                },
            ],
        },
        {
            "section": "CDCSA-CL",
            "title": "Childcare Leave",
            "formal_text": (
                "Under the CDCSA, each parent of a Singapore citizen "
                "child below the age of 7 is entitled to 6 days of "
                "childcare leave per year. The first 3 days are "
                "employer-paid. The next 3 days are government-paid, "
                "capped at $500 per day. Eligibility: the child must be "
                "a Singapore citizen and the employee must have served "
                "the employer for at least 3 months."
            ),
            "plain_summary": (
                "Parents of a Singapore citizen child under 7 years old "
                "get 6 days of childcare leave per year. The employer "
                "pays for the first 3 days and the government pays for "
                "the remaining 3 days (up to $500 per day). The employee "
                "must have worked for the employer for at least 3 months."
            ),
            "interpretation_notes": (
                "Childcare leave is per parent, not per child. If an "
                "employee has multiple children under 7, they still get "
                "only 6 days total. The leave must be used within the "
                "calendar year and does not carry forward. The $500/day "
                "government cap means the employer bears no cost for the "
                "last 3 days if the employee's daily rate is at or below "
                "$500. Extended childcare leave (2 additional days) is "
                "available for parents of children aged 7-12, but is "
                "unpaid by the government."
            ),
            "authority_level": "statute",
            "domain_name": "Family Leave",
            "effective_date": "2001-04-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {
                        "included": ["all_employees_with_sc_child_under_7"],
                        "child_citizenship": "singapore_citizen",
                        "child_age_limit": 7,
                        "min_service": "3_months",
                    },
                    "notes": (
                        "Both parents eligible. Child must be SC and "
                        "below age 7. 3 months minimum service."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "An employee earning $3,000/month has a 4-year-old "
                        "Singapore citizen child. She wants to take all 6 "
                        "days of childcare leave."
                    ),
                    "calculation": {
                        "daily_rate": "$3,000 / 26 = $115.38",
                        "employer_paid_days": 3,
                        "employer_cost": "$115.38 x 3 = $346.14",
                        "government_paid_days": 3,
                        "government_cap": "$500/day",
                        "government_pays": "$115.38 x 3 = $346.14 (below cap)",
                    },
                    "outcome": (
                        "The employee takes 6 days of childcare leave. "
                        "The employer pays for the first 3 days ($346.14). "
                        "The government reimburses the next 3 days "
                        "($346.14, within the $500/day cap)."
                    ),
                },
            ],
        },
        {
            "section": "CDCSA-ICL",
            "title": "Infant Care Leave",
            "formal_text": (
                "Under the CDCSA, each parent of a Singapore citizen "
                "child below the age of 2 is entitled to 6 days of "
                "infant care leave per year, in addition to childcare "
                "leave. The first 2 days are employer-paid. The next 4 "
                "days are government-paid. Effective from 1 January 2024, "
                "infant care leave increased from 2 days to 6 days per "
                "year. Eligibility: the child must be a Singapore citizen "
                "and the employee must have served the employer for at "
                "least 3 months."
            ),
            "plain_summary": (
                "Parents of a Singapore citizen child under 2 years old "
                "get 6 extra days of infant care leave per year (on top "
                "of childcare leave). The employer pays for 2 days and "
                "the government pays for 4 days. This increased from 2 "
                "days to 6 days starting 1 January 2024."
            ),
            "interpretation_notes": (
                "Infant care leave is in addition to the 6 days of "
                "childcare leave, giving parents of infants up to 12 days "
                "of child-related leave per year. The increase from 2 to "
                "6 days is part of the 2024 family support enhancements. "
                "Like childcare leave, infant care leave is per parent "
                "and does not carry forward. Both parents can claim "
                "simultaneously."
            ),
            "authority_level": "statute",
            "domain_name": "Family Leave",
            "effective_date": "2024-01-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {
                        "included": ["all_employees_with_sc_child_under_2"],
                        "child_citizenship": "singapore_citizen",
                        "child_age_limit": 2,
                        "min_service": "3_months",
                    },
                    "notes": (
                        "Both parents eligible. Child must be SC and "
                        "below age 2. 3 months minimum service. "
                        "In addition to childcare leave."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "A father has a 6-month-old Singapore citizen "
                        "child and has worked for his employer for 1 year. "
                        "How much child-related leave can he take?"
                    ),
                    "calculation": {
                        "childcare_leave": "6 days (child under 7)",
                        "infant_care_leave": "6 days (child under 2)",
                        "total": "12 days",
                        "employer_paid": "3 (childcare) + 2 (infant care) = 5 days",
                        "government_paid": "3 (childcare) + 4 (infant care) = 7 days",
                    },
                    "outcome": (
                        "The father can take up to 12 days of child-related "
                        "leave: 6 days childcare leave plus 6 days infant "
                        "care leave. The employer pays for 5 days and the "
                        "government pays for 7 days."
                    ),
                },
            ],
        },
        {
            "section": "CDCSA-AL",
            "title": "Adoption Leave",
            "formal_text": (
                "Under the CDCSA, eligible adoptive mothers are entitled "
                "to 12 weeks of adoption leave. The first 4 weeks are "
                "employer-paid. The next 8 weeks are government-paid. "
                "Eligibility: the child must be a Singapore citizen and "
                "below 12 months of age at the formal intent to adopt. "
                "The adoptive mother must have served the employer for "
                "at least 3 months."
            ),
            "plain_summary": (
                "Adoptive mothers get 12 weeks of adoption leave. The "
                "employer pays for the first 4 weeks and the government "
                "pays for the next 8 weeks. The child must be a "
                "Singapore citizen and under 12 months old when the "
                "formal adoption process begins."
            ),
            "interpretation_notes": (
                "The formal intent to adopt is the date the prospective "
                "adoptive parent files the application with the court or "
                "adoption agency. The 12-month age limit is assessed at "
                "the date of formal intent, not the date of the court "
                "order. Adoption leave can be taken flexibly within 12 "
                "months of the formal intent to adopt. Government "
                "reimbursement caps are similar to maternity leave."
            ),
            "authority_level": "statute",
            "domain_name": "Family Leave",
            "effective_date": "2004-10-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {
                        "included": ["female_adoptive_parents"],
                        "child_citizenship": "singapore_citizen",
                        "child_age_limit_months": 12,
                        "min_service": "3_months",
                    },
                    "notes": (
                        "Adoptive mothers only. Child must be SC and "
                        "below 12 months at formal intent to adopt."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "An adoptive mother earning $5,000/month files a "
                        "formal intent to adopt a 10-month-old Singapore "
                        "citizen baby. She has worked for 2 years."
                    ),
                    "calculation": {
                        "total_leave": "12 weeks",
                        "weeks_1_to_4": "Employer-paid at $5,000/month",
                        "weeks_5_to_12": "Government-paid (capped)",
                        "child_age_at_intent": "10 months (eligible)",
                    },
                    "outcome": (
                        "The adoptive mother qualifies for 12 weeks of "
                        "adoption leave. The employer pays weeks 1-4 and "
                        "the government reimburses weeks 5-12."
                    ),
                },
            ],
        },
    ]


# ------------------------------------------------------------------
# Workplace Safety & Health (WSHA)
# ------------------------------------------------------------------


def _wsh_provisions() -> list[dict]:
    return [
        {
            "section": "WSHA-S12",
            "title": "Employer General Duties",
            "formal_text": (
                "Section 12 of the Workplace Safety and Health Act. It "
                "shall be the duty of every employer to take, so far as "
                "is reasonably practicable, such measures as are necessary "
                "to ensure the safety and health of persons at work in "
                "the workplace. This includes conducting risk assessments, "
                "establishing safe work procedures, providing personal "
                "protective equipment (PPE), and ensuring adequate safety "
                "training for all employees. Penalty for contravention: "
                "fine up to $500,000 and/or imprisonment."
            ),
            "plain_summary": (
                "Employers must take all reasonably practicable steps to "
                "keep employees safe at work. This includes doing risk "
                "assessments, setting up safe work procedures, providing "
                "safety equipment, and training staff. Failure to comply "
                "can result in fines up to $500,000 and/or imprisonment."
            ),
            "interpretation_notes": (
                "'Reasonably practicable' means considering the severity "
                "of the risk, the state of knowledge about the risk, "
                "the availability of measures to reduce the risk, and "
                "the cost of those measures. The employer's duty is "
                "non-delegable: even if a safety officer is appointed, "
                "the employer remains ultimately responsible. Risk "
                "assessments must be documented and reviewed regularly, "
                "especially after workplace incidents or changes in "
                "work processes."
            ),
            "authority_level": "statute",
            "domain_name": "Workplace Safety & Health",
            "effective_date": "2006-03-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {
                        "included": ["all_employers_in_singapore"],
                    },
                    "notes": (
                        "Applies to all employers in Singapore across "
                        "all industries and workplace types."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "An SME with 20 office employees has never "
                        "conducted a risk assessment. An employee slips "
                        "on a wet floor and fractures a wrist."
                    ),
                    "calculation": {
                        "duty": "Risk assessment should have identified wet floor hazard",
                        "measures": "Non-slip mats, warning signs, cleaning schedule",
                        "penalty_risk": "Fine up to $500,000 for failing general duty",
                    },
                    "outcome": (
                        "The employer may be liable under WSHA for failing "
                        "to conduct risk assessments and implement "
                        "preventive measures. MOM may issue a notice of "
                        "non-compliance or prosecute."
                    ),
                },
            ],
        },
        {
            "section": "WSHA-REPORT",
            "title": "Incident Reporting",
            "formal_text": (
                "Under the Workplace Safety and Health (Incident "
                "Reporting) Regulations, employers must report to the "
                "Ministry of Manpower: (a) workplace accidents where an "
                "employee is unable to work for more than 3 consecutive "
                "days, within 10 days of the accident; (b) dangerous "
                "occurrences, within 10 days; (c) occupational diseases, "
                "within 10 days of diagnosis. Fatal accidents must be "
                "reported immediately. Failure to report is an offence."
            ),
            "plain_summary": (
                "Employers must report workplace accidents (where the "
                "worker is off work for more than 3 days), dangerous "
                "events, and work-related diseases to MOM within 10 "
                "days. Deaths at work must be reported immediately. "
                "Not reporting is an offence."
            ),
            "interpretation_notes": (
                "The 3-day threshold means 3 consecutive days of medical "
                "leave, not including the day of the accident. Dangerous "
                "occurrences include structural collapses, explosions, "
                "electrical incidents, and crane failures even if no one "
                "is injured. Reports are made via the iReport system on "
                "MOM's website. Occupational diseases include those listed "
                "in the Second Schedule of WSHA, such as hearing loss, "
                "skin diseases, and respiratory conditions."
            ),
            "authority_level": "statute",
            "domain_name": "Workplace Safety & Health",
            "effective_date": "2006-03-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {
                        "included": ["all_employers_in_singapore"],
                    },
                    "notes": (
                        "Mandatory for all employers. Occupiers of "
                        "workplaces also have reporting duties."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "A warehouse worker falls from a ladder and is "
                        "given 5 days of medical leave. The accident "
                        "happens on Monday."
                    ),
                    "calculation": {
                        "mc_days": 5,
                        "threshold": "3 consecutive days",
                        "reportable": True,
                        "deadline": "10 days from Monday = following Thursday (week after)",
                    },
                    "outcome": (
                        "The employer must report the accident to MOM "
                        "within 10 days via iReport. The 5-day MC exceeds "
                        "the 3-day threshold, making it a reportable "
                        "workplace accident."
                    ),
                },
            ],
        },
        {
            "section": "WSHA-BIZSAFE",
            "title": "bizSAFE Programme",
            "formal_text": (
                "The bizSAFE programme is a 5-level capability-building "
                "programme for workplace safety and health (WSH), "
                "administered by the Workplace Safety and Health Council. "
                "Level 1: Top management demonstrates commitment to WSH "
                "by attending a workshop. Level 3: Company implements "
                "risk management with an approved WSH consultant. "
                "Level Star: Company achieves a full WSH management "
                "system audited by an approved auditor. bizSAFE "
                "certification is required for some government contracts."
            ),
            "plain_summary": (
                "bizSAFE is a 5-level workplace safety programme. "
                "Level 1 requires management commitment, Level 3 "
                "requires risk management implementation, and Star "
                "level means a full safety management system is in "
                "place. Some government contracts require bizSAFE "
                "certification."
            ),
            "interpretation_notes": (
                "bizSAFE is voluntary but increasingly expected, "
                "especially for companies in construction, manufacturing, "
                "and marine sectors. Government procurement often requires "
                "bizSAFE Level 3 or Star as a prerequisite. The programme "
                "levels are: Level 1 (CEO commitment) -> Level 2 (risk "
                "management plan) -> Level 3 (risk management "
                "implementation) -> Level 4 (WSH management system) -> "
                "Star (independent audit). Each level builds on the "
                "previous one."
            ),
            "authority_level": "best_practice",
            "domain_name": "Workplace Safety & Health",
            "effective_date": "2007-01-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {
                        "included": ["all_employers_in_singapore"],
                        "mandatory_for": "some_government_contracts",
                    },
                    "notes": (
                        "Voluntary programme but required for some "
                        "government tenders and contracts."
                    ),
                },
            ],
        },
    ]


# ------------------------------------------------------------------
# Retirement & Re-employment (RRA)
# ------------------------------------------------------------------


def _retirement_provisions() -> list[dict]:
    return [
        {
            "section": "RRA-S4",
            "title": "Minimum Retirement Age",
            "formal_text": (
                "Section 4 of the Retirement and Re-employment Act. The "
                "minimum retirement age is 63 years (raised from 62 in "
                "July 2022). It is scheduled to increase to 64 years "
                "from 1 July 2026. An employer shall not dismiss an "
                "employee on the grounds of age before the employee has "
                "reached the minimum retirement age. Penalty for "
                "contravention: fine up to $5,000."
            ),
            "plain_summary": (
                "Employers cannot force employees to retire before age "
                "63 (or 64 from July 2026). Dismissing someone because "
                "of their age before the retirement age can result in a "
                "fine of up to $5,000."
            ),
            "interpretation_notes": (
                "The retirement age applies to all employees regardless "
                "of salary or job type. The age increase schedule: 62 "
                "(before July 2022) -> 63 (July 2022) -> 64 (July 2026). "
                "The retirement age is the minimum: employers can allow "
                "employees to work past it. Dismissing an employee just "
                "before the retirement age to avoid re-employment "
                "obligations may be viewed as a contravention. This "
                "section does not prevent employees from voluntarily "
                "retiring earlier."
            ),
            "authority_level": "statute",
            "domain_name": "Retirement & Re-employment",
            "effective_date": "2022-07-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {
                        "included": ["all_employees_in_singapore"],
                    },
                    "notes": (
                        "Applies to all employees regardless of salary, "
                        "job type, or citizenship."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "An employer wants to retire a 62-year-old "
                        "employee to bring in younger staff."
                    ),
                    "calculation": {
                        "employee_age": 62,
                        "current_retirement_age": 63,
                        "can_force_retire": False,
                        "penalty_risk": "Fine up to $5,000",
                    },
                    "outcome": (
                        "The employer cannot force the employee to retire "
                        "at 62. The minimum retirement age is 63. Forcing "
                        "retirement is an offence punishable by a fine "
                        "of up to $5,000."
                    ),
                },
            ],
        },
        {
            "section": "RRA-S7",
            "title": "Re-employment Obligation",
            "formal_text": (
                "Section 7 of the Retirement and Re-employment Act. An "
                "employer must offer re-employment to an eligible employee "
                "who reaches the minimum retirement age, up to age 68 "
                "(increasing to 69 from 1 July 2026). Eligibility "
                "conditions: the employee must be a Singapore citizen or "
                "permanent resident, have served the employer for at "
                "least 3 years, have satisfactory work performance, and "
                "be medically fit. The terms of re-employment may be "
                "modified from the original contract. If re-employment "
                "is not possible, the employer must offer an Employment "
                "Assistance Payment (EAP) of $6,250 for the 63 to 64 "
                "age band (amount varies by age band)."
            ),
            "plain_summary": (
                "When an employee reaches the retirement age, the "
                "employer must offer them a new job (re-employment) up "
                "to age 68 (or 69 from July 2026). The employee must be "
                "a Singapore citizen or PR, have worked for at least 3 "
                "years, have good performance, and be medically fit. "
                "The job terms can be changed. If the employer cannot "
                "re-employ them, they must pay an Employment Assistance "
                "Payment of $6,250."
            ),
            "interpretation_notes": (
                "Re-employment terms can include different job scope, "
                "working hours, and remuneration, but must be reasonable. "
                "The EAP amount is set by the Ministry and varies: "
                "$6,250 for the 63-64 band. If the employee rejects a "
                "reasonable re-employment offer, the employer has no "
                "further obligation. Re-employment age cap schedule: "
                "67 (before July 2022) -> 68 (July 2022) -> 69 (July "
                "2026). Employers should start the re-employment "
                "discussion at least 6 months before the employee "
                "reaches retirement age."
            ),
            "authority_level": "statute",
            "domain_name": "Retirement & Re-employment",
            "effective_date": "2022-07-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {
                        "included": ["singapore_citizens", "permanent_residents"],
                        "min_service": "3_years",
                        "satisfactory_performance": True,
                        "medically_fit": True,
                    },
                    "notes": (
                        "SC/PR only. 3 years minimum service. "
                        "Satisfactory performance and medically fit."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "A Singapore citizen employee turns 63 after "
                        "working for the company for 10 years. The "
                        "employer cannot offer the same role."
                    ),
                    "calculation": {
                        "eligible_for_re_employment": True,
                        "re_employment_age_cap": 68,
                        "option_1": "Offer different role (modified terms)",
                        "option_2": "Pay EAP of $6,250",
                    },
                    "outcome": (
                        "The employer must first try to offer re-employment "
                        "in a different role with reasonable terms. If no "
                        "suitable role exists, the employer must pay the "
                        "Employment Assistance Payment of $6,250."
                    ),
                },
            ],
        },
    ]


# ------------------------------------------------------------------
# Work Injury Compensation (WICA)
# ------------------------------------------------------------------


def _wica_provisions() -> list[dict]:
    return [
        {
            "section": "WICA-S3",
            "title": "Employer Liability for Work Injuries",
            "formal_text": (
                "Section 3 of the Work Injury Compensation Act. An "
                "employer is liable to pay compensation regardless of "
                "fault for: (a) work accidents arising out of and in "
                "the course of employment; (b) commuting accidents "
                "(injuries sustained while travelling to or from work by "
                "the most direct route); (c) occupational diseases "
                "listed in the Second Schedule. Employers must have "
                "compulsory work injury compensation insurance for "
                "manual workers earning up to $2,100 per month and "
                "non-manual workers earning up to $2,600 per month. "
                "From recent amendments, insurance is compulsory for "
                "all employees."
            ),
            "plain_summary": (
                "Employers must pay compensation for work injuries even "
                "if the employer is not at fault. This covers workplace "
                "accidents, injuries during the commute, and work-related "
                "diseases. Employers must have work injury insurance. "
                "The insurance is compulsory for manual workers earning "
                "up to $2,100/month and non-manual workers earning up to "
                "$2,600/month, and is being extended to all employees."
            ),
            "interpretation_notes": (
                "WICA provides a no-fault compensation system as an "
                "alternative to common law claims. Employees can choose "
                "WICA or common law, but not both. WICA claims are "
                "faster and do not require proving employer negligence. "
                "Compensation covers: medical expenses, temporary "
                "incapacity (lost wages), permanent incapacity (lump sum), "
                "and death. The employer is liable from day one of "
                "employment. Insurance must cover all manual workers "
                "earning up to $2,100/month and non-manual workers up to "
                "$2,600/month; failure to insure is an offence with a "
                "fine of up to $10,000 and/or imprisonment up to 12 "
                "months."
            ),
            "authority_level": "statute",
            "domain_name": "Work Injury Compensation",
            "effective_date": "2020-09-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {
                        "included": ["all_employees"],
                        "insurance_mandatory_for": {
                            "manual_workers": "up_to_$2100_month",
                            "non_manual_workers": "up_to_$2600_month",
                        },
                    },
                    "notes": (
                        "Employer liability applies to all employees. "
                        "Compulsory insurance thresholds apply."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "A delivery driver earning $2,000/month slips at "
                        "a client's premises and breaks an arm. The "
                        "employer argues the client's premises caused "
                        "the injury."
                    ),
                    "calculation": {
                        "liability": "Employer liable regardless of fault",
                        "insurance_required": True,
                        "worker_type": "manual worker",
                        "salary": "$2,000 (below $2,100 threshold)",
                        "covers": "Medical expenses + temporary incapacity",
                    },
                    "outcome": (
                        "The employer is liable under WICA regardless of "
                        "who caused the hazard. The employer must have "
                        "work injury insurance for this manual worker "
                        "(earning below $2,100). The insurance covers "
                        "medical expenses and lost wages."
                    ),
                },
            ],
        },
    ]


# ------------------------------------------------------------------
# Tax Obligations (IRAS)
# ------------------------------------------------------------------


def _tax_provisions() -> list[dict]:
    return [
        {
            "section": "IRAS-IR8A",
            "title": "Employer Tax Filing",
            "formal_text": (
                "Under the Income Tax Act and IRAS requirements, all "
                "employers must file IR8A returns for all employees by "
                "1 March each year. IR8S must be filed for employees with "
                "excess CPF contributions. Appendix 8A must be filed for "
                "employees receiving benefits-in-kind (BIK). Electronic "
                "submission (e-submission via AIS) is mandatory for "
                "employers with 5 or more employees."
            ),
            "plain_summary": (
                "Employers must report all employees' earnings to IRAS "
                "by 1 March each year using the IR8A form. Additional "
                "forms are needed for CPF excess (IR8S) and non-cash "
                "benefits like company cars or housing (Appendix 8A). "
                "If the company has 5 or more employees, filing must "
                "be done electronically."
            ),
            "interpretation_notes": (
                "IR8A covers: gross salary, bonus, director's fees, "
                "commissions, allowances, pension, and any other "
                "employment income. BIK (Appendix 8A) includes: company "
                "car, accommodation, holiday passages, interest-free "
                "loans, club memberships. The e-submission requirement "
                "applies from YA 2024 for employers with 5+ employees. "
                "Late filing or non-filing: penalties of up to $5,000 "
                "and/or prosecution. Employers should issue the IR8A to "
                "employees by 1 March as well."
            ),
            "authority_level": "statute",
            "domain_name": "Tax Obligations",
            "effective_date": "2024-01-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {
                        "included": ["all_employers_in_singapore"],
                        "e_submission_mandatory": "5_or_more_employees",
                    },
                    "notes": (
                        "All employers must file. e-submission mandatory "
                        "for employers with 5 or more employees."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "An SME with 8 employees has been filing paper "
                        "IR8A forms. What changes are needed for YA 2024?"
                    ),
                    "calculation": {
                        "employee_count": 8,
                        "e_submission_threshold": 5,
                        "must_e_submit": True,
                        "deadline": "1 March 2024",
                    },
                    "outcome": (
                        "The company must switch to electronic submission "
                        "via the Auto-Inclusion Scheme (AIS) on IRAS's "
                        "myTax Portal. Paper filing is no longer "
                        "acceptable for employers with 5 or more employees."
                    ),
                },
            ],
        },
        {
            "section": "IRAS-IR21",
            "title": "Tax Clearance",
            "formal_text": (
                "Under the Income Tax Act, an employer must file IR21 "
                "(tax clearance) at least 1 month before a foreign "
                "employee (non-Singapore citizen) ceases employment or "
                "leaves Singapore. The employer must withhold all monies "
                "due to the employee (including salary, bonus, and any "
                "other payments) until tax clearance is obtained from "
                "IRAS. IRAS will process the tax clearance and notify "
                "the employer of the amount of tax to be deducted."
            ),
            "plain_summary": (
                "When a foreign employee is leaving the company or "
                "leaving Singapore, the employer must file a tax "
                "clearance form (IR21) with IRAS at least 1 month "
                "before the last day. The employer must hold back all "
                "money owed to the employee until IRAS says how much "
                "tax is due."
            ),
            "interpretation_notes": (
                "Tax clearance applies to all non-Singapore citizen "
                "employees, including permanent residents who are "
                "leaving Singapore permanently. The employer must file "
                "IR21 even if the employee has no tax liability. Failure "
                "to file IR21 or withhold monies: the employer may be "
                "personally liable for the employee's outstanding tax. "
                "Processing time is typically 21 working days. For "
                "Singapore citizens, IR21 is not required."
            ),
            "authority_level": "statute",
            "domain_name": "Tax Obligations",
            "effective_date": "2024-01-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {
                        "included": ["employers_of_foreign_employees"],
                        "applies_to": "non_singapore_citizens",
                    },
                    "notes": (
                        "Required for all foreign employees ceasing "
                        "employment or leaving Singapore."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "A work permit holder gives 1 month notice and "
                        "plans to return to their home country. Their "
                        "last day is 31 March."
                    ),
                    "calculation": {
                        "ir21_deadline": "1 March (1 month before last day)",
                        "withhold": "All salary, bonus, and outstanding payments",
                        "processing_time": "~21 working days",
                    },
                    "outcome": (
                        "The employer must file IR21 by 1 March at the "
                        "latest and withhold all monies. Once IRAS "
                        "processes the clearance, the employer deducts "
                        "any tax owing and releases the remaining funds "
                        "to the employee."
                    ),
                },
            ],
        },
    ]


# ------------------------------------------------------------------
# Data Protection (PDPA)
# ------------------------------------------------------------------


def _pdpa_provisions() -> list[dict]:
    return [
        {
            "section": "PDPA-EMP",
            "title": "Employee Data Protection",
            "formal_text": (
                "Under the Personal Data Protection Act (PDPA), "
                "employers must comply with data protection obligations "
                "when collecting, using, or disclosing employee personal "
                "data. Requirements include: obtaining consent (or "
                "relying on exceptions), limiting use to stated purposes, "
                "providing access and correction rights, and protecting "
                "data with reasonable security arrangements. Exceptions "
                "for employers: legitimate business purposes, legal "
                "requirements, and necessity for the employment "
                "relationship. Data breach notification: organisations "
                "must notify the PDPC within 3 business days if a data "
                "breach is likely to result in significant harm to "
                "affected individuals."
            ),
            "plain_summary": (
                "Employers must protect employee personal data under the "
                "PDPA. They need consent to collect, use, or share data "
                "(though some employment-related purposes are exempt). "
                "Employees can ask to see and correct their data. If "
                "there is a data breach that could cause serious harm, "
                "the employer must notify the authorities within 3 "
                "business days."
            ),
            "interpretation_notes": (
                "The employment relationship exception allows employers "
                "to collect, use, and disclose personal data without "
                "consent when it is necessary for employment purposes "
                "(e.g., salary processing, CPF submissions, tax filings). "
                "However, this does not extend to all purposes: employee "
                "personal data used for marketing or shared with "
                "unrelated third parties requires consent. The Data "
                "Protection Officer (DPO) designation is mandatory for "
                "all organisations. Penalties for PDPA breaches: "
                "financial penalty of up to $1 million or 10% of annual "
                "turnover, whichever is higher (from the 2020 "
                "amendments). Employee data includes NRIC numbers, "
                "salary information, medical records, and performance "
                "evaluations."
            ),
            "authority_level": "statute",
            "domain_name": "Data Protection",
            "effective_date": "2014-07-02",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {
                        "included": ["all_organisations_in_singapore"],
                        "dpo_required": True,
                    },
                    "notes": (
                        "All organisations handling employee personal "
                        "data must comply. DPO designation is mandatory."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "An SME discovers that an employee's personal "
                        "data (including NRIC and salary details) was "
                        "accidentally emailed to the wrong recipient."
                    ),
                    "calculation": {
                        "breach_type": "Unauthorised disclosure",
                        "significant_harm_likely": True,
                        "notification_deadline": "3 business days",
                        "notify_to": "PDPC and affected individuals",
                    },
                    "outcome": (
                        "The employer must notify the PDPC within 3 "
                        "business days and notify the affected employee. "
                        "The employer should also take immediate steps to "
                        "recall the email and assess the extent of the "
                        "breach. Failure to notify can result in "
                        "penalties up to $1 million."
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
            "source_section": "CDCSA-ML",
            "target_section": "CDCSA-SPL",
            "relationship_type": "supplements",
            "notes": (
                "Shared Parental Leave is taken from the mother's "
                "maternity leave entitlement. SPL supplements the "
                "maternity leave framework by allowing fathers to share "
                "up to 4 weeks."
            ),
        },
        {
            "source_section": "CDCSA-CL",
            "target_section": "CDCSA-ICL",
            "relationship_type": "supplements",
            "notes": (
                "Infant care leave is in addition to childcare leave. "
                "Parents of children under 2 can claim both entitlements."
            ),
        },
        {
            "source_section": "RRA-S4",
            "target_section": "RRA-S7",
            "relationship_type": "supplements",
            "notes": (
                "The minimum retirement age (Section 4) and the "
                "re-employment obligation (Section 7) work together: "
                "the employer cannot force retirement before the minimum "
                "age and must offer re-employment up to the re-employment "
                "age."
            ),
        },
    ]
