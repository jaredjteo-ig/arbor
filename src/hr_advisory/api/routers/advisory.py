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
import json
import logging
import uuid
from collections import OrderedDict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from hr_advisory.api.middleware.auth_middleware import get_current_user
from hr_advisory.api.middleware.tenant_isolation import validate_company_access
from hr_advisory.security.validation import sanitise_input, validate_query_length
from hr_advisory.trust.citation_validator import CitationValidationResult, validate_citations
from hr_advisory.trust.disclaimers import get_disclaimer
from hr_advisory.trust.eatp_lineage import (
    AgentAttestation,
    AgentRole,
    GenesisRecord,
    TrustLevel,
    create_trust_chain,
    validate_constraint_envelope,
)
from hr_advisory.trust.learning_pipeline import record_query_pattern
from hr_advisory.workflows.guardrails import (
    ScreeningResult,
    check_confidence_escalation,
    check_rate_limit,
    screen_injection,
    screen_query,
    screen_response,
    screen_scope,
)

from hr_advisory.agents.config import (
    install_kaizen_provider_patch,
)
from hr_advisory.agents.memory.short_term import ShortTermMemory
from hr_advisory.services.llm_config import build_llm_context
from hr_advisory.services.llm_budget import check_budget, record_usage
from hr_advisory.services.llm_metrics import log_llm_call, log_budget_warning, log_budget_exceeded

logger = logging.getLogger(__name__)

router = APIRouter()

# Install Kaizen provider monkey-patch for BYOK support.
# Safe to call multiple times (idempotent).
install_kaizen_provider_patch()

# Session-scoped pipeline cache keyed by conversation_id.
# Bounded with LRU eviction to prevent OOM in long-running processes.
_MAX_CONVERSATIONS = 10000
_conversation_memory: OrderedDict[str, ShortTermMemory] = OrderedDict()

# Custom titles set via PATCH /conversations/{id} (overrides auto-generated titles)
_conversation_titles: OrderedDict[str, str] = OrderedDict()

# Tenant isolation: maps conversation_id → user_id who created it
_conversation_owners: OrderedDict[str, str] = OrderedDict()


def _touch_conversation(conv_key: str) -> None:
    """Move a conversation to the end of LRU order and evict oldest if at capacity."""
    for store in (_conversation_memory, _conversation_titles, _conversation_owners):
        if conv_key in store:
            store.move_to_end(conv_key)

    # Evict oldest conversations when at capacity
    while len(_conversation_memory) > _MAX_CONVERSATIONS:
        _conversation_memory.popitem(last=False)
    while len(_conversation_titles) > _MAX_CONVERSATIONS:
        _conversation_titles.popitem(last=False)
    while len(_conversation_owners) > _MAX_CONVERSATIONS:
        _conversation_owners.popitem(last=False)


def _rehydrate_conversation(conv_key: str, messages: list, owner_id: str) -> None:
    """Rebuild in-memory conversation state from DB messages after a restart."""
    memory = ShortTermMemory()
    user_msgs = [m for m in messages if m["role"] == "user"]
    agent_msgs = [m for m in messages if m["role"] == "assistant"]
    for i in range(min(len(user_msgs), len(agent_msgs))):
        turn = {
            "user": user_msgs[i].get("content", ""),
            "agent": agent_msgs[i].get("content", ""),
            "entities": {},
            "domains": agent_msgs[i].get("domains", []),
            "risk_tier": agent_msgs[i].get("risk_tier", "green"),
            "timestamp": agent_msgs[i].get("timestamp", ""),
        }
        if agent_msgs[i].get("provisions_cited"):
            turn["provisions_cited"] = agent_msgs[i]["provisions_cited"]
        if agent_msgs[i].get("confidence_score") is not None:
            turn["confidence_score"] = agent_msgs[i]["confidence_score"]
        memory._buffer.save_turn(conv_key, turn)

    _conversation_memory[conv_key] = memory
    _conversation_owners[conv_key] = owner_id
    _touch_conversation(conv_key)


