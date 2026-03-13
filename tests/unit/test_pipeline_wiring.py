"""Unit tests for pipeline wiring tasks T065-T069.

Tests the wiring of:
  T065: Conversation history through the full pipeline
  T066: Company context enrichment through the full pipeline
  T067: ComplianceAgent as mandatory post-specialist quality gate
  T069: Anti-amnesia injection and EATP trust lineage into the live pipeline

Tier 1 (Unit): Fast, isolated, uses mocks for LLM calls.
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import MagicMock, patch

import pytest

from hr_advisory.agents.config import UNCERTAINTY_DEFAULTS


# ===================================================================
# T065: Conversation History Wiring
# ===================================================================


class TestT065ConversationHistoryInSignature:
    """SpecialistSignature must include a conversation_history InputField."""

    def test_specialist_signature_has_conversation_history_field(self):
        """SpecialistSignature must declare a conversation_history InputField."""
        from hr_advisory.agents.specialists.signatures import SpecialistSignature

        assert hasattr(SpecialistSignature, "conversation_history"), (
            "SpecialistSignature must declare a conversation_history field"
        )

    def test_conversation_history_field_is_optional(self):
        """conversation_history should have a default (not required)."""
        from hr_advisory.agents.specialists.signatures import SpecialistSignature

        sig = SpecialistSignature()
        # The field should have a default value (empty string)
        assert sig.conversation_history is not None or sig.conversation_history == ""


class TestT065ConversationHistoryInAdvise:
    """BaseDomainSpecialist.advise() must accept and forward conversation_history."""

    def test_advise_accepts_conversation_history_parameter(self):
        """advise() must have a conversation_history parameter."""
        from hr_advisory.agents.specialists._base import BaseDomainSpecialist

        sig = inspect.signature(BaseDomainSpecialist.advise)
        assert "conversation_history" in sig.parameters, (
            "advise() must accept a conversation_history parameter"
        )

    def test_advise_conversation_history_is_optional(self):
        """conversation_history should be Optional with a default."""
        from hr_advisory.agents.specialists._base import BaseDomainSpecialist

        sig = inspect.signature(BaseDomainSpecialist.advise)
        param = sig.parameters["conversation_history"]
        assert param.default is not inspect.Parameter.empty, (
            "conversation_history should have a default value (Optional)"
        )

    def test_advise_passes_conversation_history_to_run(self):
        """advise() must pass conversation_history to self.run()."""
        from hr_advisory.agents.specialists._base import BaseDomainSpecialist

        agent = _make_mock_specialist()
        agent.run = MagicMock(return_value={
            "answer_text": "test answer",
            "cited_provisions": "[]",
            "confidence": "0.85",
            "risk_tier": "green",
            "cross_domain_flags": "[]",
        })

        agent.advise(
            query_text="test query",
            conversation_history="User: hello\nAssistant: hi",
        )

        agent.run.assert_called_once()
        call_kwargs = agent.run.call_args.kwargs
        assert "conversation_history" in call_kwargs, (
            "advise() must pass conversation_history to self.run()"
        )
        assert call_kwargs["conversation_history"] == "User: hello\nAssistant: hi"

    def test_advise_passes_empty_string_when_no_history(self):
        """When no conversation_history is provided, advise() should pass empty string."""
        from hr_advisory.agents.specialists._base import BaseDomainSpecialist

        agent = _make_mock_specialist()
        agent.run = MagicMock(return_value={
            "answer_text": "test answer",
            "cited_provisions": "[]",
            "confidence": "0.85",
            "risk_tier": "green",
            "cross_domain_flags": "[]",
        })

        agent.advise(query_text="test query")

        call_kwargs = agent.run.call_args.kwargs
        assert "conversation_history" in call_kwargs
        assert call_kwargs["conversation_history"] == ""


class TestT065ConversationHistoryInSynthesizer:
    """ResponseSynthesizerAgent.synthesize() must accept conversation_history."""

    def test_synthesize_accepts_conversation_history_parameter(self):
        """synthesize() must have a conversation_history parameter."""
        from hr_advisory.agents.orchestration.response_synthesizer import (
            ResponseSynthesizerAgent,
        )

        sig = inspect.signature(ResponseSynthesizerAgent.synthesize)
        assert "conversation_history" in sig.parameters, (
            "synthesize() must accept a conversation_history parameter"
        )

    def test_synthesize_conversation_history_is_optional(self):
        """conversation_history should be Optional with a default."""
        from hr_advisory.agents.orchestration.response_synthesizer import (
            ResponseSynthesizerAgent,
        )

        sig = inspect.signature(ResponseSynthesizerAgent.synthesize)
        param = sig.parameters["conversation_history"]
        assert param.default is not inspect.Parameter.empty


class TestT065ConversationHistoryInSynthesizerSignature:
    """ResponseSynthesizerSignature must include a conversation_history InputField."""

    def test_synthesizer_signature_has_conversation_history_field(self):
        """ResponseSynthesizerSignature must declare a conversation_history InputField."""
        from hr_advisory.agents.signatures import ResponseSynthesizerSignature

        assert hasattr(ResponseSynthesizerSignature, "conversation_history"), (
            "ResponseSynthesizerSignature must declare a conversation_history field"
        )


class TestT065ConversationHistoryInPipeline:
    """_run_llm_advisory must pass conversation_history through the pipeline."""

    @patch("hr_advisory.agents.config.has_llm_available", return_value=True)
    def test_pipeline_passes_conversation_history_to_specialists(self, mock_llm):
        """Each specialist's advise() call should receive conversation_history."""
        with _patch_pipeline() as mocks:
            from hr_advisory.api.routers.advisory import _run_llm_advisory

            _run_llm_advisory(
                query="test query",
                domains=["cpf"],
                provisions=[],
                conversation_history="User: previous question\nAssistant: previous answer",
            )

            # Verify the specialist's advise was called with conversation_history
            specialist_instance = mocks["specialist_instance"]
            specialist_instance.advise.assert_called_once()
            call_kwargs = specialist_instance.advise.call_args.kwargs
            assert "conversation_history" in call_kwargs
            assert "previous question" in call_kwargs["conversation_history"]

    @patch("hr_advisory.agents.config.has_llm_available", return_value=True)
    def test_pipeline_passes_conversation_history_to_synthesizer(self, mock_llm):
        """The synthesizer should receive conversation_history."""
        with _patch_pipeline() as mocks:
            from hr_advisory.api.routers.advisory import _run_llm_advisory

            _run_llm_advisory(
                query="test query",
                domains=["cpf"],
                provisions=[],
                conversation_history="User: previous\nAssistant: response",
            )

            synthesizer_instance = mocks["synthesizer_instance"]
            synthesizer_instance.synthesize.assert_called_once()
            call_kwargs = synthesizer_instance.synthesize.call_args.kwargs
            assert "conversation_history" in call_kwargs


