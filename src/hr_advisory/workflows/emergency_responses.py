"""Emergency HR response data — structured crisis guidance for Singapore SMEs.

Each emergency type provides:
- Immediate obligations (with deadlines)
- Documents to gather
- Step-by-step process
- When to seek professional help
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EmergencyStep:
    step_number: int
    action: str
    deadline: str
    detail: str


@dataclass(frozen=True)
class EmergencyResponse:
    topic_id: str
    title: str
    icon: str
    description: str
    immediate_obligations: list[EmergencyStep]
    documents_needed: list[str]
    process_steps: list[EmergencyStep]
    when_to_get_help: list[str]
    key_provisions: list[str]


EMERGENCY_RESPONSES: dict[str, EmergencyResponse] = {
    "tadm-claim": EmergencyResponse(
        topic_id="tadm-claim",
        title="TADM / ECT Claim Against You",
        icon="gavel",
        description="An employee or ex-employee has filed a claim with the Tripartite Alliance for Dispute Management (TADM) or Employment Claims Tribunal (ECT).",
        immediate_obligations=[
            EmergencyStep(
                1,
                "Do NOT contact the claimant directly about the claim",
                "Immediately",
                "All communication should go through TADM mediation.",
            ),
            EmergencyStep(
                2,
                "Gather all relevant employment records",
                "Within 3 working days",
                "TADM will request documentation during mediation.",
            ),
            EmergencyStep(
                3,
                "Attend the mediation session",
                "As scheduled by TADM",
                "Non-attendance may result in the claim proceeding to ECT without your input.",
            ),
        ],
        documents_needed=[
            "Employment contract and KET",
            "Payslips for the claim period",
            "Leave records",
            "Any written warnings or performance records",
            "Termination letter (if applicable)",
            "CPF contribution records",
            "Correspondence with the employee about the disputed matter",
        ],
        process_steps=[
            EmergencyStep(
                1,
                "Receive TADM notice",
                "Day 0",
                "You will receive written notice of the claim with details.",
            ),
            EmergencyStep(
                2,
                "Prepare your response and documents",
                "Days 1-3",
                "Organize all evidence supporting your position.",
            ),
            EmergencyStep(
                3,
                "Attend TADM mediation",
                "Typically within 4 weeks",
                "A mediator will help both parties reach resolution.",
            ),
            EmergencyStep(
                4,
                "If unresolved, claim proceeds to ECT",
                "Within 4 weeks of failed mediation",
                "ECT is a tribunal hearing — more formal than mediation.",
            ),
            EmergencyStep(
                5,
                "ECT hearing and decision",
                "Scheduled by ECT",
                "Tribunal makes a binding decision. Claims limited to $20,000 (or $30,000 with union).",
            ),
        ],
        when_to_get_help=[
            "The claim amount exceeds $10,000",
            "Multiple employees have filed claims simultaneously",
            "The claim involves allegations of discrimination or wrongful dismissal",
            "You are unsure whether your employment practices are compliant",
            "You need representation at ECT",
        ],
        key_provisions=["EA-S14-misconduct-dismissal", "EA-S22-final-payment", "TADM-ECT-process"],
    ),
    "workplace-injury": EmergencyResponse(
        topic_id="workplace-injury",
        title="Workplace Injury",
        icon="local_hospital",
        description="An employee has been injured at work. You have immediate legal obligations under the Work Injury Compensation Act (WICA) and Workplace Safety and Health Act (WSH Act).",
        immediate_obligations=[
            EmergencyStep(
                1,
                "Ensure the injured employee receives medical attention",
                "Immediately",
                "Call 995 for emergencies. Do NOT delay treatment.",
            ),
            EmergencyStep(
                2,
                "Secure the accident scene",
                "Immediately",
                "Preserve evidence. Do not disturb the scene for serious injuries.",
            ),
            EmergencyStep(
                3,
                "Report to MOM if serious injury or death",
                "Within 24 hours",
                "WSH (Incident Reporting) Regulations require immediate notification for fatal or dangerous incidents.",
            ),
            EmergencyStep(
                4,
                "File incident report with MOM via iReport",
                "Within 10 days",
                "Required for all workplace injuries resulting in >3 days MC.",
            ),
        ],
        documents_needed=[
            "Accident/incident report form",
            "Medical certificate and medical reports",
            "Witness statements",
            "Photos of the accident scene",
            "Employee's employment records",
            "Safety training records for the employee",
            "Risk assessment for the work activity",
            "WICA insurance policy details",
        ],
        process_steps=[
            EmergencyStep(
                1, "Provide immediate medical assistance", "Day 0", "Employee's health comes first."
            ),
            EmergencyStep(
                2,
                "Notify MOM via iReport",
                "Within 10 days",
                "Submit the incident report with all required details.",
            ),
            EmergencyStep(
                3,
                "Notify your WICA insurer",
                "Within 14 days",
                "Your insurer will manage the compensation claim.",
            ),
            EmergencyStep(
                4,
                "Continue paying medical leave wages",
                "Ongoing",
                "EA s89: Paid sick leave and hospitalisation leave apply.",
            ),
            EmergencyStep(
                5,
                "Cooperate with MOM investigation",
                "As required",
                "MOM may investigate workplace safety compliance.",
            ),
        ],
        when_to_get_help=[
            "The injury is fatal or results in permanent disability",
            "MOM has initiated a WSH investigation",
            "The employee disputes the compensation amount",
            "You do not have valid WICA insurance",
            "Multiple injuries have occurred at your workplace",
        ],
        key_provisions=["WICA-employer-obligations", "WSH-incident-reporting", "EA-S89-sick-leave"],
    ),
    "wrongful-dismissal": EmergencyResponse(
        topic_id="wrongful-dismissal",
        title="Wrongful Dismissal Allegation",
        icon="person_off",
        description="A terminated employee is alleging wrongful dismissal. This could lead to TADM mediation, ECT claim, or MOM investigation.",
        immediate_obligations=[
            EmergencyStep(
                1,
                "Review the termination decision and documentation",
                "Immediately",
                "Ensure you have written records of the reason for termination.",
            ),
            EmergencyStep(
                2,
                "Verify notice period was served or paid in lieu",
                "Immediately",
                "EA s10 and s11 require proper notice.",
            ),
            EmergencyStep(
                3,
                "Ensure all final payments are made",
                "Within 3 working days of last day",
                "EA s22: salary, leave encashment, any outstanding payments.",
            ),
            EmergencyStep(
                4,
                "File IR21 with IRAS",
                "At least 1 month before cessation",
                "Tax clearance is mandatory for all cessations.",
            ),
        ],
        documents_needed=[
            "Employment contract",
            "Termination letter with stated reason",
            "Performance appraisals and warning letters",
            "Evidence supporting the reason for termination",
            "Payslips and CPF records",
            "Proof of final payment",
            "Notice period calculation",
            "Any correspondence with the employee about the termination",
        ],
        process_steps=[
            EmergencyStep(
                1,
                "Document your position thoroughly",
                "Days 1-3",
                "Write down the timeline and reasons clearly.",
            ),
            EmergencyStep(
                2,
                "Review against TGFEP fair dismissal guidelines",
                "Days 1-3",
                "Ensure the dismissal was for valid reasons with proper process.",
            ),
            EmergencyStep(
                3,
                "If TADM claim filed, prepare for mediation",
                "Within 4 weeks",
                "Gather all documentation and attend mediation.",
            ),
            EmergencyStep(
                4,
                "If ECT proceeding, consider legal representation",
                "As scheduled",
                "ECT has a 1-year limitation from dismissal date.",
            ),
        ],
        when_to_get_help=[
            "The employee was dismissed during pregnancy or maternity leave",
            "The dismissal may relate to union activity or whistleblowing",
            "There are allegations of discrimination (age, race, gender, disability)",
            "You did not follow a proper due inquiry process (EA s14)",
            "Multiple wrongful dismissal claims have been filed",
        ],
        key_provisions=[
            "EA-S14-misconduct-dismissal",
            "EA-S10-notice",
            "EA-S11-salary-in-lieu",
            "TGFEP-fair-dismissal",
        ],
    ),
    "mom-inspection": EmergencyResponse(
        topic_id="mom-inspection",
        title="MOM Inspection or Audit",
        icon="policy",
        description="The Ministry of Manpower is conducting an inspection of your workplace. This could be routine or triggered by a complaint.",
        immediate_obligations=[
            EmergencyStep(
                1,
                "Cooperate fully with MOM officers",
                "Immediately",
                "Obstruction of MOM officers is a criminal offence.",
            ),
            EmergencyStep(
                2,
                "Designate a point of contact for the inspection",
                "Immediately",
                "One person should coordinate all information requests.",
            ),
            EmergencyStep(
                3,
                "Gather all required records",
                "As requested",
                "MOM can request records going back 2 years.",
            ),
        ],
        documents_needed=[
            "Employment contracts and KETs for all employees",
            "Payslips for the past 2 years",
            "CPF contribution records",
            "Leave records",
            "Working hours and overtime records",
            "Foreign worker employment passes and conditions",
            "Workplace safety and health records",
            "Insurance policies (WICA, etc.)",
        ],
        process_steps=[
            EmergencyStep(
                1, "MOM issues inspection notice", "Day 0", "May be scheduled or unannounced."
            ),
            EmergencyStep(
                2,
                "Prepare all requested documents",
                "Before inspection",
                "Organize by employee and category.",
            ),
            EmergencyStep(
                3,
                "MOM conducts on-site inspection",
                "Inspection day",
                "Officers may interview employees directly.",
            ),
            EmergencyStep(
                4,
                "MOM issues findings",
                "1-4 weeks after inspection",
                "May include rectification orders or prosecution notices.",
            ),
            EmergencyStep(
                5,
                "Rectify any findings within deadline",
                "As specified by MOM",
                "Failure to comply can result in prosecution.",
            ),
        ],
        when_to_get_help=[
            "MOM has found potential violations",
            "You are unsure if your records are complete",
            "The inspection involves foreign worker compliance",
            "MOM has issued a stop-work order",
            "Prosecution proceedings have been initiated",
        ],
        key_provisions=[
            "EA-S95-KETs",
            "EA-S88A-payslip",
            "EA-S21-salary-payment",
            "EFMA-conditions",
        ],
    ),
    "discrimination-complaint": EmergencyResponse(
        topic_id="discrimination-complaint",
        title="Discrimination or Harassment Complaint",
        icon="report_problem",
        description="An employee has raised a discrimination or harassment complaint. This could involve TAFEP investigation if escalated.",
        immediate_obligations=[
            EmergencyStep(
                1,
                "Take the complaint seriously — acknowledge receipt",
                "Within 24 hours",
                "Document the complaint in writing.",
            ),
            EmergencyStep(
                2,
                "Ensure the complainant is not subjected to retaliation",
                "Immediately",
                "Retaliation can result in additional claims.",
            ),
            EmergencyStep(
                3,
                "Begin internal investigation",
                "Within 1 week",
                "Appoint an impartial investigator (not the alleged harasser's manager).",
            ),
        ],
        documents_needed=[
            "Written complaint from the employee",
            "Company anti-harassment/discrimination policy",
            "Statements from all parties involved",
            "Witness statements",
            "Relevant email or message records",
            "HR records of any prior complaints",
        ],
        process_steps=[
            EmergencyStep(
                1, "Receive and document the complaint", "Day 0", "Record all details accurately."
            ),
            EmergencyStep(
                2,
                "Conduct confidential investigation",
                "Weeks 1-3",
                "Interview all relevant parties, review evidence.",
            ),
            EmergencyStep(
                3,
                "Determine findings and take action",
                "Week 3-4",
                "Outcomes may include mediation, warning, disciplinary action, or policy changes.",
            ),
            EmergencyStep(
                4,
                "Communicate outcome to all parties",
                "After investigation",
                "Both complainant and respondent should be informed.",
            ),
            EmergencyStep(
                5,
                "Follow up and monitor",
                "Ongoing",
                "Ensure no retaliation and the situation is resolved.",
            ),
        ],
        when_to_get_help=[
            "The complaint involves sexual harassment or assault",
            "A TAFEP complaint has been filed",
            "The alleged discriminator is in senior management",
            "Multiple complaints have been filed about the same person or issue",
            "The company does not have an anti-harassment policy",
        ],
        key_provisions=[
            "TGFEP-fair-employment",
            "TAFEP-complaint-process",
            "WFA-workplace-fairness",
        ],
    ),
    "data-breach": EmergencyResponse(
        topic_id="data-breach",
        title="Employee Data Breach",
        icon="security",
        description="Employee personal data has been exposed, leaked, or accessed without authorization. Singapore's PDPA requires prompt action.",
        immediate_obligations=[
            EmergencyStep(
                1,
                "Contain the breach",
                "Immediately",
                "Stop the unauthorized access, secure affected systems.",
            ),
            EmergencyStep(
                2,
                "Assess the scope of the breach",
                "Within 24 hours",
                "Determine what data was exposed and how many people are affected.",
            ),
            EmergencyStep(
                3,
                "Notify PDPC if significant harm likely",
                "Within 3 calendar days",
                "PDPA mandatory breach notification for notifiable data breaches.",
            ),
            EmergencyStep(
                4,
                "Notify affected individuals",
                "As soon as practicable",
                "If the breach is likely to result in significant harm.",
            ),
        ],
        documents_needed=[
            "Incident log with timeline",
            "List of affected data and individuals",
            "Description of data protection measures in place",
            "Evidence of how the breach occurred",
            "Remediation actions taken",
            "PDPC notification form (if applicable)",
        ],
        process_steps=[
            EmergencyStep(
                1,
                "Contain and assess the breach",
                "Day 0-1",
                "Identify scope and stop ongoing exposure.",
            ),
            EmergencyStep(
                2,
                "Notify PDPC (if notifiable breach)",
                "Within 3 days",
                "Use the PDPC data breach notification form.",
            ),
            EmergencyStep(
                3,
                "Notify affected individuals",
                "As soon as practicable",
                "Clear, plain language about what happened and what to do.",
            ),
            EmergencyStep(
                4,
                "Investigate root cause",
                "Weeks 1-2",
                "Determine how the breach occurred and fix the vulnerability.",
            ),
            EmergencyStep(
                5,
                "Review and strengthen data protection",
                "Ongoing",
                "Update policies, training, and technical measures.",
            ),
        ],
        when_to_get_help=[
            "The breach involves NRIC numbers, financial data, or health records",
            "More than 500 individuals are affected",
            "The breach was caused by a malicious attack",
            "You are unsure whether the breach is notifiable to PDPC",
            "Affected individuals have suffered or may suffer significant harm",
        ],
        key_provisions=[
            "PDPA-breach-notification",
            "PDPA-protection-obligation",
            "PDPA-accountability",
        ],
    ),
}


def get_emergency_response(topic_id: str) -> EmergencyResponse | None:
    """Get the emergency response for a given topic ID."""
    return EMERGENCY_RESPONSES.get(topic_id)


def list_emergency_topics() -> list[dict[str, str]]:
    """Return a summary list of all emergency topics."""
    return [
        {
            "topic_id": r.topic_id,
            "title": r.title,
            "icon": r.icon,
            "description": r.description,
        }
        for r in EMERGENCY_RESPONSES.values()
    ]
