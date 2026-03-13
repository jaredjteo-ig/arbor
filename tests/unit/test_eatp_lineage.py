"""Unit tests for the EATP trust lineage implementation.

Tests trust chain creation, agent attestation recording, constraint
envelope validation, and anti-amnesia injection.
"""

from __future__ import annotations

from hr_advisory.trust.eatp_lineage import (
    AgentAttestation,
    AgentRole,
    GenesisRecord,
    TrustLevel,
    create_trust_chain,
    get_anti_amnesia_injection,
    get_constraint_envelope,
    get_trust_chain,
    validate_constraint_envelope,
)


class TestGenesisRecord:
    """Test trust anchor creation."""

    def test_fingerprint_is_deterministic(self) -> None:
        """Same genesis record should produce same fingerprint."""
        genesis = _make_genesis("session-1")
        fp1 = genesis.fingerprint
        fp2 = genesis.fingerprint
        assert fp1 == fp2

    def test_different_sessions_different_fingerprints(self) -> None:
        """Different session IDs should produce different fingerprints."""
        g1 = _make_genesis("session-1")
        g2 = _make_genesis("session-2")
        assert g1.fingerprint != g2.fingerprint


class TestTrustChain:
    """Test trust chain operations."""

    def test_create_trust_chain(self) -> None:
        """Should create a trust chain with genesis record."""
        genesis = _make_genesis("tc-1")
        chain = create_trust_chain(genesis)
        assert chain.genesis.session_id == "tc-1"
        assert chain.attestations == []

    def test_retrieve_trust_chain(self) -> None:
        """Should retrieve a created trust chain by session ID."""
        genesis = _make_genesis("tc-retrieve")
        create_trust_chain(genesis)
        retrieved = get_trust_chain("tc-retrieve")
        assert retrieved is not None
        assert retrieved.genesis.session_id == "tc-retrieve"

    def test_nonexistent_chain_returns_none(self) -> None:
        """Should return None for unknown session ID."""
        result = get_trust_chain("nonexistent-session")
        assert result is None

    def test_add_attestation(self) -> None:
        """Should add an attestation to the chain."""
        genesis = _make_genesis("tc-attest")
        chain = create_trust_chain(genesis)
        attestation = _make_attestation("orchestrator")
        chain.add_attestation(attestation)
        assert len(chain.attestations) == 1

    def test_chain_confidence_minimum(self) -> None:
        """Chain confidence should be the minimum of all attestations."""
        genesis = _make_genesis("tc-conf")
        chain = create_trust_chain(genesis)
        chain.add_attestation(_make_attestation("agent-1", confidence=0.9))
        chain.add_attestation(_make_attestation("agent-2", confidence=0.7))
        chain.add_attestation(_make_attestation("agent-3", confidence=0.85))
        assert chain.chain_confidence == 0.7

    def test_empty_chain_zero_confidence(self) -> None:
        """Chain with no attestations should have zero confidence."""
        genesis = _make_genesis("tc-empty")
        chain = create_trust_chain(genesis)
        assert chain.chain_confidence == 0.0

    def test_all_provisions_cited(self) -> None:
        """Should aggregate all provisions across attestations (deduplicated)."""
        genesis = _make_genesis("tc-prov")
        chain = create_trust_chain(genesis)
        a1 = _make_attestation("agent-1")
        a1 = AgentAttestation(
            agent_id="agent-1",
            agent_role=AgentRole.SPECIALIST,
            agent_version="v1",
            domain="cpf",
            provisions_retrieved=["CPFA-S52"],
            reasoning_summary="test",
            conclusion="test",
            confidence_score=0.9,
            constraint_envelope_id="cpf_specialist",
        )
        a2 = AgentAttestation(
            agent_id="agent-2",
            agent_role=AgentRole.SPECIALIST,
            agent_version="v1",
            domain="employment_act",
            provisions_retrieved=["EA-S95-KETs", "CPFA-S52"],
            reasoning_summary="test",
            conclusion="test",
            confidence_score=0.85,
            constraint_envelope_id="employment_act_specialist",
        )
        chain.add_attestation(a1)
        chain.add_attestation(a2)
        cited = chain.all_provisions_cited
        assert "CPFA-S52" in cited
        assert "EA-S95-KETs" in cited

    def test_to_dict(self) -> None:
        """Trust chain should serialize to a dict for API response."""
        genesis = _make_genesis("tc-dict")
        chain = create_trust_chain(genesis)
        chain.add_attestation(_make_attestation("agent-1", confidence=0.9))
        d = chain.to_dict()
        assert d["session_id"] == "tc-dict"
        assert "genesis_fingerprint" in d
        assert d["attestation_count"] == 1
        assert d["chain_confidence"] == 0.9


