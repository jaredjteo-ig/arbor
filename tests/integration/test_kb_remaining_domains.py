"""Integration tests for remaining domains KB content loading.

Validates that the remaining domains content bundle (CDCSA, WSHA, RRA,
WICA, IRAS, PDPA) loads correctly via KBContentPipeline and that all
provisions, applicability rules, practical examples, and cross-references
are stored properly.
"""

import pytest

from hr_advisory.kb.content.remaining_domains import get_bundle
from hr_advisory.kb.pipeline import KBContentPipeline
from hr_advisory.kb.validator import KBContentValidator

# -- helpers ----------------------------------------------------------


def _extract_records(result) -> list[dict]:
    """Normalize ListNode results to a plain list."""
    if isinstance(result, list):
        return result
    if isinstance(result, dict) and "records" in result:
        return result["records"]
    return []


# -- fixtures ---------------------------------------------------------


@pytest.fixture(scope="module")
def pipeline():
    return KBContentPipeline()


@pytest.fixture(scope="module")
def bundle():
    return get_bundle()


@pytest.fixture(scope="module")
def loaded(pipeline, bundle, _cleanup_cdcsa):
    """Load the remaining domains bundle once for all tests in this module."""
    return pipeline.bulk_load(bundle)


@pytest.fixture(scope="module")
def _cleanup_cdcsa(pipeline):
    """Clean up any existing CDCSA test data before and after the module."""
    _do_cleanup(pipeline)
    yield
    _do_cleanup(pipeline)


