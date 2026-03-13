"""Adversarial scenario gap provisions (T082).

Fills 10 identified gaps in the knowledge base that support adversarial
test scenarios. Each gap adds at least 3 provisions covering the specific
regulatory area.

Gaps:
1.  Compound OT Day Types (EA s.36/s.38/Seventh Schedule)
2.  Extended Childcare Leave Ages 7-12 (CDCSA s.12B)
3.  Low-Wage CPF Rules (CPF Act Third Schedule)
4.  Platform Workers Act 2024
5.  Constructive Dismissal (EA s.14 + Tripartite Guidelines)
6.  PDPA Breach Notification (PDPA s.26D)
7.  Salary Deduction Aggregation (EA s.27)
8.  Part-Time Employee Regulations (EA Part IV + Tripartite Guidelines)
9.  Mental Health Workplace Obligations (WSH Act s.12 + Advisory)
10. AI and Algorithmic Discrimination (TAFEP Advisory + FCF)
"""

# Known domains from all existing content bundles.
# New gap provisions MUST use one of these domain names so they
# slot into the correct domain when loaded via bulk_load().
KNOWN_DOMAINS: set[str] = {
    # Employment Act
    "Working Hours & Overtime",
    "Leave Entitlements",
    "Salary & Compensation",
    "Termination & Dismissal",
    "Employment Records",
    "Maternity & Family",
    # Foreign Manpower
    "Work Pass Types",
    "Foreign Worker Quotas",
    "Foreign Worker Levy",
    "COMPASS Framework",
    "Employer Obligations",
    # Remaining Domains (CDCSA-based bundle)
    "Family Leave",
    "Workplace Safety & Health",
    "Retirement & Re-employment",
    "Work Injury Compensation",
    "Tax Obligations",
    "Data Protection",
    # TAFEP
    "Fair Recruitment",
    "Fair Employment Practices",
    "Flexible Work Arrangements",
    "Wrongful Dismissal Guidelines",
    "Workplace Fairness Legislation",
    # CPF
    "CPF Contribution Rates",
    "CPF Wage Ceilings",
    "CPF Allocation",
    "CPF Compliance",
    # New domains introduced by adversarial gaps
    "Platform Workers",
    "Part-Time Employment",
}


def get_provisions() -> list[dict]:
    """Return all adversarial-gap provisions as a flat list of dicts.

    Each dict is compatible with ``KBContentPipeline.load_provision()``
    (uses ``act_short_name`` and ``domain_name`` for foreign-key resolution).
    """
    return [
        *_gap_01_compound_ot(),
        *_gap_02_extended_childcare(),
        *_gap_03_low_wage_cpf(),
        *_gap_04_platform_workers(),
        *_gap_05_constructive_dismissal(),
        *_gap_06_pdpa_breach(),
        *_gap_07_salary_deduction(),
        *_gap_08_part_time(),
        *_gap_09_mental_health(),
        *_gap_10_ai_discrimination(),
    ]


# ------------------------------------------------------------------
# Gap 1: Compound OT Day Types
# ------------------------------------------------------------------


