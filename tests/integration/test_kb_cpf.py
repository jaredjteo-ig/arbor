"""Integration tests for CPF Act KB content loading.

Validates that the CPFA content bundle loads correctly via KBContentPipeline
and that all provisions, applicability rules, practical examples, rate tables,
and cross-references are stored properly.
"""

import pytest

from hr_advisory.kb.content.cpf import get_bundle
from hr_advisory.kb.pipeline import KBContentPipeline
from hr_advisory.kb.validator import KBContentValidator

# -- helpers ------------------------------------------------------------------


def _extract_records(result) -> list[dict]:
    """Normalize ListNode results to a plain list."""
    if isinstance(result, list):
        return result
    if isinstance(result, dict) and "records" in result:
        return result["records"]
    return []


# -- fixtures -----------------------------------------------------------------


@pytest.fixture(scope="module")
def pipeline():
    return KBContentPipeline()


@pytest.fixture(scope="module")
def bundle():
    return get_bundle()


@pytest.fixture(scope="module")
def loaded(pipeline, bundle, _cleanup_cpfa):
    """Load the CPFA bundle once for all tests in this module."""
    return pipeline.bulk_load(bundle)


@pytest.fixture(scope="module")
def _cleanup_cpfa(pipeline):
    """Clean up any existing CPFA test data before and after the module."""
    _do_cleanup(pipeline)
    yield
    _do_cleanup(pipeline)


