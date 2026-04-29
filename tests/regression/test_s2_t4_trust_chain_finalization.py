"""Regression: S2-T4 — finalize_trust_chain integration (round-12 HIGH).

advisory.py builds a trust chain via create_trust_chain → add_attestation
on every /query and /stream response. Pre-S2-T4 the chain stayed in the
in-memory cache and was never persisted: proof debt. Auditors could not
retrieve the chain by id later.

This test pins:
  1. finalize_trust_chain returns a bool (True = persisted, False = not)
     so callers can surface persistence status to clients.
  2. _persist_trust_chain returns a bool too (True on DB write success).
  3. /query and /stream both call finalize_trust_chain and expose
     trust_chain.persisted + trust_chain_id in the response.
  4. finalize_trust_chain on a stale/missing session_id returns False
     instead of raising — defense against cache eviction races.
"""

from __future__ import annotations

import inspect

import pytest


# ---------------------------------------------------------------------------
# Trust-chain library guards
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_s2_t4_finalize_trust_chain_returns_bool():
    """finalize_trust_chain MUST return a bool. Pre-S2-T4 it returned None,
    so callers had no way to distinguish "persisted" from "no-op".
    """
    from hr_advisory.trust.eatp_lineage import finalize_trust_chain

    sig = inspect.signature(finalize_trust_chain)
    annotation = sig.return_annotation
    # The return annotation should resolve to bool. Accept both bool and "bool"
    # forms in case `from __future__ import annotations` keeps it as a string.
    assert annotation is bool or annotation == "bool", (
        f"finalize_trust_chain must annotate `-> bool`. Got {annotation!r}. "
        f"Without a typed return value, callers can't tell whether the chain "
        f"actually persisted vs. was a no-op."
    )


@pytest.mark.regression
def test_s2_t4_finalize_missing_session_returns_false():
    """Calling finalize on a session_id that was never registered must
    return False — NOT raise. Cache eviction can legitimately remove a
    chain before finalization, and we should not crash the response.
    """
    from hr_advisory.trust.eatp_lineage import finalize_trust_chain

    result = finalize_trust_chain(session_id="never-registered-uuid-12345")
    assert result is False, (
        "finalize_trust_chain on an unknown session_id must return False, "
        "not raise. Cache eviction races would otherwise crash live traffic."
    )


@pytest.mark.regression
def test_s2_t4_finalize_persisted_chain_returns_true_on_success(monkeypatch):
    """When _persist_trust_chain succeeds, finalize_trust_chain returns True.
    """
    from hr_advisory.trust.eatp_lineage import (
        AgentRole,
        GenesisRecord,
        TrustLevel,
        create_trust_chain,
        finalize_trust_chain,
    )
    from hr_advisory.trust import eatp_lineage as lineage_module

    # Bypass the actual DB write to keep the test tier-1
    monkeypatch.setattr(
        lineage_module,
        "_persist_trust_chain",
        lambda chain, user_id=0, company_id=0: True,
    )

    genesis = GenesisRecord(
        session_id="test-session-finalize-true",
        user_verification_level=TrustLevel.STANDARD,
        company_profile_completeness=0.5,
        kb_currency_status={"employment_act": "2026-01-01"},
        agent_version_hashes={"advisory_engine": "v2.0.0"},
        query_text="test",
        query_domains=["employment_act"],
    )
    create_trust_chain(genesis)

    result = finalize_trust_chain("test-session-finalize-true")
    assert result is True


@pytest.mark.regression
def test_s2_t4_finalize_returns_false_on_persist_failure(monkeypatch):
    """When _persist_trust_chain fails (returns False), finalize_trust_chain
    propagates False so the API response can flag the missing audit trail.
    """
    from hr_advisory.trust.eatp_lineage import (
        GenesisRecord,
        TrustLevel,
        create_trust_chain,
        finalize_trust_chain,
    )
    from hr_advisory.trust import eatp_lineage as lineage_module

    monkeypatch.setattr(
        lineage_module,
        "_persist_trust_chain",
        lambda chain, user_id=0, company_id=0: False,
    )

    genesis = GenesisRecord(
        session_id="test-session-finalize-false",
        user_verification_level=TrustLevel.STANDARD,
        company_profile_completeness=0.5,
        kb_currency_status={"cpf": "2026-01-01"},
        agent_version_hashes={"advisory_engine": "v2.0.0"},
        query_text="test",
        query_domains=["cpf"],
    )
    create_trust_chain(genesis)

    result = finalize_trust_chain("test-session-finalize-false")
    assert result is False


# ---------------------------------------------------------------------------
# advisory.py wiring guards
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_s2_t4_advisory_query_finalizes_trust_chain():
    """The /query path MUST import finalize_trust_chain and call it on
    the session_id before returning the response.
    """
    from hr_advisory.api.routers import advisory as advisory_module

    src = inspect.getsource(advisory_module)
    assert "finalize_trust_chain" in src, (
        "advisory.py must import finalize_trust_chain — without it the "
        "trust chain never persists to the DB."
    )
    # The query handler should pass session_id to finalize
    handler_src = inspect.getsource(advisory_module.advisory_query)
    assert "finalize_trust_chain" in handler_src, (
        "advisory_query() must call finalize_trust_chain — pre-S2-T4 it "
        "called create_trust_chain + add_attestation but never finalized, "
        "leaving the chain unsealed."
    )
    assert "session_id=session_id" in handler_src, (
        "finalize_trust_chain must be called with the same session_id used "
        "for create_trust_chain — otherwise it persists nothing."
    )


@pytest.mark.regression
def test_s2_t4_advisory_query_response_includes_persisted_and_id():
    """The /query response MUST include trust_chain.persisted and
    trust_chain_id so clients can verify and retrieve the audit chain.
    """
    from hr_advisory.api.routers import advisory as advisory_module

    handler_src = inspect.getsource(advisory_module.advisory_query)
    assert '"persisted"' in handler_src, (
        "Response must surface trust_chain.persisted so the caller knows "
        "whether the audit trail was committed."
    )
    assert '"trust_chain_id"' in handler_src, (
        "Response must include trust_chain_id so the caller can retrieve "
        "the persisted chain later for audit/verification."
    )


@pytest.mark.regression
def test_s2_t4_advisory_stream_finalizes_trust_chain():
    """The /stream path also builds a trust chain — it MUST also finalize."""
    from hr_advisory.api.routers import advisory as advisory_module

    src = inspect.getsource(advisory_module.advisory_stream)
    assert "finalize_trust_chain" in src, (
        "advisory_stream() must call finalize_trust_chain at the end of "
        "attestation, before emitting the stream — pre-S2-T4 it built the "
        "chain in memory but never persisted, so streaming responses had "
        "no audit trail."
    )
    assert '"persisted"' in src, (
        "Stream response must surface trust_chain.persisted."
    )
    assert '"trust_chain_id"' in src, (
        "Stream response must include trust_chain_id."
    )