def _gap_01_compound_ot() -> list[dict]:
    """EA s.36 (rest day), s.38 (overtime), Seventh Schedule (PH).

    Covers the scenario where a public holiday falls on a rest day
    and how pay is calculated for overtime worked on such compound days.
    """
    return [
        {
            "section": "EA-S36-RD",
            "title": "Rest Day Work Pay Rates",
            "act_short_name": "EA",
            "domain_name": "Working Hours & Overtime",
            "authority_level": "statute",
            "effective_date": "2019-04-01",
            "formal_text": (
                "Section 36 of the Employment Act. An employee who works on "
                "a rest day at the employer's request shall be paid at not less "
                "than the following rates: (a) if work does not exceed half the "
                "normal daily hours, 1 day's pay; (b) if work exceeds half but "
                "does not exceed the normal daily hours, 2 days' pay; (c) for "
                "work exceeding the normal daily hours, in addition to the "
                "above, at the rate of not less than 1.5 times the hourly "
                "basic rate of pay for each hour exceeding the normal hours."
            ),
            "plain_summary": (
                "If your boss asks you to work on your rest day, you get "
                "extra pay: up to half a day work gets 1 day's pay, a full "
                "day gets 2 days' pay, and any hours beyond the normal "
                "daily limit are paid at 1.5 times the hourly rate on top "
                "of that."
            ),
        },
        {
            "section": "EA-S38-PH",
            "title": "Public Holiday Pay Entitlement",
            "act_short_name": "EA",
            "domain_name": "Working Hours & Overtime",
            "authority_level": "statute",
            "effective_date": "2019-04-01",
            "formal_text": (
                "Section 88 read with the Employment Act Seventh Schedule. "
                "Every employee is entitled to a paid holiday on each of the "
                "11 gazetted public holidays. If required to work on a public "
                "holiday, the employee is entitled to an additional day's pay "
                "at the basic rate of pay (i.e. total of 2 days' pay if the "
                "employee is on a monthly salary, or 1 extra day's pay on top "
                "of the gross daily rate for daily/hourly-rated employees). "
                "For Part IV employees who work overtime on a public holiday, "
                "overtime is paid at 1.5 times the hourly basic rate."
            ),
            "plain_summary": (
                "All employees get paid for 11 public holidays. If you have "
                "to work on a PH, you receive an extra day's pay on top of "
                "your normal salary. If you also work overtime on that PH, "
                "the OT hours are paid at 1.5 times the hourly rate."
            ),
        },
        {
            "section": "EA-S36-RD-PH",
            "title": "Compound Rest Day + Public Holiday Pay Rules",
            "act_short_name": "EA",
            "domain_name": "Working Hours & Overtime",
            "authority_level": "statute",
            "effective_date": "2019-04-01",
            "formal_text": (
                "When a gazetted public holiday falls on a rest day, the "
                "Employment Act requires that the next working day be treated "
                "as a paid holiday. If the employee is required to work on "
                "the rest day that is also a public holiday, the employer must "
                "pay: (i) the public holiday pay (1 extra day's basic pay) "
                "plus (ii) the rest day premium (2 days' pay for a full day "
                "of work requested by employer). For Part IV employees who "
                "also work overtime on such a compound day, overtime is at "
                "1.5 times the hourly basic rate on top of the above."
            ),
            "plain_summary": (
                "If a public holiday falls on your rest day, the next working "
                "day becomes a paid holiday. If your boss asks you to work on "
                "that rest day/PH, you get both the PH extra pay and the "
                "rest day premium. Overtime on top of that is still 1.5 times "
                "the hourly rate."
            ),
            "interpretation_notes": (
                "This is the most complex pay scenario in the EA. Employers "
                "must add together: (1) PH pay entitlement under s.88/Seventh "
                "Schedule, (2) rest day premium under s.36, and (3) overtime "
                "premium under s.38 if applicable. Common error is to pay "
                "only one of these rates instead of stacking them."
            ),
        },
        {
            "section": "EA-S38-OT-CAP",
            "title": "Overtime Rate and Monthly Cap on Special Days",
            "act_short_name": "EA",
            "domain_name": "Working Hours & Overtime",
            "authority_level": "statute",
            "effective_date": "2019-04-01",
            "formal_text": (
                "Section 38 of the Employment Act. Overtime pay for Part IV "
                "employees is not less than 1.5 times the hourly basic rate "
                "of pay regardless of the day type (normal day, rest day, or "
                "public holiday). The 72-hour monthly overtime cap under s.37 "
                "applies to all day types combined. Overtime worked on rest "
                "days and public holidays counts toward this monthly cap."
            ),
            "plain_summary": (
                "Overtime is always at least 1.5 times the hourly rate, "
                "whether worked on a normal day, rest day, or public holiday. "
                "The 72-hour monthly overtime limit includes all day types "
                "combined."
            ),
        },
    ]


# ------------------------------------------------------------------
# Gap 2: Extended Childcare Leave (Ages 7-12)
# ------------------------------------------------------------------


def _gap_02_extended_childcare() -> list[dict]:
    """Child Development Co-Savings Act s.12B -- 6 days/year for ages 7-12."""
    return [
        {
            "section": "CDCSA-S12B-ECL",
            "title": "Extended Childcare Leave for Children Aged 7-12",
            "act_short_name": "CDCSA",
            "domain_name": "Family Leave",
            "authority_level": "statute",
            "effective_date": "2017-07-01",
            "formal_text": (
                "Section 12B of the Child Development Co-Savings Act. An "
                "employee who has any child below the age of 13 years (i.e. "
                "aged 7 to 12) and has served the employer for at least 3 "
                "months is entitled to 2 days of extended childcare leave "
                "per year per employer. This leave is in addition to the "
                "6 days of childcare leave under s.12A (for children below "
                "age 7). For children aged 7-12, the employer pays for the "
                "first 2 days. There is no government reimbursement for "
                "extended childcare leave."
            ),
            "plain_summary": (
                "Parents with children aged 7 to 12 get 2 days of extra "
                "childcare leave per year (on top of the 6 days for kids "
                "under 7). The employer pays for these 2 days and there is "
                "no government reimbursement."
            ),
            "interpretation_notes": (
                "Note the distinction: s.12A childcare leave (6 days, for "
                "children under 7, employer pays first 3, government pays "
                "last 3) vs s.12B extended childcare leave (2 days, for "
                "children 7-12, employer pays all). If an employee has "
                "children in both age ranges, they may be entitled to both "
                "types simultaneously."
            ),
        },
        {
            "section": "CDCSA-S12B-ELIG",
            "title": "Extended Childcare Leave Eligibility Criteria",
            "act_short_name": "CDCSA",
            "domain_name": "Family Leave",
            "authority_level": "statute",
            "effective_date": "2017-07-01",
            "formal_text": (
                "Eligibility for extended childcare leave under s.12B of "
                "the CDCSA requires: (a) the employee must have at least "
                "one child below 13 years of age (7-12 inclusive); (b) the "
                "child must be a Singapore citizen; (c) the employee must "
                "have worked for the employer for a continuous period of at "
                "least 3 months. Both parents are independently entitled to "
                "the leave from their respective employers."
            ),
            "plain_summary": (
                "To qualify for extended childcare leave, your child must be "
                "aged 7 to 12, a Singapore citizen, and you must have worked "
                "for your employer for at least 3 months. Both parents can "
                "claim from their own employers."
            ),
        },
        {
            "section": "CDCSA-S12B-CALC",
            "title": "Extended Childcare Leave Pro-Ration Rules",
            "act_short_name": "CDCSA",
            "domain_name": "Family Leave",
            "authority_level": "statute",
            "effective_date": "2017-07-01",
            "formal_text": (
                "Extended childcare leave under s.12B is pro-rated for the "
                "year in which the employee starts employment and the year "
                "in which the youngest qualifying child turns 13. The leave "
                "cannot be carried forward to the next year if unused. The "
                "leave entitlement is per employer, not per child -- an "
                "employee with multiple qualifying children still receives "
                "only 2 days per year."
            ),
            "plain_summary": (
                "Extended childcare leave is pro-rated in the first year of "
                "work and the year the youngest child turns 13. Unused days "
                "cannot be brought forward. You get 2 days total regardless "
                "of how many children you have."
            ),
        },
    ]


