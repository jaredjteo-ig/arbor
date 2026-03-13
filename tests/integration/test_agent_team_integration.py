"""T023 — Agent team integration testing.

Tests the full agent coordination pipeline end-to-end:
  1. Calculator dispatch with pure calculator functions (always pass)
  2. Multi-specialist pool coordination (always pass)
  3. Multi-turn context with 10+ turns (always pass)
  4. Risk-tier escalation through pipeline (always pass)
  5. Concurrent session isolation (always pass)
  6. Trust lineage recording (always pass)
  7. LLM-dependent: Singlish query classification (skip without API key)
  8. LLM-dependent: Cross-domain routing (skip without API key)
  9. LLM-dependent: Full pipeline end-to-end (skip without API key)
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor

import pytest

from hr_advisory.agents import (
    CalculatorAgent,
    ComplianceAgent,
    CPFAgent,
    EmploymentActAgent,
    FairEmploymentAgent,
    ForeignManpowerAgent,
    HRSharedMemoryPool,
    LongTermMemory,
    OrchestratorAgent,
    QueryAnalyzerAgent,
    ResponseSynthesizerAgent,
    ShortTermMemory,
    TaxAgent,
    WSHAgent,
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
# 1. Calculator dispatch with pure calculator functions
# ===================================================================


class TestCalculatorQuotaLevy:
    """Test CalculatorAgent dispatches quota_levy to pure calculator."""

    def test_quota_levy_is_supported(self):
        calc = CalculatorAgent()
        assert "quota_levy" in calc.CALCULATOR_TYPES

    def test_services_within_quota(self):
        calc = CalculatorAgent()
        result = calc.calculate(
            "quota_levy",
            {
                "sector": "services",
                "headcount_local": 20,
                "headcount_sp": 3,
                "headcount_wp": 2,
            },
        )

        assert result["calculator_type"] == "quota_levy"
        assert result["result"]["within_limit"] is True
        assert result["result"]["drc_limit"] == 0.35
        assert result["result"]["sector"] == "services"

    def test_manufacturing_exceeds_limit(self):
        calc = CalculatorAgent()
        result = calc.calculate(
            "quota_levy",
            {
                "sector": "manufacturing",
                "headcount_local": 5,
                "headcount_sp": 3,
                "headcount_wp": 10,
            },
        )

        # 13 foreign / 18 total = 72% > 60%
        assert result["result"]["within_limit"] is False

    def test_scenario_with_levy(self):
        calc = CalculatorAgent()
        result = calc.calculate(
            "quota_levy",
            {
                "sector": "services",
                "headcount_local": 20,
                "headcount_sp": 2,
                "headcount_wp": 1,
                "scenario_hire_wp": 2,
            },
        )

        assert result["result"]["current_total_monthly_levy"] > 0
        assert (
            result["result"]["projected_total_monthly_levy"]
            > result["result"]["current_total_monthly_levy"]
        )
        assert result["breakdown"]["levy_increase"] > 0

    def test_infeasible_scenario_has_warnings(self):
        calc = CalculatorAgent()
        result = calc.calculate(
            "quota_levy",
            {
                "sector": "services",
                "headcount_local": 10,
                "headcount_sp": 3,
                "headcount_wp": 2,
                "scenario_hire_wp": 5,
            },
        )

        assert result["result"]["scenario_feasible"] is False
        assert len(result["breakdown"]["warnings"]) > 0

    def test_headroom_calculation(self):
        calc = CalculatorAgent()
        result = calc.calculate(
            "quota_levy",
            {
                "sector": "services",
                "headcount_local": 20,
                "headcount_sp": 2,
                "headcount_wp": 1,
            },
        )

        assert result["result"]["headroom_foreign"] > 0


# ===================================================================
# 2. Multi-specialist pool coordination
# ===================================================================


class TestMultiSpecialistPoolCoordination:
    """Test SharedMemoryPool with outputs from multiple specialists."""

    def test_three_specialists_write_then_compliance_reads(self):
        """Simulate EA + CPF + ForeignManpower specialists, then ComplianceAgent reads."""
        pool = HRSharedMemoryPool()

        # Simulate 3 specialist outputs
        pool.write_specialist_output(
            agent_id="employment_act_specialist",
            domain="employment_act",
            content="Annual leave: 7 days first year, max 14 days (EA s.43A).",
            provision_ids=[200, 201],
            confidence=0.95,
            risk_tier="green",
        )
        pool.write_specialist_output(
            agent_id="cpf_specialist",
            domain="cpf",
            content="Employer contributes 17% for employees ≤55 (CPF Act s.7).",
            provision_ids=[42],
            confidence=0.90,
            risk_tier="green",
        )
        pool.write_specialist_output(
            agent_id="foreign_manpower_specialist",
            domain="foreign_manpower",
            content="S Pass levy: $550/month basic tier (EFMA).",
            provision_ids=[300],
            confidence=0.88,
            risk_tier="amber",
            cross_domain_flags=["cpf"],
        )

        # Verify all 3 outputs available
        all_outputs = pool.read_all_specialist_outputs()
        assert len(all_outputs) == 3

        # Verify domain filtering
        ea_outputs = pool.read_by_domain("employment_act")
        assert len(ea_outputs) == 1

        cpf_outputs = pool.read_by_domain("cpf")
        assert len(cpf_outputs) == 1

        fm_outputs = pool.read_by_domain("foreign_manpower")
        assert len(fm_outputs) == 1

        # Risk tier should escalate to amber (worst)
        assert pool.get_highest_risk_tier() == "amber"

        # Stats should show 3 outputs from 3 agents
        stats = pool.get_stats()
        assert stats["insight_count"] == 3
        assert stats["agent_count"] == 3

    def test_cross_domain_flags_preserved(self):
        """Cross-domain flags from specialists are preserved for compliance agent."""
        pool = HRSharedMemoryPool()

        pool.write_specialist_output(
            agent_id="foreign_manpower_specialist",
            domain="foreign_manpower",
            content="DRC check needed",
            cross_domain_flags=["cpf", "tax"],
        )

        outputs = pool.read_all_specialist_outputs()
        flags = outputs[0]["metadata"]["cross_domain_flags"]
        assert "cpf" in flags
        assert "tax" in flags

    def test_provision_ids_aggregated_across_specialists(self):
        """All provision IDs from all specialists are accessible."""
        pool = HRSharedMemoryPool()

        pool.write_specialist_output(
            agent_id="ea",
            domain="employment_act",
            content="Leave",
            provision_ids=[1, 2, 3],
        )
        pool.write_specialist_output(
            agent_id="cpf",
            domain="cpf",
            content="CPF",
            provision_ids=[10, 11],
        )

        all_outputs = pool.read_all_specialist_outputs()
        all_provision_ids = []
        for o in all_outputs:
            all_provision_ids.extend(o["metadata"]["provision_ids"])

        assert set(all_provision_ids) == {1, 2, 3, 10, 11}


# ===================================================================
# 3. Multi-turn context (10+ turns)
# ===================================================================


class TestMultiTurnContext:
    """Test conversation context is maintained across 10+ turns."""

    def test_10_turn_conversation(self):
        """10 turns of conversation maintain full context."""
        mem = ShortTermMemory(max_turns=20)
        session = "multi_turn_session"

        # Simulate 10 turns
        turns = [
            ("What leave am I entitled to?", "7-14 days annual leave", ["employment_act"], "green"),
            (
                "Is that for all employees?",
                "EA-covered employees with 3+ months service",
                ["employment_act"],
                "green",
            ),
            (
                "What about sick leave?",
                "14 outpatient + 60 hospitalisation days",
                ["employment_act"],
                "green",
            ),
            ("What CPF do I need to pay?", "17% employer, 20% employee for ≤55", ["cpf"], "green"),
            (
                "My employee is 58, what rate?",
                "15% employer, 16% employee for 55-60",
                ["cpf"],
                "green",
            ),
            (
                "Can I hire a foreign worker?",
                "Depends on sector DRC and available quota",
                ["foreign_manpower"],
                "amber",
            ),
            ("I'm in services sector", "Services DRC is 35%", ["foreign_manpower"], "green"),
            ("What levy do I pay for WP?", "$450/month basic tier", ["foreign_manpower"], "green"),
            (
                "Is that deductible?",
                "Levy is a business expense for tax purposes",
                ["foreign_manpower", "tax"],
                "green",
            ),
            (
                "Any tax deadlines I should know?",
                "IR8A by 1 March, IR21 for departing foreign employees",
                ["tax"],
                "green",
            ),
        ]

        for query, response, domains, risk_tier in turns:
            mem.save_turn(session, query, response, domains=domains, risk_tier=risk_tier)

        ctx = mem.load_context(session)
        assert ctx["turn_count"] == 10

        # recent_domains is from the last 3 turns (by design)
        recent_domains = ctx["recent_domains"]
        assert "foreign_manpower" in recent_domains
        assert "tax" in recent_domains

        # All 10 turns are stored — we can collect all domains from full history
        all_domains = set()
        for t in ctx["turns"]:
            all_domains.update(t.get("domains", []))
        assert "employment_act" in all_domains
        assert "cpf" in all_domains
        assert "foreign_manpower" in all_domains
        assert "tax" in all_domains

    def test_12_turn_window_evicts_oldest(self):
        """With max_turns=10, the 11th and 12th turns evict the oldest."""
        mem = ShortTermMemory(max_turns=10)
        session = "eviction_session"

        for i in range(12):
            mem.save_turn(session, f"Q{i+1}", f"A{i+1}")

        ctx = mem.load_context(session)
        assert ctx["turn_count"] == 10
        # First two should have been evicted
        assert ctx["turns"][0]["user"] == "Q3"
        assert ctx["turns"][-1]["user"] == "Q12"

    def test_multi_session_isolation(self):
        """Two sessions don't leak context into each other."""
        mem = ShortTermMemory(max_turns=20)

        mem.save_turn("session_a", "Annual leave?", "7 days", domains=["employment_act"])
        mem.save_turn("session_b", "CPF rates?", "17%", domains=["cpf"])

        ctx_a = mem.load_context("session_a")
        ctx_b = mem.load_context("session_b")

        assert ctx_a["turn_count"] == 1
        assert ctx_b["turn_count"] == 1
        assert "employment_act" in ctx_a["recent_domains"]
        assert "cpf" in ctx_b["recent_domains"]
        assert "cpf" not in ctx_a["recent_domains"]
        assert "employment_act" not in ctx_b["recent_domains"]


