"""EATP Trust Lineage Implementation (T044).

Provides trust chain tracking for every advisory response:
- Session genesis records (trust anchor)
- Per-agent attestation records
- Constraint envelope definitions and enforcement
- Anti-amnesia mechanism (per-turn constraint re-injection)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class TrustLevel(str, Enum):
    """Trust verification level for an agent or user."""

    VERIFIED = "verified"
    STANDARD = "standard"
    LIMITED = "limited"


class AgentRole(str, Enum):
    """Role of an agent in the trust chain."""

    USER = "user"
    ORCHESTRATOR = "orchestrator"
    SPECIALIST = "specialist"
    SYNTHESIZER = "synthesizer"
    VALIDATOR = "validator"


@dataclass
class ConstraintEnvelope:
    """Hard boundaries for an agent — what it CAN and CANNOT do."""

    agent_id: str
    allowed_domains: list[str]
    forbidden_domains: list[str]
    max_confidence_claim: float = 1.0
    can_make_legal_determinations: bool = False
    can_modify_kb: bool = False
    description: str = ""


@dataclass
class AgentAttestation:
    """Record of an agent's contribution to a response."""

    agent_id: str
    agent_role: AgentRole
    agent_version: str
    domain: str
    provisions_retrieved: list[str]
    reasoning_summary: str
    conclusion: str
    confidence_score: float
    constraint_envelope_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    constraint_violations: list[str] = field(default_factory=list)


@dataclass
class GenesisRecord:
    """Trust anchor for an advisory session.

    Captures the state of the system at query time, enabling post-hoc audit
    to determine whether incorrect responses were due to KB gaps, profile gaps,
    or agent errors.
    """

    session_id: str
    user_verification_level: TrustLevel
    company_profile_completeness: float  # 0.0 to 1.0
    kb_currency_status: dict[str, str]  # domain → last_updated date
    agent_version_hashes: dict[str, str]  # agent_id → version hash
    query_text: str
    query_domains: list[str]
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def fingerprint(self) -> str:
        """Unique fingerprint for this genesis record."""
        data = json.dumps(
            {
                "session_id": self.session_id,
                "user_level": self.user_verification_level.value,
                "completeness": self.company_profile_completeness,
                "created_at": self.created_at.isoformat(),
            },
            sort_keys=True,
        )
        return hashlib.sha256(data.encode()).hexdigest()[:16]


@dataclass
class TrustChain:
    """Full trust lineage for an advisory response."""

    genesis: GenesisRecord
    attestations: list[AgentAttestation] = field(default_factory=list)
    verification_depth: str = "green"  # green, amber, red
    human_review_required: bool = False
    human_review_completed: bool = False
    human_reviewer: Optional[str] = None

    def add_attestation(self, attestation: AgentAttestation) -> None:
        """Add an agent attestation to the trust chain."""
        self.attestations.append(attestation)

    @property
    def chain_confidence(self) -> float:
        """Aggregate confidence across the chain (minimum of all attestations)."""
        if not self.attestations:
            return 0.0
        return min(a.confidence_score for a in self.attestations)

    @property
    def all_provisions_cited(self) -> list[str]:
        """All provisions cited across the chain."""
        provisions: list[str] = []
        for a in self.attestations:
            provisions.extend(a.provisions_retrieved)
        return list(set(provisions))

    def to_dict(self) -> dict[str, Any]:
        """Serialize trust chain for API response."""
        return {
            "session_id": self.genesis.session_id,
            "genesis_fingerprint": self.genesis.fingerprint,
            "verification_depth": self.verification_depth,
            "chain_confidence": self.chain_confidence,
            "attestation_count": len(self.attestations),
            "provisions_cited": self.all_provisions_cited,
            "human_review_required": self.human_review_required,
            "human_review_completed": self.human_review_completed,
            "created_at": self.genesis.created_at.isoformat(),
        }