# ===================================================================
# T066: Company Context Enrichment
# ===================================================================


class TestT066CompanyContextInSynthesizer:
    """ResponseSynthesizerAgent.synthesize() must accept and use company_context."""

    def test_synthesize_accepts_company_context_parameter(self):
        """synthesize() must have a company_context parameter."""
        from hr_advisory.agents.orchestration.response_synthesizer import (
            ResponseSynthesizerAgent,
        )

        sig = inspect.signature(ResponseSynthesizerAgent.synthesize)
        assert "company_context" in sig.parameters, (
            "synthesize() must accept a company_context parameter"
        )

    def test_synthesize_company_context_is_optional(self):
        """company_context should be Optional with a default."""
        from hr_advisory.agents.orchestration.response_synthesizer import (
            ResponseSynthesizerAgent,
        )

        sig = inspect.signature(ResponseSynthesizerAgent.synthesize)
        param = sig.parameters["company_context"]
        assert param.default is not inspect.Parameter.empty


class TestT066CompanyContextInSynthesizerSignature:
    """ResponseSynthesizerSignature must include a company_context InputField."""

    def test_synthesizer_signature_has_company_context_field(self):
        """ResponseSynthesizerSignature must declare a company_context InputField."""
        from hr_advisory.agents.signatures import ResponseSynthesizerSignature

        assert hasattr(ResponseSynthesizerSignature, "company_context"), (
            "ResponseSynthesizerSignature must declare a company_context field"
        )


