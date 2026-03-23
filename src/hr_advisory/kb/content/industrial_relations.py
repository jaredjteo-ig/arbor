"""Industrial Relations Act & Retrenchment -- structured content bundle.

Covers:
- Industrial Relations Act (Cap 136): Trade unions, collective agreements,
  industrial disputes, conciliation, arbitration, strikes/lockouts
- Retrenchment procedures: MOM notification, consultation, benefits,
  fair retrenchment practices
- Collective bargaining framework: Recognition, negotiation, lodging,
  IAC certification, enforcement

All content reflects legislation and guidelines as at 1 January 2025.
"""


def get_bundle() -> dict:
    """Return the Industrial Relations content bundle."""
    return {
        "act": _act(),
        "domains": _domains(),
        "provisions": _provisions(),
        "cross_references": _cross_references(),
        "rate_tables": [],
    }


def _act() -> dict:
    return {
        "title": "Industrial Relations Act",
        "short_name": "IRA",
        "authority_type": "statute",
        "issuing_body": "Ministry of Manpower",
        "official_url": "https://sso.agc.gov.sg/Act/IRA1960",
        "is_active": True,
    }


def _domains() -> list[dict]:
    return [
        {
            "name": "Collective Bargaining",
            "description": (
                "Union recognition, collective agreements, negotiation "
                "procedures, and IAC certification."
            ),
        },
        {
            "name": "Industrial Disputes",
            "description": (
                "Conciliation, arbitration, strikes, lockouts, and "
                "dispute resolution procedures."
            ),
        },
        {
            "name": "Retrenchment",
            "description": (
                "Retrenchment procedures, MOM notification, consultation "
                "with unions, benefits, and fair retrenchment practices."
            ),
        },
    ]