class TestConstraintEnvelopes:
    """Test constraint envelope validation."""

    def test_get_known_envelope(self) -> None:
        """Should return envelope for a known agent."""
        envelope = get_constraint_envelope("cpf_specialist")
        assert envelope is not None
        assert "cpf" in envelope.allowed_domains

    def test_get_unknown_envelope(self) -> None:
        """Should return None for unknown agent."""
        envelope = get_constraint_envelope("nonexistent_agent")
        assert envelope is None

    def test_valid_domain_no_violations(self) -> None:
        """Agent responding within allowed domains should have no violations."""
        violations = validate_constraint_envelope("cpf_specialist", ["cpf"])
        assert violations == []

    def test_forbidden_domain_violation(self) -> None:
        """Agent responding about forbidden domain should produce violation."""
        violations = validate_constraint_envelope("cpf_specialist", ["employment_act"])
        assert len(violations) > 0
        assert "forbidden" in violations[0].lower()

    def test_unauthorized_domain_violation(self) -> None:
        """Agent responding about domain not in allowed list should produce violation."""
        violations = validate_constraint_envelope("cpf_specialist", ["compliance"])
        assert len(violations) > 0

    def test_orchestrator_all_domains(self) -> None:
        """Orchestrator has 'all' domains — no violations for any domain."""
        violations = validate_constraint_envelope("orchestrator", ["cpf", "employment_act", "tax"])
        assert violations == []


class TestAntiAmnesia:
    """Test anti-amnesia constraint injection."""

    def test_injection_contains_rules(self) -> None:
        """Anti-amnesia injection should contain constraint rules."""
        injection = get_anti_amnesia_injection("orchestrator")
        assert "[CONSTRAINT" in injection
        assert "CRITICAL" in injection

    def test_injection_includes_domain_constraints(self) -> None:
        """Injection for a specialist should include domain restrictions."""
        injection = get_anti_amnesia_injection("cpf_specialist")
        assert "cpf" in injection.lower()
        assert "AUTHORIZED DOMAINS" in injection

    def test_injection_for_unknown_agent(self) -> None:
        """Injection for unknown agent should still include base rules."""
        injection = get_anti_amnesia_injection("unknown_agent")
        assert "[CONSTRAINT" in injection
        assert "CRITICAL" in injection


# ── Helpers ──────────────────────────────────────────────────


def _make_genesis(session_id: str) -> GenesisRecord:
    return GenesisRecord(
        session_id=session_id,
        user_verification_level=TrustLevel.STANDARD,
        company_profile_completeness=0.8,
        kb_currency_status={"employment_act": "2026-03-01"},
        agent_version_hashes={"orchestrator": "v1.0.0"},
        query_text="test query",
        query_domains=["employment_act"],
    )


def _make_attestation(
    agent_id: str,
    confidence: float = 0.85,
) -> AgentAttestation:
    return AgentAttestation(
        agent_id=agent_id,
        agent_role=AgentRole.ORCHESTRATOR,
        agent_version="v1",
        domain="employment_act",
        provisions_retrieved=["EA-S95-KETs"],
        reasoning_summary="test",
        conclusion="test conclusion",
        confidence_score=confidence,
        constraint_envelope_id="orchestrator",
    )
