"""Employment of Foreign Manpower Act (Cap 91A) -- structured content bundle.

Covers:
- Work pass types: Employment Pass, S Pass, Work Permit
- Foreign worker quotas (Dependency Ratio Ceiling)
- Foreign worker levy tiers and rates
- COMPASS framework for Employment Pass applications
- Fair Consideration Framework
- Employer obligations for foreign workers

All content reflects the EFMA as at 1 January 2025,
including COMPASS implementation (Sep 2023/2024) and
S Pass quota changes effective Sep 2025.
"""


def get_bundle() -> dict:
    """Return the full EFMA content bundle.

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
        "title": "Employment of Foreign Manpower Act",
        "short_name": "EFMA",
        "authority_type": "statute",
        "issuing_body": "Ministry of Manpower",
        "official_url": "https://sso.agc.gov.sg/Act/EFMA1990",
        "is_active": True,
    }


# ------------------------------------------------------------------
# Domains
# ------------------------------------------------------------------


def _domains() -> list[dict]:
    return [
        {
            "name": "Work Pass Types",
            "description": (
                "Employment Pass, S Pass, and Work Permit categories "
                "under the EFMA. Covers eligibility criteria, minimum "
                "salary thresholds, and pass-specific conditions for "
                "foreign professionals, mid-skilled, and semi-skilled workers."
            ),
            "sort_order": 1,
        },
        {
            "name": "Foreign Worker Quotas",
            "description": (
                "Dependency Ratio Ceiling (DRC) and quota ratios by sector. "
                "Determines the maximum proportion of foreign workers an "
                "employer may hire relative to total workforce, with sector-"
                "specific limits for services, manufacturing, construction, "
                "and process industries."
            ),
            "sort_order": 2,
        },
        {
            "name": "Foreign Worker Levy",
            "description": (
                "Tiered levy system for S Pass and Work Permit holders. "
                "Levy rates vary by sector, pass type, and the employer's "
                "utilisation of their foreign worker quota (DRC). Includes "
                "basic and higher tier rates."
            ),
            "sort_order": 3,
        },
        {
            "name": "COMPASS Framework",
            "description": (
                "Complementarity Assessment Framework for Employment Pass "
                "applications. A points-based system with foundational and "
                "bonus criteria that evaluates EP candidates on salary, "
                "qualifications, workforce diversity, and support for "
                "local employment."
            ),
            "sort_order": 4,
        },
        {
            "name": "Employer Obligations",
            "description": (
                "Statutory obligations of employers hiring foreign workers "
                "under the EFMA. Covers housing standards, medical and "
                "personal accident insurance, upkeep and maintenance, "
                "repatriation responsibilities, and restrictions on "
                "retaining travel documents."
            ),
            "sort_order": 5,
        },
    ]


# ------------------------------------------------------------------
# Provisions
# ------------------------------------------------------------------


def _provisions() -> list[dict]:
    return [
        # ====== WORK PASS TYPES ======
        {
            "section": "EFMA-EP",
            "title": "Employment Pass",
            "formal_text": (
                "The Employment Pass (EP) is issued to foreign professionals, "
                "managers, and executives seeking employment in Singapore. "
                "Applicants must earn a minimum fixed monthly salary of "
                "$5,000 (general sectors) or $5,500 (financial services "
                "sector). The minimum salary threshold increases "
                "progressively with age, reflecting expected seniority and "
                "experience. From 1 September 2023, all new EP applications "
                "are subject to the Complementarity Assessment Framework "
                "(COMPASS). From 1 September 2024, COMPASS also applies to "
                "EP renewal applications. Employers must demonstrate that "
                "the candidate meets both the salary criterion and the "
                "COMPASS points threshold."
            ),
            "plain_summary": (
                "The Employment Pass is for foreign professionals earning "
                "at least $5,000 per month ($5,500 in financial services). "
                "Since September 2023, new EP applications must also pass "
                "a points-based assessment called COMPASS. Renewals became "
                "subject to COMPASS from September 2024."
            ),
            "interpretation_notes": (
                "The $5,000 minimum is a floor for younger candidates; "
                "older and more experienced candidates are expected to "
                "command higher salaries. MOM publishes age-adjusted salary "
                "benchmarks. EP holders can bring dependants (Dependant's "
                "Pass) if they earn at least $6,000/month. Letter of "
                "Consent for spouses to work requires the EP holder to "
                "earn at least $6,000/month. EP applications are employer-"
                "sponsored -- individuals cannot self-apply. Processing "
                "time is typically 3-6 weeks but may take longer if "
                "additional checks are required."
            ),
            "authority_level": "statute",
            "domain_name": "Work Pass Types",
            "effective_date": "2023-09-01",
            "applicability_rules": [
                {
                    "rule_type": "salary_threshold",
                    "criteria_type": "minimum",
                    "criteria_value": {
                        "general_minimum": 5000,
                        "financial_services_minimum": 5500,
                        "basis": "fixed_monthly_salary",
                        "age_progressive": True,
                    },
                    "notes": (
                        "Minimum salary for EP is $5,000 (general) or $5,500 "
                        "(financial services). Higher thresholds apply for "
                        "older candidates based on MOM's age-salary matrix."
                    ),
                },
                {
                    "rule_type": "assessment_framework",
                    "criteria_type": "mandatory",
                    "criteria_value": {
                        "framework": "COMPASS",
                        "new_applications_from": "2023-09-01",
                        "renewals_from": "2024-09-01",
                    },
                    "notes": (
                        "All EP applications must pass COMPASS. New "
                        "applications from Sep 2023, renewals from Sep 2024."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "A technology company wants to hire a 30-year-old "
                        "software engineer from India on an Employment Pass "
                        "with a fixed monthly salary of $6,500."
                    ),
                    "calculation": {
                        "salary_check": "$6,500 >= $5,000 minimum -- PASS",
                        "compass_required": "Yes (new application after Sep 2023)",
                        "compass_assessment": (
                            "Salary criterion, qualifications, diversity, "
                            "and local employment support will be scored"
                        ),
                        "dependant_eligibility": (
                            "$6,500 >= $6,000 -- eligible for Dependant's Pass"
                        ),
                    },
                    "outcome": (
                        "The candidate meets the minimum salary requirement. "
                        "The employer must submit a COMPASS self-assessment "
                        "along with the EP application. If the candidate "
                        "scores at least 40 COMPASS points and meets all "
                        "other criteria, the EP is likely to be approved."
                    ),
                },
            ],
        },
        {
            "section": "EFMA-SP",
            "title": "S Pass",
            "formal_text": (
                "The S Pass is issued to mid-skilled foreign workers. "
                "Applicants must earn a minimum fixed monthly salary of "
                "$3,150 (general sectors) or $3,650 (financial services "
                "sector). The minimum salary threshold increases "
                "progressively with age. S Pass holders are subject to the "
                "Dependency Ratio Ceiling (DRC): employers may employ S "
                "Pass holders up to a maximum of 15% of their total "
                "workforce (effective 1 September 2025; previously 18%). "
                "Employers must pay a foreign worker levy for each S Pass "
                "holder."
            ),
            "plain_summary": (
                "The S Pass is for mid-skilled foreign workers earning at "
                "least $3,150 per month ($3,650 in financial services). "
                "Companies can only have up to 15% of their total workforce "
                "on S Passes (from September 2025). Employers pay a monthly "
                "levy for each S Pass holder."
            ),
            "interpretation_notes": (
                "The S Pass quota was reduced from 20% to 18% in January "
                "2021, and will be further reduced to 15% from September "
                "2025. The quota is calculated based on the employer's "
                "total workforce (local + foreign). S Pass holders are "
                "counted within the overall DRC for the relevant sector. "
                "S Pass holders may apply for dependant privileges if they "
                "earn at least $6,000/month. The S Pass requires relevant "
                "qualifications (degree, diploma, or technical certificate) "
                "and work experience."
            ),
            "authority_level": "statute",
            "domain_name": "Work Pass Types",
            "effective_date": "2024-01-01",
            "applicability_rules": [
                {
                    "rule_type": "salary_threshold",
                    "criteria_type": "minimum",
                    "criteria_value": {
                        "general_minimum": 3150,
                        "financial_services_minimum": 3650,
                        "basis": "fixed_monthly_salary",
                        "age_progressive": True,
                    },
                    "notes": (
                        "Minimum salary for S Pass is $3,150 (general) or "
                        "$3,650 (financial services). Higher for older candidates."
                    ),
                },
                {
                    "rule_type": "quota",
                    "criteria_type": "maximum_proportion",
                    "criteria_value": {
                        "max_percentage": 15,
                        "effective_date": "2025-09-01",
                        "previous_percentage": 18,
                        "basis": "total_workforce",
                    },
                    "notes": (
                        "S Pass sub-DRC is 15% of total workforce from Sep "
                        "2025 (reduced from 18%)."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "A manufacturing company has 100 local employees and "
                        "wants to know how many S Pass holders it can hire "
                        "after September 2025."
                    ),
                    "calculation": {
                        "total_workforce_assumption": (
                            "100 local + existing foreign = total (iterative)"
                        ),
                        "s_pass_quota": "15% of total workforce",
                        "step_1": ("If total workforce is 100 local + 0 foreign = 100"),
                        "step_2": "15% of 100 = 15 S Pass holders maximum",
                        "step_3": (
                            "But adding 15 S Pass makes total = 115, so "
                            "15/115 = 13.0% -- within quota"
                        ),
                        "max_s_pass": (
                            "Iteratively: 100 / (1 - 0.15) = 117.6, so max "
                            "17 S Pass holders (17/117 = 14.5%)"
                        ),
                    },
                    "outcome": (
                        "The company can hire up to approximately 17 S Pass "
                        "holders while staying within the 15% sub-DRC limit. "
                        "Each S Pass holder will also attract a monthly levy "
                        "that varies based on the company's overall DRC "
                        "utilisation."
                    ),
                },
            ],
        },
        {
            "section": "EFMA-WP",
            "title": "Work Permit",
            "formal_text": (
                "The Work Permit (WP) is issued to semi-skilled and "
                "unskilled foreign workers in specified sectors: "
                "construction, manufacturing, marine shipyard, process, "
                "and services. There is no minimum salary requirement for "
                "Work Permits. Workers must be from approved source "
                "countries as determined by MOM for each sector. The "
                "maximum employment period varies by sector: construction "
                "and process sectors allow up to 14 years for Malaysian "
                "and up to 10 years for non-Malaysian workers. Employers "
                "must pay a foreign worker levy and provide a security "
                "bond ($5,000 for non-Malaysian workers)."
            ),
            "plain_summary": (
                "The Work Permit is for semi-skilled and unskilled foreign "
                "workers in sectors like construction, manufacturing, and "
                "services. There is no minimum salary, but workers must "
                "come from approved countries. Employers pay a monthly "
                "levy and must post a security bond for non-Malaysian "
                "workers."
            ),
            "interpretation_notes": (
                "Approved source countries vary by sector. Construction: "
                "Malaysia, China, India, Bangladesh, Thailand, Myanmar, "
                "Philippines, and others. Services: Malaysia, China, and "
                "a limited list. Manufacturing: broader list including "
                "PRC and non-traditional source countries. The security "
                "bond ($5,000 for non-Malaysians) is forfeited if the "
                "worker goes missing or if the employer fails to send the "
                "worker home. Workers must pass a medical examination "
                "before and during employment. Maximum age for new WP "
                "applications: 50 years (non-Malaysian) or 58 years "
                "(Malaysian) in most sectors."
            ),
            "authority_level": "statute",
            "domain_name": "Work Pass Types",
            "effective_date": "1990-01-01",
            "applicability_rules": [
                {
                    "rule_type": "sector_restriction",
                    "criteria_type": "inclusion",
                    "criteria_value": {
                        "sectors": [
                            "construction",
                            "manufacturing",
                            "marine_shipyard",
                            "process",
                            "services",
                        ],
                    },
                    "notes": (
                        "Work Permits are only issued for specified sectors. "
                        "Each sector has its own approved source country list."
                    ),
                },
                {
                    "rule_type": "source_country",
                    "criteria_type": "restriction",
                    "criteria_value": {
                        "varies_by_sector": True,
                        "security_bond": {
                            "non_malaysian": 5000,
                            "malaysian": 0,
                        },
                    },
                    "notes": (
                        "Workers must be from MOM-approved source countries "
                        "for the relevant sector."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "A services sector employer wants to hire a Work "
                        "Permit holder from China. The worker's monthly "
                        "salary is $800. The employer is within the basic "
                        "levy tier."
                    ),
                    "calculation": {
                        "salary": "$800/month (no minimum required for WP)",
                        "security_bond": "$5,000 (non-Malaysian worker)",
                        "monthly_levy": "$450 (services sector, basic tier)",
                        "total_monthly_cost": ("$800 salary + $450 levy = $1,250/month"),
                        "annual_levy_cost": "$450 x 12 = $5,400/year",
                    },
                    "outcome": (
                        "The employer's total monthly cost for this worker "
                        "is $1,250 ($800 salary plus $450 levy). The "
                        "employer must also post a $5,000 security bond, "
                        "provide acceptable housing, and maintain medical "
                        "and personal accident insurance for the worker."
                    ),
                },
            ],
        },
        # ====== FOREIGN WORKER QUOTAS ======
        {
            "section": "EFMA-DRC",
            "title": "Dependency Ratio Ceiling",
            "formal_text": (
                "The Dependency Ratio Ceiling (DRC) sets the maximum "
                "proportion of foreign workers an employer may hire. The "
                "DRC varies by sector: Services sector -- 35% overall; "
                "Manufacturing sector -- 60% overall (with a Work Permit "
                "sub-quota of 25%); Construction sector -- sector-specific "
                "and project-based; Process sector -- 60% overall (with a "
                "Work Permit sub-quota of 25%). The DRC is calculated as "
                "the ratio of foreign workers (S Pass + Work Permit) to "
                "the employer's total workforce (local employees + foreign "
                "workers). Employers who exceed the DRC cannot hire "
                "additional foreign workers until they are within the limit."
            ),
            "plain_summary": (
                "The DRC limits how many foreign workers a company can "
                "hire relative to its total workforce. Services companies "
                "can have up to 35% foreign workers. Manufacturing and "
                "process companies can have up to 60% (but only 25% on "
                "Work Permits). Construction quotas depend on the specific "
                "project."
            ),
            "interpretation_notes": (
                "The DRC is not a fixed number of workers but a ratio. As "
                "an employer hires more locals, the number of foreign "
                "workers they can employ also increases. The formula: "
                "maximum foreign workers = (DRC / (1 - DRC)) x local "
                "workers. For manufacturing at 60% DRC: max foreign = "
                "(0.6 / 0.4) x locals = 1.5 x locals. The S Pass has its "
                "own sub-DRC (15% from Sep 2025) within the overall DRC. "
                "Construction sector uses a Man-Year Entitlement system "
                "tied to project value. Employers must maintain the ratio "
                "at all times, not just at the point of application."
            ),
            "authority_level": "statute",
            "domain_name": "Foreign Worker Quotas",
            "effective_date": "2024-01-01",
            "applicability_rules": [
                {
                    "rule_type": "sector_variation",
                    "criteria_type": "quota_limits",
                    "criteria_value": {
                        "services": {
                            "overall_drc": 0.35,
                        },
                        "manufacturing": {
                            "overall_drc": 0.60,
                            "wp_sub_quota": 0.25,
                        },
                        "construction": {
                            "overall_drc": "project_specific",
                        },
                        "process": {
                            "overall_drc": 0.60,
                            "wp_sub_quota": 0.25,
                        },
                    },
                    "notes": (
                        "DRC limits vary by sector. Manufacturing and process "
                        "have WP sub-quotas. Construction uses MYE system."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "A services sector company has 50 local employees "
                        "and currently employs 15 foreign workers (10 WP + "
                        "5 S Pass). Can the company hire 5 more foreign "
                        "workers?"
                    ),
                    "calculation": {
                        "current_total_workforce": "50 local + 15 foreign = 65",
                        "current_foreign_ratio": "15 / 65 = 23.1%",
                        "drc_limit": "35%",
                        "max_foreign_at_current_local": (
                            "(0.35 / 0.65) x 50 = 26.9, so max 26 foreign " "workers"
                        ),
                        "remaining_headroom": "26 - 15 = 11 more foreign workers",
                        "after_hiring_5": "20 / 70 = 28.6% -- within 35% DRC",
                    },
                    "outcome": (
                        "Yes, the company can hire 5 more foreign workers. "
                        "The current ratio is 23.1%, and after hiring 5 "
                        "more it would be 28.6%, still within the 35% DRC. "
                        "The company has headroom for up to 11 additional "
                        "foreign workers at the current local headcount."
                    ),
                },
            ],
        },
        # ====== FOREIGN WORKER LEVY ======
        {
            "section": "EFMA-LEVY",
            "title": "Foreign Worker Levy",
            "formal_text": (
                "Employers of S Pass and Work Permit holders must pay a "
                "monthly foreign worker levy to MOM. The levy operates on "
                "a tiered system based on the employer's DRC utilisation. "
                "Services sector Work Permit: basic tier $450/month, "
                "Tier 2 $650/month. Manufacturing sector Work Permit: "
                "basic tier $450/month, Tier 2 $650/month. S Pass across "
                "all sectors: Tier 1 $550/month (for S Pass holders within "
                "10% of total workforce), Tier 2 $650/month (for S Pass "
                "holders exceeding 10% sub-DRC). The levy is payable "
                "monthly and is the responsibility of the employer. "
                "Employers may not recover levy costs from the worker's "
                "salary."
            ),
            "plain_summary": (
                "Employers pay a monthly levy for each S Pass and Work "
                "Permit holder. The levy amount depends on the sector and "
                "how many foreign workers the company already employs. "
                "Work Permit levies range from $450 to $650 per month. "
                "S Pass levies are $550 or $650 per month depending on "
                "the company's S Pass ratio. Employers cannot deduct the "
                "levy from the worker's salary."
            ),
            "interpretation_notes": (
                "The tiered levy system encourages employers to hire "
                "locals by making additional foreign workers progressively "
                "more expensive. The basic tier applies when the employer "
                "is well within their DRC; the higher tier kicks in as the "
                "employer approaches or exceeds sub-quota thresholds. "
                "Levy is charged from the day the work pass is issued to "
                "the day it is cancelled or expires. Partial month levies "
                "are pro-rated. Late payment of levy incurs a penalty of "
                "2% per month on the outstanding amount. Employers in "
                "financial difficulty may apply for levy deferment."
            ),
            "authority_level": "statute",
            "domain_name": "Foreign Worker Levy",
            "effective_date": "2024-01-01",
            "applicability_rules": [
                {
                    "rule_type": "pass_type",
                    "criteria_type": "levy_applicable",
                    "criteria_value": {
                        "applicable_passes": ["s_pass", "work_permit"],
                        "not_applicable": ["employment_pass"],
                    },
                    "notes": (
                        "Levy applies to S Pass and Work Permit holders only. "
                        "Employment Pass holders are not subject to levy."
                    ),
                },
                {
                    "rule_type": "levy_recovery_prohibition",
                    "criteria_type": "restriction",
                    "criteria_value": {
                        "cannot_deduct_from": "worker_salary",
                        "penalty": "fine_up_to_30000_or_imprisonment_12_months",
                    },
                    "notes": (
                        "It is an offence to recover levy costs from the "
                        "worker. Fine up to $30,000 or imprisonment up to "
                        "12 months or both."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "A services sector employer has 80 local employees "
                        "and 20 foreign workers (12 WP in basic tier, 4 WP "
                        "in Tier 2, and 4 S Pass holders). Calculate the "
                        "total monthly levy."
                    ),
                    "calculation": {
                        "wp_basic_tier": "12 x $450 = $5,400",
                        "wp_tier_2": "4 x $650 = $2,600",
                        "s_pass_ratio": "4 / 100 = 4% (within 10% sub-DRC)",
                        "s_pass_tier_1": "4 x $550 = $2,200",
                        "total_monthly_levy": "$5,400 + $2,600 + $2,200 = $10,200",
                        "annual_levy_cost": "$10,200 x 12 = $122,400",
                    },
                    "outcome": (
                        "The employer's total monthly levy is $10,200, or "
                        "$122,400 per year. All 4 S Pass holders fall "
                        "within the 10% Tier 1 threshold, so they attract "
                        "the lower $550 levy. If the employer hires more "
                        "S Pass workers beyond 10% of total workforce, "
                        "those additional S Pass holders would attract the "
                        "higher $650 Tier 2 levy."
                    ),
                },
            ],
        },
        # ====== COMPASS FRAMEWORK ======
        {
            "section": "EFMA-COMPASS",
            "title": "COMPASS Framework",
            "formal_text": (
                "The Complementarity Assessment Framework (COMPASS) is a "
                "points-based system for evaluating Employment Pass "
                "applications. It comprises 4 foundational criteria (C1-C4) "
                "and 2 bonus criteria (C5-C6). C1: Salary -- benchmarked "
                "against local PMET salaries in the same sector. C2: "
                "Qualifications -- recognised qualifications from top-tier "
                "institutions. C3: Diversity -- nationality diversity in "
                "the employer's PME workforce. C4: Support for local "
                "employment -- share of local PMEs in the firm relative to "
                "industry peers. C5 (Bonus): Skills shortage -- occupation "
                "on the Shortage Occupation List. C6 (Bonus): Strategic "
                "economic priorities -- partnership with government on "
                "economic objectives. Each criterion is scored 0, 10, or "
                "20 points. The pass mark is 40 points. Exemptions apply "
                "to candidates earning $22,500/month or more."
            ),
            "plain_summary": (
                "COMPASS is a points-based scoring system for EP "
                "applications. Candidates are scored on 4 main criteria "
                "(salary, qualifications, diversity, local hiring) and "
                "2 bonus criteria (skills shortage, strategic priorities). "
                "Each criterion scores 0, 10, or 20 points. A total of 40 "
                "points is needed to pass. Those earning $22,500/month or "
                "more are exempt."
            ),
            "interpretation_notes": (
                "COMPASS scoring is holistic -- a candidate who scores low "
                "on salary may still pass if they score well on "
                "qualifications and other criteria. The Shortage Occupation "
                "List (SOL) is reviewed periodically by MOM. For C3 "
                "(diversity), firms with a high concentration of any single "
                "nationality among their PMEs will score 0 on this "
                "criterion. For C4 (local employment), firms that employ a "
                "lower share of local PMEs compared to industry peers will "
                "score 0. MOM publishes sector benchmarks for salary (C1) "
                "and local PMET share (C4). The $22,500 exemption threshold "
                "means very highly paid candidates bypass COMPASS entirely. "
                "Intra-corporate transferees (ICTs) are assessed under a "
                "modified COMPASS framework."
            ),
            "authority_level": "statute",
            "domain_name": "COMPASS Framework",
            "effective_date": "2023-09-01",
            "applicability_rules": [
                {
                    "rule_type": "pass_type",
                    "criteria_type": "mandatory_for",
                    "criteria_value": {
                        "applies_to": "employment_pass",
                        "new_applications_from": "2023-09-01",
                        "renewals_from": "2024-09-01",
                        "exemption_salary_threshold": 22500,
                    },
                    "notes": (
                        "COMPASS is mandatory for all EP applications. "
                        "Exemptions for salary >= $22,500/month and certain "
                        "intra-corporate transfers."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "A mid-sized tech company applies for an EP for a "
                        "35-year-old data scientist earning $7,000/month. "
                        "The candidate has a Master's degree from a top-"
                        "ranked university. The company has 40% of one "
                        "nationality among its PMEs and a local PMET share "
                        "that is above the industry median."
                    ),
                    "calculation": {
                        "C1_salary": (
                            "$7,000 is above sector median for age 35 -- " "Score: 20 points"
                        ),
                        "C2_qualifications": (
                            "Master's from top-tier institution -- " "Score: 20 points"
                        ),
                        "C3_diversity": (
                            "40% single nationality concentration is moderate "
                            "-- Score: 10 points"
                        ),
                        "C4_local_employment": (
                            "Above industry median local PMET share -- " "Score: 10 points"
                        ),
                        "C5_bonus_skills": "Not on SOL -- Score: 0 points",
                        "C6_bonus_strategic": ("No strategic partnership -- Score: 0 points"),
                        "total": "20 + 20 + 10 + 10 + 0 + 0 = 60 points",
                    },
                    "outcome": (
                        "The candidate scores 60 points, well above the 40-"
                        "point pass mark. The EP application is likely to be "
                        "approved on COMPASS grounds. The strong salary and "
                        "qualifications scores compensate for moderate "
                        "diversity and local employment scores."
                    ),
                },
            ],
        },
        # ====== FAIR CONSIDERATION FRAMEWORK ======
        {
            "section": "EFMA-FCF",
            "title": "Fair Consideration Framework",
            "formal_text": (
                "Under the Fair Consideration Framework (FCF), employers "
                "must advertise job vacancies on the MyCareersFuture "
                "portal for at least 14 consecutive days before submitting "
                "an Employment Pass or S Pass application for a foreign "
                "candidate. The job advertisement must be open to "
                "Singaporeans and must accurately reflect the job scope, "
                "requirements, and salary. Exemptions from FCF advertising: "
                "(a) firms with fewer than 10 employees; (b) positions "
                "with a fixed monthly salary of $22,500 or above; (c) "
                "intra-corporate transferees; (d) short-term roles of 1 "
                "month or less. Employers on the FCF Watchlist or "
                "identified by the Tripartite Alliance for Fair and "
                "Progressive Employment Practices (TAFEP) for "
                "discriminatory hiring may face additional scrutiny, "
                "curtailed work pass privileges, or penalties."
            ),
            "plain_summary": (
                "Before hiring a foreign professional, employers must "
                "advertise the job on MyCareersFuture for at least 14 "
                "days to give Singaporeans a fair chance to apply. Small "
                "companies (fewer than 10 employees), very high-salary "
                "roles ($22,500+/month), and internal company transfers "
                "are exempt. Companies caught discriminating against "
                "locals may lose the ability to hire foreign workers."
            ),
            "interpretation_notes": (
                "The FCF is not a law by itself but is enforced through "
                "MOM's administrative powers over work pass approvals. "
                "TAFEP investigates complaints and monitors firms with "
                "unusually low local hiring. Firms placed on the FCF "
                "Watchlist will have their EP and S Pass applications "
                "scrutinised more closely and may face longer processing "
                "times or rejections. The job ad must not contain "
                "discriminatory language (e.g., specifying nationality, "
                "race, or language unless it is a genuine job requirement). "
                "Employers must interview qualified local candidates in "
                "good faith."
            ),
            "authority_level": "tripartite_guideline",
            "domain_name": "Work Pass Types",
            "effective_date": "2014-08-01",
            "applicability_rules": [
                {
                    "rule_type": "firm_size",
                    "criteria_type": "exemption",
                    "criteria_value": {
                        "exempt_below_employees": 10,
                        "exempt_salary_above": 22500,
                        "exempt_categories": [
                            "intra_corporate_transferees",
                            "short_term_roles_under_1_month",
                        ],
                    },
                    "notes": (
                        "Small firms (<10 employees), high-salary roles "
                        "($22,500+/month), ICTs, and short-term roles are "
                        "exempt from FCF advertising."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "A company with 50 employees wants to hire a "
                        "marketing manager from overseas on an EP with a "
                        "salary of $6,000/month. The company has not "
                        "previously been flagged by TAFEP."
                    ),
                    "calculation": {
                        "firm_size_check": "50 employees > 10 -- not exempt",
                        "salary_check": "$6,000 < $22,500 -- not exempt",
                        "fcf_requirement": ("Must advertise on MyCareersFuture for 14 days"),
                        "timeline": (
                            "Post job ad -> wait 14 days -> interview local "
                            "candidates -> if no suitable local found -> "
                            "submit EP application"
                        ),
                    },
                    "outcome": (
                        "The company must advertise the marketing manager "
                        "position on MyCareersFuture for at least 14 "
                        "consecutive days before applying for the EP. The "
                        "company should document its efforts to consider "
                        "local candidates. If TAFEP later inquires, the "
                        "company must show evidence of fair consideration."
                    ),
                },
            ],
        },
        # ====== EMPLOYER OBLIGATIONS ======
        {
            "section": "EFMA-OBLIG",
            "title": "Employer Obligations for Foreign Workers",
            "formal_text": (
                "Employers of Work Permit holders have the following "
                "statutory obligations under the EFMA and its regulations: "
                "(a) Housing -- provide acceptable accommodation that meets "
                "Temporary Occupation Licence (TOL) standards or approved "
                "dormitory requirements. (b) Medical insurance -- maintain "
                "medical insurance with a minimum coverage of $15,000 per "
                "year for the worker's inpatient care and day surgery. "
                "(c) Personal accident insurance -- maintain personal "
                "accident insurance with minimum coverage of $40,000 for "
                "accidental death and $40,000 for permanent disability. "
                "(d) Upkeep and maintenance -- bear the costs of the "
                "worker's upkeep and maintenance, including adequate food, "
                "medical treatment, and acceptable living conditions. "
                "(e) Repatriation -- pay for the worker's repatriation at "
                "the end of employment or upon pass cancellation. "
                "(f) Travel documents -- must not retain the worker's "
                "passport or travel document. Contravention is an offence "
                "with penalties including fines up to $10,000 and/or "
                "imprisonment up to 12 months."
            ),
            "plain_summary": (
                "Employers who hire Work Permit holders must provide proper "
                "housing, medical insurance (at least $15,000 coverage), "
                "personal accident insurance (at least $40,000 coverage), "
                "and cover basic living needs. The employer must pay for "
                "the worker's flight home when employment ends and cannot "
                "keep the worker's passport. Breaking these rules can "
                "result in fines up to $10,000 or jail."
            ),
            "interpretation_notes": (
                "Housing standards for WP holders are regulated by MOM and "
                "the Building and Construction Authority. Dormitories must "
                "meet minimum space requirements (4.5 sqm per resident). "
                "Medical insurance must cover the worker from the date of "
                "arrival to the date of departure. The personal accident "
                "insurance requirement was increased to $40,000 in 2021. "
                "Retaining a worker's passport is a criminal offence -- "
                "even if the worker 'consents'. Employers must also ensure "
                "workers are paid on time (within 7 days of salary period) "
                "and are not charged for recruitment costs in excess of "
                "1 month's salary. Common violations that result in work "
                "pass revocation: late salary payment, poor housing, no "
                "insurance coverage."
            ),
            "authority_level": "statute",
            "domain_name": "Employer Obligations",
            "effective_date": "2021-01-01",
            "applicability_rules": [
                {
                    "rule_type": "pass_type",
                    "criteria_type": "primary_applicability",
                    "criteria_value": {
                        "primary": ["work_permit"],
                        "partial": ["s_pass"],
                        "notes": (
                            "Full obligations apply to WP holders. Some "
                            "obligations (medical insurance, no passport "
                            "retention) also apply to S Pass holders."
                        ),
                    },
                    "notes": (
                        "Primary obligations for WP employers. Some "
                        "obligations extend to S Pass employers."
                    ),
                },
            ],
            "practical_examples": [
                {
                    "scenario": (
                        "A construction company is hiring 10 Work Permit "
                        "holders from Bangladesh. Calculate the minimum "
                        "insurance and mandatory costs beyond salary."
                    ),
                    "calculation": {
                        "medical_insurance_per_worker": "$15,000 minimum annual coverage",
                        "medical_insurance_premium_estimate": (
                            "approximately $200-$400 per worker per year"
                        ),
                        "personal_accident_per_worker": "$40,000 coverage",
                        "accident_insurance_premium_estimate": (
                            "approximately $150-$300 per worker per year"
                        ),
                        "security_bond_per_worker": "$5,000 (non-Malaysian)",
                        "total_security_bonds": "$5,000 x 10 = $50,000",
                        "repatriation_estimate": (
                            "approximately $500-$800 per worker (one-way flight)"
                        ),
                        "annual_insurance_cost_10_workers": (
                            "($300 + $225) x 10 = approximately $5,250/year"
                        ),
                    },
                    "outcome": (
                        "Beyond salaries and levies, the employer must budget "
                        "for: security bonds ($50,000 total, refundable), "
                        "annual insurance premiums (approximately $5,250 for "
                        "10 workers), and repatriation costs ($5,000-$8,000 "
                        "at the end). The employer must also provide "
                        "acceptable housing (dormitory or equivalent) and "
                        "cannot retain the workers' passports."
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
            "source_section": "EFMA-EP",
            "target_section": "EFMA-COMPASS",
            "relationship_type": "supplements",
            "notes": (
                "Employment Pass applications must pass the COMPASS "
                "framework assessment (new applications from Sep 2023, "
                "renewals from Sep 2024)."
            ),
        },
        {
            "source_section": "EFMA-SP",
            "target_section": "EFMA-DRC",
            "relationship_type": "supplements",
            "notes": (
                "S Pass holders are subject to the Dependency Ratio "
                "Ceiling with a specific sub-quota (15% from Sep 2025)."
            ),
        },
        {
            "source_section": "EFMA-WP",
            "target_section": "EFMA-DRC",
            "relationship_type": "supplements",
            "notes": (
                "Work Permit holders are subject to sector-specific " "Dependency Ratio Ceilings."
            ),
        },
        {
            "source_section": "EFMA-WP",
            "target_section": "EFMA-LEVY",
            "relationship_type": "supplements",
            "notes": (
                "Work Permit holders attract foreign worker levies at "
                "rates determined by sector and DRC utilisation tier."
            ),
        },
        {
            "source_section": "EFMA-SP",
            "target_section": "EFMA-LEVY",
            "relationship_type": "supplements",
            "notes": (
                "S Pass holders attract foreign worker levies at tiered "
                "rates based on the employer's S Pass ratio."
            ),
        },
        {
            "source_section": "EFMA-EP",
            "target_section": "EFMA-FCF",
            "relationship_type": "supplements",
            "notes": (
                "EP applications require compliance with the Fair "
                "Consideration Framework, including job advertising on "
                "MyCareersFuture for 14 days (unless exempt)."
            ),
        },
        {
            "source_section": "EFMA-WP",
            "target_section": "EFMA-OBLIG",
            "relationship_type": "supplements",
            "notes": (
                "Employers of Work Permit holders have additional "
                "statutory obligations including housing, insurance, "
                "upkeep, and repatriation."
            ),
        },
    ]


# ------------------------------------------------------------------
# Rate tables
# ------------------------------------------------------------------


def _rate_tables() -> list[dict]:
    return [
        {
            "table_type": "foreign_worker_levy",
            "name": "Services Sector WP Levy - Tier 1 (Basic)",
            "rate_value": 450.00,
            "rate_unit": "SGD/month",
            "effective_date": "2024-01-01",
            "source_url": "https://www.mom.gov.sg/passes-and-permits/work-permit-for-foreign-worker/foreign-worker-levy",
            "metadata": {
                "sector": "services",
                "pass_type": "work_permit",
                "tier": 1,
                "tier_label": "basic",
            },
        },
        {
            "table_type": "foreign_worker_levy",
            "name": "Services Sector WP Levy - Tier 2",
            "rate_value": 650.00,
            "rate_unit": "SGD/month",
            "effective_date": "2024-01-01",
            "source_url": "https://www.mom.gov.sg/passes-and-permits/work-permit-for-foreign-worker/foreign-worker-levy",
            "metadata": {
                "sector": "services",
                "pass_type": "work_permit",
                "tier": 2,
                "tier_label": "higher",
            },
        },
        {
            "table_type": "foreign_worker_levy",
            "name": "Manufacturing Sector WP Levy - Tier 1 (Basic)",
            "rate_value": 450.00,
            "rate_unit": "SGD/month",
            "effective_date": "2024-01-01",
            "source_url": "https://www.mom.gov.sg/passes-and-permits/work-permit-for-foreign-worker/foreign-worker-levy",
            "metadata": {
                "sector": "manufacturing",
                "pass_type": "work_permit",
                "tier": 1,
                "tier_label": "basic",
            },
        },
        {
            "table_type": "foreign_worker_levy",
            "name": "Manufacturing Sector WP Levy - Tier 2",
            "rate_value": 650.00,
            "rate_unit": "SGD/month",
            "effective_date": "2024-01-01",
            "source_url": "https://www.mom.gov.sg/passes-and-permits/work-permit-for-foreign-worker/foreign-worker-levy",
            "metadata": {
                "sector": "manufacturing",
                "pass_type": "work_permit",
                "tier": 2,
                "tier_label": "higher",
            },
        },
        {
            "table_type": "foreign_worker_levy",
            "name": "S Pass Levy - Tier 1 (up to 10% sub-DRC)",
            "rate_value": 550.00,
            "rate_unit": "SGD/month",
            "effective_date": "2024-01-01",
            "source_url": "https://www.mom.gov.sg/passes-and-permits/s-pass/s-pass-levy",
            "metadata": {
                "sector": "all",
                "pass_type": "s_pass",
                "tier": 1,
                "tier_label": "up_to_10_percent",
            },
        },
        {
            "table_type": "foreign_worker_levy",
            "name": "S Pass Levy - Tier 2 (above 10% sub-DRC)",
            "rate_value": 650.00,
            "rate_unit": "SGD/month",
            "effective_date": "2024-01-01",
            "source_url": "https://www.mom.gov.sg/passes-and-permits/s-pass/s-pass-levy",
            "metadata": {
                "sector": "all",
                "pass_type": "s_pass",
                "tier": 2,
                "tier_label": "above_10_percent",
            },
        },
    ]