class TestT066CompanyContextFormatting:
    """BaseDomainSpecialist._format_company_context must produce prompt text."""

    def test_company_context_included_in_prompt_when_provided(self):
        """When company_context is non-empty, the specialist should include
        it in the context passed to the LLM."""
        from hr_advisory.agents.specialists._base import BaseDomainSpecialist

        agent = _make_mock_specialist()
        agent.run = MagicMock(return_value={
            "answer_text": "test answer",
            "cited_provisions": "[]",
            "confidence": "0.85",
            "risk_tier": "green",
            "cross_domain_flags": "[]",
        })

        company = {"sector": "manufacturing", "headcount": 50}
        agent.advise(query_text="test", company_context=company)

        call_kwargs = agent.run.call_args.kwargs
        # company_context should be serialized to JSON string
        ctx_str = call_kwargs.get("company_context", "")
        assert "manufacturing" in ctx_str
        assert "50" in ctx_str


class TestT066CompanyContextInPipeline:
    """_run_llm_advisory must pass company_context to both specialists and synthesizer."""

    @patch("hr_advisory.agents.config.has_llm_available", return_value=True)
    def test_pipeline_passes_company_context_to_synthesizer(self, mock_llm):
        """The synthesizer should receive company_context."""
        with _patch_pipeline() as mocks:
            from hr_advisory.api.routers.advisory import _run_llm_advisory

            company = {"sector": "tech", "headcount": 20}
            _run_llm_advisory(
                query="test query",
                domains=["cpf"],
                provisions=[],
                company_context=company,
            )

            synthesizer_instance = mocks["synthesizer_instance"]
            synthesizer_instance.synthesize.assert_called_once()
            call_kwargs = synthesizer_instance.synthesize.call_args.kwargs
            assert "company_context" in call_kwargs


# ===================================================================
# T067: ComplianceAgent as Quality Gate
# ===================================================================


class TestT067ComplianceGateReceivesAllOutputs:
    """ComplianceAgent must receive ALL specialist outputs, not just provisions."""

    def test_compliance_check_compliance_accepts_specialist_outputs(self):
        """check_compliance() must accept specialist_outputs parameter."""
        from hr_advisory.agents.specialists.compliance import ComplianceAgent

        sig = inspect.signature(ComplianceAgent.check_compliance)
        assert "specialist_outputs" in sig.parameters

    def test_compliance_signature_has_specialist_outputs_field(self):
        """ComplianceSignature must have a specialist_outputs InputField."""
        from hr_advisory.agents.specialists.signatures import ComplianceSignature

        assert hasattr(ComplianceSignature, "specialist_outputs")


