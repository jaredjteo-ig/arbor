"""Red-team P5-AD — advisory legacy guardrail-fallback filter.

Origin: workspaces/obayashi/04-validate/13-redteam-comprehensive-2026-05-19.md
finding O3 / C9. Live walk turned up 2 conversations in History
sidebar showing "(earlier reply unavailable)" — they're real
persisted conversations whose assistant reply was a degraded-state
fallback ("I'm having trouble processing your question right now…").

This file pins three structural fixes:

  1. `short_term._is_legacy_fallback_reply` returns True for the
     known legacy phrases and False for valid replies.
  2. `_persist_turn` short-circuits on legacy responses — they
     never land in the DB.
  3. `scripts/maintenance/purge_legacy_advisory.py` exists with the
     correct shape (idempotent, dry-run option, prod safety guard).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SHORT_TERM = (
    REPO_ROOT / "src/hr_advisory/agents/memory/short_term.py"
)
PURGE_SCRIPT = (
    REPO_ROOT / "scripts/maintenance/purge_legacy_advisory.py"
)
HOOK = (
    REPO_ROOT / "apps/web/src/hooks/useAdvisoryHistory.ts"
)
PAGE = (
    REPO_ROOT / "apps/web/src/app/(dashboard)/advisory/page.tsx"
)
CHAT_CONTAINER = (
    REPO_ROOT / "apps/web/src/components/advisory/ChatContainer.tsx"
)


# ---------------------------------------------------------------------------
# Backend filter — predicate
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_p5_ad_predicate_matches_known_fallbacks():
    from hr_advisory.agents.memory.short_term import _is_legacy_fallback_reply

    # The two phrases that bled into prod History.
    assert _is_legacy_fallback_reply(
        "I'm having trouble processing your question right now. Please try again."
    )
    assert _is_legacy_fallback_reply(
        "I was unable to fully process your query. Please try rephrasing."
    )


@pytest.mark.regression
def test_p5_ad_predicate_passes_valid_replies():
    from hr_advisory.agents.memory.short_term import _is_legacy_fallback_reply

    # CPF answer from the round-3 walk — must be persisted normally.
    assert not _is_legacy_fallback_reply(
        "In this example, for an employee earning $4,500 monthly wages and a "
        "$1,000 bonus (and is 55 and below):\n* Employer contributes $935.00\n* …"
    )
    # Edge cases that should NOT match.
    assert not _is_legacy_fallback_reply("Yes — see EA s95A for details.")
    assert not _is_legacy_fallback_reply(
        "  I'm sorry, I cannot help with that"  # similar but distinct phrase
    )


@pytest.mark.regression
def test_p5_ad_predicate_empty_response_is_treated_as_fallback():
    """An empty assistant response is also a degraded state — we
    should NOT persist it. The buyer would otherwise see an entry
    with no reply content under their question."""
    from hr_advisory.agents.memory.short_term import _is_legacy_fallback_reply

    assert _is_legacy_fallback_reply("")
    assert _is_legacy_fallback_reply("   ")
    assert _is_legacy_fallback_reply(None)


# ---------------------------------------------------------------------------
# Backend filter — _persist_turn short-circuits on legacy
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_p5_ad_persist_turn_skips_legacy_response(caplog):
    """`_persist_turn` must NOT call into the DB workflow when the
    assistant text matches a legacy phrase."""
    from hr_advisory.agents.memory.short_term import ShortTermMemory

    mem = ShortTermMemory()

    with patch.object(mem, "_ensure_thread") as ensure_thread:
        mem._persist_turn(
            session_id="sess-1",
            query="How do I calculate CPF?",
            response="I'm having trouble processing your question right now.",
            entities=None,
            domains=["cpf"],
            risk_tier="amber",
            provisions_cited=None,
            confidence_score=0.0,
            user_id=10,
            company_id=1,
        )
        ensure_thread.assert_not_called()


@pytest.mark.regression
def test_p5_ad_persist_turn_persists_normal_response():
    """The happy-path response must still ATTEMPT to persist — verify
    `_ensure_thread` is called once. The subsequent DataFlow write is
    best-effort and wrapped in try/except, so we don't need to mock
    the lazy `from kailash import ...` import."""
    from hr_advisory.agents.memory.short_term import ShortTermMemory

    mem = ShortTermMemory()

    # _ensure_thread returns None so the function exits cleanly without
    # invoking the WorkflowBuilder path. Calling _ensure_thread itself
    # is the evidence we want.
    with patch.object(mem, "_ensure_thread", return_value=None) as ensure_thread:
        mem._persist_turn(
            session_id="sess-1",
            query="How do I calculate CPF?",
            response="Employer contributes 17%. Employee contributes 20%.",
            entities=None,
            domains=["cpf"],
            risk_tier="green",
            provisions_cited=None,
            confidence_score=1.0,
            user_id=10,
            company_id=1,
        )
        ensure_thread.assert_called_once()


# ---------------------------------------------------------------------------
# Purge script — source pins
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_p5_ad_purge_script_exists():
    assert PURGE_SCRIPT.exists(), (
        "scripts/maintenance/purge_legacy_advisory.py must exist."
    )


@pytest.mark.regression
def test_p5_ad_purge_script_has_safety_features():
    src = PURGE_SCRIPT.read_text()
    # Dry-run support
    assert "--dry-run" in src
    assert "dry_run" in src
    # Prod safety: refuse to run against non-localhost without admin pwd
    assert "_prod_safety_check" in src
    assert "ADMIN_PASSWORD" in src
    # Must delete both messages AND orphan threads
    assert "DELETE FROM conversation_messages" in src
    assert "DELETE FROM conversation_threads" in src
    # The legacy phrases the script targets
    assert "I'm having trouble processing your question" in src
    assert "I was unable to fully process your query" in src


# ---------------------------------------------------------------------------
# Frontend pins (hook + page + ChatContainer)
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_p5_ad_hook_filters_legacy_conversations():
    """The useAdvisoryHistory hook now HIDES conversations whose
    preview is a legacy fallback, rather than substituting placeholder
    text. Combined with the backend purge + persistence filter, this
    makes the orphan rows disappear cleanly."""
    src = HOOK.read_text()
    assert "LEGACY_FALLBACK_PHRASES" in src
    assert "I'm having trouble processing your question" in src
    assert "I was unable to fully process your query" in src
    assert "isLegacyFallback" in src
    # The filter must actually be applied to the conversation list
    # returned by the hook.
    assert "visibleConversations" in src
    assert "allConversations.filter" in src


@pytest.mark.regression
def test_p5_ad_page_drops_clean_preview_substitution():
    """The page must no longer rewrite legacy text into the
    '(earlier reply unavailable)' placeholder — those entries are now
    filtered out at the hook level."""
    src = PAGE.read_text()
    assert "cleanPreview" not in src
    # The placeholder substring must not appear in user-facing copy
    # anymore.
    assert "(earlier reply unavailable)" not in src


@pytest.mark.regression
def test_p5_ad_chat_container_propagates_stream_errors():
    """ChatContainer must call onStreamError on SSE failure so the
    parent can invalidate the conversations React Query cache."""
    src = CHAT_CONTAINER.read_text()
    assert "onStreamError" in src
    # The error path must invoke the callback.
    assert "onStreamError?.(error)" in src


@pytest.mark.regression
def test_p5_ad_advisory_page_wires_stream_error_to_refresh():
    """The Advisory page must pass handleStreamError → refreshConversations
    so a failed stream re-fetches the canonical sidebar."""
    src = PAGE.read_text()
    assert "handleStreamError" in src
    assert "refreshConversations()" in src
    assert "onStreamError={handleStreamError}" in src