# ------------------------------------------------------------------
# Gap 3: Low-Wage CPF Rules
# ------------------------------------------------------------------


def _gap_03_low_wage_cpf() -> list[dict]:
    """CPF Act Third Schedule -- graduated employer contributions for wages < $750."""
    return [
        {
            "section": "CPFA-3S-LW",
            "title": "CPF Third Schedule -- Low-Wage Graduated Contributions",
            "act_short_name": "CPFA",
            "domain_name": "CPF Contribution Rates",
            "authority_level": "statute",
            "effective_date": "2025-01-01",
            "formal_text": (
                "Third Schedule of the Central Provident Fund Act. For "
                "employees earning total wages of $50 or more but less than "
                "$750 per month, a graduated employer CPF contribution rate "
                "applies. The employer contributes 17% of total wages with "
                "no employee contribution required for wages below $500. "
                "For wages between $500 and $749.99, the employee contributes "
                "a graduated rate: 0.15 x (Total Wages - $500). The intent "
                "is to ensure low-wage workers still receive CPF savings "
                "without a disproportionate deduction from take-home pay."
            ),
            "plain_summary": (
                "For workers earning less than $750/month, the employer still "
                "pays CPF at 17% but the employee pays little or nothing. "
                "Workers earning under $500 have zero employee CPF deduction. "
                "Between $500 and $750, the employee's share gradually "
                "increases."
            ),
            "interpretation_notes": (
                "The low-wage threshold was increased from $500 to $750 in "
                "2023 as part of the Progressive Wage Model expansion. "
                "Employers who fail to contribute CPF for low-wage workers "
                "face penalties under s.52 of the CPF Act."
            ),
        },
        {
            "section": "CPFA-3S-LW-FORMULA",
            "title": "CPF Low-Wage Employee Contribution Formula",
            "act_short_name": "CPFA",
            "domain_name": "CPF Contribution Rates",
            "authority_level": "statute",
            "effective_date": "2025-01-01",
            "formal_text": (
                "For employees earning total wages of $500 to $749.99 per "
                "month, the employee CPF contribution is calculated as: "
                "0.15 x (Total Wages - $500). Example: an employee earning "
                "$600/month contributes 0.15 x ($600 - $500) = $15. The "
                "employer contribution remains at 17% of total wages "
                "regardless of the employee's wage level."
            ),
            "plain_summary": (
                "If you earn between $500 and $750 a month, your CPF "
                "deduction is calculated as 15% of the amount above $500. "
                "Your employer still pays the full 17% on your behalf."
            ),
        },
        {
            "section": "CPFA-AW-WIS",
            "title": "Workfare Income Supplement Eligibility for Low-Wage Workers",
            "act_short_name": "CPFA",
            "domain_name": "CPF Contribution Rates",
            "authority_level": "statute",
            "effective_date": "2025-01-01",
            "formal_text": (
                "The Workfare Income Supplement (WIS) Scheme supplements "
                "income and CPF savings of lower-wage Singapore citizen "
                "workers. Eligibility: (a) Singapore citizen aged 30+; "
                "(b) gross monthly income not exceeding $2,500; (c) lives "
                "in a property with annual value not exceeding $13,000; "
                "(d) does not own two or more properties. The WIS payment "
                "is split 60% to CPF and 40% as cash. This interacts with "
                "the CPF Third Schedule graduated contributions for workers "
                "earning below $750/month."
            ),
            "plain_summary": (
                "Low-wage Singapore citizens earning up to $2,500/month can "
                "receive extra government payments through Workfare. 60% "
                "goes to your CPF and 40% comes as cash. This is on top of "
                "the CPF contributions from your employer."
            ),
        },
    ]


# ------------------------------------------------------------------
# Gap 4: Platform Workers Act
# ------------------------------------------------------------------


