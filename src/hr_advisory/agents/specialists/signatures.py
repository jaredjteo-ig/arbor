"""Kaizen signatures for HR domain specialist agents.

Each specialist shares a common output contract (advisory text, cited
provisions, confidence, risk tier, cross-domain flags) but has its own
domain-specific system prompt constraints.
"""

from kaizen import InputField, OutputField, Signature


# ---------------------------------------------------------------------------
# Base specialist inputs/outputs (shared across all 7 specialists)
# ---------------------------------------------------------------------------

# All specialists receive the same input shape and produce the same output
# shape.  The domain-specific behaviour is governed by the system prompt
# inside each agent, not by the signature.


class SpecialistSignature(Signature):
    """Base signature for all HR domain specialist agents.

    You are an expert in a specific Singapore HR regulatory domain.
    Given the user query, company context, and relevant provisions from
    the knowledge base, produce a structured advisory response scoped
    strictly to your domain.
    """

    __intent__ = "Produce domain-specific advisory output for an HR query"
    __guidelines__ = [
        "Only advise within your designated domain -- refuse out-of-scope queries",
        "Cite only provisions supplied in the relevant_provisions input",
        "Never fabricate section numbers or legislative references",
        "Flag any cross-domain implications so other specialists can address them",
    ]

    # Inputs
    query_text: str = InputField(
        description="The HR query from the SME user",
    )
    company_context: str = InputField(
        description="JSON string of company profile (headcount, sector, nationality mix, etc.)",
        default="{}",
    )
    relevant_provisions: str = InputField(
        description=(
            "JSON list of knowledge-base provisions relevant to this query, "
            "each with id, section, act, and text"
        ),
        default="[]",
    )
    conversation_history: str = InputField(
        description=(
            "Formatted string of previous conversation turns for multi-turn context. "
            "Each turn shows User: ... and Assistant: ... pairs."
        ),
        default="",
    )

    # Outputs
    answer_text: str = OutputField(
        description="Plain-language advisory answer scoped to this domain",
    )
    cited_provisions: str = OutputField(
        description=(
            "JSON list of provision citations used: "
            '[{"provision_id": int, "section": "...", "act": "..."}]'
        ),
    )
    confidence: str = OutputField(
        description="Confidence score as a decimal string between 0.0 and 1.0",
    )
    risk_tier: str = OutputField(
        description="Risk tier for this domain assessment: green, amber, or red",
    )
    cross_domain_flags: str = OutputField(
        description=("JSON list of other domain keys that may be affected, " 'e.g. ["cpf", "tax"]'),
    )


class EmploymentActSignature(SpecialistSignature):
    """Employment Act specialist.

    You are an expert on the Singapore Employment Act. You advise on
    Part IV protections, leave entitlements, termination, notice periods,
    salary, overtime, and related provisions.
    """

    __intent__ = "Advise on Employment Act matters"


class CPFSignature(SpecialistSignature):
    """CPF specialist.

    You are an expert on the Singapore Central Provident Fund Act.
    You advise on contribution rates, age bands, PR graduated rates,
    OW/AW ceilings, voluntary contributions, and employer obligations.
    """

    __intent__ = "Advise on CPF contribution and compliance matters"


class ForeignManpowerSignature(SpecialistSignature):
    """Foreign Manpower specialist.

    You are an expert on the Singapore Employment of Foreign Manpower Act.
    You advise on dependency ratio ceilings, levy tiers, COMPASS framework,
    pass types (EP, S Pass, WP), sector-specific rules, and quota management.
    """

    __intent__ = "Advise on foreign manpower regulations and pass requirements"


class FairEmploymentSignature(SpecialistSignature):
    """Fair Employment specialist.

    You are an expert on Singapore fair employment practices. You advise
    on TAFEP guidelines, the Workplace Fairness Legislation, flexible
    work arrangements, anti-discrimination requirements, and grievance
    handling best practices.
    """

    __intent__ = "Advise on fair employment and workplace fairness obligations"


class TaxSignature(SpecialistSignature):
    """Tax specialist.

    You are an expert on Singapore employer tax obligations under IRAS
    rules. You advise on benefits-in-kind treatment, tax clearance (IR21),
    withholding tax for non-residents, and Appendix 8A/8B reporting.
    """

    __intent__ = "Advise on employer tax obligations and IRAS compliance"


class WSHSignature(SpecialistSignature):
    """Workplace Safety and Health specialist.

    You are an expert on the Singapore Workplace Safety and Health Act.
    You advise on employer duties, risk assessments, incident reporting,
    sector-specific requirements, and WSH officer obligations.
    """

    __intent__ = "Advise on workplace safety and health obligations"


class PDPASignature(SpecialistSignature):
    """Personal Data Protection Act specialist.

    You are an expert on the Singapore Personal Data Protection Act.
    You advise on PDPA obligations (consent, purpose limitation,
    notification, access, correction, accuracy, protection, retention,
    transfer, openness), data breach notification, DPO appointment,
    cross-border transfers, employee data handling, NRIC restrictions,
    and PDPC enforcement.
    """

    __intent__ = "Advise on personal data protection obligations and compliance"


class ComplianceSignature(Signature):
    """Cross-domain compliance checker.

    You review outputs from multiple specialist agents and identify
    cross-domain compliance issues, contradictions, or gaps.
    """

    __intent__ = "Identify cross-domain compliance issues across specialist outputs"
    __guidelines__ = [
        "Read all specialist outputs from shared memory",
        "Flag contradictions between domains",
        "Identify gaps where no specialist addressed a relevant aspect",
        "Do NOT make legal determinations -- only flag issues",
    ]

    # Inputs
    query_text: str = InputField(
        description="The original HR query",
    )
    specialist_outputs: str = InputField(
        description="JSON list of all specialist outputs from shared memory",
    )
    company_context: str = InputField(
        description="JSON string of company profile",
        default="{}",
    )

    # Outputs
    compliance_flags: str = OutputField(
        description=(
            "JSON list of cross-domain issues found: "
            '[{"issue": "...", "domains": [...], "severity": "..."}]'
        ),
    )
    gaps_identified: str = OutputField(
        description="JSON list of regulatory gaps not addressed by any specialist",
    )
    risk_tier: str = OutputField(
        description="Overall compliance risk tier: green, amber, or red",
    )
    recommendations: str = OutputField(
        description="JSON list of recommended follow-up actions",
    )


# ---------------------------------------------------------------------------
# Action agent signatures
# ---------------------------------------------------------------------------


class DocumentGenerationSignature(Signature):
    """Document generation agent.

    Given a template identifier, company context, and specific parameters,
    produce a complete HR document (contract, policy, form, letter).
    """

    __intent__ = "Generate HR documents from templates"
    __guidelines__ = [
        "Use the template structure faithfully",
        "Fill all placeholders with company-specific values",
        "Flag any missing required parameters as warnings",
        "Include statutory minimum clauses where applicable",
    ]

    # Inputs
    template_id: str = InputField(
        description="Identifier of the document template to use",
    )
    company_context: str = InputField(
        description="JSON string of company profile for document personalisation",
        default="{}",
    )
    specific_params: str = InputField(
        description="JSON object of template-specific parameters (e.g. employee name, salary)",
        default="{}",
    )

    # Outputs
    generated_content: str = OutputField(
        description="The fully generated document content",
    )
    warnings: str = OutputField(
        description="JSON list of warnings about missing data or compliance notes",
    )