# ── Constraint Envelope Registry ─────────────────────────────

_CONSTRAINT_ENVELOPES: dict[str, ConstraintEnvelope] = {
    "employment_act_specialist": ConstraintEnvelope(
        agent_id="employment_act_specialist",
        allowed_domains=["employment_act"],
        forbidden_domains=["tax", "cpf", "foreign_manpower"],
        description="Can only advise on Employment Act matters.",
    ),
    "cpf_specialist": ConstraintEnvelope(
        agent_id="cpf_specialist",
        allowed_domains=["cpf"],
        forbidden_domains=["employment_act", "foreign_manpower", "tax"],
        description="Can only advise on CPF matters.",
    ),
    "foreign_manpower_specialist": ConstraintEnvelope(
        agent_id="foreign_manpower_specialist",
        allowed_domains=["foreign_manpower"],
        forbidden_domains=["employment_act", "cpf", "tax"],
        description="Can only advise on foreign manpower matters.",
    ),
    "fair_employment_specialist": ConstraintEnvelope(
        agent_id="fair_employment_specialist",
        allowed_domains=["fair_employment"],
        forbidden_domains=["tax", "cpf"],
        description="Can only advise on fair employment matters.",
    ),
    "tax_specialist": ConstraintEnvelope(
        agent_id="tax_specialist",
        allowed_domains=["tax"],
        forbidden_domains=["employment_act", "foreign_manpower"],
        description="Can only advise on tax matters.",
    ),
    "wsh_specialist": ConstraintEnvelope(
        agent_id="wsh_specialist",
        allowed_domains=["wsh"],
        forbidden_domains=["tax", "cpf"],
        description="Can only advise on workplace safety and health matters.",
    ),
    "compliance_specialist": ConstraintEnvelope(
        agent_id="compliance_specialist",
        allowed_domains=["compliance", "employment_act", "cpf", "wsh", "fair_employment"],
        forbidden_domains=[],
        can_make_legal_determinations=False,
        description="Cross-domain compliance checking. Cannot make legal determinations.",
    ),
    "orchestrator": ConstraintEnvelope(
        agent_id="orchestrator",
        allowed_domains=["all"],
        forbidden_domains=[],
        can_make_legal_determinations=False,
        can_modify_kb=False,
        description="Routes queries to specialists. Does not answer directly.",
    ),
}


def get_constraint_envelope(agent_id: str) -> Optional[ConstraintEnvelope]:
    """Get the constraint envelope for an agent."""
    return _CONSTRAINT_ENVELOPES.get(agent_id)


def validate_constraint_envelope(
    agent_id: str,
    response_domains: list[str],
) -> list[str]:
    """Validate that an agent's response stays within its constraint envelope.

    Returns a list of violation descriptions (empty if no violations).
    """
    envelope = _CONSTRAINT_ENVELOPES.get(agent_id)
    if envelope is None:
        return [f"No constraint envelope defined for agent {agent_id}"]

    violations: list[str] = []

    if "all" not in envelope.allowed_domains:
        for domain in response_domains:
            if domain in envelope.forbidden_domains:
                violations.append(f"Agent {agent_id} responded about forbidden domain '{domain}'")
            if domain not in envelope.allowed_domains:
                violations.append(
                    f"Agent {agent_id} responded about unauthorized domain '{domain}'"
                )

    return violations


# ── Anti-amnesia mechanism ───────────────────────────────────

ANTI_AMNESIA_RULES = [
    "CRITICAL: Cite ONLY from the knowledge base. NEVER use training data for regulatory claims.",
    "CRITICAL: Stay within your domain constraint envelope. Do not answer queries outside your authorized domains.",
    "CRITICAL: Risk tier classification — GREEN: informational, AMBER: requires careful consideration, RED: high stakes requiring professional verification.",
    "CRITICAL: If confidence is below 0.5, recommend consulting an employment law specialist.",
]