def _do_cleanup(pipeline):
    """Remove CPFA test data using raw SQL via DataFlow."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    runtime = LocalRuntime()

    # Find and delete CPFA act and all related data
    act_result = pipeline._execute(
        "ActListNode", "find", {"filter": {"short_name": "CPFA"}, "enable_cache": False}
    )
    acts = _extract_records(act_result)

    if not acts:
        return

    act_id = acts[0]["id"]

    # Delete in dependency order: examples, rules, xrefs, rate_tables -> provisions -> domains -> act
    prov_result = pipeline._execute(
        "ProvisionListNode",
        "provs",
        {"filter": {"source_act_id": act_id}, "enable_cache": False},
    )
    provisions = _extract_records(prov_result)
    prov_ids = [p["id"] for p in provisions]

    for prov_id in prov_ids:
        # Delete practical examples
        ex_result = pipeline._execute(
            "PracticalExampleListNode",
            "ex",
            {"filter": {"provision_id": prov_id}, "enable_cache": False},
        )
        for ex in _extract_records(ex_result):
            pipeline._execute(
                "PracticalExampleDeleteNode", "del_ex", {"conditions": {"id": ex["id"]}}
            )

        # Delete applicability rules
        rule_result = pipeline._execute(
            "ApplicabilityRuleListNode",
            "rules",
            {"filter": {"provision_id": prov_id}, "enable_cache": False},
        )
        for rule in _extract_records(rule_result):
            pipeline._execute(
                "ApplicabilityRuleDeleteNode", "del_rule", {"conditions": {"id": rule["id"]}}
            )

        # Delete cross-references (source or target)
        xref_result = pipeline._execute(
            "CrossReferenceListNode",
            "xrefs_src",
            {"filter": {"source_provision_id": prov_id}, "enable_cache": False},
        )
        for xref in _extract_records(xref_result):
            pipeline._execute(
                "CrossReferenceDeleteNode", "del_xref", {"conditions": {"id": xref["id"]}}
            )

        xref_result2 = pipeline._execute(
            "CrossReferenceListNode",
            "xrefs_tgt",
            {"filter": {"target_provision_id": prov_id}, "enable_cache": False},
        )
        for xref in _extract_records(xref_result2):
            pipeline._execute(
                "CrossReferenceDeleteNode", "del_xref2", {"conditions": {"id": xref["id"]}}
            )

        # Delete provision (hard delete via DeleteNode)
        pipeline._execute("ProvisionDeleteNode", "del_prov", {"conditions": {"id": prov_id}})

    # Delete rate tables for CPF
    rate_result = pipeline._execute(
        "RateTableListNode",
        "rates",
        {"filter": {"table_type": "cpf_contribution_rate"}, "enable_cache": False},
    )
    for rate in _extract_records(rate_result):
        pipeline._execute("RateTableDeleteNode", "del_rate", {"conditions": {"id": rate["id"]}})

    # Delete domains created for CPFA
    for domain_name in [
        "CPF Contribution Rates",
        "CPF Wage Ceilings",
        "CPF Allocation",
        "CPF Compliance",
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


# -- bundle structure tests ---------------------------------------------------


class TestCPFBundleStructure:
    """Verify the bundle is well-formed before loading."""

    def test_bundle_has_act(self, bundle):
        assert bundle["act"]["short_name"] == "CPFA"
        assert bundle["act"]["title"] == "Central Provident Fund Act"

    def test_bundle_has_four_domains(self, bundle):
        assert len(bundle["domains"]) == 4
        names = {d["name"] for d in bundle["domains"]}
        assert "CPF Contribution Rates" in names
        assert "CPF Wage Ceilings" in names
        assert "CPF Allocation" in names
        assert "CPF Compliance" in names

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

    def test_bundle_has_cross_references(self, bundle):
        assert len(bundle["cross_references"]) >= 5

    def test_bundle_has_rate_tables(self, bundle):
        assert len(bundle["rate_tables"]) == 8

    def test_every_rate_table_has_required_fields(self, bundle):
        for rt in bundle["rate_tables"]:
            assert (
                rt.get("table_type") == "cpf_contribution_rate"
            ), f"Rate table missing or wrong table_type: {rt.get('table_type')}"
            assert rt.get("effective_date"), f"Rate table missing effective_date"
            assert rt.get("source_url"), f"Rate table missing source_url"
            assert rt.get("criteria"), f"Rate table missing criteria"
            assert rt.get("rate_value"), f"Rate table missing rate_value"

    def test_rate_tables_have_citizenship_and_age_band(self, bundle):
        """Every rate table criteria must include citizenship_status and age_band."""
        for rt in bundle["rate_tables"]:
            criteria = rt["criteria"]
            assert (
                "citizenship_status" in criteria
            ), f"Rate table criteria missing citizenship_status: {criteria}"
            assert "age_band" in criteria, f"Rate table criteria missing age_band: {criteria}"

    def test_pr_rate_tables_have_pr_year(self, bundle):
        """PR rate table entries must explicitly model pr_year (S4 red-team fix)."""
        pr_tables = [
            rt for rt in bundle["rate_tables"] if rt["criteria"].get("citizenship_status") == "PR"
        ]
        assert len(pr_tables) >= 2, "Expected at least 2 PR rate table entries"
        for rt in pr_tables:
            assert (
                "pr_year" in rt["criteria"]
            ), f"PR rate table missing pr_year in criteria: {rt['criteria']}"

    def test_bundle_validates_cleanly(self, bundle):
        validator = KBContentValidator()
        result = validator.validate_bundle(bundle)
        assert result["errors"] == [], f"Bundle validation errors: {result['errors']}"


# -- loading tests ------------------------------------------------------------


class TestCPFLoading:
    """Test that the bundle loads successfully into the database."""

    def test_act_loaded(self, loaded):
        assert loaded["act"] is not None
        assert loaded["act"]["short_name"] == "CPFA"
        assert loaded["act"]["id"] is not None

    def test_domains_loaded(self, loaded):
        assert len(loaded["domains"]) == 4
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
        assert len(loaded["cross_references"]) >= 5
        for xref in loaded["cross_references"]:
            assert xref["id"] is not None

    def test_rate_tables_loaded(self, loaded):
        assert len(loaded["rate_tables"]) == 8
        for rt in loaded["rate_tables"]:
            assert rt["id"] is not None


# -- data integrity tests -----------------------------------------------------


class TestCPFDataIntegrity:
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

    def test_employer_contribution_provision_content(self, loaded):
        """Spot-check: CPFA-S7 provision has expected content."""
        s7 = next((p for p in loaded["provisions"] if p["section"] == "CPFA-S7"), None)
        assert s7 is not None
        assert "Employer" in s7["title"]
        assert s7["authority_level"] == "statute"
        assert "17%" in s7["formal_text"] or "17%" in s7["plain_summary"]

    def test_employee_contribution_provision_content(self, loaded):
        """Spot-check: CPFA-S9 provision has expected content."""
        s9 = next((p for p in loaded["provisions"] if p["section"] == "CPFA-S9"), None)
        assert s9 is not None
        assert "Employee" in s9["title"]
        assert "20%" in s9["formal_text"] or "20%" in s9["plain_summary"]

    def test_ow_ceiling_provision_content(self, loaded):
        """Spot-check: CPFA-S13 provision has OW ceiling content."""
        s13 = next((p for p in loaded["provisions"] if p["section"] == "CPFA-S13"), None)
        assert s13 is not None
        assert "Ordinary Wage" in s13["title"] or "OW" in s13["title"]
        assert "8,000" in s13["plain_summary"] or "$8,000" in s13["formal_text"]

    def test_aw_ceiling_provision_content(self, loaded):
        """Spot-check: CPFA-S14 provision has AW ceiling content."""
        s14 = next((p for p in loaded["provisions"] if p["section"] == "CPFA-S14"), None)
        assert s14 is not None
        assert "Additional Wage" in s14["title"] or "AW" in s14["title"]
        assert "102,000" in s14["plain_summary"] or "$102,000" in s14["formal_text"]

    def test_pr_rates_provision_content(self, loaded):
        """Spot-check: CPFA-PR-RATES provision has PR graduated rates."""
        pr = next((p for p in loaded["provisions"] if p["section"] == "CPFA-PR-RATES"), None)
        assert pr is not None
        assert "PR" in pr["title"]

    def test_allocation_provision_content(self, loaded):
        """Spot-check: CPFA-ALLOC provision has allocation rates."""
        alloc = next((p for p in loaded["provisions"] if p["section"] == "CPFA-ALLOC"), None)
        assert alloc is not None
        assert "Allocation" in alloc["title"]
        # OA 23% for age <=55 should be mentioned
        assert "23%" in alloc["formal_text"] or "23%" in alloc["plain_summary"]

    def test_late_payment_provision_content(self, loaded):
        """Spot-check: CPFA-S52 provision has late payment interest."""
        s52 = next((p for p in loaded["provisions"] if p["section"] == "CPFA-S52"), None)
        assert s52 is not None
        assert "18%" in s52["formal_text"] or "18%" in s52["plain_summary"]

    def test_voluntary_contributions_provision_content(self, loaded):
        """Spot-check: CPFA-S58 provision has voluntary contributions."""
        s58 = next((p for p in loaded["provisions"] if p["section"] == "CPFA-S58"), None)
        assert s58 is not None
        assert "Voluntary" in s58["title"]
        assert "8,000" in s58["plain_summary"] or "$8,000" in s58["formal_text"]

    def test_rate_table_sc_age_55_and_below(self, loaded, pipeline):
        """Spot-check: SC age <=55 rate table has correct rates."""
        rate_result = pipeline._execute(
            "RateTableListNode",
            "rates",
            {"filter": {"table_type": "cpf_contribution_rate"}, "enable_cache": False},
        )
        all_rates = _extract_records(rate_result)

        import json

        sc_55 = None
        for rt in all_rates:
            raw_criteria = rt.get("criteria", {})
            criteria = json.loads(raw_criteria) if isinstance(raw_criteria, str) else raw_criteria
            if (
                criteria.get("citizenship_status") == "SC"
                and criteria.get("age_band") == "55_and_below"
            ):
                sc_55 = rt
                break

        assert sc_55 is not None, "SC age <=55 rate table entry not found"
        rate_value = (
            json.loads(sc_55["rate_value"])
            if isinstance(sc_55["rate_value"], str)
            else sc_55["rate_value"]
        )
        assert rate_value["employer_rate"] == 17.0
        assert rate_value["employee_rate"] == 20.0
        assert rate_value["total_rate"] == 37.0

    def test_rate_table_pr_1st_year(self, loaded, pipeline):
        """Spot-check: PR 1st year <=55 graduated rate table (S4 red-team fix)."""
        rate_result = pipeline._execute(
            "RateTableListNode",
            "rates",
            {"filter": {"table_type": "cpf_contribution_rate"}, "enable_cache": False},
        )
        all_rates = _extract_records(rate_result)

        import json

        pr_1st = None
        for rt in all_rates:
            raw_criteria = rt.get("criteria", {})
            criteria = json.loads(raw_criteria) if isinstance(raw_criteria, str) else raw_criteria
            if (
                criteria.get("citizenship_status") == "PR"
                and criteria.get("age_band") == "55_and_below"
                and criteria.get("pr_year") == "1st_year"
            ):
                pr_1st = rt
                break

        assert pr_1st is not None, "PR 1st year age <=55 rate table entry not found"
        rate_value = (
            json.loads(pr_1st["rate_value"])
            if isinstance(pr_1st["rate_value"], str)
            else pr_1st["rate_value"]
        )
        assert rate_value["employer_rate"] == 4.0
        assert rate_value["employee_rate"] == 5.0
        assert rate_value["total_rate"] == 9.0


# -- idempotency tests -------------------------------------------------------


class TestCPFIdempotency:
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


# -- validator tests ----------------------------------------------------------


class TestCPFValidation:
    """Run the validator against the loaded CPFA data."""

    def test_no_provisions_without_domains(self, loaded):
        validator = KBContentValidator()
        all_provs_raw = validator._execute(
            "ProvisionListNode", "all", {"filter": {}, "enable_cache": False}
        )
        all_provs = validator._extract_records(all_provs_raw)
        cpfa_prov_ids = {p["id"] for p in loaded["provisions"]}
        cpfa_provs_without_domain = [
            p for p in all_provs if p["id"] in cpfa_prov_ids and not p.get("domain_id")
        ]
        assert len(cpfa_provs_without_domain) == 0

    def test_no_rate_tables_without_source_url(self, loaded):
        """All CPFA rate tables must have a source_url."""
        for rt in loaded["rate_tables"]:
            assert rt.get("source_url"), f"Rate table id={rt['id']} missing source_url"

    def test_quality_report_includes_cpfa_domains(self, loaded):
        validator = KBContentValidator()
        report = validator.generate_quality_report()
        assert report["total_provisions"] >= len(loaded["provisions"])
        # At least some CPFA domains should appear
        assert len(report["provisions_per_domain"]) >= 1
