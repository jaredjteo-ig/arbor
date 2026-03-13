"""Integration tests for the HR advisory orchestration pipeline.

Tests are split into two groups:
  1. Memory / infrastructure tests -- always pass, no LLM needed.
  2. LLM-dependent agent tests -- skip when OPENAI_API_KEY is absent.
"""

import pytest

from hr_advisory.agents import (
    HRSharedMemoryPool,
    LongTermMemory,
    OrchestratorAgent,
    QueryAnalyzerAgent,
    ResponseSynthesizerAgent,
    ShortTermMemory,
    create_orchestration_pipeline,
)

# ---------------------------------------------------------------------------
# Skip condition for LLM tests
# ---------------------------------------------------------------------------

from hr_advisory.agents.config import has_llm_available

HAS_LLM = has_llm_available()

requires_llm = pytest.mark.skipif(
    not HAS_LLM,
    reason="No LLM provider available (set OPENAI_API_KEY or run ollama)",
)


# ===================================================================
# 1. Memory / infrastructure tests  (always pass)
# ===================================================================


class TestHRSharedMemoryPool:
    """Validate shared memory pool for specialist outputs."""

    def test_write_and_read_specialist_output(self):
        pool = HRSharedMemoryPool()
        pool.write_specialist_output(
            agent_id="cpf_specialist",
            domain="cpf",
            content={"advice": "Contribute 17% employer share"},
            provision_ids=[42, 43],
            confidence=0.9,
            risk_tier="green",
        )

        outputs = pool.read_all_specialist_outputs()
        assert len(outputs) == 1
        assert outputs[0]["agent_id"] == "cpf_specialist"
        assert outputs[0]["metadata"]["domain"] == "cpf"
        assert outputs[0]["metadata"]["provision_ids"] == [42, 43]
        assert outputs[0]["metadata"]["confidence"] == 0.9
        assert outputs[0]["metadata"]["risk_tier"] == "green"

    def test_read_by_domain(self):
        pool = HRSharedMemoryPool()
        pool.write_specialist_output(
            agent_id="cpf_specialist",
            domain="cpf",
            content="CPF advice",
            confidence=0.8,
        )
        pool.write_specialist_output(
            agent_id="tax_specialist",
            domain="tax",
            content="Tax advice",
            confidence=0.7,
        )

        cpf_outputs = pool.read_by_domain("cpf")
        assert len(cpf_outputs) == 1
        assert cpf_outputs[0]["metadata"]["domain"] == "cpf"

    def test_highest_risk_tier_escalation(self):
        pool = HRSharedMemoryPool()
        pool.write_specialist_output(agent_id="a", domain="cpf", content="ok", risk_tier="green")
        pool.write_specialist_output(
            agent_id="b", domain="tax", content="tricky", risk_tier="amber"
        )

        assert pool.get_highest_risk_tier() == "amber"

        pool.write_specialist_output(agent_id="c", domain="wsh", content="danger", risk_tier="red")
        assert pool.get_highest_risk_tier() == "red"

    def test_invalid_risk_tier_rejected(self):
        pool = HRSharedMemoryPool()
        with pytest.raises(ValueError, match="risk_tier"):
            pool.write_specialist_output(
                agent_id="x",
                domain="cpf",
                content="oops",
                risk_tier="purple",
            )

    def test_clear_pool(self):
        pool = HRSharedMemoryPool()
        pool.write_specialist_output(agent_id="a", domain="cpf", content="data")
        assert len(pool.read_all_specialist_outputs()) > 0

        pool.clear()
        assert len(pool.read_all_specialist_outputs()) == 0

    def test_stats(self):
        pool = HRSharedMemoryPool()
        pool.write_specialist_output(agent_id="a", domain="cpf", content="data")
        stats = pool.get_stats()
        assert stats["insight_count"] == 1
        assert stats["agent_count"] == 1