_RISK_TIER_SEVERITY = {"green": 0, "amber": 1, "red": 2}


def _escalate_risk_tier(current: str, proposed: str) -> str:
    """Enforce monotonic risk tier escalation — tier can only go up, never down."""
    current_level = _RISK_TIER_SEVERITY.get(current, 0)
    proposed_level = _RISK_TIER_SEVERITY.get(proposed, 0)
    return proposed if proposed_level >= current_level else current


def _get_company_budget_limit(company_id: int) -> float | None:
    """Fetch the company's custom monthly LLM budget, or None for default."""
    try:
        from kailash.runtime import LocalRuntime
        from kailash.workflow.builder import WorkflowBuilder
        import hr_advisory.models  # noqa: F401

        wf = WorkflowBuilder()
        wf.add_node(
            "CompanyListNode",
            "co",
            {
                "filter": {"id": company_id},
                "limit": 1,
                "enable_cache": False,
            },
        )
        runtime = LocalRuntime()
        results, _ = runtime.execute(wf.build())
        raw = results.get("co", {})
        records = raw.get("records", []) if isinstance(raw, dict) else []
        if records:
            val = records[0].get("monthly_llm_budget_usd")
            if val is not None:
                import math

                fval = float(val)
                if math.isfinite(fval) and fval > 0:
                    return fval
    except Exception:
        pass
    return None


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