def _gap_04_platform_workers() -> list[dict]:
    """Platform Workers Act 2024 -- CPF, work injury, minimum income for gig workers."""
    return [
        {
            "section": "PWA-CPF",
            "title": "Platform Workers Act -- CPF Contributions for Platform Workers",
            "act_short_name": "PWA",
            "domain_name": "Platform Workers",
            "authority_level": "statute",
            "effective_date": "2025-01-01",
            "formal_text": (
                "The Platform Workers Act 2024 requires platform operators "
                "to make CPF contributions for platform workers who are "
                "Singapore citizens or permanent residents born on or after "
                "1 January 1995. CPF contributions will be phased in "
                "gradually from 2025, starting at lower rates and reaching "
                "parity with standard employee rates by 2029. Platform "
                "operators (not the workers themselves) are responsible for "
                "the employer's share of CPF contributions."
            ),
            "plain_summary": (
                "Gig workers (delivery riders, private-hire drivers, etc.) "
                "will start getting CPF contributions from the platforms "
                "they work for, beginning in 2025. The rates start lower "
                "and gradually increase to match regular employees by 2029."
            ),
            "interpretation_notes": (
                "The Act applies to 'platform operators' defined as entities "
                "that facilitate work through a digital platform. Workers "
                "born before 1 January 1995 can opt in but are not required "
                "to. This is a major shift from treating platform workers as "
                "independent contractors."
            ),
        },
        {
            "section": "PWA-WIC",
            "title": "Platform Workers Act -- Work Injury Compensation",
            "act_short_name": "PWA",
            "domain_name": "Platform Workers",
            "authority_level": "statute",
            "effective_date": "2025-01-01",
            "formal_text": (
                "The Platform Workers Act 2024 extends work injury "
                "compensation coverage to platform workers. Platform "
                "operators must provide work injury insurance for all "
                "platform workers performing work through their platform. "
                "Coverage includes: (a) medical expenses; (b) temporary "
                "incapacity compensation; (c) permanent incapacity "
                "compensation; (d) death benefits. The coverage applies "
                "while the worker is performing platform work or travelling "
                "to or from a job obtained through the platform."
            ),
            "plain_summary": (
                "Platform operators must buy work injury insurance for gig "
                "workers. If a delivery rider or private-hire driver gets "
                "hurt while working, they are now covered for medical costs, "
                "lost income, and disability -- similar to regular employees."
            ),
        },
        {
            "section": "PWA-HOUSING",
            "title": "Platform Workers Act -- Housing and Retirement Adequacy",
            "act_short_name": "PWA",
            "domain_name": "Platform Workers",
            "authority_level": "statute",
            "effective_date": "2025-01-01",
            "formal_text": (
                "With CPF contributions mandated under the Platform Workers "
                "Act 2024, platform workers will accumulate savings in their "
                "CPF Ordinary Account, Special Account, and Medisave Account "
                "following the standard allocation ratios. This enables "
                "platform workers to use CPF OA for housing (HDB loans), "
                "CPF SA for retirement adequacy, and Medisave for healthcare. "
                "Platform operators must ensure CPF contributions are made "
                "on time to avoid penalties under the CPF Act."
            ),
            "plain_summary": (
                "Gig workers with CPF contributions can now use their CPF "
                "savings for housing loans, retirement, and medical costs -- "
                "benefits that were previously only available to regular "
                "employees."
            ),
        },
    ]


# ------------------------------------------------------------------
# Gap 5: Constructive Dismissal
# ------------------------------------------------------------------


def _gap_05_constructive_dismissal() -> list[dict]:
    """EA s.14 read with wrongful dismissal framework, Tripartite Guidelines."""
    return [
        {
            "section": "EA-S14-CD-DEF",
            "title": "Constructive Dismissal -- Definition and Legal Basis",
            "act_short_name": "EA",
            "domain_name": "Termination & Dismissal",
            "authority_level": "statute",
            "effective_date": "2019-04-01",
            "formal_text": (
                "Constructive dismissal arises when an employer's conduct "
                "amounts to a fundamental breach of the employment contract, "
                "leaving the employee with no reasonable alternative but to "
                "resign. Under the Employment Act s.14 read with the wrongful "
                "dismissal framework (s.14A), a resignation that is in "
                "substance a dismissal may be treated as a wrongful dismissal. "
                "The employee must show: (a) the employer breached an "
                "essential term of the contract; (b) the breach was "
                "sufficiently serious; (c) the employee resigned in response "
                "to the breach, not for some other reason."
            ),
            "plain_summary": (
                "If your employer makes working conditions so bad that you "
                "have no real choice but to resign, this can be treated as "
                "a wrongful dismissal. You must prove the employer broke a "
                "key part of the contract and that you quit because of it."
            ),
            "interpretation_notes": (
                "Singapore follows the UK common law test from Western "
                "Excavating v Sharp. Examples include: unilateral pay cuts, "
                "demotion without cause, hostile work environment, failure "
                "to provide safe working conditions. The burden of proof "
                "is on the employee."
            ),
        },
        {
            "section": "EA-S14-CD-TADM",
            "title": "Constructive Dismissal -- TADM/ECT Claims Process",
            "act_short_name": "EA",
            "domain_name": "Termination & Dismissal",
            "authority_level": "statute",
            "effective_date": "2019-04-01",
            "formal_text": (
                "An employee who claims constructive dismissal may file a "
                "wrongful dismissal claim through the Tripartite Alliance "
                "for Dispute Management (TADM) within 1 month of the last "
                "day of employment. If mediation at TADM is unsuccessful, "
                "the claim may be referred to the Employment Claims Tribunal "
                "(ECT). The ECT may order reinstatement or compensation of "
                "up to the equivalent of the employee's gross salary for the "
                "notice period they would have been entitled to, subject to "
                "a maximum of $20,000 (or $30,000 if the employee was "
                "represented by a union)."
            ),
            "plain_summary": (
                "If you believe you were constructively dismissed, you can "
                "file a wrongful dismissal claim at TADM within 1 month of "
                "leaving. If mediation fails, the Employment Claims Tribunal "
                "can order reinstatement or compensation up to $20,000 "
                "(or $30,000 with union representation)."
            ),
        },
        {
            "section": "EA-S14-CD-EXAMPLES",
            "title": "Constructive Dismissal -- Common Scenarios",
            "act_short_name": "EA",
            "domain_name": "Termination & Dismissal",
            "authority_level": "tripartite_guideline",
            "effective_date": "2019-04-01",
            "formal_text": (
                "The Tripartite Guidelines on Wrongful Dismissal identify "
                "the following as potential grounds for constructive "
                "dismissal claims: (a) unilateral and substantial reduction "
                "in salary without the employee's agreement; (b) demotion "
                "without valid cause or without following due process; "
                "(c) requiring the employee to perform duties fundamentally "
                "different from those agreed in the contract; (d) persistent "
                "failure to address serious workplace harassment; "
                "(e) unilateral changes to essential employment terms such "
                "as work location or hours that cause hardship."
            ),
            "plain_summary": (
                "Common reasons employees may claim constructive dismissal "
                "include: big pay cuts without agreement, demotion without "
                "reason, being given completely different work than agreed, "
                "ignoring serious harassment complaints, or major changes "
                "to work location or hours."
            ),
        },
    ]


