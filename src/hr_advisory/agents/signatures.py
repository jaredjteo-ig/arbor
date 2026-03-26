"""Kaizen signatures for HR advisory agents.

Each signature declares the typed input/output contract for an agent.
Signatures are compiled to Core SDK workflow parameters at runtime.
"""

from kaizen import InputField, OutputField, Signature


# ---------------------------------------------------------------------------
# QueryAnalyzer
# ---------------------------------------------------------------------------


class QueryAnalyzerSignature(Signature):
    """You are a Singapore HR regulatory query classifier.

    Analyze the user query and company context, then output a structured
    classification. Do NOT answer the question -- only classify and route it.
    """

    __intent__ = "Route HR queries to the correct specialist domain(s)"
    __guidelines__ = [
        "Only classify and route -- never provide legal advice in this step",
        "When in doubt, flag the higher risk tier",
        "Multiple domains are acceptable for cross-cutting questions",
    ]

    # Inputs
    query_text: str = InputField(
        description="The HR query from the SME user",
    )
    company_context: str = InputField(
        description="JSON string of company profile (headcount, sector, etc.)",
        default="{}",
    )
    conversation_history: str = InputField(
        description=(
            "Formatted string of previous conversation turns for context. "
            "Each turn shows User: ... and Assistant: ... pairs."
        ),
        default="",
    )

    # Outputs
    domains: str = OutputField(
        description=(
            "JSON list of applicable domains from: employment_act, cpf, "
            "foreign_manpower, fair_employment, tax, wsh, pdpa, compliance, general"
        ),
    )
    entities: str = OutputField(
        description=(
            "JSON object of extracted entities (company_name, employee_type, "
            "salary_amount, dates, etc.)"
        ),
    )
    risk_tier: str = OutputField(
        description="Initial risk tier: green, amber, or red",
    )
    routing_decision: str = OutputField(
        description=(
            "JSON object with routing strategy: parallel, sequential, or "
            "router, plus ordered list of specialist domain keys"
        ),
    )
    intent: str = OutputField(
        description=(
            "Query intent classification. One of: ADVISORY (standard advisory question), "
            "CALCULATION (wants a number computed), DOCUMENT (wants a document generated), "
            "EMERGENCY (workplace safety emergency), COMPLIANCE_CHECK (requesting a "
            "compliance audit), CLARIFICATION_NEEDED (ambiguous query needing clarification)"
        ),
    )


# ---------------------------------------------------------------------------
# QueryClarifier
# ---------------------------------------------------------------------------


class QueryClarifierSignature(Signature):
    """You determine whether an HR query is too ambiguous to classify.

    Analyze the query and conversation history to decide if a clarifying
    question is needed before the query can be routed to the right specialist.
    Do NOT answer the query -- only assess whether it is clear enough to route.
    """

    __intent__ = "Detect ambiguous HR queries and generate a single clarifying question"
    __guidelines__ = [
        "Only flag a query as ambiguous when it genuinely cannot be routed",
        "Clear domain queries (CPF, overtime, leave, dismissal) are NOT ambiguous",
        "Conversation history may resolve pronoun references -- check before flagging",
        "Generate exactly one clarifying question, never multiple",
    ]

    # Inputs
    query_text: str = InputField(
        description="The HR query from the SME user",
    )
    conversation_history: str = InputField(
        description=(
            "Formatted string of previous conversation turns for context. "
            "Each turn shows User: ... and Assistant: ... pairs. "
            "Use this to resolve pronoun references before flagging ambiguity."
        ),
        default="",
    )

    # Outputs
    is_ambiguous: str = OutputField(
        description=(
            "Whether the query is too ambiguous to classify: 'true' or 'false'. "
            "Only return 'true' when the query genuinely cannot be routed."
        ),
    )
    clarification_question: str = OutputField(
        description=(
            "A single plain-language clarifying question to ask the user. "
            "Empty string if is_ambiguous is 'false'."
        ),
    )
    ambiguity_reason: str = OutputField(
        description=(
            "Brief explanation of why the query is ambiguous, for logging. "
            "Empty string if is_ambiguous is 'false'."
        ),
    )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class OrchestratorSignature(Signature):
    """You are the dispatch planner for a multi-agent HR advisory system.

    Given the query analysis, decide which specialist agents to engage,
    in what order, and whether they run in parallel or sequentially.
    """

    __intent__ = "Produce an optimal dispatch plan for specialist agents"
    __guidelines__ = [
        "Prefer parallel dispatch unless one specialist depends on another",
        "Limit to at most 3 specialists per query to control cost",
        "Always include the primary domain specialist",
    ]

    # Inputs
    analysis_result: str = InputField(
        description=(
            "JSON string of QueryAnalyzer output (domains, entities, "
            "risk_tier, routing_decision)"
        ),
    )

    # Outputs
    dispatch_plan: str = OutputField(
        description=(
            "JSON object: {mode: parallel|sequential|router, "
            "specialists: [{domain, priority, reason}], "
            "estimated_tokens: int}"
        ),
    )


# ---------------------------------------------------------------------------
# ResponseSynthesizer
# ---------------------------------------------------------------------------


class ResponseSynthesizerSignature(Signature):
    """You are a plain-language HR advisory response writer for Singapore SMEs.

    Synthesize specialist outputs into a clear, actionable response.
    Always cite legislative provisions and apply the correct risk-tier
    disclaimer.
    """

    __intent__ = "Produce a clear, cited, risk-aware advisory response"
    __guidelines__ = [
        "Write for non-HR-professionals (SME owners, managers)",
        "Cite provision sections in parentheses, e.g. (EA s.13(1))",
        "Amber risk: append 'We recommend professional review'",
        "Red risk: append 'Mandatory professional review required'",
        "Never fabricate provisions -- only cite what specialists provided",
    ]

    # Inputs
    specialist_outputs: str = InputField(
        description="JSON string of all specialist outputs collected from shared memory",
    )
    risk_tier: str = InputField(
        description="Risk tier from query analysis: green, amber, or red",
    )
    company_context: str = InputField(
        description="JSON string of company profile (headcount, sector, nationality mix, etc.)",
        default="{}",
    )
    conversation_history: str = InputField(
        description=(
            "Formatted string of previous conversation turns for multi-turn context. "
            "Each turn shows User: ... and Assistant: ... pairs."
        ),
        default="",
    )
    compliance_results: str = InputField(
        description=(
            "JSON string of ComplianceAgent cross-domain review results, "
            "including contradictions and risk escalation flags"
        ),
        default="{}",
    )

    # Outputs
    response_text: str = OutputField(
        description="Plain-language advisory response suitable for SME owners",
    )
    citations: str = OutputField(
        description="JSON list of {provision, section, act} citation objects",
    )
    disclaimers: str = OutputField(
        description="JSON list of disclaimer strings based on risk tier",
    )
    final_risk_tier: str = OutputField(
        description=("Final risk tier after synthesis (may be escalated from " "the input tier)"),
    )
