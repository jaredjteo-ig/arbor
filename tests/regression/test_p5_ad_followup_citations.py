"""Red-team P5-AD followup — advisory citations side-finding.

Origin: post-deploy walk on 2026-05-19 (after the bundled
RT3+P5-PL+P5-AD+P5-VL commit `080988c` shipped). The advisory CPF
question now correctly classifies as `domains: ["cpf"]` (the round-3
pre-classifier worked) but `provisions_cited` came back EMPTY in the
conversation history. The grounded answer still used the pre-seeded
KB context, but citations weren't populating.

Root cause traced to `_kb_search_provisions(domain="cpf")` filtering
`Domain.name == "cpf"` — but the prod KB stores Domain rows as
sub-areas ("CPF Contribution Rates", "CPF Wage Ceilings", "CPF
Allocation", "CPF Compliance") rather than the top-level domain.
Filter never matched → 0 hits → empty `kb_results_seen` →
`_extract_citations` returned [] → `provisions_cited` stayed empty
on the persisted message.

Fix:
  1. Lift the domain → Act.short_name mapping out of compliance.py
     into `hr_advisory.kb.domain_lookup` so the advisory engine can
     reuse it without importing a router module.
  2. Engine pre-seed now calls `provisions_for_domain(dom)` which
     resolves Act → Provision rows. The provision rows have a
     `section` field that `_extract_citations` keys on.
  3. Classifier output keys aligned with the canonical domain keys
     (cpf / employment_act / foreign_manpower / wsh /
     fair_employment / tax). Legacy spellings (efma / tafep /
     tax_iras) accepted via DOMAIN_ALIASES.

This file pins the four invariants behind the fix.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ENGINE = REPO_ROOT / "src/hr_advisory/agents/advisory_engine.py"
DOMAIN_LOOKUP = REPO_ROOT / "src/hr_advisory/kb/domain_lookup.py"
CLASSIFIER = REPO_ROOT / "src/hr_advisory/services/advisory_domain_classifier.py"
COMPLIANCE = REPO_ROOT / "src/hr_advisory/api/routers/compliance.py"


# ---------------------------------------------------------------------------
# domain_lookup module — canonical mapping exists
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_p5ad_followup_domain_lookup_exists():
    """The shared module must exist with the documented API."""
    from hr_advisory.kb import domain_lookup

    assert hasattr(domain_lookup, "DOMAIN_KEYS")
    assert hasattr(domain_lookup, "DOMAIN_ALIASES")
    assert hasattr(domain_lookup, "normalize_domain_key")
    assert hasattr(domain_lookup, "get_act_short_names")
    assert hasattr(domain_lookup, "provisions_for_domain")


@pytest.mark.regression
def test_p5ad_followup_canonical_keys_cover_six_domains():
    """The six regulatory domains the platform claims to cover must
    all be canonical keys."""
    from hr_advisory.kb.domain_lookup import DOMAIN_KEYS

    required = {
        "employment_act",
        "cpf",
        "foreign_manpower",
        "wsh",
        "fair_employment",
        "tax",
    }
    assert required <= set(DOMAIN_KEYS)


@pytest.mark.regression
def test_p5ad_followup_legacy_aliases_normalize():
    """The renamed classifier outputs (efma / tafep / tax_iras) must
    still normalise to the canonical keys."""
    from hr_advisory.kb.domain_lookup import normalize_domain_key

    assert normalize_domain_key("efma") == "foreign_manpower"
    assert normalize_domain_key("tafep") == "fair_employment"
    assert normalize_domain_key("tax_iras") == "tax"
    # Unknown stays as-is so caller can decide.
    assert normalize_domain_key("zzz") == "zzz"


# ---------------------------------------------------------------------------
# provisions_for_domain — Act-based lookup returns real rows
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_p5ad_followup_provisions_for_domain_routes_via_act():
    """For a known domain, the lookup must go Act → Provision rows.
    NOT the legacy `Domain.name == "cpf"` path which returns []."""
    from hr_advisory.kb import domain_lookup

    fake_acts = [{"id": 7, "short_name": "CPFA"}]
    fake_provisions = [
        {
            "id": 100,
            "source_act_id": 7,
            "section": "CPFA-S52",
            "title": "Late payment interest",
            "is_active": True,
        },
        {
            "id": 101,
            "source_act_id": 7,
            "section": "CPFA-S70",
            "title": "Contribution rates",
            "is_active": True,
        },
    ]

    def fake_list(model, filter_dict=None, **kwargs):
        if model == "Act" and filter_dict and filter_dict.get("short_name") == "CPFA":
            return fake_acts
        if model == "Provision":
            return fake_provisions
        return []

    with patch(
        "hr_advisory.services.dataflow_crud.list_records", side_effect=fake_list
    ):
        result = domain_lookup.provisions_for_domain("cpf", limit=10)

    assert len(result) == 2, result
    assert {r["section"] for r in result} == {"CPFA-S52", "CPFA-S70"}


@pytest.mark.regression
def test_p5ad_followup_provisions_for_domain_handles_alias():
    """`efma` must resolve to the same rows as `foreign_manpower`."""
    from hr_advisory.kb import domain_lookup

    fake_acts = [{"id": 11, "short_name": "EFMA"}]
    fake_provisions = [
        {"id": 200, "source_act_id": 11, "section": "EFMA-S5", "is_active": True}
    ]

    def fake_list(model, filter_dict=None, **kwargs):
        if model == "Act" and filter_dict and filter_dict.get("short_name") == "EFMA":
            return fake_acts
        if model == "Provision":
            return fake_provisions
        return []

    with patch(
        "hr_advisory.services.dataflow_crud.list_records", side_effect=fake_list
    ):
        via_alias = domain_lookup.provisions_for_domain("efma", limit=10)
        via_canonical = domain_lookup.provisions_for_domain(
            "foreign_manpower", limit=10
        )

    assert via_alias == via_canonical
    assert len(via_alias) == 1


@pytest.mark.regression
def test_p5ad_followup_provisions_for_unknown_domain_returns_empty():
    """Unknown domain → empty list (caller falls back to general LLM
    reasoning per the engine contract)."""
    from hr_advisory.kb import domain_lookup

    with patch("hr_advisory.services.dataflow_crud.list_records", return_value=[]):
        assert domain_lookup.provisions_for_domain("not-a-domain") == []


# ---------------------------------------------------------------------------
# Engine wiring — pre-seed routes through the shared lookup
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_p5ad_followup_engine_uses_shared_provisions_for_domain():
    """The engine must call `provisions_for_domain` (not the legacy
    `_search_kb_with_fallback(domain=...)`) for the pre-seed path."""
    src = ENGINE.read_text()
    assert "from hr_advisory.kb.domain_lookup import provisions_for_domain" in src
    assert "provisions_for_domain(dom, limit=3, query=query)" in src
    # And the pre-seed must STILL extend kb_results_seen so citation
    # extraction picks them up downstream.
    assert "kb_results_seen.extend(hits)" in src


@pytest.mark.regression
def test_p5ad_followup_engine_preseed_handles_provision_row_shape():
    """The pre-seed format string must read from provision-row fields
    (title / section / plain_summary), not the search_kb wrapper output
    fields (content / text). Otherwise pre-seed lines are blank."""
    src = ENGINE.read_text()
    assert 'h.get("section")' in src
    assert 'h.get("plain_summary")' in src or 'h.get("formal_text")' in src


# ---------------------------------------------------------------------------
# compliance.py refactor — uses the shared module
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_p5ad_followup_compliance_uses_shared_lookup():
    """compliance.py must import the shared module (DRY)."""
    src = COMPLIANCE.read_text()
    assert "from hr_advisory.kb.domain_lookup import" in src
    assert "_shared_provisions_for_domain" in src or "provisions_for_domain" in src