# ------------------------------------------------------------------
# Gap 6: PDPA Breach Notification
# ------------------------------------------------------------------


def _gap_06_pdpa_breach() -> list[dict]:
    """PDPA s.26D -- 3-calendar-day notification, PDPC Advisory Guidelines."""
    return [
        {
            "section": "PDPA-S26D-NOTIFY",
            "title": "PDPA Data Breach Notification -- Obligation to Notify",
            "act_short_name": "PDPA",
            "domain_name": "Data Protection",
            "authority_level": "statute",
            "effective_date": "2021-02-01",
            "formal_text": (
                "Section 26D of the Personal Data Protection Act. An "
                "organisation that has reason to believe that a notifiable "
                "data breach has occurred must notify the Personal Data "
                "Protection Commission (PDPC) as soon as practicable and "
                "in any case no later than 3 calendar days after making "
                "the assessment that the breach is notifiable. A breach is "
                "notifiable if it: (a) results in or is likely to result in "
                "significant harm to affected individuals; or (b) involves "
                "the personal data of 500 or more individuals."
            ),
            "plain_summary": (
                "If your company suffers a data breach that could seriously "
                "harm people or affects 500+ individuals, you must report it "
                "to the PDPC within 3 calendar days of assessing it as "
                "notifiable."
            ),
            "interpretation_notes": (
                "The 3-day clock starts from the date the organisation "
                "completes its assessment that the breach is notifiable, "
                "not from the date of the breach itself. However, the PDPC "
                "expects organisations to conduct their assessment 'as soon "
                "as practicable' -- delays in assessment do not extend the "
                "notification window."
            ),
        },
        {
            "section": "PDPA-S26D-INDIV",
            "title": "PDPA Data Breach -- Notification to Affected Individuals",
            "act_short_name": "PDPA",
            "domain_name": "Data Protection",
            "authority_level": "statute",
            "effective_date": "2021-02-01",
            "formal_text": (
                "Where a data breach is likely to result in significant harm "
                "to affected individuals, the organisation must also notify "
                "the affected individuals as soon as practicable, at the same "
                "time as or after notifying the PDPC. The notification must "
                "include: (a) the nature of the breach; (b) the personal "
                "data compromised; (c) what the individual can do to protect "
                "themselves; (d) the organisation's contact details for "
                "further enquiries."
            ),
            "plain_summary": (
                "If the data breach could seriously harm people, you must "
                "also tell the affected individuals (not just the PDPC). "
                "The notice must explain what happened, what data was "
                "compromised, and how they can protect themselves."
            ),
        },
        {
            "section": "PDPA-S26D-ASSESS",
            "title": "PDPA Data Breach -- Assessment and Remediation",
            "act_short_name": "PDPA",
            "domain_name": "Data Protection",
            "authority_level": "advisory",
            "effective_date": "2021-02-01",
            "formal_text": (
                "The PDPC Advisory Guidelines on Key Concepts in the PDPA "
                "state that upon discovering a data breach, an organisation "
                "should: (a) contain the breach immediately to prevent "
                "further data loss; (b) assess the scope and severity of the "
                "breach; (c) determine whether the breach is notifiable; "
                "(d) document all actions taken. Organisations must also "
                "review their data protection policies and practices to "
                "prevent future breaches. Failure to have reasonable "
                "security arrangements may itself constitute a breach of "
                "the PDPA protection obligation under s.24."
            ),
            "plain_summary": (
                "When a data breach happens, you must: stop the breach, "
                "figure out how bad it is, decide if it needs reporting, "
                "and keep records of everything you did. Not having proper "
                "security in the first place can also get you in trouble."
            ),
        },
        {
            "section": "PDPA-S26D-PENALTY",
            "title": "PDPA Data Breach -- Penalties for Non-Compliance",
            "act_short_name": "PDPA",
            "domain_name": "Data Protection",
            "authority_level": "statute",
            "effective_date": "2021-02-01",
            "formal_text": (
                "Failure to notify the PDPC of a notifiable data breach "
                "within the prescribed timeframe is an offence under the "
                "PDPA. The PDPC may impose financial penalties of up to "
                "$1 million or 10% of the organisation's annual turnover in "
                "Singapore (whichever is higher) for organisations with "
                "annual turnover exceeding $10 million. The PDPC may also "
                "issue directions requiring the organisation to take specific "
                "remedial actions."
            ),
            "plain_summary": (
                "If you fail to report a data breach on time, you face "
                "fines of up to $1 million or 10% of your Singapore "
                "turnover (whichever is higher for larger companies). The "
                "PDPC can also order you to take specific steps to fix "
                "the problem."
            ),
        },
    ]