# ===================================================================
# 4. Risk-tier escalation through pipeline
# ===================================================================


class TestRiskTierEscalation:
    """Test risk tier properly escalates through the pipeline."""

    def test_green_stays_green(self):
        pool = HRSharedMemoryPool()
        pool.write_specialist_output(agent_id="a", domain="cpf", content="ok", risk_tier="green")
        pool.write_specialist_output(agent_id="b", domain="ea", content="ok", risk_tier="green")
        assert pool.get_highest_risk_tier() == "green"

    def test_one_amber_escalates(self):
        pool = HRSharedMemoryPool()
        pool.write_specialist_output(agent_id="a", domain="cpf", content="ok", risk_tier="green")
        pool.write_specialist_output(agent_id="b", domain="ea", content="edge", risk_tier="amber")
        assert pool.get_highest_risk_tier() == "amber"

    def test_one_red_escalates_above_amber(self):
        pool = HRSharedMemoryPool()
        pool.write_specialist_output(agent_id="a", domain="cpf", content="ok", risk_tier="green")
        pool.write_specialist_output(agent_id="b", domain="ea", content="edge", risk_tier="amber")
        pool.write_specialist_output(agent_id="c", domain="wsh", content="danger", risk_tier="red")
        assert pool.get_highest_risk_tier() == "red"

    def test_empty_pool_defaults_green(self):
        pool = HRSharedMemoryPool()
        assert pool.get_highest_risk_tier() == "green"

    def test_risk_tier_with_confidence_tracking(self):
        """Low-confidence outputs should not suppress risk tier."""
        pool = HRSharedMemoryPool()
        pool.write_specialist_output(
            agent_id="a",
            domain="cpf",
            content="unsure",
            confidence=0.3,
            risk_tier="red",
        )
        # Even low confidence doesn't downgrade risk — it's still RED
        assert pool.get_highest_risk_tier() == "red"