class TestT067ComplianceOutputShape:
    """ComplianceAgent.check_compliance() must return contradictions,
    risk_escalation, and override_risk_tier."""

    def test_compliance_output_includes_contradictions(self):
        """check_compliance() result must include compliance_flags (contradictions)."""
        from hr_advisory.agents.specialists.compliance import ComplianceAgent

        agent = ComplianceAgent()
        agent.run = MagicMock(return_value={
            "compliance_flags": json.dumps([
                {"issue": "test contradiction", "domains": ["cpf", "tax"], "severity": "high"}
            ]),
            "gaps_identified": "[]",
            "risk_tier": "amber",
            "recommendations": "[]",
        })

        result = agent.check_compliance(
            query_text="test",
            specialist_outputs=[{"domain": "cpf", "answer_text": "answer"}],
        )

        assert "compliance_flags" in result
        assert isinstance(result["compliance_flags"], list)

    def test_compliance_output_includes_risk_escalation(self):
        """check_compliance() result must include risk_escalation flag."""
        from hr_advisory.agents.specialists.compliance import ComplianceAgent

        agent = ComplianceAgent()
        agent.run = MagicMock(return_value={
            "compliance_flags": json.dumps([
                {"issue": "contradiction found", "domains": ["cpf", "tax"], "severity": "high"}
            ]),
            "gaps_identified": "[]",
            "risk_tier": "red",
            "recommendations": "[]",
        })

        result = agent.check_compliance(
            query_text="test",
            specialist_outputs=[
                {"domain": "cpf", "answer_text": "a", "risk_tier": "green"},
                {"domain": "tax", "answer_text": "b", "risk_tier": "green"},
            ],
        )

        assert "risk_escalation" in result
        assert isinstance(result["risk_escalation"], bool)

    def test_compliance_output_includes_override_risk_tier(self):
        """check_compliance() result must include override_risk_tier."""
        from hr_advisory.agents.specialists.compliance import ComplianceAgent

        agent = ComplianceAgent()
        agent.run = MagicMock(return_value={
            "compliance_flags": "[]",
            "gaps_identified": "[]",
            "risk_tier": "amber",
            "recommendations": "[]",
        })

        result = agent.check_compliance(
            query_text="test",
            specialist_outputs=[{"domain": "cpf", "answer_text": "a"}],
        )

        assert "override_risk_tier" in result


class TestT067ComplianceRiskEscalation:
    """Compliance risk tier should override specialist tiers when higher."""

    def test_compliance_red_escalates_green_specialists(self):
        """When compliance returns red and specialists returned green,
        the compliance output should signal escalation."""
        from hr_advisory.agents.specialists.compliance import ComplianceAgent

        agent = ComplianceAgent()
        agent.run = MagicMock(return_value={
            "compliance_flags": json.dumps([
                {"issue": "cross-domain contradiction", "domains": ["cpf", "tax"], "severity": "high"}
            ]),
            "gaps_identified": "[]",
            "risk_tier": "red",
            "recommendations": '["Seek professional review"]',
        })

        specialist_outputs = [
            {"domain": "cpf", "answer_text": "a", "risk_tier": "green", "confidence": 0.9},
            {"domain": "tax", "answer_text": "b", "risk_tier": "green", "confidence": 0.9},
        ]

        result = agent.check_compliance(
            query_text="test",
            specialist_outputs=specialist_outputs,
        )

        # Compliance found issues => should escalate
        assert result["risk_escalation"] is True
        assert result["override_risk_tier"] == "red"

    def test_compliance_green_no_escalation(self):
        """When compliance returns green, risk_escalation should be False."""
        from hr_advisory.agents.specialists.compliance import ComplianceAgent

        agent = ComplianceAgent()
        agent.run = MagicMock(return_value={
            "compliance_flags": "[]",
            "gaps_identified": "[]",
            "risk_tier": "green",
            "recommendations": "[]",
        })

        result = agent.check_compliance(
            query_text="test",
            specialist_outputs=[
                {"domain": "cpf", "answer_text": "a", "risk_tier": "green"},
            ],
        )

        assert result["risk_escalation"] is False


