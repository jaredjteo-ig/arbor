"""Integration tests for TAFEP KB content loading.

Validates that the TGFEP content bundle loads correctly via KBContentPipeline
and that all provisions, applicability rules, practical examples, and
cross-references are stored properly.
"""

import pytest

from hr_advisory.kb.content.tafep import get_bundle
from hr_advisory.kb.pipeline import KBContentPipeline
from hr_advisory.kb.validator import KBContentValidator

# ── helpers ──────────────────────────────────────────────────────────


def _extract_records(result) -> list[dict]:
    """Normalize ListNode results to a plain list."""
    if isinstance(result, list):
        return result
    if isinstance(result, dict) and "records" in result:
        return result["records"]
    return []


# ── fixtures ─────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def pipeline():
    return KBContentPipeline()


@pytest.fixture(scope="module")
def bundle():
    return get_bundle()


@pytest.fixture(scope="module")
def loaded(pipeline, bundle, _cleanup_tafep):
    """Load the TAFEP bundle once for all tests in this module."""
    return pipeline.bulk_load(bundle)


@pytest.fixture(scope="module")
def _cleanup_tafep(pipeline):
    """Clean up any existing TAFEP test data before and after the module."""
    _do_cleanup(pipeline)
    yield
    _do_cleanup(pipeline)


def _do_cleanup(pipeline):
    """Remove TAFEP test data using raw SQL via DataFlow."""
    # Find and delete TGFEP act and all related data
    act_result = pipeline._execute(
        "ActListNode", "find", {"filter": {"short_name": "TGFEP"}, "enable_cache": False}
    )
    acts = _extract_records(act_result)

    if not acts:
        return

    act_id = acts[0]["id"]

    # Delete in dependency order: examples, rules, xrefs -> provisions -> domains -> act
    prov_result = pipeline._execute(
        "ProvisionListNode",
        "provs",
        {"filter": {"source_act_id": act_id}, "enable_cache": False, "limit": 10000},
    )
    provisions = _extract_records(prov_result)
    prov_ids = [p["id"] for p in provisions]

    for prov_id in prov_ids:
        # Delete practical examples
        ex_result = pipeline._execute(
            "PracticalExampleListNode",
            "ex",
            {"filter": {"provision_id": prov_id}, "enable_cache": False, "limit": 10000},
        )
        for ex in _extract_records(ex_result):
            pipeline._execute(
                "PracticalExampleDeleteNode", "del_ex", {"conditions": {"id": ex["id"]}}
            )

        # Delete applicability rules
        rule_result = pipeline._execute(
            "ApplicabilityRuleListNode",
            "rules",
            {"filter": {"provision_id": prov_id}, "enable_cache": False, "limit": 10000},
        )
        for rule in _extract_records(rule_result):
            pipeline._execute(
                "ApplicabilityRuleDeleteNode", "del_rule", {"conditions": {"id": rule["id"]}}
            )

        # Delete cross-references (source or target)
        xref_result = pipeline._execute(
            "CrossReferenceListNode",
            "xrefs_src",
            {"filter": {"source_provision_id": prov_id}, "enable_cache": False, "limit": 10000},
        )
        for xref in _extract_records(xref_result):
            pipeline._execute(
                "CrossReferenceDeleteNode", "del_xref", {"conditions": {"id": xref["id"]}}
            )

        xref_result2 = pipeline._execute(
            "CrossReferenceListNode",
            "xrefs_tgt",
            {"filter": {"target_provision_id": prov_id}, "enable_cache": False, "limit": 10000},
        )
        for xref in _extract_records(xref_result2):
            pipeline._execute(
                "CrossReferenceDeleteNode", "del_xref2", {"conditions": {"id": xref["id"]}}
            )

        # Delete provision (hard delete via DeleteNode)
        pipeline._execute("ProvisionDeleteNode", "del_prov", {"conditions": {"id": prov_id}})

    # Delete domains created for TAFEP
    for domain_name in [
        "Fair Recruitment",
        "Fair Employment Practices",
        "Flexible Work Arrangements",
        "Wrongful Dismissal Guidelines",
        "Workplace Fairness Legislation",
    ]:
        dom_result = pipeline._execute(
            "DomainListNode",
            "dom",
            {"filter": {"name": domain_name}, "enable_cache": False, "limit": 10000},
        )
        for dom in _extract_records(dom_result):
            pipeline._execute("DomainDeleteNode", "del_dom", {"conditions": {"id": dom["id"]}})

    # Delete the act
    pipeline._execute("ActDeleteNode", "del_act", {"conditions": {"id": act_id}})