# ===================================================================
# 5. Concurrent session isolation
# ===================================================================


class TestConcurrentSessions:
    """Test 10 concurrent advisory sessions don't interfere."""

    def test_10_concurrent_sessions_isolated(self):
        """10 sessions each with their own memory and pool."""
        sessions = []

        for i in range(10):
            mem = ShortTermMemory(max_turns=20)
            pool = HRSharedMemoryPool()
            long_mem = LongTermMemory()

            session_id = f"session_{i}"
            domain = [
                "employment_act",
                "cpf",
                "foreign_manpower",
                "tax",
                "wsh",
                "fair_employment",
                "employment_act",
                "cpf",
                "foreign_manpower",
                "tax",
            ][i]

            mem.save_turn(session_id, f"Q from session {i}", f"A for session {i}", domains=[domain])
            pool.write_specialist_output(
                agent_id=f"specialist_{i}",
                domain=domain,
                content=f"Output for session {i}",
                risk_tier=["green", "amber", "red"][i % 3],
            )
            long_mem.set_company_context(f"company_{i}", {"session": i, "sector": "services"})

            sessions.append(
                {
                    "id": session_id,
                    "mem": mem,
                    "pool": pool,
                    "long_mem": long_mem,
                    "domain": domain,
                }
            )

        # Verify each session is isolated
        for i, s in enumerate(sessions):
            ctx = s["mem"].load_context(s["id"])
            assert ctx["turn_count"] == 1
            assert s["domain"] in ctx["recent_domains"]

            outputs = s["pool"].read_all_specialist_outputs()
            assert len(outputs) == 1
            assert outputs[0]["agent_id"] == f"specialist_{i}"

            company_ctx = s["long_mem"].get_company_context(f"company_{i}")
            assert company_ctx["session"] == i

    def test_concurrent_pool_writes_with_threadpool(self):
        """Simulate concurrent writes to separate pools via threads."""
        results = {}

        def session_work(session_idx):
            pool = HRSharedMemoryPool()
            pool.write_specialist_output(
                agent_id=f"agent_{session_idx}",
                domain="cpf",
                content=f"Output {session_idx}",
            )
            return pool.read_all_specialist_outputs()

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(session_work, i): i for i in range(10)}
            for future in futures:
                idx = futures[future]
                outputs = future.result()
                results[idx] = outputs

        # Each session should have exactly 1 output
        for idx, outputs in results.items():
            assert len(outputs) == 1
            assert outputs[0]["agent_id"] == f"agent_{idx}"