# ------------------------------------------------------------------
# Gap 7: Salary Deduction Aggregation
# ------------------------------------------------------------------


def _gap_07_salary_deduction() -> list[dict]:
    """EA s.27 all sub-clauses -- 25% per category, 50% aggregate cap."""
    return [
        {
            "section": "EA-S27-TYPES",
            "title": "Salary Deductions -- Authorised Deduction Types",
            "act_short_name": "EA",
            "domain_name": "Salary & Compensation",
            "authority_level": "statute",
            "effective_date": "2019-04-01",
            "formal_text": (
                "Section 27 of the Employment Act. An employer shall not "
                "make deductions from the salary of an employee other than "
                "the following: (a) deductions for absence from work; "
                "(b) deductions for damage to or loss of goods or money "
                "entrusted to the employee, where the damage or loss is "
                "directly attributable to the employee's neglect; "
                "(c) deductions for recovery of advances or loans; "
                "(d) deductions authorised by any written law (CPF, income "
                "tax); (e) deductions for payment to any registered "
                "cooperative society; (f) deductions with the employee's "
                "written consent for housing, amenities, or services."
            ),
            "plain_summary": (
                "Employers can only deduct from your salary for specific "
                "reasons listed in the law: absences, damage you caused, "
                "loan repayments, CPF/tax, cooperative payments, or "
                "things you agreed to in writing like housing."
            ),
        },
        {
            "section": "EA-S27-CAP",
            "title": "Salary Deductions -- Per-Category 25% Cap",
            "act_short_name": "EA",
            "domain_name": "Salary & Compensation",
            "authority_level": "statute",
            "effective_date": "2019-04-01",
            "formal_text": (
                "Section 27(2) of the Employment Act. Deductions made for "
                "any one category under subsection (1) must not exceed 25% "
                "of the salary due to the employee for that salary period. "
                "This per-category cap applies to each type of deduction "
                "independently: for example, deductions for absence cannot "
                "exceed 25%, deductions for damage cannot exceed 25%, and "
                "so on."
            ),
            "plain_summary": (
                "No single type of deduction can take more than 25% of your "
                "salary for that pay period. For example, your employer "
                "cannot deduct more than 25% of your salary just for "
                "damages, even if the damage was bigger."
            ),
        },
        {
            "section": "EA-S27-AGG",
            "title": "Salary Deductions -- 50% Aggregate Cap",
            "act_short_name": "EA",
            "domain_name": "Salary & Compensation",
            "authority_level": "statute",
            "effective_date": "2019-04-01",
            "formal_text": (
                "Section 27(3) of the Employment Act. The total deductions "
                "from any one salary period shall not exceed 50% of the "
                "salary due to the employee for that period. This 50% "
                "aggregate cap includes all categories of authorised "
                "deductions combined, EXCEPT deductions made under any "
                "written law (such as CPF contributions and income tax), "
                "which are excluded from this cap. Deductions for recovery "
                "of advances and loans are also excluded from the 50% cap "
                "upon termination of employment."
            ),
            "plain_summary": (
                "Total salary deductions for all reasons combined cannot "
                "exceed 50% of your pay for that period. CPF and tax "
                "deductions do not count toward this 50% limit. On "
                "termination, loan repayments can also exceed the cap."
            ),
            "interpretation_notes": (
                "Common employer error: adding CPF deductions into the 50% "
                "cap calculation. CPF is excluded as it is a statutory "
                "deduction under written law. Another error: making "
                "multiple categories of deductions that individually stay "
                "below 25% but collectively exceed 50%."
            ),
        },
    ]


# ------------------------------------------------------------------
# Gap 8: Part-Time Employee Regulations
# ------------------------------------------------------------------


