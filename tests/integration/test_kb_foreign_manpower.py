"""Integration tests for Foreign Manpower (EFMA) KB content loading.

Validates that the EFMA content bundle loads correctly via KBContentPipeline
and that all provisions, applicability rules, practical examples,
cross-references, and rate tables are stored properly.
"""

import pytest

from hr_advisory.kb.content.foreign_manpower import get_bundle
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
def loaded(pipeline, bundle, _cleanup_efma):
    """Load the EFMA bundle once for all tests in this module."""
    return pipeline.bulk_load(bundle)


@pytest.fixture(scope="module")
def _cleanup_efma(pipeline):
    """Clean up any existing EFMA test data before and after the module."""
    _do_cleanup(pipeline)
    yield
    _do_cleanup(pipeline)


def _do_cleanup(pipeline):
    """Remove EFMA test data using DataFlow workflow nodes."""
    # Find EFMA act
    act_result = pipeline._execute(
        "ActListNode", "find", {"filter": {"short_name": "EFMA"}, "enable_cache": False}
    )
    acts = _extract_records(act_result)

    if not acts:
        return

    act_id = acts[0]["id"]

    # Find all provisions belonging to EFMA
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

    # Delete rate tables associated with EFMA (foreign_worker_levy type)
    rate_result = pipeline._execute(
        "RateTableListNode",
        "rates",
        {"filter": {"table_type": "foreign_worker_levy"}, "enable_cache": False, "limit": 10000},
    )
    for rate in _extract_records(rate_result):
        pipeline._execute("RateTableDeleteNode", "del_rate", {"conditions": {"id": rate["id"]}})

    # Delete domains created for EFMA
    for domain_name in [
        "Work Pass Types",
        "Foreign Worker Quotas",
        "Foreign Worker Levy",
        "COMPASS Framework",
        "Employer Obligations",
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


# -- bundle structure tests -------------------------------------------


class TestBundleStructure:
    """Verify the bundle is well-formed before loading."""

    def test_bundle_has_act(self, bundle):
        assert bundle["act"]["short_name"] == "EFMA"
        assert bundle["act"]["title"] == "Employment of Foreign Manpower Act"

    def test_bundle_has_five_domains(self, bundle):
        assert len(bundle["domains"]) == 5
        names = {d["name"] for d in bundle["domains"]}
        assert "Work Pass Types" in names
        assert "Foreign Worker Quotas" in names
        assert "Foreign Worker Levy" in names
        assert "COMPASS Framework" in names
        assert "Employer Obligations" in names

    def test_bundle_has_provisions(self, bundle):
        assert len(bundle["provisions"]) == 8

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

    def test_every_provision_has_effective_date(self, bundle):
        for prov in bundle["provisions"]:
            assert prov.get("effective_date"), f"Missing effective_date in {prov['section']}"

    def test_every_provision_has_practical_examples(self, bundle):
        for prov in bundle["provisions"]:
            examples = prov.get("practical_examples", [])
            assert (
                len(examples) >= 1
            ), f"Provision {prov['section']} must have at least one practical example"

    def test_bundle_has_cross_references(self, bundle):
        assert len(bundle["cross_references"]) == 7

    def test_bundle_has_rate_tables(self, bundle):
        assert len(bundle["rate_tables"]) == 6

    def test_rate_tables_have_required_fields(self, bundle):
        for rt in bundle["rate_tables"]:
            assert (
                rt.get("table_type") == "foreign_worker_levy"
            ), f"Rate table '{rt.get('name')}' has wrong table_type"
            assert rt.get("effective_date"), f"Rate table '{rt.get('name')}' missing effective_date"
            assert rt.get("source_url"), f"Rate table '{rt.get('name')}' missing source_url"
            assert (
                rt.get("rate_value") is not None
            ), f"Rate table '{rt.get('name')}' missing rate_value"

    def test_bundle_validates_cleanly(self, bundle):
        validator = KBContentValidator()
        result = validator.validate_bundle(bundle)
        assert result["errors"] == [], f"Bundle validation errors: {result['errors']}"


# -- loading tests ----------------------------------------------------


class TestEFMALoading:
    """Test that the bundle loads successfully into the database."""

    def test_act_loaded(self, loaded):
        assert loaded["act"] is not None
        assert loaded["act"]["short_name"] == "EFMA"
        assert loaded["act"]["id"] is not None

    def test_domains_loaded(self, loaded):
        assert len(loaded["domains"]) == 5
        for domain in loaded["domains"]:
            assert domain["id"] is not None

    def test_provisions_loaded(self, loaded):
        assert len(loaded["provisions"]) == 8
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
        assert len(loaded["cross_references"]) == 7
        for xref in loaded["cross_references"]:
            assert xref["id"] is not None

    def test_rate_tables_loaded(self, loaded):
        assert len(loaded["rate_tables"]) == 6
        for rt in loaded["rate_tables"]:
            assert rt["id"] is not None


# -- data integrity tests ---------------------------------------------


class TestEFMADataIntegrity:
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

    def test_employment_pass_provision_content(self, loaded):
        """Spot-check: EFMA-EP provision has expected content."""
        ep = next((p for p in loaded["provisions"] if p["section"] == "EFMA-EP"), None)
        assert ep is not None
        assert "Employment Pass" in ep["title"]
        assert ep["authority_level"] == "statute"

    def test_s_pass_provision_content(self, loaded):
        """Spot-check: EFMA-SP has correct S Pass content."""
        sp = next((p for p in loaded["provisions"] if p["section"] == "EFMA-SP"), None)
        assert sp is not None
        assert "S Pass" in sp["title"]
        assert "$3,150" in sp["plain_summary"]

    def test_work_permit_provision_content(self, loaded):
        """Spot-check: EFMA-WP has correct Work Permit content."""
        wp = next((p for p in loaded["provisions"] if p["section"] == "EFMA-WP"), None)
        assert wp is not None
        assert "Work Permit" in wp["title"]
        assert "no minimum salary" in wp["plain_summary"].lower()

    def test_drc_provision_content(self, loaded):
        """Spot-check: EFMA-DRC has Dependency Ratio Ceiling content."""
        drc = next((p for p in loaded["provisions"] if p["section"] == "EFMA-DRC"), None)
        assert drc is not None
        assert "Dependency Ratio Ceiling" in drc["title"]
        assert "35%" in drc["plain_summary"]

    def test_levy_provision_content(self, loaded):
        """Spot-check: EFMA-LEVY has Foreign Worker Levy content."""
        levy = next((p for p in loaded["provisions"] if p["section"] == "EFMA-LEVY"), None)
        assert levy is not None
        assert "Levy" in levy["title"]
        assert "$450" in levy["plain_summary"] or "$450" in levy["formal_text"]

    def test_compass_provision_content(self, loaded):
        """Spot-check: EFMA-COMPASS has COMPASS framework content."""
        compass = next((p for p in loaded["provisions"] if p["section"] == "EFMA-COMPASS"), None)
        assert compass is not None
        assert "COMPASS" in compass["title"]
        assert "40" in compass["plain_summary"]

    def test_fcf_provision_content(self, loaded):
        """Spot-check: EFMA-FCF has Fair Consideration Framework content."""
        fcf = next((p for p in loaded["provisions"] if p["section"] == "EFMA-FCF"), None)
        assert fcf is not None
        assert "Fair Consideration" in fcf["title"]
        assert "14 days" in fcf["plain_summary"] or "14" in fcf["plain_summary"]

    def test_obligations_provision_content(self, loaded):
        """Spot-check: EFMA-OBLIG has employer obligations content."""
        oblig = next((p for p in loaded["provisions"] if p["section"] == "EFMA-OBLIG"), None)
        assert oblig is not None
        assert "Employer Obligations" in oblig["title"]
        assert "$15,000" in oblig["plain_summary"]
        assert "$40,000" in oblig["plain_summary"]

    def test_rate_tables_have_correct_values(self, loaded, pipeline):
        """Spot-check: rate table values match expected levy amounts."""
        rate_result = pipeline._execute(
            "RateTableListNode",
            "levy_rates",
            {
                "filter": {"table_type": "foreign_worker_levy"},
                "enable_cache": False,
                "limit": 10000,
            },
        )
        rates = _extract_records(rate_result)

        # We expect at least 6 rate entries from this bundle
        efma_rates = [r for r in rates if r["id"] in {rt["id"] for rt in loaded["rate_tables"]}]
        assert len(efma_rates) == 6

        # Check that the expected rate values are present
        rate_values = {float(r["rate_value"]) for r in efma_rates}
        assert 450.0 in rate_values, "Expected $450 WP basic tier levy in rate tables"
        assert 550.0 in rate_values, "Expected $550 S Pass Tier 1 levy in rate tables"
        assert 650.0 in rate_values, "Expected $650 higher tier levy in rate tables"


# -- idempotency tests ------------------------------------------------


class TestEFMAIdempotency:
    """Verify loading the same bundle twice does not create duplicates."""

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


class TestEFMAValidation:
    """Run the validator against the loaded EFMA data."""

    def test_no_provisions_without_domains(self, loaded):
        validator = KBContentValidator()
        all_provs_raw = validator._execute(
            "ProvisionListNode",
            "all",
            {"filter": {}, "enable_cache": False, "limit": 10000},
        )
        all_provs = validator._extract_records(all_provs_raw)
        efma_prov_ids = {p["id"] for p in loaded["provisions"]}
        efma_provs_without_domain = [
            p for p in all_provs if p["id"] in efma_prov_ids and not p.get("domain_id")
        ]
        assert len(efma_provs_without_domain) == 0

    def test_no_rate_tables_without_source_url(self, loaded):
        validator = KBContentValidator()
        all_rates_raw = validator._execute(
            "RateTableListNode",
            "all_rates",
            {"filter": {}, "enable_cache": False, "limit": 10000},
        )
        all_rates = validator._extract_records(all_rates_raw)
        efma_rate_ids = {rt["id"] for rt in loaded["rate_tables"]}
        efma_rates_without_url = [
            r
            for r in all_rates
            if r["id"] in efma_rate_ids
            and (
                not r.get("source_url")
                or (isinstance(r.get("source_url"), str) and not r["source_url"].strip())
            )
        ]
        assert len(efma_rates_without_url) == 0

    def test_quality_report_includes_efma_domains(self, loaded):
        validator = KBContentValidator()
        report = validator.generate_quality_report()
        assert report["total_provisions"] >= len(loaded["provisions"])
        # At least some EFMA domains should appear
        assert len(report["provisions_per_domain"]) >= 1