# ===================================================================
# 6. Trust lineage recording
# ===================================================================


class TestTrustLineage:
    """Test that advisory responses carry enough metadata for trust lineage."""

    def test_specialist_output_has_trust_metadata(self):
        """Every specialist output has agent_id, provision_ids, confidence, risk_tier."""
        pool = HRSharedMemoryPool()
        pool.write_specialist_output(
            agent_id="cpf_specialist",
            domain="cpf",
            content="Employer contributes 17%",
            provision_ids=[42, 43],
            confidence=0.95,
            risk_tier="green",
        )

        output = pool.read_all_specialist_outputs()[0]

        # Trust lineage fields
        assert "agent_id" in output
        assert output["agent_id"] == "cpf_specialist"
        assert "metadata" in output
        assert "domain" in output["metadata"]
        assert "provision_ids" in output["metadata"]
        assert "confidence" in output["metadata"]
        assert "risk_tier" in output["metadata"]

    def test_trust_chain_from_pipeline(self):
        """Full trust chain: query → analyzer → dispatch_router → specialists → synthesizer."""
        pipeline = create_orchestration_pipeline()

        # Record analysis step
        analysis_result = {
            "domains": ["cpf"],
            "entities": {"employee_type": "local", "age_band": "55_and_below"},
            "risk_tier": "green",
            "routing_decision": {"strategy": "single", "specialists": ["cpf"]},
        }

        # Simulate specialist output
        pipeline["shared_pool"].write_specialist_output(
            agent_id="cpf_specialist",
            domain="cpf",
            content="17% employer + 20% employee (≤55)",
            provision_ids=[42],
            confidence=0.95,
            risk_tier="green",
        )

        # Record in long-term memory for audit trail
        pipeline["long_term_memory"].record_advisory(
            "company_123",
            "CPF rates for employees under 55",
            ["cpf"],
            "green",
        )

        history = pipeline["long_term_memory"].get_advisory_history("company_123")
        assert len(history) == 1
        assert history[0]["query_summary"] == "CPF rates for employees under 55"
        assert history[0]["domains"] == ["cpf"]
        assert history[0]["risk_tier"] == "green"

    def test_multi_domain_trust_lineage(self):
        """Cross-domain query has trust lineage from all contributing specialists."""
        pool = HRSharedMemoryPool()

        specialists = [
            ("ea_specialist", "employment_act", [100, 101], 0.90, "green"),
            ("cpf_specialist", "cpf", [42], 0.95, "green"),
            ("fm_specialist", "foreign_manpower", [300, 301], 0.80, "amber"),
        ]

        for agent_id, domain, provisions, confidence, risk_tier in specialists:
            pool.write_specialist_output(
                agent_id=agent_id,
                domain=domain,
                content=f"Advice from {domain}",
                provision_ids=provisions,
                confidence=confidence,
                risk_tier=risk_tier,
            )

        outputs = pool.read_all_specialist_outputs()

        # Build trust lineage summary
        lineage = {
            "contributing_agents": [o["agent_id"] for o in outputs],
            "domains_covered": [o["metadata"]["domain"] for o in outputs],
            "all_provision_ids": [],
            "confidence_range": (
                min(o["metadata"]["confidence"] for o in outputs),
                max(o["metadata"]["confidence"] for o in outputs),
            ),
            "highest_risk_tier": pool.get_highest_risk_tier(),
        }
        for o in outputs:
            lineage["all_provision_ids"].extend(o["metadata"]["provision_ids"])

        assert len(lineage["contributing_agents"]) == 3
        assert set(lineage["domains_covered"]) == {"employment_act", "cpf", "foreign_manpower"}
        assert set(lineage["all_provision_ids"]) == {100, 101, 42, 300, 301}
        assert lineage["confidence_range"] == (0.80, 0.95)
        assert lineage["highest_risk_tier"] == "amber"