@router.post("/query")
async def advisory_query(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
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

    # Record conversation ownership for tenant isolation
    _conv_key = str(conversation_id)
    if _conv_key not in _conversation_owners:
        _conversation_owners[_conv_key] = str(user_id)

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

    # ── Step 2b: Scope check (is this an HR question?) ──────────
    scope_result = screen_scope(query)
    if scope_result.result == ScreeningResult.BLOCK:
        return {
            "query": query,
            "response": scope_result.reason,
            "alternative_guidance": scope_result.alternative_guidance,
            "risk_tier": "green",
            "confidence_score": 1.0,
            "out_of_scope": True,
            "provisions_cited": [],
            "company_id": company_id,
            "conversation_id": conversation_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ── Step 2c: Prompt injection detection ───────────────────
    injection_result = screen_injection(query, user_id=user_id)
    if injection_result.result == ScreeningResult.BLOCK:
        return {
            "query": query,
            "response": injection_result.reason,
            "risk_tier": "red",
            "confidence_score": 1.0,
            "blocked": True,
            "provisions_cited": [],
            "company_id": company_id,
            "conversation_id": conversation_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ── Step 3: Query screening (circumvention + escalation) ──
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
    _touch_conversation(conv_key)
    conversation_messages = memory.load_as_messages(conv_key)

    # ── Step 3c: Fetch company profile ────────────────────────
    company_profile = None
    jwt_company_id = current_user.get("company_id")
    effective_company_id = company_id or jwt_company_id
    if effective_company_id is not None:
        try:
            company_profile = _fetch_company_profile(int(effective_company_id))
        except (TypeError, ValueError):
            logger.debug("Invalid company_id for profile fetch: %s", effective_company_id)

    # ── Step 3d: Resolve LLM context (BYOK / Ollama / server default) ─
    llm_context = None
    budget_result = None
    try:
        _user_id_int = None
        try:
            _user_id_int = int(user_id) if user_id != "anonymous" else None
        except (TypeError, ValueError):
            pass
        if effective_company_id is not None:
            llm_context = build_llm_context(
                company_id=int(effective_company_id),
                user_id=_user_id_int,
            )
        else:
            from hr_advisory.agents.llm_context import LLMKeyContext

            llm_context = LLMKeyContext.from_server_env()
    except Exception:
        logger.warning("Failed to resolve LLM context — using server defaults", exc_info=True)

    # ── Step 3e: Budget check (server-key users only) ────────────
    budget_result = None
    if (
        llm_context is not None
        and not llm_context.is_byok
        and llm_context.provider != "ollama"
        and effective_company_id is not None
    ):
        try:
            company_budget_limit = _get_company_budget_limit(int(effective_company_id))
            budget_result = check_budget(
                int(effective_company_id), budget_limit_usd=company_budget_limit
            )
            if budget_result.warning:
                log_budget_warning(
                    int(effective_company_id), budget_result.used_usd, budget_result.limit_usd
                )
            if not budget_result.allowed:
                log_budget_exceeded(int(effective_company_id))
                from fastapi.responses import JSONResponse

                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "budget_exceeded",
                        "message": (
                            "Your company's free AI advisory allowance has been used this month. "
                            "You can add your own API key in Settings to continue, or wait until "
                            "next month when the allowance resets."
                        ),
                        "budget_info": budget_result.to_dict(),
                    },
                )
        except Exception:
            logger.warning("Budget check failed — allowing query", exc_info=True)

    # ── Step 4: Run autonomous advisory engine ────────────────────
    from hr_advisory.agents.advisory_engine import AdvisoryEngine

    engine = AdvisoryEngine(llm_context=llm_context)
    import asyncio

    # Build user context for personalisation
    _user_ctx = {
        "role": current_user.get("role", ""),
        "name": current_user.get("name", ""),
    }

    loop = asyncio.get_event_loop()
    engine_result = await loop.run_in_executor(
        None,
        lambda: engine.run(
            query=query,
            conversation_history=conversation_messages,
            company_context=company_profile,
            company_id=int(effective_company_id) if effective_company_id else None,
            user_context=_user_ctx,
        ),
    )

    response_text = engine_result.get("response_text", "")
    confidence = engine_result.get("confidence", 0.7)
    risk_tier = engine_result.get("risk_tier", "amber")
    response_degraded = engine_result.get("degraded", False)
    domains = engine_result.get("domains", ["general"])
    provisions_cited = engine_result.get("citations", [])
    engine_usage = engine_result.get("usage", {})

    # Build trust chain from engine results
    session_id = str(uuid.uuid4())
    genesis = GenesisRecord(
        session_id=session_id,
        user_verification_level=TrustLevel.STANDARD,
        company_profile_completeness=0.8 if company_profile else (0.5 if company_id else 0.3),
        kb_currency_status={d: "2026-03-01" for d in domains},
        agent_version_hashes={"advisory_engine": "v2.0.0"},
        query_text=query,
        query_domains=domains,
    )
    trust_chain = create_trust_chain(genesis)

    logger.info(
        "Advisory response via autonomous engine (confidence=%.2f, degraded=%s, tools=%s)",
        confidence,
        response_degraded,
        engine_result.get("tools_called", []),
    )

    # ── Step 8: Confidence escalation check ─────────────────────
    escalation = check_confidence_escalation(confidence)
    if escalation is not None:
        risk_tier = "red"

    # ── Step 9: Response content screening ──────────────────────
    response_screening = screen_response(response_text)
    if response_screening.result == ScreeningResult.BLOCK:
        response_text = (
            "This response was flagged by our content safety review. "
            "The relevant provisions are shown below for your reference. "
            "Please rephrase your question or connect with an employment law specialist."
        )
        risk_tier = "red"
        confidence = 0.0

    # ── Step 9b: Citation validation ──────────────────────────
    _cited_ids = [p.get("provision_id", "") for p in provisions_cited] if provisions_cited else []
    citation_result = (
        validate_citations(_cited_ids)
        if _cited_ids
        else CitationValidationResult(
            is_valid=True, validated_citations=[], invalid_citations=[], warnings=[]
        )
    )

    # ── Step 10: Disclaimer ─────────────────────────────────────
    disclaimer = get_disclaimer(risk_tier, confidence, domains)

    # ── Step 11: Constraint envelope validation ─────────────────
    violations = validate_constraint_envelope("orchestrator", domains)

    # ── Step 12: Record attestation in trust chain ──────────────
    attestation = AgentAttestation(
        agent_id="advisory_engine",
        agent_role=AgentRole.ORCHESTRATOR,
        agent_version="v2.0.0",
        domain=",".join(domains),
        provisions_retrieved=_cited_ids,
        reasoning_summary=f"Autonomous engine: domains={domains}, tools={engine_result.get('tools_called', [])}",
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
    # Convert user_id/company_id to int for DB persistence
    _persist_uid = None
    try:
        _persist_uid = int(user_id) if str(user_id).isdigit() else None
    except (TypeError, ValueError):
        pass
    _persist_cid = None
    try:
        _persist_cid = int(effective_company_id) if effective_company_id is not None else None
    except (TypeError, ValueError):
        pass
    memory.save_turn(
        session_id=conv_key,
        query=query,
        response=response_text,
        domains=domains,
        risk_tier=risk_tier,
        provisions_cited=provisions_cited,
        confidence_score=confidence,
        user_id=_persist_uid,
        company_id=_persist_cid,
    )

    # ── Step 14b: Record token usage for budget tracking ────────
    if llm_context and not llm_context.is_byok and effective_company_id is not None:
        try:
            # Use real token counts from the engine (no more estimation)
            _real_input_tokens = engine_usage.get("input_tokens", 0)
            _real_output_tokens = engine_usage.get("output_tokens", 0)
            _cost = record_usage(
                company_id=int(effective_company_id),
                input_tokens=_real_input_tokens,
                output_tokens=_real_output_tokens,
                model=llm_context.model or "unknown",
            )
            log_llm_call(
                company_id=int(effective_company_id),
                provider=llm_context.provider,
                model=llm_context.model or "unknown",
                input_tokens=_real_input_tokens,
                output_tokens=_real_output_tokens,
                cost_usd=_cost.get("estimated_cost", 0.0) if isinstance(_cost, dict) else 0.0,
                duration_ms=0.0,
                is_byok=llm_context.is_byok,
            )
        except Exception:
            logger.warning("Failed to record LLM usage", exc_info=True)

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

    # Include budget info for server-key users
    if budget_result and llm_context and not llm_context.is_byok:
        advisory_response["budget_info"] = {
            "used_usd": budget_result.used_usd,
            "limit_usd": budget_result.limit_usd,
            "queries_this_month": budget_result.query_count,
            "warning": budget_result.warning,
        }

    # Include LLM provider info (masked key)
    if llm_context:
        advisory_response["llm_info"] = {
            "provider": llm_context.provider,
            "model": llm_context.model,
            "is_byok": llm_context.is_byok,
        }

    return advisory_response

    # --- Dead code removed (2026-03-24) ---
    # The following functions were part of the old Kaizen pipeline that was
    # replaced by AdvisoryEngine (LLM ReAct loop in advisory_engine.py):
    #   _get_provision_details, _generate_topic_intro, _get_domain_context,
    #   _fallback_response, _run_llm_advisory
    # ~1000 lines of keyword routing, deterministic dispatch, and hardcoded
    # domain maps removed. The LLM IS the router now.


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

    # Record conversation ownership for tenant isolation
    _conv_key = str(conversation_id)
    if _conv_key not in _conversation_owners:
        _conversation_owners[_conv_key] = str(user_id)

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

    # ── Step 2b: Scope check ─────────────────────────────────────
    scope_result = screen_scope(query)
    if scope_result.result == ScreeningResult.BLOCK:
        # Return as proper SSE events (event: type prefix required
        # for the frontend parseSSEChunk/processEvent dispatcher).
        async def _scope_decline():
            start_data = json.dumps({"conversation_id": conversation_id})
            yield f"event: start\ndata: {start_data}\n\n"
            decline_data = json.dumps(
                {
                    "response": scope_result.reason,
                    "out_of_scope": True,
                    "risk_tier": "green",
                    "confidence_score": 1.0,
                    "conversation_id": conversation_id,
                }
            )
            yield f"event: complete\ndata: {decline_data}\n\n"

        return StreamingResponse(_scope_decline(), media_type="text/event-stream")

    # ── Step 2c: Prompt injection detection ───────────────────
    injection_result = screen_injection(query, user_id=user_id)
    if injection_result.result == ScreeningResult.BLOCK:

        async def _injection_decline():
            start_data = json.dumps({"conversation_id": conversation_id})
            yield f"event: start\ndata: {start_data}\n\n"
            decline_data = json.dumps(
                {
                    "response": injection_result.reason,
                    "risk_tier": "red",
                    "confidence_score": 1.0,
                    "conversation_id": conversation_id,
                }
            )
            yield f"event: complete\ndata: {decline_data}\n\n"

        return StreamingResponse(_injection_decline(), media_type="text/event-stream")

    # ── Step 3: Query screening (circumvention + escalation) ──
    screening = screen_query(query, user_id=user_id)
    if screening.result in (ScreeningResult.BLOCK, ScreeningResult.ESCALATE):

        async def _screening_decline():
            start_data = json.dumps({"conversation_id": conversation_id})
            yield f"event: start\ndata: {start_data}\n\n"
            decline_data = json.dumps(
                {
                    "response": screening.reason,
                    "risk_tier": "red",
                    "confidence_score": 1.0,
                    "conversation_id": conversation_id,
                }
            )
            yield f"event: complete\ndata: {decline_data}\n\n"

        return StreamingResponse(_screening_decline(), media_type="text/event-stream")

    # ── Step 3b: Load conversation memory ───────────────────────
    conv_key = str(conversation_id)
    memory = _conversation_memory.setdefault(conv_key, ShortTermMemory())
    _touch_conversation(conv_key)
    conversation_messages = memory.load_as_messages(conv_key)

    # ── Step 3c: Fetch company profile ────────────────────────
    company_profile = None
    jwt_company_id = current_user.get("company_id")
    effective_company_id = company_id or jwt_company_id
    if effective_company_id is not None:
        try:
            company_profile = _fetch_company_profile(int(effective_company_id))
        except (TypeError, ValueError):
            logger.debug("Invalid company_id for profile fetch: %s", effective_company_id)

    # ── Step 3d: Resolve LLM context (BYOK / Ollama / server default) ─
    llm_context = None
    budget_result = None
    try:
        _user_id_int = None
        try:
            _user_id_int = int(user_id) if user_id != "anonymous" else None
        except (TypeError, ValueError):
            pass
        if effective_company_id is not None:
            llm_context = build_llm_context(
                company_id=int(effective_company_id),
                user_id=_user_id_int,
            )
        else:
            from hr_advisory.agents.llm_context import LLMKeyContext

            llm_context = LLMKeyContext.from_server_env()
    except Exception:
        logger.warning(
            "Stream: failed to resolve LLM context — using server defaults", exc_info=True
        )

    # ── Step 3e: Budget check (server-key users only) ────────────
    if (
        llm_context is not None
        and not llm_context.is_byok
        and llm_context.provider != "ollama"
        and effective_company_id is not None
    ):
        try:
            stream_budget_limit = _get_company_budget_limit(int(effective_company_id))
            budget_result = check_budget(
                int(effective_company_id), budget_limit_usd=stream_budget_limit
            )
            if not budget_result.allowed:
                raise HTTPException(
                    status_code=429,
                    detail=(
                        "Your company's free AI advisory allowance has been used this month. "
                        "You can add your own API key in Settings to continue, or wait until "
                        "next month when the allowance resets."
                    ),
                )
        except HTTPException:
            raise
        except Exception:
            logger.warning("Stream: budget check failed — allowing query", exc_info=True)

    # ── Step 4: Stream via kaizen-agents Delegate ───────────────
    from hr_advisory.delegate.arbor_loop import DelegateConfig, create_delegate
    from kaizen_agents.delegate import TextDelta, ErrorEvent

    _stream_user_ctx = {
        "role": current_user.get("role", ""),
        "name": current_user.get("name", ""),
    }

    delegate_config = DelegateConfig(
        company_id=int(effective_company_id) if effective_company_id else None,
        company_context=company_profile,
        user_context=_stream_user_ctx,
    )
    # Pass BYOK key if available
    if llm_context and llm_context.api_key:
        delegate_config.api_key = llm_context.api_key
    if llm_context and llm_context.base_url:
        delegate_config.base_url = llm_context.base_url
    if llm_context and llm_context.model:
        delegate_config.model = llm_context.model

    delegate_loop = create_delegate(delegate_config)

    # Inject conversation history into the delegate's underlying loop
    for msg in conversation_messages:
        if msg.get("role") == "user":
            delegate_loop.loop.conversation.add_user(msg["content"])
        elif msg.get("role") == "assistant":
            delegate_loop.loop.conversation.add_assistant(msg["content"])

    async def event_generator():
        """Stream tokens from the kaizen-agents Delegate loop."""
        # Start event
        start_event = {
            "type": "start",
            "query": query,
            "conversation_id": conversation_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        yield f"event: start\ndata: {json.dumps(start_event)}\n\n"

        # Stream real tokens from the Delegate
        full_response = []
        stream_error = False
        token_index = 0
        try:
            async for event in delegate_loop.run(query):
                if isinstance(event, TextDelta):
                    full_response.append(event.text)
                    token_event = {
                        "type": "token",
                        "token": event.text,
                        "index": token_index,
                    }
                    token_index += 1
                    yield f"event: token\ndata: {json.dumps(token_event)}\n\n"
                elif isinstance(event, ErrorEvent):
                    logger.warning("Delegate ErrorEvent: %s", event.error)
                    # Don't emit error mid-stream — collect and handle at end
                    stream_error = True
        except Exception as stream_exc:
            logger.error("Delegate stream error: %s", stream_exc, exc_info=True)
            stream_error = True

        response_text = "".join(full_response)

        # Handle error: emit error event and stop (no complete after error)
        if stream_error and not response_text:
            error_event = {"type": "error", "message": "Advisory engine encountered an error."}
            yield f"event: error\ndata: {json.dumps(error_event)}\n\n"
            return

        # Guard empty response
        if not response_text:
            response_text = (
                "I wasn't able to generate a response for that question. "
                "Could you rephrase or provide more detail?"
            )

        # Post-stream safety: screen the response
        response_screening = screen_response(response_text)
        risk_tier = "green"
        if response_screening.result == ScreeningResult.BLOCK:
            response_text = (
                "This response was flagged by our content safety review. "
                "Please rephrase your question."
            )
            risk_tier = "red"

        # Save conversation turn for multi-turn continuity
        memory.save_turn(
            session_id=conv_key,
            query=query,
            response=response_text,
            domains=[],
            risk_tier=risk_tier,
            provisions_cited=[],
            confidence_score=0.9,
        )

        # Complete event
        complete_event = {
            "type": "complete",
            "response": response_text,
            "provisions_cited": [],
            "risk_tier": risk_tier,
            "confidence_score": 0.9,
            "company_id": company_id,
            "conversation_id": conversation_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
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


@router.get("/conversations")
async def list_conversations(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List all conversations for the current user.

    Returns conversation summaries derived from the in-memory
    conversation store. Each summary includes an auto-generated
    title from the first user message.
    """
    user_id = str(current_user.get("sub", "anonymous"))

    conversations = []
    for conv_key, memory in _conversation_memory.items():
        ctx = memory.load_context(conv_key)
        turns = ctx.get("turns", [])
        if not turns:
            continue

        # Tenant isolation: skip conversations that don't belong to this user
        conv_owner = _conversation_owners.get(conv_key, "")
        if conv_owner and conv_owner != user_id:
            continue

        # Auto-generate title from first user message (first 60 chars)
        first_user_msg = turns[0].get("user", "New conversation")
        title = _conversation_titles.get(conv_key, "")
        if not title:
            title = first_user_msg[:60].rstrip()
            if len(first_user_msg) > 60:
                title += "..."

        # Last message for preview
        last_turn = turns[-1]
        last_message = last_turn.get("agent", last_turn.get("user", ""))

        # Timestamp from last turn
        timestamp = last_turn.get("timestamp", "")

        # Highest risk tier across turns
        risk_tiers = [t.get("risk_tier", "green") for t in turns]
        worst_risk = "green"
        for tier in risk_tiers:
            worst_risk = _escalate_risk_tier(worst_risk, tier)

        try:
            conv_id = int(conv_key)
        except (ValueError, TypeError):
            continue

        conversations.append(
            {
                "id": conv_id,
                "title": title,
                "last_message": last_message[:100] if last_message else "",
                "timestamp": timestamp,
                "risk_tier": worst_risk,
                "message_count": len(turns),
            }
        )

    # If in-memory is empty, try loading from database (survives restarts)
    if not conversations:
        try:
            from kailash import LocalRuntime, WorkflowBuilder

            wf = WorkflowBuilder()
            wf.add_node(
                "ConversationThreadListNode",
                "list_threads",
                {
                    "filter": {"user_id": int(user_id) if user_id.isdigit() else 0},
                    "limit": 50,
                    "enable_cache": False,
                },
            )
            runtime = LocalRuntime()
            results, _ = runtime.execute(wf.build())
            records = results.get("list_threads", {})
            items = records.get("records", []) if isinstance(records, dict) else []

            for thread in items:
                # Load last message for preview
                last_msg = ""
                try:
                    wf2 = WorkflowBuilder()
                    wf2.add_node(
                        "ConversationMessageListNode",
                        "msgs",
                        {
                            "filter": {"thread_id": thread["id"]},
                            "limit": 1,
                            "enable_cache": False,
                        },
                    )
                    msg_results, _ = runtime.execute(wf2.build())
                    msg_records = msg_results.get("msgs", {})
                    msg_items = (
                        msg_records.get("records", []) if isinstance(msg_records, dict) else []
                    )
                    if msg_items:
                        last_msg = msg_items[-1].get("text", "")[:100]
                except Exception:
                    pass

                title = thread.get("subject", "") or "New conversation"
                conversations.append(
                    {
                        "id": thread["id"],
                        "title": title[:60],
                        "last_message": last_msg,
                        "timestamp": thread.get("started_at", ""),
                        "risk_tier": "green",
                        "message_count": thread.get("turn_count", 0),
                    }
                )
        except Exception as exc:
            logger.warning("Failed to load conversations from DB: %s", exc)

    # Sort by timestamp descending (newest first)
    conversations.sort(key=lambda c: str(c.get("timestamp", "")), reverse=True)

    return {
        "conversations": conversations,
        "total": len(conversations),
    }


@router.get("/history/{conversation_id}")
async def advisory_history(
    conversation_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Retrieve conversation history for a given conversation.

    Returns the messages from the in-memory conversation store,
    including both user and assistant messages in chronological order.
    """
    conv_key = str(conversation_id)
    user_id = str(current_user.get("sub", "anonymous"))

    # Tenant isolation: verify ownership
    owner = _conversation_owners.get(conv_key, "")
    if owner and owner != user_id:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    memory = _conversation_memory.get(conv_key)

    messages = []
    if memory is not None:
        ctx = memory.load_context(conv_key)
        turns = ctx.get("turns", [])
        for turn in turns:
            # User message
            user_content = turn.get("user", "")
            if user_content:
                messages.append(
                    {
                        "role": "user",
                        "content": user_content,
                        "timestamp": turn.get("timestamp", ""),
                    }
                )
            # Assistant message
            agent_content = turn.get("agent", "")
            if agent_content:
                msg: dict = {
                    "role": "assistant",
                    "content": agent_content,
                    "domains": turn.get("domains", []),
                    "risk_tier": turn.get("risk_tier", "green"),
                    "timestamp": turn.get("timestamp", ""),
                }
                if turn.get("provisions_cited"):
                    msg["provisions_cited"] = turn["provisions_cited"]
                if turn.get("confidence_score") is not None:
                    msg["confidence_score"] = turn["confidence_score"]
                messages.append(msg)

    # If in-memory is empty, try loading from database (survives restarts)
    if not messages:
        try:
            from kailash import LocalRuntime, WorkflowBuilder

            # Find the thread by session_id (conversation_id)
            wf = WorkflowBuilder()
            wf.add_node(
                "ConversationThreadListNode",
                "find_thread",
                {
                    "filter": {"session_id": conv_key},
                    "limit": 1,
                    "enable_cache": False,
                },
            )
            runtime = LocalRuntime()
            results, _ = runtime.execute(wf.build())
            records = results.get("find_thread", {})
            items = records.get("records", []) if isinstance(records, dict) else []

            if items:
                thread = items[0]
                thread_id = thread["id"]
                thread_owner = str(thread.get("user_id", ""))

                # Tenant isolation: verify ownership
                if thread_owner and thread_owner != user_id and thread_owner != "0":
                    raise HTTPException(status_code=404, detail="Conversation not found.")

                # Load messages from DB
                wf2 = WorkflowBuilder()
                wf2.add_node(
                    "ConversationMessageListNode",
                    "load_msgs",
                    {
                        "filter": {"thread_id": thread_id},
                        "limit": 10000,
                        "enable_cache": False,
                    },
                )
                msg_results, _ = runtime.execute(wf2.build())
                msg_records = msg_results.get("load_msgs", {})
                msg_items = msg_records.get("records", []) if isinstance(msg_records, dict) else []

                for db_msg in msg_items:
                    sender = db_msg.get("sender", "user")
                    role = "assistant" if sender == "agent" else "user"
                    entry: dict = {
                        "role": role,
                        "content": db_msg.get("text", ""),
                        "timestamp": db_msg.get("created_at", ""),
                    }
                    if role == "assistant":
                        entry["domains"] = (
                            json.loads(db_msg.get("domains", "[]")) if db_msg.get("domains") else []
                        )
                        entry["risk_tier"] = db_msg.get("risk_tier", "green")
                        if db_msg.get("provisions_cited"):
                            entry["provisions_cited"] = json.loads(db_msg["provisions_cited"])
                        if db_msg.get("confidence_score") is not None:
                            entry["confidence_score"] = db_msg["confidence_score"]
                    messages.append(entry)

                # Rehydrate in-memory state so subsequent requests are fast
                if messages and conv_key not in _conversation_memory:
                    _rehydrate_conversation(conv_key, messages, thread_owner)

        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("Failed to load conversation history from DB: %s", exc)

    return {
        "conversation_id": conversation_id,
        "messages": messages,
        "total": len(messages),
    }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Delete a conversation and its history.

    Removes the conversation from the in-memory store.
    """
    conv_key = str(conversation_id)
    user_id = str(current_user.get("sub", "anonymous"))

    # Tenant isolation: verify ownership before deletion
    owner = _conversation_owners.get(conv_key, "")
    if owner and owner != user_id:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    removed = conv_key in _conversation_memory
    _conversation_memory.pop(conv_key, None)
    _conversation_titles.pop(conv_key, None)
    _conversation_owners.pop(conv_key, None)

    if not removed:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    return {
        "conversation_id": conversation_id,
        "deleted": True,
    }


@router.patch("/conversations/{conversation_id}")
async def rename_conversation(
    conversation_id: int,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Rename a conversation.

    Accepts a JSON body with a ``title`` field.
    """
    conv_key = str(conversation_id)
    user_id = str(current_user.get("sub", "anonymous"))

    # Tenant isolation: verify ownership before renaming
    owner = _conversation_owners.get(conv_key, "")
    if owner and owner != user_id:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    if conv_key not in _conversation_memory:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    body = await request.json()
    new_title = body.get("title", "").strip()
    if not new_title:
        raise HTTPException(status_code=400, detail="Title must not be empty.")
    if len(new_title) > 200:
        raise HTTPException(status_code=400, detail="Title must be 200 characters or less.")

    _conversation_titles[conv_key] = new_title

    return {
        "conversation_id": conversation_id,
        "title": new_title,
        "updated": True,
    }
