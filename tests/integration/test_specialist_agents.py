"""Integration tests for HR domain specialist and action agents.

Tests are split into groups:
  1. Instantiation tests -- always pass, no LLM needed.
  2. Domain attribute tests -- verify domain metadata.
  3. Constraint envelope tests -- verify out-of-domain rejection (mock).
  4. ComplianceAgent shared memory test -- verify pool reading.
  5. Action agent tests -- calculator deterministic, doc-gen instantiation.
  6. Full roster count -- 12 total agents.
  7. LLM-dependent tests -- skip when OPENAI_API_KEY is absent.
"""

import json

import pytest

from hr_advisory.agents import (
    CalculatorAgent,
    ComplianceAgent,
    CPFAgent,
    DocumentGenerationAgent,
    EmploymentActAgent,
    FairEmploymentAgent,
    ForeignManpowerAgent,
    HRSharedMemoryPool,
    OrchestratorAgent,
    QueryAnalyzerAgent,
    ResponseSynthesizerAgent,
    TaxAgent,
    WSHAgent,
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
# 1. Instantiation tests  (no LLM call, always pass)
# ===================================================================


class TestSpecialistInstantiation:
    """Verify all 7 specialist agents can be created without an API key."""

    def test_employment_act_agent_creates(self):
        agent = EmploymentActAgent()
        assert agent.agent_id == "employment_act_specialist"
        assert agent.signature is not None

    def test_cpf_agent_creates(self):
        agent = CPFAgent()
        assert agent.agent_id == "cpf_specialist"
        assert agent.signature is not None

    def test_foreign_manpower_agent_creates(self):
        agent = ForeignManpowerAgent()
        assert agent.agent_id == "foreign_manpower_specialist"
        assert agent.signature is not None

    def test_fair_employment_agent_creates(self):
        agent = FairEmploymentAgent()
        assert agent.agent_id == "fair_employment_specialist"
        assert agent.signature is not None

    def test_tax_agent_creates(self):
        agent = TaxAgent()
        assert agent.agent_id == "tax_specialist"
        assert agent.signature is not None

    def test_wsh_agent_creates(self):
        agent = WSHAgent()
        assert agent.agent_id == "wsh_specialist"
        assert agent.signature is not None

    def test_compliance_agent_creates(self):
        agent = ComplianceAgent()
        assert agent.agent_id == "compliance_specialist"
        assert agent.signature is not None


# ===================================================================
# 2. Domain attribute tests
# ===================================================================


class TestSpecialistDomainAttributes:
    """Verify each specialist has correct domain metadata."""

    @pytest.mark.parametrize(
        "agent_cls,expected_domain,expected_label",
        [
            (EmploymentActAgent, "employment_act", "Employment Act"),
            (CPFAgent, "cpf", "CPF"),
            (ForeignManpowerAgent, "foreign_manpower", "Foreign Manpower"),
            (FairEmploymentAgent, "fair_employment", "Fair Employment"),
            (TaxAgent, "tax", "Tax"),
            (WSHAgent, "wsh", "WSH"),
            (ComplianceAgent, "compliance", "Compliance"),
        ],
    )
    def test_domain_and_label(self, agent_cls, expected_domain, expected_label):
        agent = agent_cls()
        assert agent.domain == expected_domain
        assert agent.domain_label == expected_label

    @pytest.mark.parametrize(
        "agent_cls",
        [
            EmploymentActAgent,
            CPFAgent,
            ForeignManpowerAgent,
            FairEmploymentAgent,
            TaxAgent,
            WSHAgent,
        ],
    )
    def test_specialist_has_advise_method(self, agent_cls):
        agent = agent_cls()
        assert callable(getattr(agent, "advise", None))

    def test_compliance_has_check_compliance_method(self):
        agent = ComplianceAgent()
        assert callable(getattr(agent, "check_compliance", None))


# ===================================================================
# 3. Constraint envelope tests (mock LLM)
# ===================================================================


class TestConstraintEnvelope:
    """Verify each specialist has a domain-specific system prompt
    that includes constraint language."""

    @pytest.mark.parametrize(
        "agent_cls,constraint_phrase",
        [
            (EmploymentActAgent, "Employment Act"),
            (CPFAgent, "CPF"),
            (ForeignManpowerAgent, "Foreign Manpower"),
            (FairEmploymentAgent, "fair employment"),
            (TaxAgent, "tax"),
            (WSHAgent, "Workplace Safety and Health"),
        ],
    )
    def test_system_prompt_contains_domain_constraint(self, agent_cls, constraint_phrase):
        agent = agent_cls()
        prompt = agent._generate_system_prompt()
        assert (
            "DOMAIN CONSTRAINT" in prompt
        ), f"{agent_cls.__name__} system prompt must contain DOMAIN CONSTRAINT"
        assert (
            constraint_phrase.lower() in prompt.lower()
        ), f"{agent_cls.__name__} system prompt must mention '{constraint_phrase}'"

    @pytest.mark.parametrize(
        "agent_cls",
        [
            EmploymentActAgent,
            CPFAgent,
            ForeignManpowerAgent,
            FairEmploymentAgent,
            TaxAgent,
            WSHAgent,
        ],
    )
    def test_system_prompt_requires_provision_citations(self, agent_cls):
        agent = agent_cls()
        prompt = agent._generate_system_prompt()
        assert (
            "ONLY cite provisions" in prompt
        ), f"{agent_cls.__name__} must enforce citation-only from provisions"

    def test_compliance_prompt_cannot_make_legal_determinations(self):
        agent = ComplianceAgent()
        prompt = agent._generate_system_prompt()
        assert "CANNOT make legal determinations" in prompt

    @pytest.mark.parametrize(
        "agent_cls,out_of_domain_keyword",
        [
            (EmploymentActAgent, "refuse"),
            (CPFAgent, "refuse"),
            (ForeignManpowerAgent, "refuse"),
            (FairEmploymentAgent, "refuse"),
            (TaxAgent, "refuse"),
            (WSHAgent, "refuse"),
        ],
    )
    def test_system_prompt_instructs_refusal_for_out_of_domain(
        self, agent_cls, out_of_domain_keyword
    ):
        agent = agent_cls()
        prompt = agent._generate_system_prompt()
        assert (
            out_of_domain_keyword in prompt.lower()
        ), f"{agent_cls.__name__} system prompt must instruct refusal of out-of-domain queries"


# ===================================================================
# 4. ComplianceAgent shared memory test
# ===================================================================


class TestComplianceAgentMemory:
    """Verify ComplianceAgent can read from SharedMemoryPool."""

    def test_compliance_agent_with_shared_memory(self):
        pool = HRSharedMemoryPool()
        kaizen_pool = pool.inner_pool

        agent = ComplianceAgent(shared_memory=kaizen_pool)
        assert agent.shared_memory is kaizen_pool

    def test_compliance_agent_can_receive_specialist_outputs(self):
        """Verify we can construct the inputs that ComplianceAgent expects."""
        pool = HRSharedMemoryPool()

        # Simulate specialist outputs
        pool.write_specialist_output(
            agent_id="cpf_specialist",
            domain="cpf",
            content={"advice": "Employer contributes 17%"},
            provision_ids=[42],
            confidence=0.9,
            risk_tier="green",
        )
        pool.write_specialist_output(
            agent_id="tax_specialist",
            domain="tax",
            content={"advice": "BIK must be reported"},
            provision_ids=[100],
            confidence=0.85,
            risk_tier="amber",
            cross_domain_flags=["cpf"],
        )

        outputs = pool.read_all_specialist_outputs()
        assert len(outputs) == 2

        # Verify the outputs can be serialised for the compliance agent
        formatted = []
        for o in outputs:
            formatted.append(
                {
                    "domain": o.get("metadata", {}).get("domain"),
                    "content": o.get("content"),
                    "confidence": o.get("metadata", {}).get("confidence"),
                    "risk_tier": o.get("metadata", {}).get("risk_tier"),
                    "cross_domain_flags": o.get("metadata", {}).get("cross_domain_flags", []),
                }
            )

        serialised = json.dumps(formatted)
        assert "cpf" in serialised
        assert "tax" in serialised


# ===================================================================
# 5. Action agent tests
# ===================================================================


class TestDocumentGenerationAgent:
    """Verify DocumentGenerationAgent instantiates."""

    def test_creates(self):
        agent = DocumentGenerationAgent()
        assert agent.agent_id == "document_generation"
        assert agent.signature is not None
        assert agent.domain == "document_generation"

    def test_has_generate_method(self):
        agent = DocumentGenerationAgent()
        assert callable(getattr(agent, "generate", None))


class TestCalculatorAgent:
    """Verify CalculatorAgent works with deterministic calculations."""

    def test_creates(self):
        calc = CalculatorAgent()
        assert calc.agent_id == "calculator"
        assert calc.domain == "calculator"

    def test_cpf_calculation(self):
        calc = CalculatorAgent()
        result = calc.calculate(
            "cpf",
            {
                "monthly_wage": 5000,
                "age_band": "55_and_below",
            },
        )

        assert result["calculator_type"] == "cpf"
        assert result["result"]["employer_contribution"] == 850.0  # 5000 * 0.17
        assert result["result"]["employee_contribution"] == 1000.0  # 5000 * 0.20
        assert result["result"]["total_contribution"] == 1850.0

    def test_cpf_with_ow_ceiling(self):
        calc = CalculatorAgent()
        result = calc.calculate(
            "cpf",
            {
                "monthly_wage": 10000,
                "age_band": "55_and_below",
            },
        )

        # Should be capped at OW ceiling of 8000
        assert result["breakdown"]["ordinary_wages"]["capped"] == 8000
        assert result["result"]["employer_contribution"] == 1360.0  # 8000 * 0.17
        assert result["result"]["employee_contribution"] == 1600.0  # 8000 * 0.20

    def test_cpf_with_bonus(self):
        calc = CalculatorAgent()
        result = calc.calculate(
            "cpf",
            {
                "monthly_wage": 5000,
                "age_band": "55_and_below",
                "bonus": 2000,
            },
        )

        assert result["breakdown"]["additional_wages"]["employer_amount"] == 340.0
        assert result["breakdown"]["additional_wages"]["employee_amount"] == 400.0
        assert result["result"]["total_contribution"] == 2590.0

    def test_leave_annual(self):
        calc = CalculatorAgent()
        result = calc.calculate(
            "leave",
            {
                "years_of_service": 1,
                "leave_type": "annual",
            },
        )

        assert result["result"]["annual_leave_days"] == 7

    def test_leave_annual_increments(self):
        calc = CalculatorAgent()

        # Year 3: 7 + 2 = 9 days
        result = calc.calculate("leave", {"years_of_service": 3, "leave_type": "annual"})
        assert result["result"]["annual_leave_days"] == 9

        # Year 8+: capped at 14
        result = calc.calculate("leave", {"years_of_service": 10, "leave_type": "annual"})
        assert result["result"]["annual_leave_days"] == 14

    def test_leave_sick(self):
        calc = CalculatorAgent()
        result = calc.calculate(
            "leave",
            {
                "years_of_service": 2,
                "leave_type": "sick",
            },
        )

        assert result["result"]["outpatient_sick_leave_days"] == 14
        assert result["result"]["hospitalisation_leave_days"] == 60

    def test_salary_proration(self):
        calc = CalculatorAgent()
        result = calc.calculate(
            "salary",
            {
                "monthly_salary": 4400,
                "calculation_type": "proration",
                "days_worked": 15,
                "total_working_days": 22,
            },
        )

        assert result["result"]["prorated_salary"] == 3000.0

    def test_salary_overtime(self):
        calc = CalculatorAgent()
        result = calc.calculate(
            "salary",
            {
                "monthly_salary": 2080,
                "calculation_type": "overtime",
                "overtime_hours": 10,
            },
        )

        # Hourly rate: 2080 / (26*8) = 10.0
        # OT rate: 10.0 * 1.5 = 15.0
        # OT pay: 15.0 * 10 = 150.0
        assert result["result"]["overtime_pay"] == 150.0
        assert result["breakdown"]["ot_multiplier"] == 1.5

    def test_unknown_calculator_type_raises(self):
        calc = CalculatorAgent()
        with pytest.raises(ValueError, match="Unknown calculator_type"):
            calc.calculate("unknown_type", {})

    def test_supported_calculator_types(self):
        calc = CalculatorAgent()
        assert "cpf" in calc.CALCULATOR_TYPES
        assert "leave" in calc.CALCULATOR_TYPES
        assert "salary" in calc.CALCULATOR_TYPES


# ===================================================================
# 6. Full roster count
# ===================================================================


class TestFullRoster:
    """Verify total agent count: 3 orchestration + 7 specialist + 2 action = 12."""

    def test_total_agent_count(self):
        orchestration_agents = [
            QueryAnalyzerAgent,
            OrchestratorAgent,
            ResponseSynthesizerAgent,
        ]
        specialist_agents = [
            EmploymentActAgent,
            CPFAgent,
            ForeignManpowerAgent,
            FairEmploymentAgent,
            TaxAgent,
            WSHAgent,
            ComplianceAgent,
        ]
        action_agents = [
            DocumentGenerationAgent,
            CalculatorAgent,
        ]

        total = len(orchestration_agents) + len(specialist_agents) + len(action_agents)
        assert total == 12, f"Expected 12 agents, got {total}"

    def test_all_agents_importable_from_top_level(self):
        """All 12 agents should be importable from hr_advisory.agents."""
        from hr_advisory.agents import __all__ as exported

        expected_agents = [
            "QueryAnalyzerAgent",
            "OrchestratorAgent",
            "ResponseSynthesizerAgent",
            "EmploymentActAgent",
            "CPFAgent",
            "ForeignManpowerAgent",
            "FairEmploymentAgent",
            "TaxAgent",
            "WSHAgent",
            "ComplianceAgent",
            "DocumentGenerationAgent",
            "CalculatorAgent",
        ]

        for agent_name in expected_agents:
            assert agent_name in exported, f"{agent_name} not in __all__"

    def test_all_specialist_agents_instantiate(self):
        """Bulk instantiation of all 7 specialist agents."""
        agents = [
            EmploymentActAgent(),
            CPFAgent(),
            ForeignManpowerAgent(),
            FairEmploymentAgent(),
            TaxAgent(),
            WSHAgent(),
            ComplianceAgent(),
        ]
        assert len(agents) == 7

        # Verify they all have unique agent_ids
        agent_ids = {a.agent_id for a in agents}
        assert len(agent_ids) == 7

    def test_all_action_agents_instantiate(self):
        """Bulk instantiation of both action agents."""
        doc_gen = DocumentGenerationAgent()
        calc = CalculatorAgent()

        assert doc_gen.agent_id == "document_generation"
        assert calc.agent_id == "calculator"


# ===================================================================
# 7. Specialists with shared memory
# ===================================================================


class TestSpecialistsWithSharedMemory:
    """Verify specialists can be wired to SharedMemoryPool."""

    def test_specialist_accepts_shared_memory(self):
        pool = HRSharedMemoryPool()
        kaizen_pool = pool.inner_pool

        agent = CPFAgent(shared_memory=kaizen_pool)
        assert agent.shared_memory is kaizen_pool

    def test_multiple_specialists_share_pool(self):
        pool = HRSharedMemoryPool()
        kaizen_pool = pool.inner_pool

        ea = EmploymentActAgent(shared_memory=kaizen_pool)
        cpf = CPFAgent(shared_memory=kaizen_pool)
        tax = TaxAgent(shared_memory=kaizen_pool)

        assert ea.shared_memory is cpf.shared_memory
        assert cpf.shared_memory is tax.shared_memory


# ===================================================================
# 8. LLM-dependent tests  (skip without API key)
# ===================================================================


@requires_llm
class TestEmploymentActWithLLM:
    """Test EmploymentActAgent with a real LLM call."""

    def test_advise_on_annual_leave(self):
        agent = EmploymentActAgent()
        result = agent.advise(
            query_text="What is the minimum annual leave for my employees?",
            relevant_provisions=[
                {
                    "id": 200,
                    "section": "s.43A",
                    "act": "Employment Act",
                    "text": (
                        "An employee who has served an employer for not less "
                        "than 3 months shall be entitled to 7 days of paid "
                        "annual leave for the first 12 months of continuous "
                        "service, increasing by 1 day for each subsequent "
                        "12 months up to a maximum of 14 days."
                    ),
                }
            ],
        )

        assert "answer_text" in result
        assert len(result["answer_text"]) > 10
        assert result["domain"] == "employment_act"
        assert result["risk_tier"] in ("green", "amber", "red")
        assert isinstance(result["confidence"], float)
        assert 0.0 <= result["confidence"] <= 1.0


@requires_llm
class TestCPFWithLLM:
    """Test CPFAgent with a real LLM call."""

    def test_advise_on_contribution_rates(self):
        agent = CPFAgent()
        result = agent.advise(
            query_text="What are the CPF contribution rates for my employees aged 55 and below?",
            relevant_provisions=[
                {
                    "id": 42,
                    "section": "First Schedule",
                    "act": "CPF Act",
                    "text": (
                        "For employees aged 55 and below earning more than "
                        "$750 per month: employer contributes 17%, employee "
                        "contributes 20% of ordinary wages."
                    ),
                }
            ],
        )

        assert result["domain"] == "cpf"
        assert len(result["answer_text"]) > 10


@requires_llm
class TestComplianceWithLLM:
    """Test ComplianceAgent with a real LLM call."""

    def test_check_cross_domain_issues(self):
        agent = ComplianceAgent()
        result = agent.check_compliance(
            query_text="I want to hire a foreign worker and need to know CPF and levy obligations",
            specialist_outputs=[
                {
                    "domain": "cpf",
                    "answer_text": "Foreign workers are not required to contribute to CPF.",
                    "confidence": 0.9,
                    "risk_tier": "green",
                },
                {
                    "domain": "foreign_manpower",
                    "answer_text": "S Pass holders are subject to a monthly levy.",
                    "confidence": 0.85,
                    "risk_tier": "green",
                },
            ],
        )

        assert result["domain"] == "compliance"
        assert result["risk_tier"] in ("green", "amber", "red")
        assert isinstance(result["compliance_flags"], list)
        assert isinstance(result["recommendations"], list)
