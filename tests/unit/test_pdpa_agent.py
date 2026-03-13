"""Unit tests for the PDPAAgent specialist.

Verifies:
  1. Instantiation without LLM credentials
  2. Correct domain and domain_label attributes
  3. System prompt contains key PDPA concepts
  4. Agent is registered in the specialists __init__
  5. Agent is importable from the top-level hr_advisory.agents package
"""

import pytest

from hr_advisory.agents.specialists.pdpa import PDPAAgent
from hr_advisory.agents.specialists.signatures import PDPASignature


# ===================================================================
# 1. Instantiation
# ===================================================================


class TestPDPAAgentInstantiation:
    """Verify PDPAAgent can be created without an API key."""

    def test_creates_without_config(self):
        agent = PDPAAgent()
        assert agent is not None

    def test_agent_id(self):
        agent = PDPAAgent()
        assert agent.agent_id == "pdpa_specialist"

    def test_signature_is_set(self):
        agent = PDPAAgent()
        assert agent.signature is not None
        assert isinstance(agent.signature, PDPASignature)


# ===================================================================
# 2. Domain attributes
# ===================================================================


class TestPDPAAgentDomainAttributes:
    """Verify correct domain metadata."""

    def test_domain(self):
        agent = PDPAAgent()
        assert agent.domain == "pdpa"

    def test_domain_label(self):
        agent = PDPAAgent()
        assert agent.domain_label == "Data Protection"

    def test_has_advise_method(self):
        agent = PDPAAgent()
        assert callable(getattr(agent, "advise", None))


# ===================================================================
# 3. System prompt content
# ===================================================================


class TestPDPAAgentSystemPrompt:
    """Verify the system prompt contains key PDPA concepts."""

    @pytest.fixture()
    def prompt(self):
        agent = PDPAAgent()
        return agent._generate_system_prompt()

    def test_contains_domain_constraint(self, prompt):
        assert "DOMAIN CONSTRAINT" in prompt

    def test_contains_pdpa_reference(self, prompt):
        assert "Personal Data Protection Act" in prompt

    def test_contains_citation_rules(self, prompt):
        assert "ONLY cite provisions" in prompt

    def test_instructs_refusal_for_out_of_domain(self, prompt):
        assert "refuse" in prompt.lower()

    def test_contains_consent_obligation(self, prompt):
        assert "Consent Obligation" in prompt

    def test_contains_breach_notification(self, prompt):
        assert "3 CALENDAR DAYS" in prompt
        assert "breach" in prompt.lower()

    def test_contains_dpo_requirement(self, prompt):
        assert "Data Protection Officer" in prompt

    def test_contains_nric_restriction(self, prompt):
        assert "NRIC" in prompt

    def test_contains_cross_border_transfer(self, prompt):
        assert "Cross-Border" in prompt or "cross-border" in prompt.lower()

    def test_contains_penalty_amounts(self, prompt):
        assert "$1 million" in prompt or "$1M" in prompt

    def test_contains_employment_exception(self, prompt):
        assert "employment exception" in prompt.lower() or "Employment Exception" in prompt

    def test_contains_dnc_registry(self, prompt):
        assert "Do Not Call" in prompt or "DNC" in prompt

    def test_contains_common_mistakes_section(self, prompt):
        assert "COMMON MISTAKES TO AVOID" in prompt

    def test_contains_reasoning_scaffolding(self, prompt):
        assert "REASONING SCAFFOLDING" in prompt
        assert "IDENTIFY APPLICABILITY" in prompt
        assert "FIND RELEVANT PROVISIONS" in prompt
        assert "APPLY TO THE FACTS" in prompt
        assert "ASSESS RISK" in prompt
        assert "FLAG CROSS-DOMAIN IMPLICATIONS" in prompt

    def test_contains_purpose_limitation(self, prompt):
        assert "Purpose Limitation" in prompt or "purpose limitation" in prompt

    def test_contains_protection_obligation(self, prompt):
        assert "Protection Obligation" in prompt

    def test_contains_retention_limitation(self, prompt):
        assert "Retention Limitation" in prompt or "retention" in prompt.lower()


# ===================================================================
# 4. Registration checks
# ===================================================================


class TestPDPAAgentRegistration:
    """Verify PDPAAgent is properly registered in package exports."""

    def test_importable_from_specialists_package(self):
        from hr_advisory.agents.specialists import PDPAAgent as ImportedAgent

        assert ImportedAgent is PDPAAgent

    def test_in_specialists_all(self):
        from hr_advisory.agents.specialists import __all__ as specialist_all

        assert "PDPAAgent" in specialist_all

    def test_importable_from_top_level_agents(self):
        from hr_advisory.agents import PDPAAgent as TopLevelAgent

        assert TopLevelAgent is PDPAAgent

    def test_in_top_level_all(self):
        from hr_advisory.agents import __all__ as agents_all

        assert "PDPAAgent" in agents_all


# ===================================================================
# 5. Shared memory wiring
# ===================================================================


class TestPDPAAgentSharedMemory:
    """Verify PDPAAgent can be wired to SharedMemoryPool."""

    def test_accepts_shared_memory(self):
        from kaizen.memory import SharedMemoryPool

        pool = SharedMemoryPool()
        agent = PDPAAgent(shared_memory=pool)
        assert agent.shared_memory is pool


# ===================================================================
# 6. Domain mapping integration
# ===================================================================


class TestPDPADomainMapping:
    """Verify PDPA is registered in domain routing infrastructure."""

    def test_in_orchestrator_domain_map(self):
        from hr_advisory.agents.orchestration.orchestrator import DOMAIN_TO_SPECIALIST

        assert "pdpa" in DOMAIN_TO_SPECIALIST
        assert DOMAIN_TO_SPECIALIST["pdpa"] == "pdpa_specialist"

    def test_in_query_analyzer_valid_domains(self):
        from hr_advisory.agents.orchestration.query_analyzer import VALID_DOMAINS

        assert "pdpa" in VALID_DOMAINS

    def test_in_dispatch_router_domain_map(self):
        from hr_advisory.agents.orchestration.dispatch_router import DOMAIN_TO_SPECIALIST

        assert "pdpa" in DOMAIN_TO_SPECIALIST
        assert DOMAIN_TO_SPECIALIST["pdpa"] == "PDPAAgent"