class TestShortTermMemory:
    """Validate per-session conversation memory."""

    def test_save_and_load_turn(self):
        mem = ShortTermMemory(max_turns=10)
        mem.save_turn(
            session_id="s1",
            query="How to calculate CPF?",
            response="Employer contributes 17%.",
            entities={"topic": "cpf"},
            domains=["cpf"],
            risk_tier="green",
        )

        ctx = mem.load_context("s1")
        assert ctx["turn_count"] == 1
        assert ctx["turns"][0]["user"] == "How to calculate CPF?"
        assert ctx["turns"][0]["agent"] == "Employer contributes 17%."
        assert ctx["turns"][0]["entities"]["topic"] == "cpf"

    def test_context_across_turns(self):
        mem = ShortTermMemory(max_turns=10)
        mem.save_turn("s1", "Q1", "A1", domains=["cpf"])
        mem.save_turn("s1", "Q2", "A2", domains=["tax"])
        mem.save_turn("s1", "Q3", "A3", domains=["wsh"])

        ctx = mem.load_context("s1")
        assert ctx["turn_count"] == 3
        assert "cpf" in ctx["recent_domains"]
        assert "tax" in ctx["recent_domains"]
        assert "wsh" in ctx["recent_domains"]

    def test_window_limit(self):
        mem = ShortTermMemory(max_turns=2)
        mem.save_turn("s1", "Q1", "A1")
        mem.save_turn("s1", "Q2", "A2")
        mem.save_turn("s1", "Q3", "A3")

        ctx = mem.load_context("s1")
        assert ctx["turn_count"] == 2
        assert ctx["turns"][0]["user"] == "Q2"  # Q1 evicted

    def test_get_last_query(self):
        mem = ShortTermMemory()
        assert mem.get_last_query("s1") is None

        mem.save_turn("s1", "Hello", "Hi")
        assert mem.get_last_query("s1") == "Hello"

    def test_clear_session(self):
        mem = ShortTermMemory()
        mem.save_turn("s1", "Q", "A")
        mem.clear("s1")
        assert mem.get_turn_count("s1") == 0


class TestLongTermMemory:
    """Validate per-company long-term memory."""

    def test_company_context(self):
        mem = LongTermMemory()
        mem.set_company_context("c1", {"headcount": 25, "sector": "F&B"})
        ctx = mem.get_company_context("c1")
        assert ctx["headcount"] == 25
        assert ctx["sector"] == "F&B"

    def test_context_update_merges(self):
        mem = LongTermMemory()
        mem.set_company_context("c1", {"headcount": 10})
        mem.set_company_context("c1", {"sector": "Tech"})
        ctx = mem.get_company_context("c1")
        assert ctx["headcount"] == 10
        assert ctx["sector"] == "Tech"

    def test_topic_tracking(self):
        mem = LongTermMemory()
        mem.record_topic("c1", ["cpf", "tax"])
        mem.record_topic("c1", ["cpf"])
        mem.record_topic("c1", ["cpf", "wsh"])

        topics = mem.get_frequent_topics("c1", top_n=2)
        assert topics[0]["domain"] == "cpf"
        assert topics[0]["count"] == 3

    def test_advisory_history(self):
        mem = LongTermMemory()
        mem.record_advisory("c1", "CPF rates", ["cpf"], "green")
        mem.record_advisory("c1", "Leave entitlement", ["employment_act"], "amber")

        history = mem.get_advisory_history("c1")
        assert len(history) == 2
        # Most recent first
        assert history[0]["query_summary"] == "Leave entitlement"

    def test_clear_company(self):
        mem = LongTermMemory()
        mem.set_company_context("c1", {"x": 1})
        mem.clear("c1")
        ctx = mem.get_company_context("c1")
        assert ctx == {}

    def test_clear_all(self):
        mem = LongTermMemory()
        mem.set_company_context("c1", {"x": 1})
        mem.set_company_context("c2", {"y": 2})
        mem.clear()
        assert mem.get_company_context("c1") == {}
        assert mem.get_company_context("c2") == {}


# ===================================================================
# 2. Agent instantiation tests  (no LLM call, always pass)
# ===================================================================


class TestAgentInstantiation:
    """Verify agents can be created without an API key."""

    def test_query_analyzer_creates(self):
        agent = QueryAnalyzerAgent()
        assert agent.agent_id == "query_analyzer"
        assert agent.signature is not None

    def test_orchestrator_creates(self):
        agent = OrchestratorAgent()
        assert agent.agent_id == "orchestrator"
        assert agent.signature is not None

    def test_response_synthesizer_creates(self):
        agent = ResponseSynthesizerAgent()
        assert agent.agent_id == "response_synthesizer"
        assert agent.signature is not None

    def test_pipeline_factory(self):
        pipeline = create_orchestration_pipeline()
        assert "query_analyzer" in pipeline
        assert "dispatch_router" in pipeline
        assert "response_synthesizer" in pipeline
        assert "shared_pool" in pipeline
        assert "short_term_memory" in pipeline
        assert "long_term_memory" in pipeline

    def test_pipeline_shared_memory_wired(self):
        pipeline = create_orchestration_pipeline()
        qa = pipeline["query_analyzer"]
        synth = pipeline["response_synthesizer"]

        # Query analyzer and synthesizer share the same SharedMemoryPool
        assert qa.shared_memory is synth.shared_memory


# ===================================================================
# 3. LLM-dependent tests  (skip without API key)
# ===================================================================


