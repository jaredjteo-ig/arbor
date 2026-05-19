"""Red-team round-3 — advisory pre-retrieval domain classifier (P1).

Origin: workspaces/obayashi/04-validate/13-redteam-comprehensive-2026-05-19.md
finding O2 / X2 / C3. Live walk: "How do I calculate CPF
contributions?" came back as `domains: ["general"]` with no
citations and a stale answer about the OW ceiling.

This file pins:
  - The classifier maps obvious CPF / EA / EFMA / WSH / TAFEP / Tax
    queries to the correct domain(s).
  - The engine is wired to call classify_domains, inject pre-fetched
    KB hits as a system message, and union the detected domains
    into the final response.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ADV_ENGINE = REPO_ROOT / "src" / "hr_advisory" / "agents" / "advisory_engine.py"


# ---------------------------------------------------------------------------
# classify_domains — deterministic mapping
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_redteam3_classifier_detects_cpf_question():
    from hr_advisory.services.advisory_domain_classifier import classify_domains

    # The exact query from the live walk that fell through to "general".
    assert classify_domains("How do I calculate CPF contributions?") == ["cpf"]


@pytest.mark.regression
def test_redteam3_classifier_detects_ow_ceiling_question():
    from hr_advisory.services.advisory_domain_classifier import classify_domains

    # Wording that triggered the stale "$8,000 by 2026" answer.
    assert classify_domains("What is the OW ceiling for 2026?") == ["cpf"]


@pytest.mark.regression
def test_redteam3_classifier_detects_cross_domain():
    """A CPF/foreign-manpower-spanning question must return both domains so
    the engine pre-fetches from both KBs.

    Domain keys aligned with kb/domain_lookup.py canonical names
    (post-2026-05-19 followup). Legacy callers using "efma" / "tafep" /
    "tax_iras" continue to work via DOMAIN_ALIASES normalisation.
    """
    from hr_advisory.services.advisory_domain_classifier import classify_domains

    detected = classify_domains(
        "What's the CPF treatment for a foreign worker on an S Pass?"
    )
    assert "cpf" in detected
    assert "foreign_manpower" in detected


@pytest.mark.regression
def test_redteam3_classifier_detects_each_domain():
    """Spot-check the 6 regulatory domains the platform claims to cover.
    Canonical keys per kb/domain_lookup.DOMAIN_KEYS."""
    from hr_advisory.services.advisory_domain_classifier import classify_domains

    assert "employment_act" in classify_domains("notice period under the Employment Act")
    assert "foreign_manpower" in classify_domains("foreign worker quota for services sector")
    assert "wsh" in classify_domains("workplace safety policy")
    assert "fair_employment" in classify_domains("Workplace Fairness Act discrimination claim")
    assert "tax" in classify_domains("IR8A filing deadline")


@pytest.mark.regression
def test_redteam3_legacy_aliases_normalize_to_canonical():
    """Backward-compat: callers that pass `efma` / `tafep` / `tax_iras`
    must still land on the canonical KB lookup. Pinned because the
    P5-AD-followup rename broke `_kb_search_provisions(domain=...)` flow
    on prod — `provisions_for_domain` MUST accept both spellings."""
    from hr_advisory.kb.domain_lookup import normalize_domain_key, get_act_short_names

    assert normalize_domain_key("efma") == "foreign_manpower"
    assert normalize_domain_key("tafep") == "fair_employment"
    assert normalize_domain_key("tax_iras") == "tax"
    # And the Act lookup works either way:
    assert get_act_short_names("efma") == ["EFMA"]
    assert get_act_short_names("foreign_manpower") == ["EFMA"]


@pytest.mark.regression
def test_redteam3_classifier_empty_on_unrelated_query():
    """If no keyword matches, return empty — let the LLM use general
    reasoning + force-search_kb policy upstream."""
    from hr_advisory.services.advisory_domain_classifier import classify_domains

    assert classify_domains("Tell me a joke") == []


# ---------------------------------------------------------------------------
# Engine wiring — source-level pins
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_redteam3_engine_imports_classifier():
    """The engine must call classify_domains before the LLM turn."""
    src = ADV_ENGINE.read_text()
    assert (
        "from hr_advisory.services.advisory_domain_classifier import" in src
        and "classify_domains" in src
    ), "advisory_engine.py must import classify_domains."


@pytest.mark.regression
def test_redteam3_engine_preseeds_kb_into_system_message():
    """When domains are detected, the engine must inject the pre-fetched
    KB content as a system message so the LLM has grounding from turn 1."""
    src = ADV_ENGINE.read_text()
    assert "Relevant Singapore-statute provisions" in src
    assert "_search_kb_with_fallback" in src
    # The pre-seeded provisions must be tracked in kb_results_seen so
    # citation extraction picks them up even when the LLM doesn't call
    # search_kb itself.
    assert "kb_results_seen.extend(hits)" in src


@pytest.mark.regression
def test_redteam3_engine_unions_detected_domains_into_response():
    """The final 'domains' list returned to the API must be the union of
    (a) detected_domains from the classifier and (b) the domains the LLM
    actually searched. Otherwise the CPF question that the LLM didn't
    explicitly search would still come back as ["general"]."""
    src = ADV_ENGINE.read_text()
    assert "detected_domains" in src
    # The union expression must appear in the response builder.
    assert "domains_from_llm | set(detected_domains)" in src