# ── bundle structure tests ───────────────────────────────────────────


class TestBundleStructure:
    """Verify the bundle is well-formed before loading."""

    def test_bundle_has_act(self, bundle):
        assert bundle["act"]["short_name"] == "TGFEP"
        assert bundle["act"]["title"] == "Tripartite Guidelines on Fair Employment Practices"

    def test_bundle_has_five_domains(self, bundle):
        assert len(bundle["domains"]) == 5
        names = {d["name"] for d in bundle["domains"]}
        assert "Fair Recruitment" in names
        assert "Fair Employment Practices" in names
        assert "Flexible Work Arrangements" in names
        assert "Wrongful Dismissal Guidelines" in names
        assert "Workplace Fairness Legislation" in names

    def test_bundle_has_provisions(self, bundle):
        assert len(bundle["provisions"]) == 9

    def test_every_provision_has_required_fields(self, bundle):
        for prov in bundle["provisions"]:
            assert prov.get("section"), f"Missing section in provision: {prov.get('title')}"
            assert prov.get("title"), f"Missing title in provision: {prov.get('section')}"
            assert prov.get("formal_text"), f"Missing formal_text in {prov['section']}"
            assert prov.get("plain_summary"), f"Missing plain_summary in {prov['section']}"
            assert prov.get("authority_level"), f"Missing authority_level in {prov['section']}"
            assert prov.get("domain_name"), f"Missing domain_name in {prov['section']}"

    def test_every_provision_has_interpretation_notes(self, bundle):
        for prov in bundle["provisions"]:
            assert prov.get(
                "interpretation_notes"
            ), f"Missing interpretation_notes in {prov['section']}"

    def test_bundle_has_cross_references(self, bundle):
        assert len(bundle["cross_references"]) == 6

    def test_bundle_validates_cleanly(self, bundle):
        validator = KBContentValidator()
        result = validator.validate_bundle(bundle)
        assert result["errors"] == [], f"Bundle validation errors: {result['errors']}"

    def test_act_authority_type_is_tripartite_guideline(self, bundle):
        assert bundle["act"]["authority_type"] == "tripartite_guideline"

    def test_act_issuing_body(self, bundle):
        assert bundle["act"]["issuing_body"] == (
            "Tripartite Alliance for Fair and Progressive Employment Practices"
        )

    def test_fwa_provisions_have_correct_effective_date(self, bundle):
        """TG-FWAR provisions must have 1 Dec 2024 effective date."""
        fwar_sections = {"TG-FWAR-REQ", "TG-FWAR-TYPES", "TG-FWAR-REJECT"}
        for prov in bundle["provisions"]:
            if prov["section"] in fwar_sections:
                assert prov["effective_date"] == "2024-12-01", (
                    f"{prov['section']} should have effective_date 2024-12-01, "
                    f"got {prov['effective_date']}"
                )

    def test_wfl_2026_has_no_effective_date(self, bundle):
        """WFL-2026 is upcoming and must have no effective_date."""
        wfl = next(p for p in bundle["provisions"] if p["section"] == "WFL-2026")
        assert (
            wfl["effective_date"] is None
        ), "WFL-2026 should have effective_date=None (upcoming legislation)"

    def test_wfl_2026_authority_level_is_advisory(self, bundle):
        """WFL-2026 is upcoming and must be flagged as advisory."""
        wfl = next(p for p in bundle["provisions"] if p["section"] == "WFL-2026")
        assert wfl["authority_level"] == "advisory"

    def test_wfl_2026_interpretation_notes_flag_upcoming(self, bundle):
        """WFL-2026 interpretation_notes must flag it as not yet in force."""
        wfl = next(p for p in bundle["provisions"] if p["section"] == "WFL-2026")
        notes = wfl["interpretation_notes"].upper()
        assert (
            "UPCOMING" in notes or "NOT YET IN FORCE" in notes
        ), "WFL-2026 interpretation_notes must indicate it is upcoming/not yet in force"


