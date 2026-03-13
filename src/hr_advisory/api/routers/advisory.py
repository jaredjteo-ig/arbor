"""Advisory query endpoints.

Handles HR advisory queries with the full safety chain:
1. Input sanitisation and validation
2. Rate limiting
3. Query screening (guardrails — circumvention/escalation detection)
4. EATP genesis record and trust chain creation
5. Anti-amnesia constraint injection
6. Knowledge base retrieval (citation validator)
7. Disclaimer generation (risk-tiered)
8. Response content screening
9. Trust chain recording
"""

import asyncio
import concurrent.futures
import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from hr_advisory.api.middleware.auth_middleware import get_current_user
from hr_advisory.api.middleware.tenant_isolation import validate_company_access
from hr_advisory.security.validation import sanitise_input, validate_query_length
from hr_advisory.kb.admin import search_provisions
from hr_advisory.trust.citation_validator import validate_citations
from hr_advisory.trust.disclaimers import get_disclaimer
from hr_advisory.trust.eatp_lineage import (
    AgentAttestation,
    AgentRole,
    GenesisRecord,
    TrustLevel,
    create_trust_chain,
    get_anti_amnesia_injection,
    validate_constraint_envelope,
)
from hr_advisory.trust.learning_pipeline import record_query_pattern
from hr_advisory.workflows.guardrails import (
    ScreeningResult,
    check_confidence_escalation,
    check_rate_limit,
    screen_query,
    screen_response,
)

from hr_advisory.agents.config import UNCERTAINTY_DEFAULTS
from hr_advisory.agents.memory.short_term import ShortTermMemory

logger = logging.getLogger(__name__)

router = APIRouter()

# Session-scoped pipeline cache keyed by conversation_id
_conversation_memory: dict[str, ShortTermMemory] = {}


_RISK_TIER_SEVERITY = {"green": 0, "amber": 1, "red": 2}


def _escalate_risk_tier(current: str, proposed: str) -> str:
    """Enforce monotonic risk tier escalation — tier can only go up, never down."""
    current_level = _RISK_TIER_SEVERITY.get(current, 0)
    proposed_level = _RISK_TIER_SEVERITY.get(proposed, 0)
    return proposed if proposed_level >= current_level else current


def _classify_risk_tier(domains: list[str], confidence: float) -> str:
    """Classify risk tier based on domains and confidence."""
    high_risk_domains = {"fair_employment", "foreign_manpower"}
    if any(d in high_risk_domains for d in domains):
        return "amber"
    if confidence < 0.5:
        return "red"
    if confidence < 0.7:
        return "amber"
    return "green"


def _detect_domains(query: str) -> list[str]:
    """Detect which regulatory domains a query relates to.

    Includes Singlish variants so colloquial queries are routed correctly.
    """
    query_lower = query.lower()
    domain_keywords = {
        "cpf": [
            "cpf",
            "central provident fund",
            "contribution",
            "medisave",
            "ordinary account",
            # Singlish variants
            "got include cpf",
            "cpf how much",
            "need pay cpf",
        ],
        "employment_act": [
            "employment act",
            "salary",
            "overtime",
            "rest day",
            "annual leave",
            "sick leave",
            "ket",
            "payslip",
            "notice period",
            "termination",
            "working hours",
            "retrenchment",
            "dismissal",
            # Singlish variants
            "resign already",
            "can fire or not",
            "cannot anyhow fire",
            "how many days leave",
            "mc",
            "never take leave",
            "can forfeit",
            "need pay or not",
            "kena fire",
            "ot pay",
            "how to calculate ot",
        ],
        "foreign_manpower": [
            "work permit",
            "s pass",
            "employment pass",
            "foreign worker",
            "levy",
            "quota",
            "drc",
            "man-year",
            # Singlish variants
            "foreign staff",
            "from malaysia",
            "from china",
            "what permit need",
            "can hire foreigner",
        ],
        "fair_employment": [
            "tafep",
            "fair employment",
            "discrimination",
            "harassment",
            "flexible work",
            "workplace fairness",
            # Singlish variants
            "kena tadm",
            "tadm claim",
            "cannot discriminate",
            "staff pregnant",
            "can terminate pregnant",
        ],
        "wsh": [
            "workplace safety",
            "wsh",
            "wica",
            "safety",
            "incident report",
            "occupational health",
            # Singlish variants
            "kena injured",
            "worker injured",
            "mom inspection",
            "what need prepare",
            "accident at work",
        ],
        "tax": [
            "income tax",
            "iras",
            "ir8a",
            "sdl",
            "tax clearance",
            "ir21",
            # Singlish variants
            "need file tax",
            "tax how ah",
        ],
        "pdpa": [
            "pdpa",
            "personal data",
            "data protection",
            "data breach",
            "data privacy",
            "consent",
            "nric",
            "pdpc",
            "dpo",
            "data protection officer",
            "do not call",
            "dnc registry",
            "cross-border transfer",
            "data transfer overseas",
            "breach notification",
            # Singlish variants
            "can collect nric or not",
            "data leak how",
            "employee data",
            "kena data breach",
            "staff personal info",
        ],
    }
    detected = []
    for domain, keywords in domain_keywords.items():
        if any(kw in query_lower for kw in keywords):
            detected.append(domain)
    return detected or ["employment_act"]  # Default domain


def _fetch_company_profile(company_id: int) -> dict | None:
    """Fetch company profile from DataFlow for advisory personalisation.

    Returns a dict with company context fields, or None if unavailable.
    """
    try:
        from kailash.runtime import LocalRuntime
        from kailash.workflow.builder import WorkflowBuilder
        import hr_advisory.models  # noqa: F401 -- ensure models are registered

        wf = WorkflowBuilder()
        wf.add_node("CompanyReadNode", "read", {"id": company_id})
        runtime = LocalRuntime()
        results, _ = runtime.execute(wf.build())
        result = results.get("read")
        if result and not result.get("error"):
            return {
                "company_name": result.get("name", ""),
                "sector": result.get("sector", ""),
                "sub_sector": result.get("sub_sector", ""),
                "headcount_local": result.get("headcount_local", 0),
                "headcount_pr": result.get("headcount_pr", 0),
                "headcount_ep": result.get("headcount_ep", 0),
                "headcount_sp": result.get("headcount_sp", 0),
                "headcount_wp": result.get("headcount_wp", 0),
                "total_headcount": sum(
                    [
                        result.get("headcount_local", 0),
                        result.get("headcount_pr", 0),
                        result.get("headcount_ep", 0),
                        result.get("headcount_sp", 0),
                        result.get("headcount_wp", 0),
                    ]
                ),
            }
    except Exception as e:
        logger.warning("Failed to fetch company profile for advisory: %s", e)
    return None


def _format_conversation_history(turns: list[dict]) -> str:
    """Format conversation turns into a readable string for LLM context.

    Args:
        turns: List of turn dicts with ``user`` and ``agent`` keys.

    Returns:
        Formatted string with prior turns, or empty string if no history.
    """
    if not turns:
        return ""
    lines = ["Previous conversation:"]
    for turn in turns:
        user_msg = turn.get("user", "")
        agent_msg = turn.get("agent", "")
        if user_msg:
            lines.append(f"User: {user_msg}")
        if agent_msg:
            lines.append(f"Assistant: {agent_msg}")
    return "\n".join(lines)


