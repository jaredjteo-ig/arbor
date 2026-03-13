"""Tripartite Guidelines on Fair Employment Practices (TGFEP) — structured content bundle.

Covers:
- Fair recruitment and merit-based hiring
- Merit-based employment decisions and non-discrimination
- Non-discriminatory terms and conditions
- Flexible Work Arrangements (TG-FWAR, effective 1 Dec 2024)
- Wrongful dismissal guidelines (tripartite supplement to EA S14A)
- Grievance handling (Tripartite Standard)
- Workplace Fairness Legislation (upcoming, expected 2026-2027)

All content reflects TAFEP guidelines as at March 2025,
including the Tripartite Guidelines on Flexible Work Arrangement
Requests (TG-FWAR) effective 1 December 2024.
"""


def get_bundle() -> dict:
    """Return the full TAFEP content bundle.

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
        "title": "Tripartite Guidelines on Fair Employment Practices",
        "short_name": "TGFEP",
        "authority_type": "tripartite_guideline",
        "issuing_body": "Tripartite Alliance for Fair and Progressive Employment Practices",
        "official_url": "https://www.tal.sg/tafep/getting-started/fair/tripartite-guidelines",
        "is_active": True,
    }


# ------------------------------------------------------------------
# Domains
# ------------------------------------------------------------------


def _domains() -> list[dict]:
    return [
        {
            "name": "Fair Recruitment",
            "description": (
                "Non-discriminatory hiring practices including job "
                "advertisements, interview processes, and candidate "
                "selection. Employers must ensure recruitment is based "
                "on merit — skills, experience, and ability to perform "
                "the job — not personal characteristics."
            ),
            "sort_order": 1,
        },
        {
            "name": "Fair Employment Practices",
            "description": (
                "Workplace policies ensuring all employment decisions "
                "are based on merit and free from discrimination. Covers "
                "hiring, promotion, training, performance assessment, "
                "and termination practices."
            ),
            "sort_order": 2,
        },
        {
            "name": "Flexible Work Arrangements",
            "description": (
                "Tripartite Guidelines on Flexible Work Arrangement "
                "Requests (TG-FWAR), effective 1 December 2024. Covers "
                "the formal FWA request process, types of FWA, employer "
                "obligations, and reasonable grounds for rejection."
            ),
            "sort_order": 3,
        },
        {
            "name": "Wrongful Dismissal Guidelines",
            "description": (
                "Tripartite guidelines on wrongful dismissal, "
                "supplementing the Employment Act Section 14A. Covers "
                "what constitutes wrongful dismissal, the dispute "
                "resolution process via TADM and ECT, and examples "
                "of discriminatory and punitive dismissals."
            ),
            "sort_order": 4,
        },
        {
            "name": "Workplace Fairness Legislation",
            "description": (
                "Upcoming Workplace Fairness Legislation expected to be "
                "enacted in 2026-2027. Will codify key TAFEP guidelines "
                "into binding statute. Employers should begin preparing "
                "now. Flagged as upcoming — not yet in force."
            ),
            "sort_order": 5,
        },
    ]


# ------------------------------------------------------------------
# Provisions
# ------------------------------------------------------------------


def _provisions() -> list[dict]:
    return [
        # ====== FAIR RECRUITMENT ======
        {
            "section": "TGFEP-RECRUIT",
            "title": "Fair Recruitment Practices",
            "formal_text": (
                "Tripartite Guidelines on Fair Employment Practices — "
                "Recruitment. Employers should ensure that job "
                "advertisements do not state a preference for or "
                "against any personal characteristic including age, "
                "race, gender, religion, marital status, family "
                "responsibilities, or disability. All candidates should "
                "be evaluated based on their ability to perform the job, "
                "taking into account skills, experience, and "
                "qualifications relevant to the role. Interview "
                "questions should focus on job-related competencies and "
                "must not probe into personal characteristics unrelated "
                "to the position."
            ),
            "plain_summary": (
                "Job ads must not state preference for age, race, "
                "gender, religion, marital status, family "
                "responsibilities, or disability. Employers should "
                "select candidates based on merit — their skills, "
                "experience, and ability to do the job."
            ),
            "interpretation_notes": (
                "TAFEP regularly reviews job advertisements on major "
                "job portals. Non-compliant ads may result in TAFEP "
                "engagement with the employer. While currently a "
                "guideline (not legally binding), employers who "
                "persistently discriminate may lose their work pass "
                "privileges. MOM has curtailed work pass privileges "
                "for employers found to have discriminatory hiring "
                "practices. Bona fide occupational requirements (e.g. "
                "language skills for a specific client-facing role) are "
                "acceptable if clearly justified."
            ),
            "authority_level": "tripartite_guideline",
            "domain_name": "Fair Recruitment",
            "effective_date": "2007-01-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {
                        "included": ["all_employers_in_singapore"],
                    },
                    "notes": (
                        "Applies to all employers in Singapore regardless "
                        "of size or industry. Work pass privilege "
                        "curtailment is the primary enforcement mechanism."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "An SME posts a job ad on a major job portal for "
                        "an accounts executive position."
                    ),
                    "calculation": {
                        "non_compliant_ad": (
                            "'Looking for Chinese female, age 25-35, "
                            "for accounts executive role. Must be single "
                            "with no children.'"
                        ),
                        "compliant_ad": (
                            "'Accounts Executive — Requirements: "
                            "Diploma/Degree in Accounting, 2-5 years "
                            "experience, proficient in MYOB/Xero, "
                            "strong attention to detail.'"
                        ),
                    },
                    "outcome": (
                        "The non-compliant ad specifies race, gender, "
                        "age, and marital status — all prohibited under "
                        "TGFEP. TAFEP may contact the employer for "
                        "corrective action. The compliant ad focuses "
                        "only on job-relevant skills and qualifications."
                    ),
                },
            ],
        },
        # ====== FAIR EMPLOYMENT PRACTICES ======
        {
            "section": "TGFEP-MERIT",
            "title": "Merit-Based Employment Decisions",
            "formal_text": (
                "Tripartite Guidelines on Fair Employment Practices — "
                "Merit-Based Decisions. All employment decisions "
                "including hiring, promotion, training opportunities, "
                "performance assessment, and termination must be based "
                "on merit. Merit is defined as the employee's or "
                "candidate's skills, experience, qualifications, and "
                "ability to perform the job. Employment decisions must "
                "not be based on protected characteristics: age, race, "
                "gender, religion, marital status, family "
                "responsibility, or disability."
            ),
            "plain_summary": (
                "Every employment decision — hiring, promotion, "
                "training, or firing — must be based on merit: the "
                "person's ability to do the job (skills, experience, "
                "qualifications). Employers must not consider age, "
                "race, gender, religion, marital status, family "
                "responsibilities, or disability."
            ),
            "interpretation_notes": (
                "Protected characteristics under TGFEP: age, race, "
                "language, gender, religion, marital status, family "
                "responsibility, and disability. The principle of merit "
                "applies throughout the employment lifecycle. Employers "
                "should document the basis for key employment decisions "
                "(e.g. promotion criteria, performance ratings) to "
                "demonstrate merit-based decision-making. The upcoming "
                "Workplace Fairness Legislation is expected to make "
                "these guidelines legally binding for firms with 25 or "
                "more employees."
            ),
            "authority_level": "tripartite_guideline",
            "domain_name": "Fair Employment Practices",
            "effective_date": "2007-01-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {
                        "included": ["all_employers_in_singapore"],
                    },
                    "notes": (
                        "Applies to all employers. When the Workplace "
                        "Fairness Legislation takes effect, statutory "
                        "obligations will apply to firms with 25+ "
                        "employees."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "A company is deciding between two candidates "
                        "for a promotion to team lead. Candidate A has "
                        "5 years of experience and strong performance "
                        "ratings. Candidate B has 3 years of experience "
                        "but is younger and 'more energetic'."
                    ),
                    "calculation": {
                        "merit_factors": (
                            "Experience, performance ratings, leadership "
                            "competencies, team feedback"
                        ),
                        "non_merit_factors": ("Age, perceived energy level based on age"),
                    },
                    "outcome": (
                        "The promotion decision should be based on "
                        "documented merit factors: experience, "
                        "performance ratings, and demonstrated "
                        "leadership ability. Choosing Candidate B "
                        "because they are younger would constitute "
                        "age discrimination. The employer should "
                        "document the selection criteria and rationale."
                    ),
                },
            ],
        },
        {
            "section": "TGFEP-TERMS",
            "title": "Non-Discriminatory Terms and Conditions",
            "formal_text": (
                "Tripartite Guidelines on Fair Employment Practices — "
                "Terms and Conditions. Employers should provide equal "
                "pay for equal work regardless of gender. Employment "
                "benefits such as medical coverage, insurance, and "
                "training opportunities should be applied consistently "
                "across all employees performing similar roles. "
                "Employment contracts must not contain discriminatory "
                "clauses that differentiate based on protected "
                "characteristics."
            ),
            "plain_summary": (
                "Employers must pay men and women equally for the same "
                "work. Benefits like medical coverage and training "
                "should be given fairly to all staff in similar roles. "
                "Employment contracts must not have clauses that "
                "discriminate based on personal characteristics."
            ),
            "interpretation_notes": (
                "The equal pay principle applies to employees doing "
                "substantially similar work — minor differences in job "
                "title do not justify pay gaps. Pay differences are "
                "acceptable if based on objective factors such as "
                "seniority, performance, qualifications, or market "
                "benchmarks. Employers should conduct periodic pay "
                "audits to identify unexplained gender pay gaps. "
                "Discriminatory contract clauses include: different "
                "retirement ages by gender, different benefit "
                "entitlements by marital status, or probation periods "
                "that differ by nationality."
            ),
            "authority_level": "tripartite_guideline",
            "domain_name": "Fair Employment Practices",
            "effective_date": "2007-01-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {
                        "included": ["all_employers_in_singapore"],
                    },
                    "notes": "Applies to all employers in Singapore.",
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "A company pays a male marketing manager "
                        "$6,500/month but a female marketing manager "
                        "with the same experience and responsibilities "
                        "$5,800/month."
                    ),
                    "calculation": {
                        "pay_gap": "$6,500 - $5,800 = $700/month",
                        "percentage_gap": "10.8%",
                        "justification_check": (
                            "Same role, same experience, same "
                            "responsibilities — no objective basis "
                            "for the difference"
                        ),
                    },
                    "outcome": (
                        "This pay difference likely violates the equal "
                        "pay principle under TGFEP. The employer should "
                        "review and rectify the gap. Acceptable reasons "
                        "for pay differences include seniority, "
                        "performance ratings, or additional "
                        "qualifications — but not gender."
                    ),
                },
            ],
        },
        # ====== FLEXIBLE WORK ARRANGEMENTS ======
        {
            "section": "TG-FWAR-REQ",
            "title": "FWA Request Process",
            "formal_text": (
                "Tripartite Guidelines on Flexible Work Arrangement "
                "Requests (TG-FWAR), effective 1 December 2024. All "
                "employees who have completed their probation period "
                "may submit a formal request for flexible work "
                "arrangements to their employer. The employer must "
                "respond to the request within 2 months of receipt. "
                "If the request is rejected, the employer must provide "
                "written reasons for the rejection. Rejections must be "
                "based on reasonable business grounds as defined in "
                "the guidelines."
            ),
            "plain_summary": (
                "From 1 December 2024, any employee who has passed "
                "probation can formally request flexible work "
                "arrangements. The employer must reply within 2 months "
                "and must give written reasons if the request is "
                "turned down."
            ),
            "interpretation_notes": (
                "The TG-FWAR does not give employees a right to FWA — "
                "it establishes a structured process for requesting and "
                "considering FWA. Employers are expected to consider "
                "requests fairly and cannot ignore or dismiss them "
                "without proper review. The 2-month response window "
                "starts from the date the employer receives the written "
                "request. Verbal requests should be directed to a "
                "formal written process. Employers should have a "
                "documented FWA policy and request procedure."
            ),
            "authority_level": "tripartite_guideline",
            "domain_name": "Flexible Work Arrangements",
            "effective_date": "2024-12-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {
                        "included": ["all_employees_past_probation"],
                    },
                    "notes": (
                        "Applies to all employees who have completed "
                        "probation. No salary cap or sector restriction."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "An employee who passed probation 6 months ago "
                        "submits a written FWA request to work from "
                        "home 2 days a week."
                    ),
                    "calculation": {
                        "step_1": "Employee submits written FWA request on 15 Jan 2025",
                        "step_2": "Employer reviews operational impact within 2 months",
                        "step_3": "Employer must respond by 15 Mar 2025",
                        "step_4_approve": (
                            "If approved: confirm in writing with start "
                            "date and any trial period conditions"
                        ),
                        "step_4_reject": (
                            "If rejected: provide written reasons based "
                            "on reasonable business grounds"
                        ),
                    },
                    "outcome": (
                        "The employer must respond by 15 March 2025. If "
                        "the request is rejected, the employer must "
                        "explain the specific business reasons (e.g. "
                        "'your role requires daily on-site client "
                        "meetings'). A blanket 'we don't do WFH' is "
                        "not an acceptable reason."
                    ),
                },
            ],
        },
        {
            "section": "TG-FWAR-TYPES",
            "title": "Types of Flexible Work Arrangements",
            "formal_text": (
                "Tripartite Guidelines on Flexible Work Arrangement "
                "Requests — Types of FWA. Flexible work arrangements "
                "include three broad categories: (1) Flexi-place — "
                "arrangements where the employee works from a location "
                "other than the default workplace, such as working from "
                "home or remote work; (2) Flexi-time — arrangements "
                "that vary when work is performed, such as staggered "
                "hours, compressed work weeks, or flexible start and "
                "end times; (3) Flexi-load — arrangements that vary "
                "the amount of work, such as part-time work, job "
                "sharing, or reduced workload."
            ),
            "plain_summary": (
                "There are three types of FWA: (1) Flexi-place — work "
                "from home or another location; (2) Flexi-time — "
                "change when you work (e.g. staggered hours, 4-day "
                "work week); (3) Flexi-load — change how much you "
                "work (e.g. part-time, job sharing)."
            ),
            "interpretation_notes": (
                "Employees may request one or a combination of FWA "
                "types. Employers should consider the nature of the "
                "role and whether the requested FWA is feasible. "
                "Flexi-place is the most commonly requested form. "
                "Compressed work weeks (e.g. 4 days x 10 hours) are "
                "a form of flexi-time that maintains total weekly "
                "hours. Job sharing involves two or more employees "
                "sharing the responsibilities of one full-time role. "
                "Employers may propose alternative FWA if the specific "
                "request is not feasible."
            ),
            "authority_level": "tripartite_guideline",
            "domain_name": "Flexible Work Arrangements",
            "effective_date": "2024-12-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {
                        "included": ["all_employees_past_probation"],
                    },
                    "notes": (
                        "All FWA types are available for request by "
                        "employees who have completed probation."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "Three employees at the same company each "
                        "request a different type of FWA."
                    ),
                    "calculation": {
                        "employee_a": (
                            "Flexi-place: Marketing executive requests "
                            "to work from home 3 days a week"
                        ),
                        "employee_b": (
                            "Flexi-time: Software developer requests "
                            "compressed work week (4 days x 10 hours)"
                        ),
                        "employee_c": (
                            "Flexi-load: Senior analyst with caregiving "
                            "duties requests part-time (3 days a week)"
                        ),
                    },
                    "outcome": (
                        "Each request should be assessed individually "
                        "based on the nature of the role and business "
                        "needs. The marketing executive's WFH request "
                        "may be feasible if client meetings can be "
                        "scheduled on office days. The developer's "
                        "compressed week maintains total hours. The "
                        "analyst's part-time request may require "
                        "workload redistribution. All three are valid "
                        "FWA types under TG-FWAR."
                    ),
                },
            ],
        },
        {
            "section": "TG-FWAR-REJECT",
            "title": "Reasonable Business Grounds for FWA Rejection",
            "formal_text": (
                "Tripartite Guidelines on Flexible Work Arrangement "
                "Requests — Grounds for Rejection. Employers may reject "
                "an FWA request on reasonable business grounds "
                "including: (a) the cost of the arrangement would be "
                "a burden on the business; (b) the arrangement would "
                "have a detrimental impact on productivity; (c) it is "
                "not feasible to reorganise work among existing staff; "
                "(d) the nature of the role requires the employee's "
                "physical presence on-site; (e) health and safety "
                "concerns associated with the arrangement. Blanket "
                "policies that reject all FWA requests without "
                "individual assessment are not considered reasonable."
            ),
            "plain_summary": (
                "Employers can reject an FWA request if there is a "
                "genuine business reason, such as high cost, lower "
                "productivity, inability to reorganise work, the role "
                "needing on-site presence, or health and safety "
                "concerns. However, a blanket 'we don't offer WFH' "
                "policy is not acceptable."
            ),
            "interpretation_notes": (
                "Reasonable business grounds must be specific to the "
                "individual request and role — not a one-size-fits-all "
                "rejection. Employers should demonstrate they have "
                "genuinely considered the request. Examples of "
                "unreasonable rejections: 'our company culture requires "
                "everyone in the office', 'we've never done this "
                "before', 'it's not fair to other employees'. If an "
                "employee's specific request cannot be accommodated, "
                "the employer should consider proposing an alternative "
                "arrangement. TAFEP may engage with employers who "
                "demonstrate a pattern of blanket rejections."
            ),
            "authority_level": "tripartite_guideline",
            "domain_name": "Flexible Work Arrangements",
            "effective_date": "2024-12-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {
                        "included": ["all_employers_in_singapore"],
                    },
                    "notes": (
                        "Applies to all employers receiving FWA requests. "
                        "Employers must assess each request individually."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "A retail store manager requests to work from "
                        "home 3 days a week. The employer rejects the "
                        "request."
                    ),
                    "calculation": {
                        "role_requirement": (
                            "Store manager must be physically present "
                            "to manage staff, handle inventory, and "
                            "serve customers"
                        ),
                        "rejection_ground": (
                            "Nature of role requires on-site presence — "
                            "reasonable business ground"
                        ),
                        "alternative_offered": (
                            "Employer offers flexi-time instead: "
                            "staggered hours (10am-7pm instead of "
                            "9am-6pm) to help with personal commitments"
                        ),
                    },
                    "outcome": (
                        "The rejection is reasonable because a retail "
                        "store manager must be on-site. However, the "
                        "employer demonstrates good practice by offering "
                        "an alternative FWA (flexi-time). The written "
                        "rejection should specify the on-site "
                        "requirement and confirm the alternative offer."
                    ),
                },
            ],
        },
        # ====== WRONGFUL DISMISSAL GUIDELINES ======
        {
            "section": "TG-WD",
            "title": "Tripartite Guidelines on Wrongful Dismissal",
            "formal_text": (
                "Tripartite Guidelines on Wrongful Dismissal. These "
                "guidelines supplement Employment Act Section 14A and "
                "provide guidance on what constitutes wrongful "
                "dismissal. A dismissal is wrongful if it is: "
                "(a) discriminatory — based on protected "
                "characteristics such as age, race, gender, religion, "
                "marital status, family responsibility, or disability; "
                "(b) punitive — as retaliation for exercising a lawful "
                "right (e.g. filing a salary claim, reporting a "
                "workplace safety issue, taking maternity leave); "
                "(c) based on protected characteristics rather than "
                "work performance or conduct. Employees who believe "
                "they have been wrongfully dismissed should first seek "
                "mediation at TADM (Tripartite Alliance for Dispute "
                "Management), followed by adjudication at the "
                "Employment Claims Tribunals (ECT) if mediation fails."
            ),
            "plain_summary": (
                "Dismissal is wrongful if it is discriminatory (based "
                "on age, race, gender, etc.), punitive (for exercising "
                "a legal right), or based on personal characteristics "
                "instead of performance. Employees should first go to "
                "TADM for mediation, then ECT if unresolved."
            ),
            "interpretation_notes": (
                "The tripartite guidelines work alongside EA Section "
                "14A. Examples of wrongful dismissal: firing a worker "
                "after she announces pregnancy, terminating an older "
                "worker to hire a younger replacement without "
                "performance justification, dismissing an employee who "
                "filed a salary claim with MOM. Examples of lawful "
                "dismissal: termination due to poor performance with "
                "documented warnings, retrenchment following fair "
                "selection criteria, summary dismissal after due "
                "inquiry for proven misconduct. The burden is on the "
                "employer to show just cause for the dismissal. TADM "
                "mediation is a mandatory first step before ECT."
            ),
            "authority_level": "tripartite_guideline",
            "domain_name": "Wrongful Dismissal Guidelines",
            "effective_date": "2019-04-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {
                        "included": ["all_ea_covered_employees"],
                    },
                    "notes": (
                        "Applies to all employees covered by the "
                        "Employment Act, including PMEs (since April "
                        "2019 amendments)."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "A 58-year-old employee with 15 years of "
                        "service and consistently good performance "
                        "reviews is terminated. The employer hires a "
                        "28-year-old replacement at a lower salary."
                    ),
                    "calculation": {
                        "dismissal_type": "Potentially discriminatory (age-based)",
                        "evidence_for_wrongful": (
                            "Good performance history, long tenure, "
                            "immediate replacement by younger worker"
                        ),
                        "evidence_for_lawful": (
                            "Would need documented business "
                            "restructuring, fair selection criteria, "
                            "or genuine redundancy"
                        ),
                        "process": "TADM mediation -> ECT adjudication",
                    },
                    "outcome": (
                        "This dismissal appears wrongful — the pattern "
                        "suggests age discrimination. The employee "
                        "should file a claim at TADM within 1 month. "
                        "The employer would need to demonstrate a "
                        "legitimate, non-discriminatory reason for the "
                        "termination. If the employer cannot, ECT may "
                        "order reinstatement or compensation."
                    ),
                },
            ],
        },
        # ====== GRIEVANCE HANDLING ======
        {
            "section": "TGFEP-GRIEVANCE",
            "title": "Grievance Handling",
            "formal_text": (
                "Tripartite Standard on Grievance Handling. Employers "
                "should establish and maintain accessible grievance "
                "handling procedures for all employees. The procedure "
                "should include: (a) a clear channel for employees to "
                "raise grievances, including an option for anonymous "
                "reporting; (b) a commitment to investigate grievances "
                "within a reasonable timeframe; (c) a non-retaliation "
                "policy protecting employees who raise grievances in "
                "good faith; (d) an escalation path if the initial "
                "response is unsatisfactory. Employers should "
                "communicate the grievance procedure to all employees "
                "and ensure supervisors are trained in handling "
                "grievances."
            ),
            "plain_summary": (
                "Employers should have a clear process for staff to "
                "raise complaints. This should include an option to "
                "report anonymously, a promise to investigate within a "
                "reasonable time, and a rule that staff who complain "
                "in good faith will not face retaliation."
            ),
            "interpretation_notes": (
                "Based on the Tripartite Standard on Grievance "
                "Handling Processes. While classified as a tripartite "
                "standard (voluntary adoption), employers who adopt it "
                "can be recognised under the Tripartite Standards "
                "framework. A 'reasonable timeframe' for investigation "
                "is generally 2-4 weeks for straightforward cases, "
                "though complex cases may take longer with interim "
                "updates to the complainant. The non-retaliation policy "
                "should cover both direct retaliation (demotion, "
                "dismissal) and indirect retaliation (exclusion from "
                "projects, social isolation). Anonymous reporting can "
                "be via a dedicated email, hotline, or third-party "
                "platform."
            ),
            "authority_level": "tripartite_guideline",
            "domain_name": "Fair Employment Practices",
            "effective_date": "2017-01-01",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": {
                        "included": ["all_employers_in_singapore"],
                    },
                    "notes": (
                        "Voluntary adoption under the Tripartite "
                        "Standards framework. Recommended for all "
                        "employers."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "An employee believes she was passed over for "
                        "promotion due to her gender. She wants to "
                        "raise a grievance but fears retaliation from "
                        "her supervisor."
                    ),
                    "calculation": {
                        "step_1": (
                            "Employee uses anonymous grievance channel "
                            "(e.g. dedicated HR email or hotline)"
                        ),
                        "step_2": ("HR acknowledges receipt within 3 working days"),
                        "step_3": (
                            "HR investigates: reviews promotion criteria, "
                            "interviews relevant parties, checks records"
                        ),
                        "step_4": (
                            "HR provides outcome within 2-4 weeks with "
                            "actions taken or reasons for finding"
                        ),
                        "step_5": (
                            "If unsatisfied, employee can escalate to "
                            "senior management or external channels "
                            "(TAFEP, MOM)"
                        ),
                    },
                    "outcome": (
                        "The employer's grievance procedure should allow "
                        "the employee to report anonymously. HR must "
                        "investigate the promotion decision and verify "
                        "whether it was merit-based. The employee is "
                        "protected from retaliation regardless of the "
                        "outcome. If the internal process fails, the "
                        "employee can approach TAFEP."
                    ),
                },
            ],
        },
        # ====== WORKPLACE FAIRNESS LEGISLATION (UPCOMING) ======
        {
            "section": "WFL-2026",
            "title": "Workplace Fairness Legislation (Upcoming)",
            "formal_text": (
                "Workplace Fairness Legislation — upcoming statutory "
                "framework expected to be enacted in 2026-2027. The "
                "legislation will codify key Tripartite Guidelines on "
                "Fair Employment Practices into binding law. Protected "
                "characteristics — including age, race, gender, "
                "religion, marital status, family responsibility, and "
                "disability — will be defined in statute. The "
                "legislation will apply to employers with 25 or more "
                "employees. Penalties for non-compliance will include "
                "fines and enforcement actions. Employers are advised "
                "to begin reviewing and updating their employment "
                "policies now to ensure compliance when the law takes "
                "effect."
            ),
            "plain_summary": (
                "Singapore plans to pass a Workplace Fairness law in "
                "2026-2027 that will make current TAFEP guidelines "
                "legally binding. Companies with 25 or more employees "
                "will be covered. Employers should start preparing now "
                "by reviewing their hiring and employment practices."
            ),
            "interpretation_notes": (
                "THIS PROVISION IS UPCOMING AND NOT YET IN FORCE. The "
                "information reflects announced policy intent as at "
                "March 2025. The Workplace Fairness Legislation was "
                "recommended by the Tripartite Committee on Workplace "
                "Fairness and accepted by the Government. Key "
                "preparation steps for employers: (1) review all job "
                "ads for discriminatory language, (2) document merit-"
                "based criteria for hiring and promotion, (3) establish "
                "grievance handling procedures, (4) train HR and "
                "managers on fair employment, (5) conduct pay equity "
                "audits. The 25-employee threshold means SMEs below "
                "this size are initially excluded but are still "
                "encouraged to adopt fair practices."
            ),
            "authority_level": "advisory",
            "domain_name": "Workplace Fairness Legislation",
            "effective_date": None,
            "applicability_rules": [
                {
                    "rule_type": "headcount",
                    "criteria_type": "minimum",
                    "criteria_value": {
                        "minimum_employees": 25,
                        "note": (
                            "Legislation expected to apply to firms " "with 25 or more employees"
                        ),
                    },
                    "notes": (
                        "Upcoming legislation. Employer size threshold "
                        "of 25 employees. Not yet in force — advisory "
                        "only. Employers should prepare proactively."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "An HR manager at a company with 50 employees "
                        "wants to know what to do now to prepare for "
                        "the Workplace Fairness Legislation."
                    ),
                    "calculation": {
                        "headcount": 50,
                        "threshold": 25,
                        "will_be_covered": True,
                        "preparation_checklist": (
                            "(1) Audit job ads, (2) Document promotion "
                            "criteria, (3) Review pay equity, "
                            "(4) Set up grievance procedure, "
                            "(5) Train managers"
                        ),
                    },
                    "outcome": (
                        "The company will be covered when the law takes "
                        "effect (50 employees exceeds the 25-employee "
                        "threshold). The HR manager should start by "
                        "auditing current job advertisements, "
                        "documenting merit-based criteria for all "
                        "employment decisions, setting up a formal "
                        "grievance handling procedure, and training "
                        "hiring managers on fair employment practices. "
                        "These steps align with both the current "
                        "guidelines and the expected statutory "
                        "requirements."
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
            "source_section": "TGFEP-RECRUIT",
            "target_section": "TGFEP-MERIT",
            "relationship_type": "supplements",
            "notes": (
                "Fair recruitment is part of merit-based employment "
                "practices. Recruitment is the first stage where "
                "merit-based principles must be applied."
            ),
        },
        {
            "source_section": "TG-FWAR-REQ",
            "target_section": "TG-FWAR-TYPES",
            "relationship_type": "supplements",
            "notes": (
                "The FWA request process applies to all FWA types "
                "(flexi-place, flexi-time, flexi-load)."
            ),
        },
        {
            "source_section": "TG-FWAR-REQ",
            "target_section": "TG-FWAR-REJECT",
            "relationship_type": "supplements",
            "notes": (
                "Rejection grounds define what constitutes a reasonable "
                "basis for denying an FWA request."
            ),
        },
        {
            "source_section": "TG-WD",
            "target_section": "TGFEP-MERIT",
            "relationship_type": "related",
            "notes": (
                "Wrongful dismissal may involve discrimination — "
                "a dismissal that violates merit-based principles "
                "may be both unfair and wrongful."
            ),
        },
        {
            "source_section": "TGFEP-GRIEVANCE",
            "target_section": "TGFEP-MERIT",
            "relationship_type": "supplements",
            "notes": (
                "Grievance handling procedures support fair employment "
                "practices by giving employees a channel to report "
                "discrimination."
            ),
        },
        {
            "source_section": "WFL-2026",
            "target_section": "TGFEP-MERIT",
            "relationship_type": "supersedes",
            "notes": (
                "The upcoming Workplace Fairness Legislation will make "
                "the current tripartite guidelines on merit-based "
                "employment legally binding for firms with 25+ "
                "employees."
            ),
        },
    ]