# ── loading tests ────────────────────────────────────────────────────


class TestTAFEPLoading:
    """Test that the bundle loads successfully into the database."""

    def test_act_loaded(self, loaded):
        assert loaded["act"] is not None
        assert loaded["act"]["short_name"] == "TGFEP"
        assert loaded["act"]["id"] is not None

    def test_domains_loaded(self, loaded):
        assert len(loaded["domains"]) == 5
        for domain in loaded["domains"]:
            assert domain["id"] is not None

    def test_provisions_loaded(self, loaded):
        assert len(loaded["provisions"]) == 9
        for prov in loaded["provisions"]:
            assert prov["id"] is not None
            assert prov["source_act_id"] == loaded["act"]["id"]

    def test_applicability_rules_loaded(self, loaded):
        assert len(loaded["applicability_rules"]) > 0
        for rule in loaded["applicability_rules"]:
            assert rule["id"] is not None

    def test_practical_examples_loaded(self, loaded):
        assert len(loaded["practical_examples"]) > 0
        for example in loaded["practical_examples"]:
            assert example["id"] is not None

    def test_cross_references_loaded(self, loaded):
        assert len(loaded["cross_references"]) == 6
        for xref in loaded["cross_references"]:
            assert xref["id"] is not None


# ── data integrity tests ────────────────────────────────────────────