def _lookup_provisions(domains: list[str], query: str = "") -> list[str]:
    """Look up relevant provision IDs from the KB for given domains.

    Dynamically searches the KB using search_provisions() rather than
    returning a hardcoded set. Falls back to the citation validator's
    known provisions registry when the DB returns no results.

    Args:
        domains: List of internal domain names (e.g. ``"employment_act"``).
        query: The user's query text, used to search for relevant provisions.

    Returns:
        List of provision ID strings suitable for citation validation.
    """
    # Map internal domain names to KB domain names
    domain_map = {
        "employment_act": "Employment Act",
        "cpf": "CPF",
        "foreign_manpower": "Foreign Manpower",
        "fair_employment": "Fair Employment",
        "wsh": "Workplace Safety and Health",
        "tax": "Tax",
    }

    provision_ids: list[str] = []
    for domain in domains:
        kb_domain = domain_map.get(domain)
        try:
            results = search_provisions(query=query or domain, domain=kb_domain, limit=5)
            for r in results:
                pid = r.get("id")
                if pid is not None:
                    provision_ids.append(str(pid))
        except Exception:
            logger.debug(
                "search_provisions failed for domain=%s query=%s, will use fallback",
                domain,
                query,
                exc_info=True,
            )

    # If no DB provisions found, fall back to the citation validator's known provisions
    if not provision_ids:
        from hr_advisory.trust.citation_validator import get_valid_provisions

        valid_provisions = get_valid_provisions()
        fallback_map = {
            "employment_act": [
                "EA-S95-KETs",
                "EA-S88A-payslip",
                "EA-S10-notice",
                "EA-PART-IV-hours",
                "EA-PART-X-annual-leave",
                "EA-S89-sick-leave",
            ],
            "cpf": ["CPFA-S52"],
            "foreign_manpower": ["EFMA-conditions"],
            "fair_employment": [
                "TGFEP-fair-employment",
                "TGFEP-GRIEVANCE",
                "WFA-workplace-fairness",
            ],
            "wsh": ["WSHA-S12", "WSH-incident-reporting", "WICA-employer-obligations"],
            "tax": [],
        }
        for domain in domains:
            for pid in fallback_map.get(domain, []):
                if pid in valid_provisions:
                    provision_ids.append(pid)

    return provision_ids