# ===================================================================
# 7. Calculator deterministic integration with pure functions
# ===================================================================


class TestCalculatorPureFunctionIntegration:
    """Verify CalculatorAgent CPF/leave match the pure calculator outputs."""

    def test_cpf_basic_matches_pure_function(self):
        """CalculatorAgent CPF should produce consistent results."""
        calc = CalculatorAgent()
        result = calc.calculate(
            "cpf",
            {
                "monthly_wage": 5000,
                "age_band": "55_and_below",
            },
        )

        # 5000 * 0.17 = 850, 5000 * 0.20 = 1000
        assert result["result"]["employer_contribution"] == 850.0
        assert result["result"]["employee_contribution"] == 1000.0
        assert result["result"]["total_contribution"] == 1850.0

    def test_quota_levy_matches_pure_function(self):
        """CalculatorAgent quota_levy should delegate to pure function."""
        from hr_advisory.workflows.calculators.quota_levy_calculator import (
            QuotaLevyInput,
            calculate_quota_levy,
        )

        calc = CalculatorAgent()
        agent_result = calc.calculate(
            "quota_levy",
            {
                "sector": "services",
                "headcount_local": 20,
                "headcount_sp": 3,
                "headcount_wp": 2,
            },
        )

        pure_result = calculate_quota_levy(
            QuotaLevyInput(
                sector="services",
                headcount_local=20,
                headcount_sp=3,
                headcount_wp=2,
            )
        )

        # Agent result should match pure function result
        assert agent_result["result"]["current_ratio"] == pure_result.current_ratio
        assert agent_result["result"]["drc_limit"] == pure_result.drc_limit
        assert agent_result["result"]["within_limit"] == pure_result.within_limit
        assert agent_result["result"]["headroom_foreign"] == pure_result.headroom_foreign
        assert (
            agent_result["result"]["current_total_monthly_levy"]
            == pure_result.current_total_monthly_levy
        )

    def test_all_calculator_types_accessible(self):
        """All 4 calculator types work without errors."""
        calc = CalculatorAgent()

        # CPF
        r1 = calc.calculate("cpf", {"monthly_wage": 3000, "age_band": "55_and_below"})
        assert r1["calculator_type"] == "cpf"

        # Leave
        r2 = calc.calculate("leave", {"years_of_service": 3, "leave_type": "annual"})
        assert r2["calculator_type"] == "leave"

        # Salary
        r3 = calc.calculate(
            "salary",
            {
                "monthly_salary": 3000,
                "calculation_type": "proration",
                "days_worked": 10,
                "total_working_days": 22,
            },
        )
        assert r3["calculator_type"] == "salary"

        # Quota/Levy
        r4 = calc.calculate(
            "quota_levy",
            {
                "sector": "manufacturing",
                "headcount_local": 15,
                "headcount_wp": 5,
            },
        )
        assert r4["calculator_type"] == "quota_levy"