@requires_llm
class TestQueryAnalyzerWithLLM:
    """Test QueryAnalyzerAgent with a real LLM call."""

    def test_classify_simple_cpf_query(self):
        agent = QueryAnalyzerAgent()
        result = agent.analyze("How do I calculate CPF contributions for my employees?")

        assert "domains" in result
        assert isinstance(result["domains"], list)
        assert len(result["domains"]) >= 1
        assert "risk_tier" in result
        assert result["risk_tier"] in ("green", "amber", "red")
        assert "entities" in result
        assert "routing_decision" in result

    def test_classify_cross_domain_query(self):
        agent = QueryAnalyzerAgent()
        result = agent.analyze(
            "I want to hire a foreign worker on an S-Pass. "
            "What are the CPF and levy obligations?"
        )

        assert "domains" in result
        # Should identify at least foreign_manpower or cpf
        domains = result["domains"]
        assert any(
            d in domains for d in ("cpf", "foreign_manpower")
        ), f"Expected cpf or foreign_manpower in {domains}"


@requires_llm
class TestOrchestratorWithLLM:
    """Test OrchestratorAgent with a real LLM call."""

    def test_produce_dispatch_plan(self):
        agent = OrchestratorAgent()
        analysis = {
            "domains": ["cpf", "tax"],
            "entities": {"employee_type": "local"},
            "risk_tier": "green",
            "routing_decision": {"strategy": "parallel", "specialists": ["cpf", "tax"]},
        }

        result = agent.plan(analysis)
        assert "dispatch_plan" in result
        plan = result["dispatch_plan"]
        assert plan["mode"] in ("parallel", "sequential", "router")
        assert len(plan["specialists"]) >= 1


@requires_llm
class TestResponseSynthesizerWithLLM:
    """Test ResponseSynthesizerAgent with a real LLM call."""

    def test_synthesize_from_specialist_outputs(self):
        agent = ResponseSynthesizerAgent()
        specialist_outputs = [
            {
                "domain": "cpf",
                "content": (
                    "For employees aged 55 and below earning > $750/month, "
                    "employer contributes 17% and employee contributes 20% "
                    "of ordinary wages. (CPF Act s.7(1))"
                ),
                "provision_ids": [101],
                "confidence": 0.95,
                "risk_tier": "green",
            }
        ]

        result = agent.synthesize(specialist_outputs, risk_tier="green")
        assert "response_text" in result
        assert len(result["response_text"]) > 10
        assert "final_risk_tier" in result
        assert result["final_risk_tier"] in ("green", "amber", "red")

    def test_amber_risk_adds_disclaimer(self):
        agent = ResponseSynthesizerAgent()
        specialist_outputs = [
            {
                "domain": "employment_act",
                "content": "Part-time employees have pro-rated entitlements.",
                "provision_ids": [55],
                "confidence": 0.7,
                "risk_tier": "amber",
            }
        ]

        result = agent.synthesize(specialist_outputs, risk_tier="amber")
        assert len(result["disclaimers"]) >= 1
        joined = " ".join(result["disclaimers"]).lower()
        assert "professional review" in joined


# ===================================================================
# 4. End-to-end pipeline  (skip without API key)
# ===================================================================


@requires_llm
class TestEndToEndPipeline:
    """End-to-end: query -> analyze -> orchestrate -> synthesize."""

    def test_full_pipeline_with_mock_specialist(self):
        pipeline = create_orchestration_pipeline()

        # Step 1: Analyze
        analysis = pipeline["query_analyzer"].analyze(
            "What is the minimum annual leave entitlement for my employees?"
        )
        assert "domains" in analysis
        assert "risk_tier" in analysis

        # Step 2: Route via deterministic dispatch
        plan = pipeline["dispatch_router"].route(analysis)
        assert plan.specialists  # at least one specialist dispatched
        assert plan.mode in ("router", "parallel", "sequential")

        # Step 3: Simulate specialist output (real specialists not built yet)
        pipeline["shared_pool"].write_specialist_output(
            agent_id="employment_act_specialist",
            domain="employment_act",
            content=(
                "Employees who have worked for at least 3 months are entitled "
                "to a minimum of 7 days annual leave in the first year, "
                "increasing by 1 day for each subsequent year up to 14 days. "
                "(Employment Act s.43A)"
            ),
            provision_ids=[200],
            confidence=0.95,
            risk_tier="green",
        )

        # Step 4: Synthesize
        specialist_outputs = pipeline["shared_pool"].read_all_specialist_outputs()

        # Convert to a format the synthesizer expects
        formatted_outputs = []
        for output in specialist_outputs:
            formatted_outputs.append(
                {
                    "domain": output.get("metadata", {}).get("domain", "general"),
                    "content": output.get("content", ""),
                    "provision_ids": output.get("metadata", {}).get("provision_ids", []),
                    "confidence": output.get("metadata", {}).get("confidence", 0.5),
                    "risk_tier": output.get("metadata", {}).get("risk_tier", "green"),
                }
            )

        response = pipeline["response_synthesizer"].synthesize(
            specialist_outputs=formatted_outputs,
            risk_tier=analysis["risk_tier"],
        )

        assert "response_text" in response
        assert len(response["response_text"]) > 20
        assert "final_risk_tier" in response