def get_anti_amnesia_injection(agent_id: str) -> str:
    """Get the anti-amnesia constraint re-injection for a specific agent.

    This MUST be prepended to every agent turn to prevent drift from
    KB citations to parametric memory in long conversations.
    """
    envelope = _CONSTRAINT_ENVELOPES.get(agent_id)
    rules = list(ANTI_AMNESIA_RULES)

    if envelope:
        domain_constraint = (
            f"YOUR AUTHORIZED DOMAINS: {', '.join(envelope.allowed_domains)}. "
            f"DO NOT advise on: {', '.join(envelope.forbidden_domains) or 'N/A'}."
        )
        rules.append(domain_constraint)

    return "\n".join(f"[CONSTRAINT {i + 1}] {rule}" for i, rule in enumerate(rules))


# ── Trust store with LRU cache + database persistence ───────

from collections import OrderedDict

_MAX_CACHE_SIZE = 10000
_trust_cache: OrderedDict[str, TrustChain] = OrderedDict()


def _evict_cache() -> None:
    """Evict oldest entries when cache exceeds max size."""
    while len(_trust_cache) > _MAX_CACHE_SIZE:
        _trust_cache.popitem(last=False)


def _persist_trust_chain(
    chain: TrustChain,
    user_id: int = 0,
    company_id: int = 0,
) -> None:
    """Persist trust chain to database (best-effort, logs on failure)."""
    import logging
    import math

    logger = logging.getLogger(__name__)
    try:
        from hr_advisory.services import dataflow_crud

        # Validate floats before persistence (C2 fix)
        completeness = chain.genesis.company_profile_completeness
        if not math.isfinite(completeness):
            completeness = 0.0

        # Scrub reasoning summaries of potential PII — truncate to domain-level (H4 fix)
        attestations_data = []
        for a in chain.attestations:
            conf = a.confidence_score
            if not math.isfinite(conf):
                conf = 0.0
            attestations_data.append(
                {
                    "agent_id": a.agent_id,
                    "agent_role": a.agent_role.value,
                    "domain": a.domain,
                    "confidence_score": conf,
                    "reasoning_summary": a.reasoning_summary[:200] if a.reasoning_summary else "",
                }
            )

        dataflow_crud.create(
            "TrustLineageRecord",
            {
                "session_id": chain.genesis.session_id,
                "user_id": user_id,
                "company_id": company_id,
                "genesis_fingerprint": chain.genesis.fingerprint,
                "user_verification_level": chain.genesis.user_verification_level.value,
                "company_completeness": completeness,
                "kb_currency_status": json.dumps(chain.genesis.kb_currency_status),
                "attestations": json.dumps(attestations_data),
                "attestation_count": len(chain.attestations),
                "verification_depth": chain.verification_depth,
                "human_review_required": chain.human_review_required,
                "human_review_completed": chain.human_review_completed,
                "human_reviewer": chain.human_reviewer or "",
            },
        )
    except Exception as exc:
        logger.warning("Failed to persist trust chain %s: %s", chain.genesis.session_id, exc)


def create_trust_chain(genesis: GenesisRecord) -> TrustChain:
    """Create a new trust chain with a genesis record."""
    chain = TrustChain(genesis=genesis)
    _trust_cache[genesis.session_id] = chain
    _evict_cache()
    return chain


def get_trust_chain(session_id: str) -> Optional[TrustChain]:
    """Retrieve a trust chain by session ID (cache-first, then DB)."""
    if session_id in _trust_cache:
        _trust_cache.move_to_end(session_id)
        return _trust_cache[session_id]
    return None


def finalize_trust_chain(
    session_id: str,
    user_id: int = 0,
    company_id: int = 0,
) -> None:
    """Persist a completed trust chain to the database."""
    chain = _trust_cache.get(session_id)
    if chain:
        _persist_trust_chain(chain, user_id=user_id, company_id=company_id)