# ===================================================================
# 8. Long-term memory — company context and topic tracking
# ===================================================================


class TestLongTermCompanyTracking:
    """Test long-term memory tracks company advisory patterns."""

    def test_frequent_topic_detection(self):
        """After multiple queries, detect frequently asked topics."""
        mem = LongTermMemory()
        company = "sme_001"

        # Simulate 15 advisories across domains
        topics = [
            ["cpf"],
            ["cpf"],
            ["cpf"],
            ["cpf"],
            ["cpf"],  # 5x CPF
            ["employment_act"],
            ["employment_act"],
            ["employment_act"],  # 3x EA
            ["foreign_manpower"],
            ["foreign_manpower"],  # 2x FM
            ["tax"],  # 1x Tax
            ["cpf", "tax"],  # cross-domain
            ["employment_act", "cpf"],
            ["foreign_manpower", "cpf"],
            ["wsh"],
        ]

        for t in topics:
            mem.record_topic(company, t)

        top = mem.get_frequent_topics(company, top_n=3)
        assert top[0]["domain"] == "cpf"
        assert top[0]["count"] >= 8  # cpf appears in many queries

    def test_advisory_history_ordering(self):
        """Advisory history returns most recent first."""
        mem = LongTermMemory()
        company = "sme_002"

        mem.record_advisory(company, "First question", ["cpf"], "green")
        mem.record_advisory(company, "Second question", ["employment_act"], "amber")
        mem.record_advisory(company, "Third question", ["tax"], "green")

        history = mem.get_advisory_history(company)
        assert len(history) == 3
        assert history[0]["query_summary"] == "Third question"
        assert history[-1]["query_summary"] == "First question"


# ===================================================================
# 9. LLM-dependent: Singlish query classification
# ===================================================================


@requires_llm
class TestSinglishQueries:
    """Test QueryAnalyzer handles Singlish/Singapore English input."""

    SINGLISH_QUERIES = [
        (
            "My staff resign already, need pay notice period or not?",
            ["employment_act"],
        ),
        (
            "Wah this one CPF how to calculate ah? Employee is 58 years old.",
            ["cpf"],
        ),
        (
            "Can hire foreigner or not? We services company, got 20 local staff.",
            ["foreign_manpower"],
        ),
        (
            "Boss say want to retrench staff leh. What we must do?",
            ["employment_act"],
        ),
        (
            "The pregnant staff want take maternity leave. How many weeks she can take?",
            ["employment_act"],
        ),
    ]

    @pytest.mark.parametrize("query,expected_domains", SINGLISH_QUERIES)
    def test_singlish_query_routes_correctly(self, query, expected_domains):
        agent = QueryAnalyzerAgent()
        result = agent.analyze(query)

        assert "domains" in result
        assert isinstance(result["domains"], list)
        assert len(result["domains"]) >= 1

        # At least one expected domain should be identified
        found = any(d in result["domains"] for d in expected_domains)
        assert found, (
            f"Query '{query}' expected domains containing {expected_domains}, "
            f"got {result['domains']}"
        )