def _gap_08_part_time() -> list[dict]:
    """EA Part IV + Tripartite Guidelines on Part-Time Employment."""
    return [
        {
            "section": "EA-PT-DEF",
            "title": "Part-Time Employee Definition and EA Coverage",
            "act_short_name": "EA",
            "domain_name": "Part-Time Employment",
            "authority_level": "statute",
            "effective_date": "2019-04-01",
            "formal_text": (
                "Under the Employment Act and the Employment (Part-Time "
                "Employees) Regulations, a part-time employee is one who "
                "works fewer than 35 hours per week under a contract of "
                "service. Part-time employees covered by Part IV of the EA "
                "are entitled to overtime pay at 1.5 times the hourly basic "
                "rate for hours worked beyond their normal daily or weekly "
                "working hours, and for hours worked beyond 8 hours in a "
                "day or 44 hours in a week."
            ),
            "plain_summary": (
                "If you work less than 35 hours a week, you are a part-time "
                "employee under the law. You still get overtime pay at 1.5 "
                "times your hourly rate if you work beyond your agreed hours "
                "or beyond the standard 8 hours/day or 44 hours/week limit."
            ),
        },
        {
            "section": "EA-PT-LEAVE",
            "title": "Part-Time Employee Pro-Rated Leave Entitlements",
            "act_short_name": "EA",
            "domain_name": "Part-Time Employment",
            "authority_level": "statute",
            "effective_date": "2019-04-01",
            "formal_text": (
                "Part-time employees are entitled to pro-rated leave "
                "calculated using the formula: (Number of working days per "
                "week for part-timer / Number of working days per week for "
                "a comparable full-time employee) x Full-time entitlement. "
                "This applies to annual leave, sick leave, hospitalisation "
                "leave, and childcare leave. For example, a part-timer "
                "working 3 days a week is entitled to 3/5 of the full-time "
                "annual leave. Rest day entitlement is 1 rest day per week "
                "regardless of part-time or full-time status."
            ),
            "plain_summary": (
                "Part-time workers get leave proportional to their working "
                "days. If you work 3 days a week, you get 3/5 of the "
                "full-time leave for annual leave, sick leave, and "
                "childcare leave. You still get 1 rest day per week."
            ),
            "interpretation_notes": (
                "Pro-ration is based on working days per week, not hours. "
                "A part-timer working 3 long days (e.g. 10 hours each) "
                "is pro-rated the same as one working 3 short days (e.g. "
                "4 hours each)."
            ),
        },
        {
            "section": "EA-PT-PH",
            "title": "Part-Time Employee Public Holiday Entitlement",
            "act_short_name": "EA",
            "domain_name": "Part-Time Employment",
            "authority_level": "statute",
            "effective_date": "2019-04-01",
            "formal_text": (
                "Part-time employees are entitled to paid public holidays "
                "that fall on their working days. If a gazetted public "
                "holiday falls on a day they are not scheduled to work, "
                "no pay is due. If the part-time employee works on a public "
                "holiday that falls on a scheduled working day, they are "
                "entitled to an extra day's pay at the gross rate of pay. "
                "The Tripartite Guidelines on Part-Time Employment recommend "
                "that employers and employees agree in advance which days "
                "of the week are working days."
            ),
            "plain_summary": (
                "Part-timers get paid for public holidays only if the PH "
                "falls on a day they normally work. If it falls on their "
                "day off, no extra pay is needed. It is best to agree "
                "upfront which days are working days."
            ),
        },
    ]


# ------------------------------------------------------------------
# Gap 9: Mental Health Workplace Obligations
# ------------------------------------------------------------------


def _gap_09_mental_health() -> list[dict]:
    """WSH Act s.12 duty of care + Tripartite Advisory on Mental Well-Being."""
    return [
        {
            "section": "WSHA-S12-MH-DOC",
            "title": "WSH Act s.12 -- Employer Duty of Care Includes Mental Health",
            "act_short_name": "WSHA",
            "domain_name": "Workplace Safety & Health",
            "authority_level": "statute",
            "effective_date": "2006-03-01",
            "formal_text": (
                "Section 12 of the Workplace Safety and Health Act imposes "
                "a general duty on employers to take reasonably practicable "
                "measures to ensure the safety and health of employees at "
                "work. The Ministry of Manpower has clarified that 'health' "
                "under the WSHA includes both physical and mental health. "
                "Employers must therefore take reasonable steps to identify "
                "and mitigate psychosocial hazards such as excessive workload, "
                "workplace bullying, and harassment that could impact "
                "employees' mental well-being."
            ),
            "plain_summary": (
                "The workplace safety law requires employers to protect "
                "workers' mental health as well as physical health. This "
                "includes addressing issues like excessive workload, "
                "bullying, and harassment."
            ),
            "interpretation_notes": (
                "While the WSHA does not explicitly mention 'mental health', "
                "MOM's interpretation of the general duty of care encompasses "
                "psychosocial risks. The Tripartite Advisory on Mental "
                "Well-Being at Workplaces provides practical guidance."
            ),
        },
        {
            "section": "TA-MH-ADVISORY",
            "title": "Tripartite Advisory on Mental Well-Being at Workplaces",
            "act_short_name": "TGFEP",
            "domain_name": "Workplace Safety & Health",
            "authority_level": "tripartite_guideline",
            "effective_date": "2024-01-01",
            "formal_text": (
                "The Tripartite Advisory on Mental Well-Being at Workplaces "
                "recommends that employers: (a) develop a mental well-being "
                "policy; (b) train managers to recognise signs of mental "
                "distress; (c) provide access to Employee Assistance "
                "Programmes (EAP) or counselling services; (d) conduct "
                "periodic stress and workload assessments; (e) establish "
                "clear procedures for reporting and addressing workplace "
                "harassment and bullying; (f) promote work-life balance "
                "through flexible work arrangements."
            ),
            "plain_summary": (
                "The government recommends employers have a mental health "
                "policy, train managers to spot distress, provide "
                "counselling access, check workload levels regularly, "
                "have clear anti-harassment procedures, and support "
                "work-life balance."
            ),
        },
        {
            "section": "TA-MH-BURNOUT",
            "title": "Workplace Burnout Prevention -- Employer Responsibilities",
            "act_short_name": "TGFEP",
            "domain_name": "Workplace Safety & Health",
            "authority_level": "tripartite_guideline",
            "effective_date": "2024-01-01",
            "formal_text": (
                "The Tripartite Advisory highlights that prolonged excessive "
                "workload leading to employee burnout may constitute a breach "
                "of the employer's duty of care under the WSH Act. Employers "
                "should: (a) monitor overtime hours and ensure compliance "
                "with the 72-hour monthly cap; (b) implement workload "
                "management systems; (c) ensure employees take their rest "
                "day and annual leave entitlements; (d) provide reasonable "
                "notice of work schedule changes; (e) conduct return-to-work "
                "interviews after extended sick leave to identify "
                "work-related stressors."
            ),
            "plain_summary": (
                "Making employees work until they burn out could breach the "
                "employer's duty of care. Employers should track overtime, "
                "manage workload, make sure staff take their leave, give "
                "notice of schedule changes, and check in after long "
                "sick leave."
            ),
        },
    ]