def _do_cleanup(pipeline):
    """Remove CDCSA test data using DataFlow workflow nodes."""
    # Find and delete CDCSA act and all related data
    act_result = pipeline._execute(
        "ActListNode", "find", {"filter": {"short_name": "CDCSA"}, "enable_cache": False}
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

        # Delete provision
        pipeline._execute("ProvisionDeleteNode", "del_prov", {"conditions": {"id": prov_id}})

    # Delete domains created for this bundle
    for domain_name in [
        "Family Leave",
        "Workplace Safety & Health",
        "Retirement & Re-employment",
        "Work Injury Compensation",
        "Tax Obligations",
        "Data Protection",
    ]:
        dom_result = pipeline._execute(
            "DomainListNode",
            "dom",
            {"filter": {"name": domain_name}, "enable_cache": False},
        )
        for dom in _extract_records(dom_result):
            pipeline._execute("DomainDeleteNode", "del_dom", {"conditions": {"id": dom["id"]}})

    # Delete the act
    pipeline._execute("ActDeleteNode", "del_act", {"conditions": {"id": act_id}})


# -- bundle structure tests -------------------------------------------


class TestBundleStructure:
    """Verify the bundle is well-formed before loading."""

    def test_bundle_has_act(self, bundle):
        assert bundle["act"]["short_name"] == "CDCSA"
        assert bundle["act"]["title"] == "Child Development Co-Savings Act"

    def test_bundle_has_six_domains(self, bundle):
        assert len(bundle["domains"]) == 6
        names = {d["name"] for d in bundle["domains"]}
        assert "Family Leave" in names
        assert "Workplace Safety & Health" in names
        assert "Retirement & Re-employment" in names
        assert "Work Injury Compensation" in names
        assert "Tax Obligations" in names
        assert "Data Protection" in names

    def test_bundle_has_provisions(self, bundle):
        assert len(bundle["provisions"]) == 16

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
        assert len(bundle["cross_references"]) == 3

    def test_bundle_validates_cleanly(self, bundle):
        validator = KBContentValidator()
        result = validator.validate_bundle(bundle)
        assert result["errors"] == [], f"Bundle validation errors: {result['errors']}"

    def test_family_leave_provisions_have_correct_sections(self, bundle):
        """Family leave provisions should use CDCSA- prefix."""
        family_sections = {
            p["section"] for p in bundle["provisions"] if p["domain_name"] == "Family Leave"
        }
        expected = {
            "CDCSA-ML",
            "CDCSA-ML-RESIGN",
            "CDCSA-PL",
            "CDCSA-SPL",
            "CDCSA-CL",
            "CDCSA-ICL",
            "CDCSA-AL",
        }
        assert (
            family_sections == expected
        ), f"Expected family leave sections {expected}, got {family_sections}"

    def test_wsh_provisions_have_correct_sections(self, bundle):
        """WSH provisions should use WSHA- prefix."""
        wsh_sections = {
            p["section"]
            for p in bundle["provisions"]
            if p["domain_name"] == "Workplace Safety & Health"
        }
        expected = {"WSHA-S12", "WSHA-REPORT", "WSHA-BIZSAFE"}
        assert wsh_sections == expected, f"Expected WSH sections {expected}, got {wsh_sections}"

    def test_retirement_provisions_have_correct_sections(self, bundle):
        """Retirement provisions should use RRA- prefix."""
        rra_sections = {
            p["section"]
            for p in bundle["provisions"]
            if p["domain_name"] == "Retirement & Re-employment"
        }
        expected = {"RRA-S4", "RRA-S7"}
        assert rra_sections == expected, f"Expected RRA sections {expected}, got {rra_sections}"

    def test_provision_count_per_domain(self, bundle):
        """Verify provision counts match expectations per domain."""
        domain_counts = {}
        for prov in bundle["provisions"]:
            domain = prov["domain_name"]
            domain_counts[domain] = domain_counts.get(domain, 0) + 1

        assert domain_counts["Family Leave"] == 7
        assert domain_counts["Workplace Safety & Health"] == 3
        assert domain_counts["Retirement & Re-employment"] == 2
        assert domain_counts["Work Injury Compensation"] == 1
        assert domain_counts["Tax Obligations"] == 2
        assert domain_counts["Data Protection"] == 1

    def test_bundle_has_no_rate_tables(self, bundle):
        """This bundle should have no rate tables."""
        assert bundle["rate_tables"] == []


# -- loading tests ----------------------------------------------------


class TestRemainingDomainsLoading:
    """Test that the bundle loads successfully into the database."""

    def test_act_loaded(self, loaded):
        assert loaded["act"] is not None
        assert loaded["act"]["short_name"] == "CDCSA"
        assert loaded["act"]["id"] is not None

    def test_domains_loaded(self, loaded):
        assert len(loaded["domains"]) == 6
        for domain in loaded["domains"]:
            assert domain["id"] is not None

    def test_provisions_loaded(self, loaded):
        assert len(loaded["provisions"]) == 16
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
        assert len(loaded["cross_references"]) == 3
        for xref in loaded["cross_references"]:
            assert xref["id"] is not None


# -- data integrity tests ---------------------------------------------


class TestRemainingDomainsDataIntegrity:
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

    def test_maternity_leave_provision_content(self, loaded):
        """Spot-check: CDCSA-ML provision has expected content."""
        ml = next((p for p in loaded["provisions"] if p["section"] == "CDCSA-ML"), None)
        assert ml is not None, "CDCSA-ML provision should exist"
        assert "Maternity Leave" in ml["title"]
        assert ml["authority_level"] == "statute"
        assert "16 weeks" in ml["plain_summary"]

    def test_paternity_leave_provision_content(self, loaded):
        """Spot-check: CDCSA-PL has correct paternity leave content."""
        pl = next((p for p in loaded["provisions"] if p["section"] == "CDCSA-PL"), None)
        assert pl is not None, "CDCSA-PL provision should exist"
        assert "Paternity Leave" in pl["title"]
        assert "4 weeks" in pl["plain_summary"]

    def test_childcare_leave_provision_content(self, loaded):
        """Spot-check: CDCSA-CL has correct childcare leave content."""
        cl = next((p for p in loaded["provisions"] if p["section"] == "CDCSA-CL"), None)
        assert cl is not None, "CDCSA-CL provision should exist"
        assert "Childcare Leave" in cl["title"]
        assert "6 days" in cl["plain_summary"]

    def test_infant_care_leave_provision_content(self, loaded):
        """Spot-check: CDCSA-ICL has correct infant care leave content."""
        icl = next((p for p in loaded["provisions"] if p["section"] == "CDCSA-ICL"), None)
        assert icl is not None, "CDCSA-ICL provision should exist"
        assert "Infant Care Leave" in icl["title"]
        assert "6" in icl["plain_summary"]

    def test_employer_general_duties_provision_content(self, loaded):
        """Spot-check: WSHA-S12 has correct WSH content."""
        s12 = next((p for p in loaded["provisions"] if p["section"] == "WSHA-S12"), None)
        assert s12 is not None, "WSHA-S12 provision should exist"
        assert "Employer General Duties" in s12["title"]
        assert "$500,000" in s12["plain_summary"]

    def test_retirement_age_provision_content(self, loaded):
        """Spot-check: RRA-S4 has correct retirement age content."""
        s4 = next((p for p in loaded["provisions"] if p["section"] == "RRA-S4"), None)
        assert s4 is not None, "RRA-S4 provision should exist"
        assert "Retirement Age" in s4["title"]
        assert "63" in s4["plain_summary"]

    def test_re_employment_provision_content(self, loaded):
        """Spot-check: RRA-S7 has correct re-employment content."""
        s7 = next((p for p in loaded["provisions"] if p["section"] == "RRA-S7"), None)
        assert s7 is not None, "RRA-S7 provision should exist"
        assert "Re-employment" in s7["title"]
        assert "68" in s7["plain_summary"]

    def test_wica_provision_content(self, loaded):
        """Spot-check: WICA-S3 has correct work injury content."""
        s3 = next((p for p in loaded["provisions"] if p["section"] == "WICA-S3"), None)
        assert s3 is not None, "WICA-S3 provision should exist"
        assert "Work Injuries" in s3["title"]

    def test_tax_filing_provision_content(self, loaded):
        """Spot-check: IRAS-IR8A has correct tax filing content."""
        ir8a = next((p for p in loaded["provisions"] if p["section"] == "IRAS-IR8A"), None)
        assert ir8a is not None, "IRAS-IR8A provision should exist"
        assert "Tax Filing" in ir8a["title"]
        assert "1 March" in ir8a["plain_summary"]

    def test_tax_clearance_provision_content(self, loaded):
        """Spot-check: IRAS-IR21 has correct tax clearance content."""
        ir21 = next((p for p in loaded["provisions"] if p["section"] == "IRAS-IR21"), None)
        assert ir21 is not None, "IRAS-IR21 provision should exist"
        assert "Tax Clearance" in ir21["title"]
        assert "1 month" in ir21["plain_summary"]

    def test_pdpa_provision_content(self, loaded):
        """Spot-check: PDPA-EMP has correct data protection content."""
        pdpa = next((p for p in loaded["provisions"] if p["section"] == "PDPA-EMP"), None)
        assert pdpa is not None, "PDPA-EMP provision should exist"
        assert "Data Protection" in pdpa["title"]
        assert "3 business days" in pdpa["plain_summary"]

    def test_cross_reference_maternity_to_spl(self, loaded):
        """Cross-reference CDCSA-ML -> CDCSA-SPL should exist."""
        ml = next((p for p in loaded["provisions"] if p["section"] == "CDCSA-ML"), None)
        spl = next((p for p in loaded["provisions"] if p["section"] == "CDCSA-SPL"), None)
        assert ml is not None and spl is not None

        xref = next(
            (
                x
                for x in loaded["cross_references"]
                if x["source_provision_id"] == ml["id"] and x["target_provision_id"] == spl["id"]
            ),
            None,
        )
        assert xref is not None, "Cross-reference CDCSA-ML -> CDCSA-SPL should exist"
        assert xref["relationship_type"] == "supplements"

    def test_cross_reference_childcare_to_infant_care(self, loaded):
        """Cross-reference CDCSA-CL -> CDCSA-ICL should exist."""
        cl = next((p for p in loaded["provisions"] if p["section"] == "CDCSA-CL"), None)
        icl = next((p for p in loaded["provisions"] if p["section"] == "CDCSA-ICL"), None)
        assert cl is not None and icl is not None

        xref = next(
            (
                x
                for x in loaded["cross_references"]
                if x["source_provision_id"] == cl["id"] and x["target_provision_id"] == icl["id"]
            ),
            None,
        )
        assert xref is not None, "Cross-reference CDCSA-CL -> CDCSA-ICL should exist"
        assert xref["relationship_type"] == "supplements"

    def test_cross_reference_retirement_to_reemployment(self, loaded):
        """Cross-reference RRA-S4 -> RRA-S7 should exist."""
        s4 = next((p for p in loaded["provisions"] if p["section"] == "RRA-S4"), None)
        s7 = next((p for p in loaded["provisions"] if p["section"] == "RRA-S7"), None)
        assert s4 is not None and s7 is not None

        xref = next(
            (
                x
                for x in loaded["cross_references"]
                if x["source_provision_id"] == s4["id"] and x["target_provision_id"] == s7["id"]
            ),
            None,
        )
        assert xref is not None, "Cross-reference RRA-S4 -> RRA-S7 should exist"
        assert xref["relationship_type"] == "supplements"


# -- idempotency tests ------------------------------------------------


class TestRemainingDomainsIdempotency:
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


# -- validator tests --------------------------------------------------


class TestRemainingDomainsValidation:
    """Run the validator against the loaded remaining domains data."""

    def test_no_provisions_without_domains(self, loaded):
        validator = KBContentValidator()
        all_provs_raw = validator._execute(
            "ProvisionListNode", "all", {"filter": {}, "enable_cache": False, "limit": 10000}
        )
        all_provs = _extract_records(all_provs_raw)
        cdcsa_prov_ids = {p["id"] for p in loaded["provisions"]}
        cdcsa_provs_without_domain = [
            p for p in all_provs if p["id"] in cdcsa_prov_ids and not p.get("domain_id")
        ]
        assert len(cdcsa_provs_without_domain) == 0

    def test_quality_report_includes_remaining_domains(self, loaded):
        validator = KBContentValidator()
        report = validator.generate_quality_report()
        assert report["total_provisions"] >= len(loaded["provisions"])
        assert len(report["provisions_per_domain"]) >= 1