class TestT067ComplianceInPipeline:
    """_run_llm_advisory must call ComplianceAgent.check_compliance()
    instead of advise() when running the compliance gate."""

    @patch("hr_advisory.agents.config.has_llm_available", return_value=True)
    def test_compliance_gate_uses_check_compliance(self, mock_llm):
        """When compliance gate is enabled, _run_llm_advisory should call
        check_compliance() with all specialist outputs."""
        with _patch_pipeline(enable_compliance_gate=True) as mocks:
            from hr_advisory.api.routers.advisory import _run_llm_advisory

            _run_llm_advisory(
                query="complex multi-domain question",
                domains=["cpf", "tax"],
                provisions=[],
            )

            compliance_instance = mocks["compliance_instance"]
            compliance_instance.check_compliance.assert_called_once()
            call_kwargs = compliance_instance.check_compliance.call_args.kwargs
            # Must receive all specialist outputs
            assert "specialist_outputs" in call_kwargs
            specialist_outputs = call_kwargs["specialist_outputs"]
            assert isinstance(specialist_outputs, list)
            assert len(specialist_outputs) > 0

    @patch("hr_advisory.agents.config.has_llm_available", return_value=True)
    def test_compliance_risk_tier_overrides_in_synthesizer(self, mock_llm):
        """When compliance escalates risk, the escalated tier should be
        used by the synthesizer."""
        with _patch_pipeline(
            enable_compliance_gate=True,
            compliance_risk_tier="red",
            compliance_risk_escalation=True,
        ) as mocks:
            from hr_advisory.api.routers.advisory import _run_llm_advisory

            result = _run_llm_advisory(
                query="multi-domain question",
                domains=["cpf", "tax"],
                provisions=[],
            )

            # The synthesizer's risk_tier arg should be escalated
            synthesizer_instance = mocks["synthesizer_instance"]
            call_kwargs = synthesizer_instance.synthesize.call_args.kwargs
            assert call_kwargs["risk_tier"] == "red"


# ===================================================================
# T069: Anti-Amnesia Injection and EATP Trust Lineage
# ===================================================================


class TestT069TrustChainCreation:
    """_run_llm_advisory must create a trust chain at the start of the pipeline."""

    @patch("hr_advisory.agents.config.has_llm_available", return_value=True)
    def test_pipeline_creates_trust_chain(self, mock_llm):
        """The pipeline should call create_trust_chain() at the start."""
        with _patch_pipeline() as mocks:
            with patch(
                "hr_advisory.api.routers.advisory.create_trust_chain"
            ) as mock_create:
                mock_create.return_value = MagicMock(
                    add_attestation=MagicMock(),
                    to_dict=MagicMock(return_value={"session_id": "test"}),
                    verification_depth="green",
                )

                from hr_advisory.api.routers.advisory import _run_llm_advisory

                _run_llm_advisory(
                    query="test query",
                    domains=["cpf"],
                    provisions=[],
                )

                mock_create.assert_called_once()


class TestT069AgentAttestations:
    """Each specialist call should produce an AgentAttestation in the trust chain."""

    @patch("hr_advisory.agents.config.has_llm_available", return_value=True)
    def test_pipeline_adds_attestation_per_specialist(self, mock_llm):
        """An AgentAttestation should be added for each specialist that runs."""
        with _patch_pipeline() as mocks:
            mock_chain = MagicMock()
            mock_chain.to_dict.return_value = {"session_id": "test"}
            mock_chain.verification_depth = "green"

            with patch(
                "hr_advisory.api.routers.advisory.create_trust_chain",
                return_value=mock_chain,
            ):
                from hr_advisory.api.routers.advisory import _run_llm_advisory

                _run_llm_advisory(
                    query="test query",
                    domains=["cpf"],
                    provisions=[],
                )

                # At least one attestation should have been added
                assert mock_chain.add_attestation.call_count >= 1