def _provisions() -> list[dict]:
    return [
        # -- Collective Agreements --
        {
            "section": "IRA-S17",
            "title": "Notification of Collective Agreement",
            "formal_text": (
                "Section 17 of the Industrial Relations Act. Every collective "
                "agreement shall be lodged with the Industrial Arbitration Court "
                "within one week after it has been signed by the parties. The "
                "Court shall certify the collective agreement if it is in "
                "conformity with this Act."
            ),
            "plain_summary": (
                "After signing a collective agreement with the union, you must "
                "lodge it with the Industrial Arbitration Court within one week. "
                "The Court reviews and certifies it, after which it becomes "
                "legally binding."
            ),
            "interpretation_notes": (
                "Steps after concluding a collective agreement:\n"
                "1. Sign the CA — both employer and union representatives\n"
                "2. Lodge with IAC within 1 week of signing\n"
                "3. IAC reviews for legality and compliance\n"
                "4. IAC certifies — CA becomes legally binding\n"
                "5. Implement: update payroll, HR policies, employee handbooks\n"
                "6. Communicate to all affected employees\n"
                "7. Train managers on new terms\n\n"
                "A CA has a maximum duration of 3 years. It covers terms like "
                "wages, hours, leave, retrenchment benefits, and grievance "
                "procedures. Once certified, neither party can unilaterally "
                "vary the terms. Any dispute about interpretation goes to the "
                "IAC for resolution.\n\n"
                "Common mistake: Not lodging with IAC — the CA is not "
                "enforceable until certified."
            ),
            "authority_level": "statute",
            "domain_name": "Collective Bargaining",
            "effective_date": "1960-08-15",
            "applicability_rules": [
                {
                    "rule_type": "worker_type",
                    "criteria_type": "inclusion",
                    "criteria_value": ["unionised employees"],
                }
            ],
            "practical_examples": [
                {
                    "scenario": "Company concludes 2-year CA with union",
                    "calculation": {
                        "step_1": "Sign CA with both parties",
                        "step_2": "Lodge with IAC within 7 days",
                        "step_3": "IAC certifies within 2-4 weeks",
                        "step_4": "Update payroll and HR systems",
                        "step_5": "Brief all affected employees",
                    },
                    "outcome": "CA becomes legally binding after IAC certification",
                }
            ],
        },
        {
            "section": "IRA-S18",
            "title": "Duration of Collective Agreement",
            "formal_text": (
                "Section 18 of the Industrial Relations Act. A collective "
                "agreement shall be for a period not exceeding 3 years. Where "
                "no period is specified, it shall be deemed to be for 3 years "
                "from the date of certification."
            ),
            "plain_summary": (
                "A collective agreement lasts up to 3 years. If no duration is "
                "specified, it defaults to 3 years from the date of IAC "
                "certification."
            ),
            "interpretation_notes": (
                "Best practice is to specify the duration explicitly in the CA. "
                "Renegotiation should begin 3-6 months before expiry. During "
                "renegotiation, the existing CA continues to apply until a new "
                "one is certified or the IAC makes an award."
            ),
            "authority_level": "statute",
            "domain_name": "Collective Bargaining",
            "effective_date": "1960-08-15",
            "applicability_rules": [],
            "practical_examples": [],
        },
        {
            "section": "IRA-S18A",
            "title": "Binding Effect of Collective Agreement",
            "formal_text": (
                "Section 18A of the Industrial Relations Act. A certified "
                "collective agreement shall be binding on the parties to the "
                "agreement and on every employee who is a member of the trade "
                "union that is a party to the agreement."
            ),
            "plain_summary": (
                "Once certified by the IAC, a collective agreement is legally "
                "binding on the employer, the union, and all union members. "
                "Neither party can unilaterally change the terms."
            ),
            "interpretation_notes": (
                "The binding effect means:\n"
                "- Employer must comply with all CA terms (wages, hours, "
                "benefits, retrenchment procedures)\n"
                "- Union members are bound by CA terms (no individual "
                "negotiation for better terms on CA-covered matters)\n"
                "- Breach of CA can be referred to the IAC\n"
                "- Non-union employees are NOT automatically covered, but "
                "many employers extend CA terms to all employees for fairness\n\n"
                "Key risk: Unilateral variation of CA terms is an unfair "
                "labour practice and can trigger industrial action."
            ),
            "authority_level": "statute",
            "domain_name": "Collective Bargaining",
            "effective_date": "1960-08-15",
            "applicability_rules": [],
            "practical_examples": [],
        },
        # -- Union Recognition --
        {
            "section": "IRA-S17A",
            "title": "Recognition of Trade Unions",
            "formal_text": (
                "Section 17A of the Industrial Relations Act. Where a trade "
                "union of employees seeks recognition from an employer for the "
                "purpose of collective bargaining, the trade union shall serve "
                "a claim for recognition on the employer."
            ),
            "plain_summary": (
                "A trade union seeking to represent your employees must formally "
                "request recognition from you. You must respond within 14 days. "
                "If you refuse, the union can refer the matter to the Minister "
                "for Manpower."
            ),
            "interpretation_notes": (
                "Recognition process:\n"
                "1. Union serves written claim on employer\n"
                "2. Employer must respond within 14 days\n"
                "3. If employer agrees — recognition is granted\n"
                "4. If employer refuses — union refers to Minister\n"
                "5. Minister may order a secret ballot of employees\n"
                "6. If majority vote for union — employer must recognise\n\n"
                "Once recognised, employer must negotiate in good faith on "
                "terms and conditions of employment. Refusal to negotiate "
                "is an unfair labour practice."
            ),
            "authority_level": "statute",
            "domain_name": "Collective Bargaining",
            "effective_date": "1960-08-15",
            "applicability_rules": [],
            "practical_examples": [],
        },
        # -- Retrenchment --
        {
            "section": "IRA-RETRENCH-NOTIFY",
            "title": "Retrenchment Notification to MOM",
            "formal_text": (
                "Under the Employment Act and MOM guidelines, employers who "
                "retrench 5 or more employees within any 6-month period must "
                "notify the Ministry of Manpower within 5 working days after "
                "notifying the affected employees."
            ),
            "plain_summary": (
                "If you retrench 5 or more employees within 6 months, you "
                "must notify MOM within 5 working days of informing the "
                "affected employees. Use the MOM online portal."
            ),
            "interpretation_notes": (
                "Retrenchment notification requirements:\n"
                "- Threshold: 5+ employees in 6 months\n"
                "- Timeline: Within 5 working days AFTER notifying employees\n"
                "- Method: Online via MOM portal (mandatory retrenchment "
                "notification form)\n"
                "- Content: Number of employees, reasons, effective dates\n\n"
                "Failure to notify is an offence. MOM uses the data for "
                "workforce planning and to connect retrenched workers with "
                "career support services (Workforce Singapore).\n\n"
                "For unionised companies: You must notify and consult the "
                "union BEFORE notifying employees. The union consultation "
                "must be in good faith, not just informing."
            ),
            "authority_level": "guideline",
            "domain_name": "Retrenchment",
            "effective_date": "2024-01-01",
            "applicability_rules": [],
            "practical_examples": [
                {
                    "scenario": "Company retrenches 8 employees over 3 months",
                    "calculation": {
                        "threshold_check": "8 >= 5 employees → notification required",
                        "timeline": "5 working days after informing employees",
                        "method": "MOM online portal",
                    },
                    "outcome": "Must notify MOM within 5 working days",
                }
            ],
        },
        {
            "section": "IRA-RETRENCH-UNION",
            "title": "Retrenchment in Unionised Companies",
            "formal_text": (
                "Under the Industrial Relations Act and tripartite guidelines, "
                "employers with unionised workforces must engage the union "
                "early in the retrenchment process. The collective agreement "
                "typically contains retrenchment provisions that must be "
                "followed."
            ),
            "plain_summary": (
                "If your company is unionised, you must notify and consult "
                "the union before retrenching any employees. Check your "
                "collective agreement for specific retrenchment procedures, "
                "notice periods, and benefit requirements."
            ),
            "interpretation_notes": (
                "Retrenchment procedure for unionised companies:\n\n"
                "STEP 1 — Check your Collective Agreement first:\n"
                "- Retrenchment clause / redundancy provisions\n"
                "- Notice period requirements\n"
                "- Retrenchment benefit formula\n"
                "- Consultation obligations with union\n"
                "- Selection criteria (LIFO, performance, skills)\n\n"
                "STEP 2 — Inform and consult the union (MANDATORY):\n"
                "- Notify union BEFORE informing employees\n"
                "- Share: reasons, numbers, categories, timeline, criteria, benefits\n"
                "- This is good faith CONSULTATION, not just notification\n"
                "- Expect negotiation on benefit quantum and scope\n\n"
                "STEP 3 — Apply fair retrenchment practices:\n"
                "- Selection criteria must be objective and non-discriminatory\n"
                "- Cannot retrench based on age, gender, pregnancy, union membership\n"
                "- LIFO (Last In, First Out) is common but not mandatory\n\n"
                "STEP 4 — Pay retrenchment benefits:\n"
                "- If covered under CA: follow CA formula\n"
                "- Market benchmark: 2 weeks to 1 month salary per year of service\n"
                "- For employees with 2+ years service under EA: employers are "
                "encouraged (not legally required) to pay retrenchment benefits\n\n"
                "STEP 5 — Support affected employees:\n"
                "- Career transition support / outplacement\n"
                "- Job matching via NTUC, WSG\n"
                "- Time off for job search during notice period\n\n"
                "HIGH-RISK MISTAKES:\n"
                "- Informing employees before union → breach of IRA\n"
                "- Treating consultation as a formality → unfair labour practice\n"
                "- Inconsistent selection criteria → discrimination risk\n"
                "- Poor documentation → vulnerability at IAC\n\n"
                "The 'Lazada situation' (2024) — lessons:\n"
                "- Mass retrenchment via video call without warning\n"
                "- No prior consultation with affected employees or union\n"
                "- Immediate access card deactivation (perceived as undignified)\n"
                "- MOM intervened, company issued public apology\n"
                "- Key lesson: process matters as much as legal compliance — "
                "treat employees with dignity throughout the process"
            ),
            "authority_level": "statute",
            "domain_name": "Retrenchment",
            "effective_date": "2024-01-01",
            "applicability_rules": [],
            "practical_examples": [
                {
                    "scenario": "Unionised company retrenches 20 employees",
                    "calculation": {
                        "step_1": "Check CA retrenchment clause",
                        "step_2": "Consult union — share reasons, numbers, criteria",
                        "step_3": "Negotiate benefits (e.g. 1 month/year of service)",
                        "step_4": "Notify MOM within 5 working days",
                        "step_5": "Pay benefits + final salary on last day",
                    },
                    "outcome": (
                        "With 20 employees at avg 5 years service, avg $4,000/month: "
                        "retrenchment benefits = 20 x 5 x $4,000 = $400,000 total"
                    ),
                }
            ],
        },
        {
            "section": "IRA-RETRENCH-BENEFITS",
            "title": "Retrenchment Benefits and Market Benchmarks",
            "formal_text": (
                "Under the Employment Act, there is no statutory minimum "
                "retrenchment benefit. However, the tripartite guidelines "
                "strongly encourage employers to pay retrenchment benefits "
                "to employees with at least 2 years of service."
            ),
            "plain_summary": (
                "Singapore law does not mandate a minimum retrenchment payout, "
                "but employers are strongly encouraged to pay benefits, "
                "especially for employees with 2+ years of service. The market "
                "standard is 2 weeks to 1 month salary per year of service."
            ),
            "interpretation_notes": (
                "Retrenchment benefit benchmarks:\n\n"
                "LEGAL POSITION:\n"
                "- No statutory minimum under Employment Act\n"
                "- Collective agreements may specify a formula\n"
                "- Employment contracts may specify benefits\n"
                "- Tripartite guidelines: 'encouraged' for 2+ years service\n\n"
                "MARKET BENCHMARKS (2024-2025):\n"
                "- SMEs (< 50 employees): 2 weeks salary per year of service\n"
                "- Mid-size (50-200): 2-3 weeks salary per year\n"
                "- Large / MNC: 3 weeks to 1 month per year\n"
                "- Unionised companies: Typically 1 month per year (CA-defined)\n"
                "- Senior management: Often negotiated individually\n\n"
                "CALCULATION EXAMPLE:\n"
                "Employee: 5 years service, $5,000/month salary\n"
                "- At 2 weeks/year: 5 x ($5,000 / 4.33 x 2) = $11,547\n"
                "- At 1 month/year: 5 x $5,000 = $25,000\n\n"
                "ADDITIONAL OBLIGATIONS:\n"
                "- Outstanding salary up to last day\n"
                "- Unused annual leave encashment\n"
                "- Notice period payment (or salary in lieu)\n"
                "- CPF contributions on final salary\n"
                "- Any contractual bonuses or commissions earned\n\n"
                "Payment deadline:\n"
                "- If employer terminates: on the last day of employment\n"
                "- If employee is given notice: on the last day or within "
                "3 working days"
            ),
            "authority_level": "guideline",
            "domain_name": "Retrenchment",
            "effective_date": "2024-01-01",
            "applicability_rules": [],
            "practical_examples": [
                {
                    "scenario": "SME retrenches employee with 5 years service at $5,000/month",
                    "calculation": {
                        "at_2_weeks_per_year": "$5,000 / 4.33 x 2 x 5 = $11,547",
                        "at_1_month_per_year": "$5,000 x 5 = $25,000",
                        "unused_leave": "10 days x ($5,000/22) = $2,273",
                        "total_range": "$13,820 to $27,273",
                    },
                    "outcome": "Total retrenchment cost per employee: $13,820 to $27,273",
                }
            ],
        },
        # -- Industrial Disputes --
        {
            "section": "IRA-S10",
            "title": "Conciliation by Commissioner",
            "formal_text": (
                "Section 10 of the Industrial Relations Act. Where a trade "
                "dispute exists or is apprehended, the Commissioner may take "
                "steps to conciliate the dispute. The Commissioner may call "
                "conferences of the parties and use his best endeavours to "
                "settle the dispute."
            ),
            "plain_summary": (
                "When a dispute arises between employer and union, the "
                "Commissioner for Labour may step in to mediate. Both parties "
                "are expected to attend conciliation conferences in good faith."
            ),
            "interpretation_notes": (
                "Dispute resolution hierarchy:\n"
                "1. Internal grievance procedure (as per CA)\n"
                "2. Conciliation by Commissioner for Labour\n"
                "3. Referral to Industrial Arbitration Court (IAC)\n"
                "4. IAC makes binding award\n\n"
                "Conciliation is voluntary but strongly expected. If conciliation "
                "fails, either party can refer the dispute to the IAC for "
                "binding arbitration. Strikes and lockouts are permitted only "
                "after conciliation has been attempted and failed, and with "
                "proper notice."
            ),
            "authority_level": "statute",
            "domain_name": "Industrial Disputes",
            "effective_date": "1960-08-15",
            "applicability_rules": [],
            "practical_examples": [],
        },
        {
            "section": "IRA-S26",
            "title": "Strikes and Lockouts",
            "formal_text": (
                "Section 26 of the Industrial Relations Act. No employer shall "
                "commence a lockout and no trade union shall commence a strike "
                "unless the dispute has been reported to the Commissioner and "
                "14 days have elapsed since the date of reporting."
            ),
            "plain_summary": (
                "Strikes and lockouts are legal in Singapore but heavily "
                "regulated. A 14-day cooling-off period after reporting to the "
                "Commissioner is mandatory before any industrial action."
            ),
            "interpretation_notes": (
                "In essential services (water, electricity, gas, telecommunications), "
                "strikes require 14 days written notice to the employer. In practice, "
                "strikes are extremely rare in Singapore — the tripartite system "
                "(government, employers, unions via NTUC) strongly favours negotiation "
                "and mediation over industrial action.\n\n"
                "The last significant strike in Singapore was in 2012 (SMRT bus drivers). "
                "The participants were prosecuted and some deported."
            ),
            "authority_level": "statute",
            "domain_name": "Industrial Disputes",
            "effective_date": "1960-08-15",
            "applicability_rules": [],
            "practical_examples": [],
        },
    ]


def _cross_references() -> list[dict]:
    return [
        {
            "from_section": "IRA-RETRENCH-UNION",
            "to_section": "EA-S10",
            "relationship": "supplements",
            "description": "Notice period under EA applies alongside IRA retrenchment procedures",
        },
        {
            "from_section": "IRA-RETRENCH-BENEFITS",
            "to_section": "EA-S21",
            "relationship": "supplements",
            "description": "Final salary payment deadline under EA applies to retrenchment payouts",
        },
        {
            "from_section": "IRA-S17",
            "to_section": "IRA-S18A",
            "relationship": "parent",
            "description": "Lodging requirement leads to binding effect after certification",
        },
    ]