# ------------------------------------------------------------------
# Gap 10: AI and Algorithmic Discrimination
# ------------------------------------------------------------------


def _gap_10_ai_discrimination() -> list[dict]:
    """TAFEP Advisory on Fair Use of Technology in Hiring + FCF AI screening compliance."""
    return [
        {
            "section": "TAFEP-AI-SCREEN",
            "title": "TAFEP Advisory -- Fair Use of AI in Hiring and Screening",
            "act_short_name": "TGFEP",
            "domain_name": "Fair Employment Practices",
            "authority_level": "tripartite_guideline",
            "effective_date": "2024-06-01",
            "formal_text": (
                "The Tripartite Alliance for Fair and Progressive Employment "
                "Practices (TAFEP) advisory on the fair use of technology in "
                "hiring states that employers using AI or algorithmic tools "
                "for recruitment screening must ensure that: (a) the tools "
                "do not discriminate against candidates based on age, race, "
                "gender, religion, marital status, family responsibilities, "
                "or disability; (b) hiring criteria are job-relevant and "
                "based on merit; (c) human oversight is maintained in all "
                "hiring decisions; (d) candidates are informed if AI tools "
                "are used in the selection process."
            ),
            "plain_summary": (
                "If you use AI tools to screen job candidates, you must "
                "make sure they do not discriminate based on age, race, "
                "gender, or other protected characteristics. Hiring must "
                "be based on job-relevant skills, a human must oversee "
                "all decisions, and candidates should be told AI is being "
                "used."
            ),
        },
        {
            "section": "TAFEP-AI-AUDIT",
            "title": "TAFEP Advisory -- AI Tool Audit and Bias Testing",
            "act_short_name": "TGFEP",
            "domain_name": "Fair Employment Practices",
            "authority_level": "tripartite_guideline",
            "effective_date": "2024-06-01",
            "formal_text": (
                "The TAFEP advisory recommends that employers who use AI or "
                "algorithmic tools in employment decisions should: (a) conduct "
                "regular bias audits of the tools to identify discriminatory "
                "outcomes; (b) maintain documentation of the tool's design, "
                "training data, and validation methodology; (c) test the tool "
                "against the Tripartite Guidelines on Fair Employment "
                "Practices criteria before deployment; (d) retrain or retire "
                "tools that show persistent discriminatory patterns; "
                "(e) maintain records of AI-assisted decisions for review "
                "and accountability."
            ),
            "plain_summary": (
                "If you use AI for hiring or HR decisions, you should "
                "regularly check it for bias, keep records of how it works, "
                "test it against fair employment rules, fix or replace tools "
                "that discriminate, and keep records of decisions made "
                "with AI help."
            ),
        },
        {
            "section": "FCF-AI-JOBAD",
            "title": "Fair Consideration Framework -- AI in Job Advertising",
            "act_short_name": "TGFEP",
            "domain_name": "Fair Employment Practices",
            "authority_level": "advisory",
            "effective_date": "2024-06-01",
            "formal_text": (
                "Under the Fair Consideration Framework, employers advertising "
                "on MyCareersFuture must ensure that AI-powered job matching "
                "and candidate targeting tools do not narrow the candidate "
                "pool based on protected characteristics. Specifically: "
                "(a) job advertisements must not use AI-generated language "
                "that signals preference for particular demographics; "
                "(b) automated candidate matching must be based on skills, "
                "qualifications, and experience, not demographic proxies; "
                "(c) employers remain responsible for discriminatory outcomes "
                "even when using third-party AI recruitment platforms."
            ),
            "plain_summary": (
                "When posting jobs on MyCareersFuture, any AI tools used for "
                "matching candidates must not filter people based on age, "
                "race, or other protected traits. Employers are responsible "
                "for discrimination even if it comes from a third-party AI "
                "recruitment tool."
            ),
        },
    ]