class TestT069AntiAmnesiaInjection:
    """Anti-amnesia injection must be retrieved and included in specialist calls."""

    @patch("hr_advisory.agents.config.has_llm_available", return_value=True)
    def test_pipeline_calls_get_anti_amnesia_injection(self, mock_llm):
        """The pipeline should call get_anti_amnesia_injection for each specialist."""
        with _patch_pipeline() as mocks:
            mock_chain = MagicMock()
            mock_chain.to_dict.return_value = {"session_id": "test"}
            mock_chain.verification_depth = "green"

            with patch(
                "hr_advisory.api.routers.advisory.create_trust_chain",
                return_value=mock_chain,
            ):
                with patch(
                    "hr_advisory.api.routers.advisory.get_anti_amnesia_injection",
                    return_value="[CONSTRAINT 1] Test constraint",
                ) as mock_injection:
                    from hr_advisory.api.routers.advisory import _run_llm_advisory

                    _run_llm_advisory(
                        query="test query",
                        domains=["cpf"],
                        provisions=[],
                    )

                    # Anti-amnesia injection should be called at least once
                    assert mock_injection.call_count >= 1


class TestT069ConstraintEnvelopeValidation:
    """validate_constraint_envelope must be called on each specialist output."""

    @patch("hr_advisory.agents.config.has_llm_available", return_value=True)
    def test_pipeline_validates_constraint_envelopes(self, mock_llm):
        """Each specialist output should be validated against its constraint envelope."""
        with _patch_pipeline() as mocks:
            mock_chain = MagicMock()
            mock_chain.to_dict.return_value = {"session_id": "test"}
            mock_chain.verification_depth = "green"

            with patch(
                "hr_advisory.api.routers.advisory.create_trust_chain",
                return_value=mock_chain,
            ):
                with patch(
                    "hr_advisory.api.routers.advisory.validate_constraint_envelope",
                    return_value=[],
                ) as mock_validate:
                    from hr_advisory.api.routers.advisory import _run_llm_advisory

                    _run_llm_advisory(
                        query="test query",
                        domains=["cpf"],
                        provisions=[],
                    )

                    # Should be called at least once per specialist
                    assert mock_validate.call_count >= 1


class TestT069TrustMetadataInResponse:
    """The final response must include trust_metadata from the trust chain."""

    @patch("hr_advisory.agents.config.has_llm_available", return_value=True)
    def test_pipeline_includes_trust_metadata(self, mock_llm):
        """The return value should include a trust_metadata key."""
        with _patch_pipeline() as mocks:
            trust_dict = {
                "session_id": "test-session",
                "genesis_fingerprint": "abc123",
                "verification_depth": "green",
                "chain_confidence": 0.85,
                "attestation_count": 1,
                "provisions_cited": [],
                "human_review_required": False,
                "human_review_completed": False,
                "created_at": "2026-03-13T00:00:00",
            }
            mock_chain = MagicMock()
            mock_chain.to_dict.return_value = trust_dict
            mock_chain.verification_depth = "green"

            with patch(
                "hr_advisory.api.routers.advisory.create_trust_chain",
                return_value=mock_chain,
            ):
                from hr_advisory.api.routers.advisory import _run_llm_advisory

                result = _run_llm_advisory(
                    query="test query",
                    domains=["cpf"],
                    provisions=[],
                )

                assert result is not None
                assert "trust_metadata" in result
                assert result["trust_metadata"]["session_id"] == "test-session"


class TestT069ConstraintViolationLogging:
    """When constraint envelope validation detects violations, they should
    be logged and included in the attestation."""

    @patch("hr_advisory.agents.config.has_llm_available", return_value=True)
    def test_violations_logged_in_attestation(self, mock_llm):
        """Constraint violations should be attached to the attestation."""
        with _patch_pipeline() as mocks:
            mock_chain = MagicMock()
            mock_chain.to_dict.return_value = {"session_id": "test"}
            mock_chain.verification_depth = "green"

            with patch(
                "hr_advisory.api.routers.advisory.create_trust_chain",
                return_value=mock_chain,
            ):
                with patch(
                    "hr_advisory.api.routers.advisory.validate_constraint_envelope",
                    return_value=["Agent cpf_specialist responded about forbidden domain 'tax'"],
                ):
                    from hr_advisory.api.routers.advisory import _run_llm_advisory

                    _run_llm_advisory(
                        query="test query",
                        domains=["cpf"],
                        provisions=[],
                    )

                    # The attestation added should contain constraint_violations
                    assert mock_chain.add_attestation.call_count >= 1
                    attestation = mock_chain.add_attestation.call_args[0][0]
                    assert len(attestation.constraint_violations) > 0