class TestTAFEPDataIntegrity:
    """Verify loaded data can be queried back correctly."""

    def test_provisions_assigned_to_correct_domains(self, loaded, pipeline):
        """Each provision's domain_id maps to the expected domain name."""
        domain_ids = {d["name"]: d["id"] for d in loaded["domains"]}

        for prov in loaded["provisions"]:
            assert (
                prov.get("domain_id") is not None
            ), f"Provision {prov['section']} has no domain_id"
            assert (
                prov["domain_id"] in domain_ids.values()
            ), f"Provision {prov['section']} has unknown domain_id={prov['domain_id']}"

    def test_cross_references_link_valid_provisions(self, loaded):
        """All cross-reference source and target IDs exist in loaded provisions."""
        prov_ids = {p["id"] for p in loaded["provisions"]}
        for xref in loaded["cross_references"]:
            assert (
                xref["source_provision_id"] in prov_ids
            ), f"Cross-ref source {xref['source_provision_id']} not in provisions"
            assert (
                xref["target_provision_id"] in prov_ids
            ), f"Cross-ref target {xref['target_provision_id']} not in provisions"

    def test_fair_recruitment_provision_content(self, loaded):
        """Spot-check: TGFEP-RECRUIT has expected content."""
        recruit = next((p for p in loaded["provisions"] if p["section"] == "TGFEP-RECRUIT"), None)
        assert recruit is not None
        assert "Fair Recruitment" in recruit["title"]
        assert recruit["authority_level"] == "tripartite_guideline"

    def test_merit_based_provision_content(self, loaded):
        """Spot-check: TGFEP-MERIT has correct merit-based content."""
        merit = next((p for p in loaded["provisions"] if p["section"] == "TGFEP-MERIT"), None)
        assert merit is not None
        assert "Merit" in merit["title"]
        assert "merit" in merit["plain_summary"].lower()

    def test_fwa_request_provision_content(self, loaded):
        """Spot-check: TG-FWAR-REQ has correct FWA request content."""
        fwar = next((p for p in loaded["provisions"] if p["section"] == "TG-FWAR-REQ"), None)
        assert fwar is not None
        assert "FWA" in fwar["title"]
        assert "2 months" in fwar["plain_summary"]

    def test_fwa_types_provision_content(self, loaded):
        """Spot-check: TG-FWAR-TYPES lists the three FWA categories."""
        types = next((p for p in loaded["provisions"] if p["section"] == "TG-FWAR-TYPES"), None)
        assert types is not None
        assert "Flexi-place" in types["plain_summary"]
        assert "Flexi-time" in types["plain_summary"]
        assert "Flexi-load" in types["plain_summary"]

    def test_wrongful_dismissal_provision_content(self, loaded):
        """Spot-check: TG-WD has wrongful dismissal content with TADM reference."""
        wd = next((p for p in loaded["provisions"] if p["section"] == "TG-WD"), None)
        assert wd is not None
        assert "Wrongful Dismissal" in wd["title"]
        assert "TADM" in wd["plain_summary"]

    def test_grievance_provision_content(self, loaded):
        """Spot-check: TGFEP-GRIEVANCE has grievance handling content."""
        grievance = next(
            (p for p in loaded["provisions"] if p["section"] == "TGFEP-GRIEVANCE"), None
        )
        assert grievance is not None
        assert "Grievance" in grievance["title"]
        assert "retaliation" in grievance["plain_summary"].lower()

    def test_wfl_2026_provision_content(self, loaded):
        """Spot-check: WFL-2026 has upcoming legislation content."""
        wfl = next((p for p in loaded["provisions"] if p["section"] == "WFL-2026"), None)
        assert wfl is not None
        assert "Upcoming" in wfl["title"]
        assert wfl["authority_level"] == "advisory"
        assert "25" in wfl["plain_summary"]

    def test_non_discriminatory_terms_provision_content(self, loaded):
        """Spot-check: TGFEP-TERMS has equal pay content."""
        terms = next((p for p in loaded["provisions"] if p["section"] == "TGFEP-TERMS"), None)
        assert terms is not None
        assert "equal" in terms["plain_summary"].lower()

    def test_fwa_reject_provision_content(self, loaded):
        """Spot-check: TG-FWAR-REJECT references blanket policies."""
        reject = next((p for p in loaded["provisions"] if p["section"] == "TG-FWAR-REJECT"), None)
        assert reject is not None
        assert "blanket" in reject["plain_summary"].lower()


# ── idempotency tests ───────────────────────────────────────────────


class TestTAFEPIdempotency:
    """Verify loading the same bundle twice doesn't create duplicates."""

    def test_reloading_act_returns_existing(self, loaded, pipeline, bundle):
        """Loading the same act again returns the existing record."""
        act2 = pipeline.load_act(bundle["act"])
        assert act2["id"] == loaded["act"]["id"]

    def test_reloading_domain_returns_existing(self, loaded, pipeline, bundle):
        """Loading the same domain again returns the existing record."""
        for i, domain_data in enumerate(bundle["domains"]):
            dom2 = pipeline.load_domain(domain_data)
            assert dom2["id"] == loaded["domains"][i]["id"]


# ── validator tests ──────────────────────────────────────────────────


class TestTAFEPValidation:
    """Run the validator against the loaded TAFEP data."""

    def test_no_provisions_without_domains(self, loaded):
        validator = KBContentValidator()
        all_provs_raw = validator._execute(
            "ProvisionListNode", "all", {"filter": {}, "enable_cache": False, "limit": 10000}
        )
        all_provs = validator._extract_records(all_provs_raw)
        tafep_prov_ids = {p["id"] for p in loaded["provisions"]}
        tafep_provs_without_domain = [
            p for p in all_provs if p["id"] in tafep_prov_ids and not p.get("domain_id")
        ]
        assert len(tafep_provs_without_domain) == 0

    def test_quality_report_includes_tafep_domains(self, loaded):
        validator = KBContentValidator()
        report = validator.generate_quality_report()
        assert report["total_provisions"] >= len(loaded["provisions"])
        # At least some TAFEP domains should appear
        assert len(report["provisions_per_domain"]) >= 1
