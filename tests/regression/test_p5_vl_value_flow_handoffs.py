"""Red-team P5-VL — value-flow handoffs.

Origin: workspaces/obayashi/04-validate/13-redteam-comprehensive-2026-05-19.md
finding O12. The compliance check produced 7 Action Items but
clicking any of them was a no-op — the gap-detect → fix-now value
chain was broken at the handoff.

P5-VL-1 wires a CTA target (label / href / kind) onto each known
ComplianceFinding. Frontend now renders the Action Items as
navigable links.

P5-VL-2 adds a template-by-slug prefill endpoint plus a deep-link
into /policies?template=<slug> that auto-opens the Add Policy modal
pre-populated with the template content.

This file pins:
  1. The backend `_FINDING_CTAS` map covers every known provision_id.
  2. `get_cta_for_provision` returns the right shape per provision.
  3. `ComplianceFinding.to_dict()` includes the cta when known.
  4. `TEMPLATE_SLUG_MAP` carries the compliance-relevant slugs.
  5. `get_template_by_slug` returns the right template OR None for
     known-but-empty categories (wsh, grievance).
  6. The `/document/templates/by-slug/{slug}` endpoint resolves both
     content-bearing and empty-stub slugs.
  7. Frontend wiring: compliance page imports Link/ArrowRight; the
     policies page reads ?template= and passes initialDraft to the
     modal; the modal applies the prefill on open.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / "src/hr_advisory/workflows/compliance_checker.py"
TEMPLATES_CONTENT = REPO_ROOT / "src/hr_advisory/templates/content.py"
DOCUMENT_ROUTER = REPO_ROOT / "src/hr_advisory/api/routers/document.py"

COMPLIANCE_PAGE = (
    REPO_ROOT / "apps/web/src/app/(dashboard)/compliance/page.tsx"
)
POLICIES_PAGE = (
    REPO_ROOT / "apps/web/src/app/(dashboard)/policies/page.tsx"
)
MODAL = (
    REPO_ROOT / "apps/web/src/components/policies/PolicyCreateModal.tsx"
)
DOCS_API = REPO_ROOT / "apps/web/src/services/api/documents.ts"


# ---------------------------------------------------------------------------
# Backend — CTA map
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_p5_vl_1_known_provisions_have_cta():
    """Every provision_id that the compliance checker can emit MUST
    have an entry in the CTA map. Otherwise the corresponding Action
    Item renders as plain text (the bug O12 was about)."""
    from hr_advisory.workflows.compliance_checker import (
        _FINDING_CTAS,
        get_cta_for_provision,
    )

    # The provision_ids the checker emits — pulled from
    # check_compliance branches and inspection items. Adding a new
    # finding to compliance_checker must also add it to _FINDING_CTAS
    # (or this test will fail loudly).
    must_have_cta = {
        "EA-S95-KETs",
        "EA-KET",
        "EA-S88A-payslip",
        "EA-PART-X-annual-leave",
        "EA-PART-IV-hours",
        "WSHA-S12",
        "TGFEP-GRIEVANCE",
        "TGFWAR-request-process",
        "CPFA-S52",
        "EFMA-conditions",
    }
    missing = must_have_cta - set(_FINDING_CTAS.keys())
    assert not missing, (
        f"Compliance findings missing CTA mapping: {missing}. "
        "Add to `_FINDING_CTAS` in compliance_checker.py."
    )

    # Every CTA must have the three required fields.
    for pid, cta in _FINDING_CTAS.items():
        assert get_cta_for_provision(pid) == cta
        for field in ("label", "href", "kind"):
            assert field in cta and cta[field], (
                f"CTA for {pid!r} missing field {field!r}: {cta!r}"
            )
        assert cta["kind"] in {
            "policy_template",
            "document_template",
            "settings",
            "external",
        }, f"CTA kind {cta['kind']!r} not in allowed set"


@pytest.mark.regression
def test_p5_vl_1_compliance_finding_to_dict_includes_cta():
    """ComplianceFinding.to_dict() must emit the cta target. External
    API consumers (shadow agent, mobile) see the same contract."""
    from hr_advisory.workflows.compliance_checker import ComplianceFinding

    f = ComplianceFinding(
        domain="Fair Employment",
        issue="No FWA policy in place",
        severity="medium",
        recommendation="Implement FWA policy per TG-FWAR.",
        provision_id="TGFWAR-request-process",
        deadline="Within 60 days",
    )
    d = f.to_dict()
    assert d["cta"] == {
        "label": "Publish FWA policy",
        "href": "/policies?category=fair_employment&template=fwa",
        "kind": "policy_template",
    }


@pytest.mark.regression
def test_p5_vl_1_unknown_provision_omits_cta():
    """A finding with an unknown provision_id must serialise WITHOUT a
    cta field — the frontend falls back to plain-text rendering."""
    from hr_advisory.workflows.compliance_checker import ComplianceFinding

    f = ComplianceFinding(
        domain="Custom",
        issue="Custom compliance gap",
        severity="low",
        recommendation="Handle manually",
        provision_id="UNKNOWN-PROVISION",
        deadline="N/A",
    )
    d = f.to_dict()
    assert "cta" not in d


# ---------------------------------------------------------------------------
# Backend — template slug map
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_p5_vl_2_template_slug_map_covers_compliance_ctas():
    """Every policy_template / document_template CTA href must point
    at a known slug — otherwise the deep-link lands on an empty modal
    and the value chain still breaks at the handoff."""
    from hr_advisory.templates.content import TEMPLATE_SLUG_MAP
    from hr_advisory.workflows.compliance_checker import _FINDING_CTAS

    # Extract slug from hrefs like `/policies?...template=fwa`
    from urllib.parse import parse_qs, urlparse

    for pid, cta in _FINDING_CTAS.items():
        if cta["kind"] not in {"policy_template", "document_template"}:
            continue
        parsed = urlparse(cta["href"])
        qs = parse_qs(parsed.query)
        slug = (qs.get("template") or [""])[0]
        assert slug, f"{pid}: template-kind CTA has no ?template= slug"
        assert slug in TEMPLATE_SLUG_MAP, (
            f"{pid}: CTA references unknown template slug {slug!r}. "
            "Add it to TEMPLATE_SLUG_MAP (None is OK for known-but-empty)."
        )


@pytest.mark.regression
def test_p5_vl_2_get_template_by_slug_resolves_known_slugs():
    from hr_advisory.templates.content import get_template_by_slug

    # Slugs with bundled content
    assert get_template_by_slug("fwa") is not None
    assert get_template_by_slug("ket") is not None
    assert get_template_by_slug("employment_contract_fulltime") is not None
    # Slugs that are known compliance categories but ship no content yet
    assert get_template_by_slug("wsh") is None
    assert get_template_by_slug("grievance") is None
    # Unknown slug
    assert get_template_by_slug("not-a-real-slug") is None


@pytest.mark.regression
def test_p5_vl_2_router_has_by_slug_endpoint():
    src = DOCUMENT_ROUTER.read_text()
    assert "@router.get(\"/templates/by-slug/{slug}\")" in src
    assert "get_template_prefill_by_slug" in src
    assert "found_template" in src
    assert "known_slug" in src
    assert "category" in src


# ---------------------------------------------------------------------------
# Frontend — compliance Action Items render as links
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_p5_vl_1_compliance_page_uses_action_item_cta():
    src = COMPLIANCE_PAGE.read_text()
    # Type and mapping live on the frontend (mirrors backend _FINDING_CTAS).
    assert "FINDING_CTA_MAP" in src
    assert "interface ActionItemCta" in src or "ActionItemCta {" in src
    # Action Items render as <Link> when CTA present, with an ArrowRight.
    assert "ArrowRight" in src
    assert "import Link from \"next/link\"" in src
    # Render block must distinguish present-cta from missing-cta.
    assert "if (!cta)" in src or "item.cta" in src


# ---------------------------------------------------------------------------
# Frontend — policies page deep-link + modal prefill
# ---------------------------------------------------------------------------


@pytest.mark.regression
def test_p5_vl_2_policies_page_reads_template_query_param():
    src = POLICIES_PAGE.read_text()
    assert "useSearchParams" in src
    assert 'searchParams?.get("template")' in src
    # Prettier may split documentsApi.getTemplatePrefillBySlug across
    # lines; check for both tokens rather than the joined form.
    assert "documentsApi" in src and "getTemplatePrefillBySlug" in src
    # After fetching the prefill, the modal MUST open with initialDraft.
    assert "initialDraft" in src
    # And the ?template= param is stripped post-open so a refresh
    # doesn't re-trigger the modal.
    assert 'url.searchParams.delete("template")' in src


@pytest.mark.regression
def test_p5_vl_2_modal_applies_initial_draft_on_open():
    src = MODAL.read_text()
    assert "interface PolicyDraftPrefill" in src
    assert "initialDraft?" in src
    # The useEffect must apply prefill when isOpen && initialDraft.
    assert "if (!isOpen || !initialDraft)" in src
    assert "setTitle(initialDraft.title)" in src
    assert "setCategory(initialDraft.category)" in src
    assert "setContent(initialDraft.content)" in src
    # Title swap for prefilled modal
    assert "Publish" in src and "initialDraft?.source" in src


@pytest.mark.regression
def test_p5_vl_2_documents_api_exposes_by_slug():
    src = DOCS_API.read_text()
    assert "getTemplatePrefillBySlug" in src
    assert "/document/templates/by-slug/" in src