# ===================================================================
# Helpers
# ===================================================================


def _make_mock_specialist():
    """Create a mock specialist for testing advise() method.

    We instantiate the base class with overridden methods to avoid
    needing LLM credentials.
    """
    from hr_advisory.agents.specialists._base import BaseDomainSpecialist

    class MockSpecialist(BaseDomainSpecialist):
        domain = "test_domain"
        domain_label = "Test"

        def _default_signature(self):
            from hr_advisory.agents.specialists.signatures import SpecialistSignature
            return SpecialistSignature()

        def _generate_system_prompt(self) -> str:
            return "Test system prompt"

    agent = MockSpecialist()
    # Override extract methods to return values directly from the run result
    agent.extract_str = lambda result, key, default="": result.get(key, default)
    agent.extract_list = lambda result, key, default=None: (
        json.loads(result.get(key, "[]")) if isinstance(result.get(key), str) else result.get(key, default or [])
    )
    agent.write_to_memory = MagicMock()
    return agent


class _PipelineMocks:
    """Context manager that patches the full advisory pipeline for unit testing.

    Since _run_llm_advisory uses lazy imports inside the function body,
    we must patch the classes at their source modules so that when the
    function performs ``from hr_advisory.agents.specialists import CPFAgent``,
    it gets our mock.
    """

    def __init__(
        self,
        enable_compliance_gate: bool = False,
        compliance_risk_tier: str = "green",
        compliance_risk_escalation: bool = False,
    ):
        self.enable_compliance_gate = enable_compliance_gate
        self.compliance_risk_tier = compliance_risk_tier
        self.compliance_risk_escalation = compliance_risk_escalation
        self._patches = []
        self.mocks = {}

    def __enter__(self):
        # Create mock instances
        analyzer_instance = MagicMock()
        analyzer_instance.analyze.return_value = {
            "domains": ["cpf"] if not self.enable_compliance_gate else ["cpf", "tax"],
            "entities": {},
            "risk_tier": "green",
            "routing_decision": {"strategy": "router" if not self.enable_compliance_gate else "parallel"},
        }

        router_instance = MagicMock()
        dispatch_plan = MagicMock()
        dispatch_plan.specialists = ["cpf"] if not self.enable_compliance_gate else ["cpf", "tax"]
        dispatch_plan.include_compliance_gate = self.enable_compliance_gate
        router_instance.route.return_value = dispatch_plan

        specialist_instance = MagicMock()
        specialist_instance.advise.return_value = {
            "domain": "cpf",
            "answer_text": "test specialist answer",
            "cited_provisions": [],
            "confidence": 0.85,
            "risk_tier": "green",
            "cross_domain_flags": [],
        }

        # Second specialist for multi-domain tests
        specialist_instance_2 = MagicMock()
        specialist_instance_2.advise.return_value = {
            "domain": "tax",
            "answer_text": "test tax answer",
            "cited_provisions": [],
            "confidence": 0.9,
            "risk_tier": "green",
            "cross_domain_flags": [],
        }

        compliance_instance = MagicMock()
        compliance_instance.check_compliance.return_value = {
            "domain": "compliance",
            "compliance_flags": [],
            "gaps_identified": [],
            "risk_tier": self.compliance_risk_tier,
            "recommendations": [],
            "risk_escalation": self.compliance_risk_escalation,
            "override_risk_tier": self.compliance_risk_tier,
        }
        # Also mock advise for backward compat
        compliance_instance.advise.return_value = compliance_instance.check_compliance.return_value

        synthesizer_instance = MagicMock()
        synthesizer_instance.synthesize.return_value = {
            "response_text": "Synthesized response",
            "citations": [],
            "disclaimers": [],
            "final_risk_tier": "green",
        }

        # Store in mocks dict for assertions
        self.mocks = {
            "analyzer_instance": analyzer_instance,
            "router_instance": router_instance,
            "dispatch_plan": dispatch_plan,
            "specialist_instance": specialist_instance,
            "specialist_instance_2": specialist_instance_2,
            "compliance_instance": compliance_instance,
            "synthesizer_instance": synthesizer_instance,
        }

        # Patch class constructors at their source modules so lazy imports
        # inside _run_llm_advisory pick up the mocks.
        self._specialist_call_count = 0

        def make_specialist_side_effect(*args, **kwargs):
            self._specialist_call_count += 1
            if self._specialist_call_count == 1:
                return specialist_instance
            return specialist_instance_2

        def make_compliance_side_effect(*args, **kwargs):
            return compliance_instance

        # Patch at the specialists __init__ package level — this is where
        # the lazy ``from hr_advisory.agents.specialists import CPFAgent``
        # resolves names from.  We also patch at the source module level
        # for imports that go directly to the file.
        p1 = patch(
            "hr_advisory.agents.orchestration.query_analyzer.QueryAnalyzerAgent",
            return_value=analyzer_instance,
        )
        p2 = patch(
            "hr_advisory.agents.orchestration.dispatch_router.DispatchRouter",
            return_value=router_instance,
        )
        p3 = patch(
            "hr_advisory.agents.orchestration.response_synthesizer.ResponseSynthesizerAgent",
            return_value=synthesizer_instance,
        )

        # Patch at both package __init__ and source module level so the
        # lazy ``from ... import X`` inside _run_llm_advisory picks up mocks
        p4 = patch(
            "hr_advisory.agents.specialists.CPFAgent",
            side_effect=make_specialist_side_effect,
        )
        p4b = patch(
            "hr_advisory.agents.specialists.cpf.CPFAgent",
            side_effect=make_specialist_side_effect,
        )
        p5 = patch(
            "hr_advisory.agents.specialists.TaxAgent",
            side_effect=make_specialist_side_effect,
        )
        p5b = patch(
            "hr_advisory.agents.specialists.tax.TaxAgent",
            side_effect=make_specialist_side_effect,
        )
        p6 = patch(
            "hr_advisory.agents.specialists.ComplianceAgent",
            side_effect=make_compliance_side_effect,
        )
        p6b = patch(
            "hr_advisory.agents.specialists.compliance.ComplianceAgent",
            side_effect=make_compliance_side_effect,
        )

        # Patch KB retriever at source module
        p7 = patch(
            "hr_advisory.agents.orchestration.kb_retriever.retrieve_provisions_for_specialist",
            return_value=[],
        )
        p8 = patch(
            "hr_advisory.agents.orchestration.kb_retriever.provisions_to_dicts",
            return_value=[],
        )

        # Patch SharedMemoryPool at source module
        p9 = patch(
            "kaizen.memory.SharedMemoryPool",
            return_value=MagicMock(),
        )

        self._patches = [p1, p2, p3, p4, p4b, p5, p5b, p6, p6b, p7, p8, p9]
        for p in self._patches:
            p.start()

        return self.mocks

    def __exit__(self, *args):
        for p in self._patches:
            p.stop()


def _patch_pipeline(
    enable_compliance_gate: bool = False,
    compliance_risk_tier: str = "green",
    compliance_risk_escalation: bool = False,
):
    """Return a _PipelineMocks context manager."""
    return _PipelineMocks(
        enable_compliance_gate=enable_compliance_gate,
        compliance_risk_tier=compliance_risk_tier,
        compliance_risk_escalation=compliance_risk_escalation,
    )