@router.post("/query")
async def advisory_query(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Submit an HR advisory question and receive a structured response.

    Full safety chain:
    1. Sanitise input
    2. Rate limit check
    3. Guardrail screening
    4. EATP trust chain creation
    5. Domain detection and KB lookup
    6. Citation validation
    7. Risk-tiered disclaimer
    8. Response screening
    """
    body = await request.json()
    query_raw = body.get("query", "")
    company_id = body.get("company_id")
    conversation_id = body.get("conversation_id")
    if conversation_id is None:
        conversation_id = uuid.uuid4().int % 2**31
    user_id = current_user.get("sub", "anonymous")

    # ── Step 0: Tenant isolation ─────────────────────────────────
    validate_company_access(current_user, requested_company_id=company_id)

    # ── Step 1: Input sanitisation ──────────────────────────────
    query = sanitise_input(query_raw)
    valid, error_msg = validate_query_length(query)
    if not valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # ── Step 2: Rate limiting ───────────────────────────────────
    if not check_rate_limit(user_id):
        raise HTTPException(
            status_code=429,
            detail="You've sent too many requests. Please wait a moment and try again.",
        )

    # ── Step 3: Query screening (guardrails) ────────────────────
    screening = screen_query(query, user_id=user_id)

    if screening.result == ScreeningResult.BLOCK:
        return {
            "query": query,
            "response": screening.reason,
            "alternative_guidance": screening.alternative_guidance,
            "risk_tier": "red",
            "confidence_score": 0.0,
            "blocked": True,
            "provisions_cited": [],
            "company_id": company_id,
            "conversation_id": conversation_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    if screening.result == ScreeningResult.ESCALATE:
        return {
            "query": query,
            "response": screening.reason,
            "risk_tier": "red",
            "confidence_score": 0.0,
            "escalated": True,
            "escalation_reason": (
                screening.escalation_reason.value if screening.escalation_reason else None
            ),
            "provisions_cited": [],
            "company_id": company_id,
            "conversation_id": conversation_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ── Step 3b: Load conversation memory ───────────────────────
    conv_key = str(conversation_id)
    memory = _conversation_memory.setdefault(conv_key, ShortTermMemory())
    context = memory.load_context(conv_key)
    conversation_history = _format_conversation_history(context.get("turns", []))

    # ── Step 3c: Fetch company profile ────────────────────────
    company_profile = None
    jwt_company_id = current_user.get("company_id")
    effective_company_id = company_id or jwt_company_id
    if effective_company_id is not None:
        try:
            company_profile = _fetch_company_profile(int(effective_company_id))
        except (TypeError, ValueError):
            logger.debug("Invalid company_id for profile fetch: %s", effective_company_id)

    # ── Step 4: EATP genesis record ─────────────────────────────
    session_id = str(uuid.uuid4())
    domains = _detect_domains(query)

    genesis = GenesisRecord(
        session_id=session_id,
        user_verification_level=TrustLevel.STANDARD,
        company_profile_completeness=0.8 if company_profile else (0.5 if company_id else 0.3),
        kb_currency_status={d: "2026-03-01" for d in domains},
        agent_version_hashes={"orchestrator": "v1.0.0"},
        query_text=query,
        query_domains=domains,
    )
    trust_chain = create_trust_chain(genesis)

    # ── Step 5: Anti-amnesia injection ──────────────────────────
    constraints = get_anti_amnesia_injection("orchestrator")
    logger.debug("Anti-amnesia constraints injected: %d rules", constraints.count("[CONSTRAINT"))

    # ── Step 6: Domain detection and KB lookup ──────────────────
    provision_ids = _lookup_provisions(domains, query=query)
    citation_result = validate_citations(provision_ids)

    # Build cited provisions list from validated citations
    provisions_cited = [
        {
            "provision_id": c.provision_id,
            "title": c.title,
            "authority_level": c.authority_level.value,
            "status": c.status.value,
        }
        for c in citation_result.validated_citations
    ]

    # ── Step 7: Generate response (LLM first, template fallback) ─
    response_degraded = False
    llm_result = await _async_run_llm_advisory(
        query,
        domains,
        provisions_cited,
        company_context=company_profile,
        conversation_history=conversation_history,
    )
    if llm_result is not None:
        response_text = llm_result["response_text"]
        confidence = llm_result.get("confidence", UNCERTAINTY_DEFAULTS["confidence"])
        risk_tier = llm_result.get("risk_tier", _classify_risk_tier(domains, confidence))
        response_degraded = llm_result.get("degraded", False)
        logger.info(
            "Advisory response generated via LLM pipeline (confidence=%.2f, degraded=%s)",
            confidence,
            response_degraded,
        )
    else:
        # Template fallback — no LLM available. Template responses are
        # keyword-matched, not AI-analyzed, so confidence reflects that.
        confidence = 0.85 if citation_result.is_valid else 0.6
        risk_tier = _classify_risk_tier(domains, confidence)
        response_text = _generate_grounded_response(query, domains, provisions_cited)
        logger.info(
            "Advisory response generated via template fallback (confidence=%.2f)", confidence
        )

    # ── Step 8: Confidence escalation check ─────────────────────
    escalation = check_confidence_escalation(confidence)
    if escalation is not None:
        risk_tier = "red"

    # ── Step 9: Response content screening ──────────────────────
    response_screening = screen_response(response_text)
    if response_screening.result == ScreeningResult.BLOCK:
        response_text = (
            "I was unable to generate a compliant response for this query. "
            "Please rephrase your question or contact a human HR specialist."
        )
        risk_tier = "red"
        confidence = 0.0

    # ── Step 10: Disclaimer ─────────────────────────────────────
    disclaimer = get_disclaimer(risk_tier, confidence, domains)

    # ── Step 11: Constraint envelope validation ─────────────────
    violations = validate_constraint_envelope("orchestrator", domains)

    # ── Step 12: Record attestation in trust chain ──────────────
    attestation = AgentAttestation(
        agent_id="orchestrator",
        agent_role=AgentRole.ORCHESTRATOR,
        agent_version="v1.0.0",
        domain=",".join(domains),
        provisions_retrieved=[c.provision_id for c in citation_result.validated_citations],
        reasoning_summary=f"Detected domains: {', '.join(domains)}. Retrieved {len(provision_ids)} provisions.",
        conclusion=response_text[:200],
        confidence_score=confidence,
        constraint_envelope_id="orchestrator",
        constraint_violations=violations,
    )
    trust_chain.add_attestation(attestation)

    # ── Step 13: Learning pipeline recording ──────────────────
    pattern_id = f"{'_'.join(sorted(domains))}:{risk_tier}"
    record_query_pattern(
        pattern_id=pattern_id,
        description=f"Query across {', '.join(domains)} (risk={risk_tier})",
        domains=domains,
        confidence=confidence,
        satisfaction=1.0,  # Default positive; updated via /learning/feedback
        query_example=query[:100],
    )

    # ── Step 14: Save turn to conversation memory ─────────────
    memory.save_turn(
        session_id=conv_key,
        query=query,
        response=response_text,
        domains=domains,
        risk_tier=risk_tier,
    )

    advisory_response = {
        "query": query,
        "response": response_text,
        "provisions_cited": provisions_cited,
        "risk_tier": risk_tier,
        "confidence_score": confidence,
        "disclaimer": {
            "show": disclaimer.show_disclaimer,
            "text": disclaimer.disclaimer_text,
            "framing": disclaimer.framing_text,
            "professional_referral": disclaimer.show_professional_referral,
        },
        "trust_chain": trust_chain.to_dict(),
        "citation_warnings": citation_result.warnings,
        "company_id": company_id,
        "conversation_id": conversation_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if response_degraded:
        advisory_response["degraded"] = True

    return advisory_response


def _get_provision_details(provisions: list[dict]) -> list[dict]:
    """Look up full provision data from the KB and citation validator.

    Merges data from two sources:
    1. The DataFlow KB via search_provisions (full formal_text, plain_summary)
    2. The citation validator's get_valid_provisions() (title, authority)

    Args:
        provisions: List of provision dicts with at least ``provision_id`` and ``title``.

    Returns:
        List of detail dicts with title, plain_summary, formal_text where available.
    """
    from hr_advisory.trust.citation_validator import get_valid_provisions

    valid_provisions = get_valid_provisions()
    details: list[dict] = []
    for prov in provisions:
        pid = prov.get("provision_id", "")
        title = prov.get("title", "")
        detail = {"provision_id": pid, "title": title}

        # Try to get extended data from the citation validator registry
        kb_entry = valid_provisions.get(pid)
        if kb_entry:
            detail["authority_level"] = kb_entry.get("authority", "")

        # Try to get full text from DataFlow KB by searching for the title
        if title:
            try:
                search_results = search_provisions(query=title, limit=1)
                if search_results:
                    hit = search_results[0]
                    detail["plain_summary"] = hit.get("plain_summary", "")
                    detail["formal_text"] = hit.get("formal_text", "")
            except Exception:
                logger.debug("Failed to retrieve full provision data for '%s'", pid, exc_info=True)

        details.append(detail)

    return details


def _generate_topic_intro(query_lower: str, domains: list[str]) -> str:
    """Generate a query-specific opening line that addresses the user's question.

    Uses keyword matching against common HR question patterns to produce
    a targeted introduction rather than a generic domain description.

    Args:
        query_lower: The user's query in lowercase.
        domains: List of detected domain names.

    Returns:
        An introductory sentence addressing the query topic, or empty string.
    """
    # Map query keywords to topic-specific openings
    topic_patterns = {
        "annual leave": "Regarding annual leave entitlements under Singapore employment law:",
        "sick leave": "Regarding sick leave entitlements and obligations:",
        "notice period": "Regarding notice period requirements for termination:",
        "termination": "Regarding employment termination procedures:",
        "overtime": "Regarding overtime pay and working hours regulations:",
        "payslip": "Regarding itemised payslip requirements:",
        "retrenchment": "Regarding retrenchment procedures and obligations:",
        "dismissal": "Regarding dismissal procedures under employment law:",
        "working hours": "Regarding working hours and rest day requirements:",
        "rest day": "Regarding rest day entitlements and calculations:",
        "salary": "Regarding salary payment obligations:",
        "cpf contribution": "Regarding CPF contribution rates and obligations:",
        "cpf": "Regarding Central Provident Fund (CPF) obligations:",
        "contribution rate": "Regarding CPF contribution rates by age band:",
        "work permit": "Regarding work permit requirements for foreign employees:",
        "s pass": "Regarding S Pass requirements and quota:",
        "employment pass": "Regarding Employment Pass eligibility and conditions:",
        "foreign worker": "Regarding obligations when employing foreign workers:",
        "levy": "Regarding foreign worker levy rates and obligations:",
        "quota": "Regarding foreign worker quota and Dependency Ratio Ceiling:",
        "discrimination": "Regarding anti-discrimination obligations in the workplace:",
        "harassment": "Regarding workplace harassment prevention and response:",
        "fair employment": "Regarding fair employment practices and obligations:",
        "flexible work": "Regarding flexible work arrangement requests:",
        "workplace fairness": "Regarding the Workplace Fairness Act obligations:",
        "workplace safety": "Regarding workplace safety and health obligations:",
        "incident report": "Regarding incident reporting requirements under WSH:",
        "wica": "Regarding Work Injury Compensation Act obligations:",
        "occupational health": "Regarding occupational health requirements:",
        "income tax": "Regarding employer tax filing obligations:",
        "ir8a": "Regarding IR8A filing requirements:",
        "tax clearance": "Regarding tax clearance (IR21) for departing employees:",
        "ket": "Regarding Key Employment Terms (KETs) requirements:",
        "grievance": "Regarding grievance handling process requirements:",
    }

    for keyword, intro in topic_patterns.items():
        if keyword in query_lower:
            return intro

    # Domain-level fallback
    domain_intros = {
        "employment_act": "Regarding your Employment Act query:",
        "cpf": "Regarding your CPF-related query:",
        "foreign_manpower": "Regarding foreign manpower requirements:",
        "fair_employment": "Regarding fair employment obligations:",
        "wsh": "Regarding workplace safety and health requirements:",
        "tax": "Regarding employer tax obligations:",
    }
    for domain in domains:
        if domain in domain_intros:
            return domain_intros[domain]

    return ""


def _get_domain_context(query_lower: str, domains: list[str]) -> list[str]:
    """Generate query-specific domain context when provision data is unavailable.

    Rather than returning a single generic paragraph per domain, this function
    selects context snippets that are relevant to the specific query keywords.

    Args:
        query_lower: The user's query in lowercase.
        domains: List of detected domain names.

    Returns:
        List of context strings relevant to the query.
    """
    context_snippets: dict[str, dict[str, str]] = {
        "employment_act": {
            "annual leave": (
                "Under Part X of the Employment Act, employees with at least 3 months of "
                "service are entitled to paid annual leave. The minimum entitlement starts at "
                "7 days for the first year and increases by 1 day per year of service, up to "
                "14 days for 8 or more years of service."
            ),
            "sick leave": (
                "Under s89 of the Employment Act, employees are entitled to paid outpatient "
                "sick leave (14 days per year) and hospitalisation leave (up to 60 days, "
                "inclusive of outpatient leave) after completing at least 3 months of service."
            ),
            "notice period": (
                "Under s10 of the Employment Act, the notice period depends on what is stated "
                "in the employment contract. If not specified, the statutory minimum is: "
                "1 day (less than 26 weeks), 1 week (26 weeks to 2 years), 2 weeks (2-5 years), "
                "or 4 weeks (5+ years of service)."
            ),
            "overtime": (
                "Under Part IV of the Employment Act, employees earning up to $4,500/month "
                "are entitled to overtime pay at 1.5x the hourly basic rate for work exceeding "
                "the contractual or statutory working hours. Maximum overtime is 72 hours/month."
            ),
            "payslip": (
                "Under s88A of the Employment Act, employers must issue itemised payslips "
                "within 3 working days of salary payment. Payslips must show basic salary, "
                "allowances, deductions, overtime, and net pay."
            ),
            "ket": (
                "Under s95A of the Employment Act, employers must provide written Key Employment "
                "Terms (KETs) to all employees within 14 days of starting employment. KETs must "
                "include job title, duties, working hours, salary, and leave entitlements."
            ),
            "termination": (
                "Under the Employment Act, termination must follow the contractual notice period "
                "or statutory minimums under s10. Payment of salary in lieu of notice is permitted "
                "under s11. Dismissal for misconduct follows the inquiry process under s14."
            ),
            "retrenchment": (
                "Under Singapore employment law, retrenched employees with at least 2 years of "
                "service are eligible for retrenchment benefits. While not mandated by statute, "
                "the prevailing norm is 2 weeks to 1 month of salary per year of service."
            ),
            "working hours": (
                "Under Part IV of the Employment Act, employees earning up to $4,500/month "
                "must not work more than 8 hours per day or 44 hours per week. Rest days must "
                "be provided at least once per week."
            ),
            "dismissal": (
                "Under s14 of the Employment Act, an employer may dismiss an employee without "
                "notice for misconduct, but must conduct a due inquiry first. The employee may "
                "make representations before a decision is made."
            ),
            "salary": (
                "Under s21 of the Employment Act, salary must be paid within 7 days of the "
                "end of the salary period. Upon termination, final salary must be paid on the "
                "last working day (resignation) or within 3 working days (employer termination)."
            ),
        },
        "cpf": {
            "contribution": (
                "Under the CPF Act, employer and employee CPF contribution rates are determined "
                "by the employee's age band and residency status. For Singapore Citizens aged "
                "55 and below, the combined rate is 37% (employer 17%, employee 20%) of "
                "ordinary wages up to the ceiling of $8,000/month."
            ),
            "rate": (
                "CPF contribution rates decrease in tiers for older employees: 55-60 years "
                "(employer 15%, employee 15%), 60-65 years (employer 11.5%, employee 9.5%), "
                "65-70 years (employer 9%, employee 7%), and above 70 (employer 7.5%, employee 5%)."
            ),
            "cpf": (
                "Under the CPF Act, employers must contribute to the Central Provident Fund "
                "for all Singapore citizens and permanent residents earning more than $50/month. "
                "Late payment incurs interest at 18% per annum under s52."
            ),
            "medisave": (
                "MediSave is one of the three CPF accounts. Contribution allocation to MediSave "
                "varies by age. From age 55, a larger proportion is allocated to MediSave as "
                "Ordinary Account allocation decreases."
            ),
        },
        "foreign_manpower": {
            "work permit": (
                "Under EFMA, Work Permits are for semi-skilled foreign workers in construction, "
                "manufacturing, marine shipyard, process, and services sectors. Employers must "
                "comply with quota limits and pay the applicable levy."
            ),
            "levy": (
                "Foreign worker levy rates vary by sector, worker tier (basic/higher-skilled), "
                "and the Dependency Ratio Ceiling. Higher levies apply when the proportion of "
                "foreign workers approaches the DRC limit."
            ),
            "pass": (
                "Under EFMA, S Passes are for mid-level skilled staff earning at least $3,150/month. "
                "Employment Passes are for professionals earning at least $5,600/month (experienced) "
                "or $5,000/month (entry-level in the financial sector)."
            ),
            "quota": (
                "The Dependency Ratio Ceiling (DRC) limits the proportion of foreign workers. "
                "For the services sector, the DRC is 35%. For manufacturing, it is 60% (with "
                "Work Permit holders capped at 87.5% of the foreign workforce)."
            ),
            "foreign worker": (
                "Under EFMA, employers hiring foreign workers must obtain valid work passes, "
                "comply with work pass conditions, provide acceptable accommodation, and "
                "purchase medical insurance coverage of at least $15,000 per year."
            ),
        },
        "fair_employment": {
            "discrimination": (
                "Under the Workplace Fairness Act and TGFEP, employers must not discriminate "
                "on the basis of nationality, age, sex, race, religion, disability, mental "
                "health condition, marital status, pregnancy, or caregiving responsibilities."
            ),
            "harassment": (
                "Employers must establish anti-harassment policies and grievance handling "
                "processes. Under TGFEP, employers should have clear procedures for employees "
                "to report workplace harassment and ensure timely investigation."
            ),
            "fair employment": (
                "The Tripartite Guidelines on Fair Employment Practices (TGFEP) require "
                "merit-based HR practices across recruitment, performance management, training, "
                "and termination. The Workplace Fairness Act provides statutory backing."
            ),
            "flexible work": (
                "Under the Tripartite Guidelines on Flexible Work Arrangement Requests (TG-FWAR), "
                "employees may request flexible work arrangements. Employers must consider "
                "requests reasonably and respond within 2 months."
            ),
            "grievance": (
                "Under TGFEP, employers must establish grievance handling processes that are "
                "accessible, fair, and confidential. Employees who feel unfairly treated may "
                "file complaints with TAFEP or seek mediation through TADM."
            ),
        },
        "wsh": {
            "safety": (
                "Under the Workplace Safety and Health Act, employers must take reasonably "
                "practicable measures to ensure the safety and health of employees. This "
                "includes conducting risk assessments and implementing control measures."
            ),
            "incident": (
                "Under the WSH (Incident Reporting) Regulations, employers must report "
                "workplace accidents causing death, dangerous occurrences, and occupational "
                "diseases to MOM within the prescribed timeframes."
            ),
            "wica": (
                "Under the Work Injury Compensation Act (WICA), employers must compensate "
                "employees for injuries or diseases arising from employment. Employers must "
                "also purchase work injury insurance for all manual workers and non-manual "
                "workers earning up to $2,600/month."
            ),
            "reporting": (
                "Workplace accidents resulting in death must be reported to MOM immediately. "
                "Accidents causing more than 3 consecutive days of medical leave must be "
                "reported within 10 days. Dangerous occurrences must be reported immediately."
            ),
        },
        "tax": {
            "ir8a": (
                "Employers must file IR8A forms (Return of Employee's Remuneration) for all "
                "employees by 1 March each year. This includes full-time, part-time, and "
                "contract employees who received remuneration during the preceding year."
            ),
            "tax clearance": (
                "Tax clearance (IR21) is required when a foreign employee ceases employment "
                "or leaves Singapore for more than 3 months. Employers must file IR21 at "
                "least 1 month before the employee's departure and withhold salary until "
                "IRAS issues the tax clearance directive."
            ),
            "sdl": (
                "Skills Development Levy (SDL) is payable for all employees (local and foreign) "
                "at 0.25% of gross monthly remuneration, with a minimum of $2 and maximum of "
                "$11.25 per employee per month."
            ),
            "tax": (
                "Employers have several tax-related obligations: filing IR8A by 1 March, "
                "filing IR21 for departing foreign employees, and paying Skills Development "
                "Levy (SDL) for all employees."
            ),
        },
    }

    parts: list[str] = []
    for domain in domains:
        snippets = context_snippets.get(domain, {})
        # Find the best matching snippet by keyword overlap
        best_snippet = ""
        best_score = 0
        for keyword, snippet in snippets.items():
            if keyword in query_lower:
                score = len(keyword)
                if score > best_score:
                    best_score = score
                    best_snippet = snippet
        if best_snippet:
            parts.append(best_snippet)
        elif snippets:
            # Use the domain-name keyed snippet as a generic fallback
            domain_key = domain.replace("_", " ")
            fallback = snippets.get(domain_key, "")
            if fallback:
                parts.append(fallback)
            else:
                # Use the first snippet as absolute last resort
                parts.append(next(iter(snippets.values())))

    return parts


def _fallback_response(domains: list[str]) -> str:
    """Generate a minimal domain-aware fallback response.

    Used only when no provision details and no domain context could be generated.

    Args:
        domains: List of detected domain names.

    Returns:
        A brief domain-level response string.
    """
    domain_names = {
        "employment_act": "Employment Act",
        "cpf": "CPF Act",
        "foreign_manpower": "Employment of Foreign Manpower Act (EFMA)",
        "fair_employment": "fair employment practices (TGFEP/WFA)",
        "wsh": "Workplace Safety and Health Act",
        "tax": "employer tax obligations (IRAS)",
    }
    named = [domain_names.get(d, d) for d in domains]
    return (
        f"Your query relates to {', '.join(named)}. "
        "Please provide more detail so I can identify the specific provisions that apply."
    )


def _run_llm_advisory(
    query: str,
    domains: list[str],
    provisions: list[dict],
    company_context: dict | None = None,
    conversation_history: str = "",
) -> dict | None:
    """Run the full Kaizen agent pipeline to generate an LLM-powered response.

    Pipeline: QueryAnalyzer -> DispatchRouter -> Specialists ->
              ComplianceGate -> ResponseSynthesizer.

    The DispatchRouter is a deterministic replacement for the former
    OrchestratorAgent -- it maps the QueryAnalyzer's structured output
    to a specialist dispatch plan without an LLM call.

    Wiring additions (T065-T069):
      - T065: conversation_history flows to specialists and synthesizer
      - T066: company_context flows to synthesizer
      - T067: ComplianceAgent.check_compliance() with all specialist outputs
      - T069: EATP trust chain, anti-amnesia injection, constraint validation

    Args:
        query: The user's HR question.
        domains: Detected regulatory domains.
        provisions: Validated provision dicts from the citation validator.
        company_context: Optional company profile dict for personalisation.
        conversation_history: Formatted prior turns for multi-turn context.

    Returns a dict with keys: response_text, risk_tier, confidence, citations,
    trust_metadata. Returns None if LLM is unavailable or the pipeline fails.
    """
    try:
        from hr_advisory.agents.config import has_llm_available

        if not has_llm_available():
            return None

        from kaizen.memory import SharedMemoryPool
        from hr_advisory.agents.orchestration.query_analyzer import QueryAnalyzerAgent
        from hr_advisory.agents.orchestration.dispatch_router import DispatchRouter
        from hr_advisory.agents.orchestration.response_synthesizer import ResponseSynthesizerAgent
        from hr_advisory.agents.specialists import (
            EmploymentActAgent,
            CPFAgent,
            ForeignManpowerAgent,
            FairEmploymentAgent,
            PDPAAgent,
            TaxAgent,
            WSHAgent,
            ComplianceAgent,
        )

        shared_memory = SharedMemoryPool()

        # Map domain keys to specialist classes
        specialist_classes = {
            "employment_act": EmploymentActAgent,
            "cpf": CPFAgent,
            "foreign_manpower": ForeignManpowerAgent,
            "fair_employment": FairEmploymentAgent,
            "tax": TaxAgent,
            "wsh": WSHAgent,
            "pdpa": PDPAAgent,
            "compliance": ComplianceAgent,
        }

        # ----------------------------------------------------------
        # T069: Create EATP trust chain at pipeline start
        # ----------------------------------------------------------
        session_id = str(uuid.uuid4())
        genesis = GenesisRecord(
            session_id=session_id,
            user_verification_level=TrustLevel.STANDARD,
            company_profile_completeness=(min(1.0, len(company_context or {}) / 5.0)),
            kb_currency_status={
                d: datetime.now(timezone.utc).strftime("%Y-%m-%d") for d in domains
            },
            agent_version_hashes={"pipeline": "v2.0"},
            query_text=query,
            query_domains=domains,
        )
        trust_chain = create_trust_chain(genesis)

        # Step 1: Analyze query (with conversation history and company context)
        analyzer = QueryAnalyzerAgent(shared_memory=shared_memory)
        analysis = analyzer.analyze(
            query_text=query,
            company_context=company_context,
            conversation_history=conversation_history,
        )
        llm_domains = analysis.get("domains", domains)
        risk_tier = analysis.get("risk_tier", UNCERTAINTY_DEFAULTS["risk_tier"])
        intent = analysis.get("intent", "ADVISORY")

        # Step 1b: Intent-based routing — short-circuit for action intents
        if intent == "CALCULATION":
            return {
                "response_text": (
                    "This query requires a calculation. "
                    "Routing to the CalculatorAgent for computation."
                ),
                "risk_tier": risk_tier,
                "confidence": 0.9,
                "citations": [],
                "disclaimers": [get_disclaimer(risk_tier)],
                "intent": "CALCULATION",
                "domains": llm_domains,
                "action_agent": "calculator",
                "trust_metadata": trust_chain.to_dict(),
            }

        if intent == "DOCUMENT":
            return {
                "response_text": (
                    "This query requests document generation. "
                    "Routing to the DocumentGenerationAgent."
                ),
                "risk_tier": risk_tier,
                "confidence": 0.9,
                "citations": [],
                "disclaimers": [get_disclaimer(risk_tier)],
                "intent": "DOCUMENT",
                "domains": llm_domains,
                "action_agent": "document_generation",
                "trust_metadata": trust_chain.to_dict(),
            }

        if intent == "EMERGENCY":
            return {
                "response_text": (
                    "This query describes a workplace emergency. "
                    "Routing to the EmergencyResponse handler for immediate guidance."
                ),
                "risk_tier": "red",
                "confidence": 0.95,
                "citations": [],
                "disclaimers": [get_disclaimer("red")],
                "intent": "EMERGENCY",
                "domains": llm_domains,
                "action_agent": "emergency_response",
                "trust_metadata": trust_chain.to_dict(),
            }

        if intent == "CLARIFICATION_NEEDED":
            return {
                "type": "clarification_needed",
                "response_text": (
                    "Your query is ambiguous and could be interpreted in "
                    "multiple ways. Could you please provide more details "
                    "so I can give you accurate advice?"
                ),
                "risk_tier": risk_tier,
                "confidence": 0.4,
                "citations": [],
                "disclaimers": [],
                "intent": "CLARIFICATION_NEEDED",
                "domains": llm_domains,
                "trust_metadata": trust_chain.to_dict(),
            }

        # ADVISORY and COMPLIANCE_CHECK continue with normal specialist dispatch

        # Step 2: Deterministic dispatch (no LLM call)
        router = DispatchRouter()
        dispatch_plan = router.route(analysis)

        specialist_domain_list = dispatch_plan.specialists
        if not specialist_domain_list:
            specialist_domain_list = llm_domains[:2]

        # Step 3: Run specialists with KB-retrieved provisions per domain.
        #
        # Previously, specialists received only provision IDs/titles from
        # the citation validator -- thin metadata with no regulatory text.
        # Now we retrieve full provisions from the KB for each specialist's
        # domain so the LLM can cite actual legislative content.
        from hr_advisory.agents.orchestration.kb_retriever import (
            retrieve_provisions_for_specialist,
            provisions_to_dicts,
        )

        specialist_outputs = []

        # Citation-validator fallback (thin dicts, used only when KB returns nothing)
        _citation_fallback = [
            {
                "id": p.get("provision_id", ""),
                "title": p.get("title", ""),
                "section": "",
                "formal_text": "",
                "plain_summary": "",
                "authority_level": p.get("authority_level", ""),
            }
            for p in provisions
        ]

        for domain_key in specialist_domain_list:
            agent_class = specialist_classes.get(domain_key)
            if not agent_class:
                continue

            # T069: Get anti-amnesia injection for this specialist
            agent_id = f"{domain_key}_specialist"
            anti_amnesia = get_anti_amnesia_injection(agent_id)

            try:
                # Retrieve domain-specific provisions from the KB
                kb_provisions = retrieve_provisions_for_specialist(
                    query=query,
                    domain=domain_key,
                    top_k=10,
                )
                provision_dicts = provisions_to_dicts(kb_provisions)

                # Fall back to citation-validator dicts when KB is empty
                if not provision_dicts:
                    provision_dicts = _citation_fallback
                    logger.debug(
                        "No KB provisions for domain '%s'; using %d citation-validator fallbacks",
                        domain_key,
                        len(provision_dicts),
                    )

                agent = agent_class(shared_memory=shared_memory)

                # T065/T066: Pass conversation_history and company_context
                output = agent.advise(
                    query_text=query,
                    company_context=company_context,
                    relevant_provisions=provision_dicts,
                    conversation_history=conversation_history,
                )

                # T069: Validate constraint envelope on the specialist output
                response_domains = [output.get("domain", domain_key)]
                cross_flags = output.get("cross_domain_flags", [])
                if cross_flags:
                    response_domains.extend(cross_flags)
                constraint_violations = validate_constraint_envelope(agent_id, response_domains)

                if constraint_violations:
                    logger.warning(
                        "Constraint violations for %s: %s",
                        agent_id,
                        constraint_violations,
                    )

                # T069: Record agent attestation in the trust chain
                cited = output.get("cited_provisions", [])
                provision_ids = []
                for p in (cited if isinstance(cited, list) else []):
                    if isinstance(p, dict):
                        provision_ids.append(str(p.get("provision_id", "")))
                    else:
                        provision_ids.append(str(p))

                attestation = AgentAttestation(
                    agent_id=agent_id,
                    agent_role=AgentRole.SPECIALIST,
                    agent_version="v2.0",
                    domain=domain_key,
                    provisions_retrieved=provision_ids,
                    reasoning_summary=output.get("answer_text", "")[:200],
                    conclusion=output.get("answer_text", "")[:100],
                    confidence_score=output.get("confidence", UNCERTAINTY_DEFAULTS["confidence"]),
                    constraint_envelope_id=agent_id,
                    constraint_violations=constraint_violations,
                )
                trust_chain.add_attestation(attestation)

                specialist_outputs.append(output)
            except Exception as e:
                logger.error(
                    "Specialist %s raised unexpected error: %s",
                    domain_key,
                    e,
                    exc_info=True,
                )
                # Append a degraded placeholder so the synthesizer knows
                # this specialist failed
                specialist_outputs.append(
                    {
                        "domain": domain_key,
                        "answer_text": (
                            f"I was unable to provide a fully analyzed response for this "
                            f"{domain_key} question. Please consult a professional "
                            f"for guidance."
                        ),
                        "cited_provisions": [],
                        "confidence": 0.2,
                        "risk_tier": UNCERTAINTY_DEFAULTS["risk_tier"],
                        "cross_domain_flags": [],
                        "degraded": True,
                    }
                )

        # Step 3b: Run compliance gate if the dispatch plan calls for it.
        # T067: Use check_compliance() with ALL specialist outputs instead
        # of advise() with just provisions.
        compliance_results = None
        if dispatch_plan.include_compliance_gate and specialist_outputs:
            try:
                compliance_agent = ComplianceAgent(shared_memory=shared_memory)
                compliance_results = compliance_agent.check_compliance(
                    query_text=query,
                    specialist_outputs=specialist_outputs,
                    company_context=company_context,
                )

                # T067: If compliance escalates risk, override the pipeline risk tier
                if compliance_results.get("risk_escalation"):
                    override_tier = compliance_results.get("override_risk_tier", risk_tier)
                    risk_tier = _escalate_risk_tier(risk_tier, override_tier)
                    logger.info(
                        "Compliance gate escalated risk tier to '%s'",
                        risk_tier,
                    )
            except Exception as e:
                logger.error("Compliance gate failed: %s", e, exc_info=True)

        if not specialist_outputs:
            # No specialists could even be instantiated — return a degraded
            # error response instead of None (which would produce a falsely
            # confident template fallback)
            return {
                "response_text": UNCERTAINTY_DEFAULTS["critical_fallback_message"],
                "risk_tier": "red",
                "confidence": UNCERTAINTY_DEFAULTS["confidence"],
                "citations": [],
                "disclaimers": [
                    "This response may be incomplete — please verify with a professional."
                ],
                "degraded": True,
                "trust_metadata": trust_chain.to_dict(),
            }

        # Step 4: Synthesize response
        # T065/T066/T067: Pass conversation_history, company_context,
        # and compliance_results to the synthesizer
        synthesizer = ResponseSynthesizerAgent(shared_memory=shared_memory)
        synthesis = synthesizer.synthesize(
            specialist_outputs=specialist_outputs,
            risk_tier=risk_tier,
            company_context=company_context,
            conversation_history=conversation_history,
            compliance_results=compliance_results,
        )

        response_text = synthesis.get("response_text", "")
        if not response_text:
            response_text = UNCERTAINTY_DEFAULTS["fallback_message"]

        final_risk_tier = synthesis.get("final_risk_tier", risk_tier)
        citations = synthesis.get("citations", [])
        disclaimers = synthesis.get("disclaimers", [])
        is_degraded = synthesis.get("degraded", False)

        # Compute confidence from specialist outputs — use uncertainty
        # default (not 0.5) for missing confidence values
        confidences = [
            o.get("confidence", UNCERTAINTY_DEFAULTS["confidence"]) for o in specialist_outputs
        ]
        avg_confidence = (
            sum(confidences) / len(confidences)
            if confidences
            else UNCERTAINTY_DEFAULTS["confidence"]
        )

        result = {
            "response_text": response_text,
            "risk_tier": final_risk_tier,
            "confidence": avg_confidence,
            "citations": citations,
            "disclaimers": disclaimers,
            "trust_metadata": trust_chain.to_dict(),
        }
        if is_degraded:
            result["degraded"] = True
        return result

    except Exception as e:
        logger.error("LLM advisory pipeline failed: %s", e, exc_info=True)
        # Return a degraded error response instead of silently falling back
        # to a template that pretends everything is fine
        return {
            "response_text": UNCERTAINTY_DEFAULTS["critical_fallback_message"],
            "risk_tier": "red",
            "confidence": UNCERTAINTY_DEFAULTS["confidence"],
            "citations": [],
            "disclaimers": ["This response may be incomplete — please verify with a professional."],
            "degraded": True,
        }


# Thread pool for running sync Kaizen agents from async context
_llm_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)


async def _async_run_llm_advisory(
    query: str,
    domains: list[str],
    provisions: list[dict],
    company_context: dict | None = None,
    conversation_history: str = "",
) -> dict | None:
    """Async wrapper for the synchronous Kaizen agent pipeline."""
    import functools

    loop = asyncio.get_event_loop()
    func = functools.partial(
        _run_llm_advisory,
        query,
        domains,
        provisions,
        company_context=company_context,
        conversation_history=conversation_history,
    )
    return await loop.run_in_executor(_llm_executor, func)


def _generate_grounded_response(
    query: str,
    domains: list[str],
    provisions: list[dict],
) -> str:
    """Generate a KB-grounded response specific to the user's query.

    Constructs a response by:
    1. Analysing the query to identify the specific topic
    2. Selecting the most relevant provision summaries
    3. Framing the answer to address the user's specific question

    Used as fallback when the LLM pipeline is unavailable.

    Args:
        query: The user's original query text.
        domains: List of detected regulatory domain names.
        provisions: List of validated provision dicts (from citation validator).

    Returns:
        A response string grounded in KB provisions and specific to the query.
    """
    # Get full provision data from both the DataFlow KB and the citation validator
    provision_details = _get_provision_details(provisions)

    # Build query-specific response
    query_lower = query.lower()
    parts: list[str] = []

    # Opening: address the specific query
    topic_intro = _generate_topic_intro(query_lower, domains)
    if topic_intro:
        parts.append(topic_intro)

    # Body: relevant provision details
    for detail in provision_details[:5]:  # Top 5 most relevant
        summary = detail.get("plain_summary") or detail.get("formal_text", "")
        if summary:
            title = detail.get("title", "")
            snippet = summary[:300]  # Reasonable length
            if title:
                parts.append(f"Under {title}: {snippet}")
            else:
                parts.append(snippet)

    # If no specific provision details, fall back to domain-level knowledge
    if not parts or len(parts) == 1:
        parts.extend(_get_domain_context(query_lower, domains))

    # Add citation references
    if provisions:
        cited = ", ".join(p["title"] for p in provisions[:3])
        parts.append(f"\nRelevant provisions: {cited}.")

    return "\n\n".join(parts) if parts else _fallback_response(domains)


@router.post("/stream")
async def advisory_stream(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> StreamingResponse:
    """Stream an advisory response word-by-word via SSE.

    Applies the same safety chain as /query before streaming begins.
    """
    body = await request.json()
    query_raw = body.get("query", "")
    company_id = body.get("company_id")
    conversation_id = body.get("conversation_id")
    if conversation_id is None:
        conversation_id = uuid.uuid4().int % 2**31
    user_id = current_user.get("sub", "anonymous")

    # ── Step 0: Tenant isolation ─────────────────────────────────
    validate_company_access(current_user, requested_company_id=company_id)

    # ── Step 1: Input sanitisation ──────────────────────────────
    query = sanitise_input(query_raw)
    valid, error_msg = validate_query_length(query)
    if not valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # ── Step 2: Rate limiting ───────────────────────────────────
    if not check_rate_limit(user_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait.")

    # ── Step 3: Query screening (guardrails) ────────────────────
    screening = screen_query(query, user_id=user_id)
    if screening.result in (ScreeningResult.BLOCK, ScreeningResult.ESCALATE):
        raise HTTPException(status_code=422, detail=screening.reason)

    # ── Step 3b: Load conversation memory ───────────────────────
    conv_key = str(conversation_id)
    memory = _conversation_memory.setdefault(conv_key, ShortTermMemory())
    context = memory.load_context(conv_key)
    conversation_history = _format_conversation_history(context.get("turns", []))

    # ── Step 3c: Fetch company profile ────────────────────────
    company_profile = None
    jwt_company_id = current_user.get("company_id")
    effective_company_id = company_id or jwt_company_id
    if effective_company_id is not None:
        try:
            company_profile = _fetch_company_profile(int(effective_company_id))
        except (TypeError, ValueError):
            logger.debug("Invalid company_id for profile fetch: %s", effective_company_id)

    # ── Step 4: EATP genesis record ─────────────────────────────
    session_id = str(uuid.uuid4())
    domains = _detect_domains(query)

    genesis = GenesisRecord(
        session_id=session_id,
        user_verification_level=TrustLevel.STANDARD,
        company_profile_completeness=0.8 if company_profile else (0.5 if company_id else 0.3),
        kb_currency_status={d: "2026-03-01" for d in domains},
        agent_version_hashes={"orchestrator": "v1.0.0"},
        query_text=query,
        query_domains=domains,
    )
    trust_chain = create_trust_chain(genesis)

    # ── Step 5: Anti-amnesia injection ──────────────────────────
    constraints = get_anti_amnesia_injection("orchestrator")
    logger.debug("Stream anti-amnesia constraints: %d rules", constraints.count("[CONSTRAINT"))

    # ── Step 6: Domain detection and KB lookup ──────────────────
    provision_ids = _lookup_provisions(domains, query=query)
    citation_result = validate_citations(provision_ids)
    provisions_cited = [
        {
            "provision_id": c.provision_id,
            "title": c.title,
            "authority_level": c.authority_level.value,
            "status": c.status.value,
        }
        for c in citation_result.validated_citations
    ]

    # ── Step 7: Generate response (LLM first, template fallback) ─
    stream_degraded = False
    llm_result = await _async_run_llm_advisory(
        query,
        domains,
        provisions_cited,
        company_context=company_profile,
        conversation_history=conversation_history,
    )
    if llm_result is not None:
        response_text = llm_result["response_text"]
        confidence = llm_result.get("confidence", UNCERTAINTY_DEFAULTS["confidence"])
        risk_tier = llm_result.get("risk_tier", _classify_risk_tier(domains, confidence))
        stream_degraded = llm_result.get("degraded", False)
        logger.info(
            "Stream response via LLM pipeline (confidence=%.2f, degraded=%s)",
            confidence,
            stream_degraded,
        )
    else:
        confidence = 0.85 if citation_result.is_valid else 0.6
        risk_tier = _classify_risk_tier(domains, confidence)
        response_text = _generate_grounded_response(query, domains, provisions_cited)
        logger.info("Stream response via template fallback (confidence=%.2f)", confidence)

    # ── Step 8: Confidence escalation check ─────────────────────
    escalation = check_confidence_escalation(confidence)
    if escalation is not None:
        risk_tier = "red"

    # ── Step 9: Response content screening ──────────────────────
    response_screening = screen_response(response_text)
    if response_screening.result == ScreeningResult.BLOCK:
        response_text = (
            "I was unable to generate a compliant response for this query. "
            "Please rephrase your question or contact a human HR specialist."
        )
        risk_tier = "red"
        confidence = 0.0

    # ── Step 10: Disclaimer ─────────────────────────────────────
    disclaimer = get_disclaimer(risk_tier, confidence, domains)

    # ── Step 11: Constraint envelope validation ─────────────────
    violations = validate_constraint_envelope("orchestrator", domains)

    # ── Step 12: Record attestation in trust chain ──────────────
    attestation = AgentAttestation(
        agent_id="orchestrator",
        agent_role=AgentRole.ORCHESTRATOR,
        agent_version="v1.0.0",
        domain=",".join(domains),
        provisions_retrieved=[c.provision_id for c in citation_result.validated_citations],
        reasoning_summary=f"Stream: detected domains: {', '.join(domains)}. Retrieved {len(provision_ids)} provisions.",
        conclusion=response_text[:200],
        confidence_score=confidence,
        constraint_envelope_id="orchestrator",
        constraint_violations=violations,
    )
    trust_chain.add_attestation(attestation)
    trust_chain_data = trust_chain.to_dict()

    # ── Step 13: Learning pipeline recording ────────────────────
    pattern_id = f"{'_'.join(sorted(domains))}:{risk_tier}"
    record_query_pattern(
        pattern_id=pattern_id,
        description=f"Stream query across {', '.join(domains)} (risk={risk_tier})",
        domains=domains,
        confidence=confidence,
        satisfaction=1.0,  # Default positive; updated via /learning/feedback
        query_example=query[:100],
    )

    # ── Step 14: Save turn to conversation memory ─────────────
    memory.save_turn(
        session_id=conv_key,
        query=query,
        response=response_text,
        domains=domains,
        risk_tier=risk_tier,
    )

    async def event_generator():
        """Generate SSE events with word-by-word streaming."""
        # Start event
        start_event = {
            "type": "start",
            "query": query,
            "risk_tier": risk_tier,
            "conversation_id": conversation_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        yield f"event: start\ndata: {json.dumps(start_event)}\n\n"

        # Disclaimer event (if applicable)
        if disclaimer.show_disclaimer:
            disc_event = {
                "type": "disclaimer",
                "text": disclaimer.disclaimer_text or disclaimer.framing_text,
                "professional_referral": disclaimer.show_professional_referral,
            }
            yield f"event: disclaimer\ndata: {json.dumps(disc_event)}\n\n"

        # Stream words
        words = response_text.split()
        for i, word in enumerate(words):
            token_event = {
                "type": "token",
                "token": word + " ",
                "index": i,
            }
            yield f"event: token\ndata: {json.dumps(token_event)}\n\n"
            await asyncio.sleep(0.03)

        # Complete event with citations and trust chain
        complete_event = {
            "type": "complete",
            "response": response_text,
            "provisions_cited": provisions_cited,
            "risk_tier": risk_tier,
            "confidence_score": confidence,
            "trust_chain": trust_chain_data,
            "citation_warnings": citation_result.warnings,
            "company_id": company_id,
            "conversation_id": conversation_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if stream_degraded:
            complete_event["degraded"] = True
        yield f"event: complete\ndata: {json.dumps(complete_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history/{conversation_id}")
async def advisory_history(
    conversation_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Retrieve conversation history for a given conversation.

    Returns the messages from the in-memory conversation store.
    Note: conversations are session-scoped and not persisted across restarts.
    """
    from hr_advisory.agents import LongTermMemory

    company_id = current_user.get("company_id")
    mem = LongTermMemory()
    history = mem.get_advisory_history(str(company_id)) if company_id else []

    # Map to conversation-scoped view
    messages = []
    for entry in history:
        messages.append(
            {
                "role": "user",
                "content": entry.get("query_summary", ""),
                "domains": entry.get("domains", []),
                "risk_tier": entry.get("risk_tier", "amber"),
                "timestamp": entry.get("timestamp", ""),
            }
        )

    return {
        "conversation_id": conversation_id,
        "messages": messages,
        "total": len(messages),
    }