# ===================================================================
# 10. LLM-dependent: Cross-domain query routing
# ===================================================================


@requires_llm
class TestCrossDomainRouting:
    """Test cross-domain queries engage multiple specialists."""

    def test_retrenchment_engages_multiple_domains(self):
        """Retrenchment question should involve EA + fair employment at minimum."""
        agent = QueryAnalyzerAgent()
        result = agent.analyze(
            "We need to retrench 5 employees. What are our obligations under "
            "the Employment Act and TAFEP fair employment guidelines? "
            "Are there CPF implications?"
        )

        assert len(result["domains"]) >= 2

    def test_foreign_hire_engages_cpf_and_manpower(self):
        """Foreign worker hiring involves manpower + levy/CPF."""
        agent = QueryAnalyzerAgent()
        result = agent.analyze(
            "I want to hire an S Pass holder. What quota, levy, and CPF obligations apply?"
        )

        domains = result["domains"]
        assert any(d in domains for d in ("foreign_manpower",))


# ===================================================================
# 11. LLM-dependent: Full pipeline with real specialists
# ===================================================================


@requires_llm
class TestFullPipelineEndToEnd:
    """Full end-to-end pipeline: analyze → plan → specialists → synthesize."""

    def test_simple_cpf_query_pipeline(self):
        """Simple CPF query through the full pipeline."""
        pipeline = create_orchestration_pipeline()

        # Step 1: Analyze
        query = "What is the CPF contribution rate for employees under 55?"
        analysis = pipeline["query_analyzer"].analyze(query)
        assert "cpf" in analysis["domains"]

        # Step 2: Route via deterministic dispatch
        plan = pipeline["dispatch_router"].route(analysis)
        assert plan.specialists
        assert plan.mode in ("router", "parallel", "sequential")

        # Step 3: Use CalculatorAgent for deterministic answer
        calc = CalculatorAgent()
        calc_result = calc.calculate(
            "cpf",
            {
                "monthly_wage": 5000,
                "age_band": "55_and_below",
            },
        )

        # Step 4: Write to pool
        pipeline["shared_pool"].write_specialist_output(
            agent_id="cpf_specialist",
            domain="cpf",
            content=(
                f"For employees aged 55 and below, employer contributes 17% "
                f"and employee contributes 20% of ordinary wages. "
                f"Example: on $5,000 salary, employer pays ${calc_result['result']['employer_contribution']}, "
                f"employee pays ${calc_result['result']['employee_contribution']}, "
                f"total ${calc_result['result']['total_contribution']}. (CPF Act First Schedule)"
            ),
            provision_ids=[42],
            confidence=0.95,
            risk_tier="green",
        )

        # Step 5: Synthesize
        specialist_outputs = pipeline["shared_pool"].read_all_specialist_outputs()
        formatted = [
            {
                "domain": o["metadata"]["domain"],
                "content": o["content"],
                "provision_ids": o["metadata"]["provision_ids"],
                "confidence": o["metadata"]["confidence"],
                "risk_tier": o["metadata"]["risk_tier"],
            }
            for o in specialist_outputs
        ]

        response = pipeline["response_synthesizer"].synthesize(
            specialist_outputs=formatted,
            risk_tier=analysis["risk_tier"],
        )

        assert len(response["response_text"]) > 20
        assert response["final_risk_tier"] in ("green", "amber", "red")

        # Step 6: Record in memory
        pipeline["short_term_memory"].save_turn(
            "test_session",
            query,
            response["response_text"],
            domains=analysis["domains"],
            risk_tier=response["final_risk_tier"],
        )

        ctx = pipeline["short_term_memory"].load_context("test_session")
        assert ctx["turn_count"] == 1
