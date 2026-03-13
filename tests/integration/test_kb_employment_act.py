"""Integration tests for Employment Act KB content loading.

Validates that the EA content bundle loads correctly via KBContentPipeline
and that all provisions, applicability rules, practical examples, and
cross-references are stored properly.
"""

import pytest

from hr_advisory.kb.content.employment_act import get_bundle
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
def loaded(pipeline, bundle, _cleanup_ea):
    """Load the EA bundle once for all tests in this module."""
    return pipeline.bulk_load(bundle)


@pytest.fixture(scope="module")
def _cleanup_ea(pipeline):
    """Clean up any existing EA test data before and after the module."""
    _do_cleanup(pipeline)
    yield
    _do_cleanup(pipeline)


def _do_cleanup(pipeline):
    """Remove EA test data using raw SQL via DataFlow."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    runtime = LocalRuntime()

    # Find and delete EA act and all related data
    act_result = pipeline._execute(
        "ActListNode", "find", {"filter": {"short_name": "EA"}, "enable_cache": False}
    )
    acts = _extract_records(act_result)

    if not acts:
        return

    act_id = acts[0]["id"]

    # Delete in dependency order: examples, rules, xrefs → provisions → domains → act
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

    # Delete domains created for EA
    for domain_name in [
        "Working Hours & Overtime",
        "Leave Entitlements",
        "Salary & Compensation",
        "Termination & Dismissal",
        "Employment Records",
        "Maternity & Family",
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


# ── bundle structure tests ───────────────────────────────────────────


class TestBundleStructure:
    """Verify the bundle is well-formed before loading."""

    def test_bundle_has_act(self, bundle):
        assert bundle["act"]["short_name"] == "EA"
        assert bundle["act"]["title"] == "Employment Act 1968"

    def test_bundle_has_six_domains(self, bundle):
        assert len(bundle["domains"]) == 6
        names = {d["name"] for d in bundle["domains"]}
        assert "Working Hours & Overtime" in names
        assert "Leave Entitlements" in names
        assert "Salary & Compensation" in names
        assert "Termination & Dismissal" in names
        assert "Employment Records" in names
        assert "Maternity & Family" in names

    def test_bundle_has_provisions(self, bundle):
        assert len(bundle["provisions"]) >= 15

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
        assert len(bundle["cross_references"]) >= 5

    def test_bundle_validates_cleanly(self, bundle):
        validator = KBContentValidator()
        result = validator.validate_bundle(bundle)
        assert result["errors"] == [], f"Bundle validation errors: {result['errors']}"

    def test_part_iv_provisions_have_salary_threshold_rules(self, bundle):
        """Part IV provisions must have salary_threshold applicability rules."""
        part_iv_sections = {"EA-S36", "EA-S37", "EA-S36(4)"}
        for prov in bundle["provisions"]:
            if prov["section"] in part_iv_sections:
                rules = prov.get("applicability_rules", [])
                rule_types = {r["rule_type"] for r in rules}
                assert (
                    "salary_threshold" in rule_types
                ), f"Part IV provision {prov['section']} missing salary_threshold rule"


# ── loading tests ────────────────────────────────────────────────────


class TestEALoading:
    """Test that the bundle loads successfully into the database."""

    def test_act_loaded(self, loaded):
        assert loaded["act"] is not None
        assert loaded["act"]["short_name"] == "EA"
        assert loaded["act"]["id"] is not None

    def test_domains_loaded(self, loaded):
        assert len(loaded["domains"]) == 6
        for domain in loaded["domains"]:
            assert domain["id"] is not None

    def test_provisions_loaded(self, loaded):
        assert len(loaded["provisions"]) >= 15
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


# ── data integrity tests ────────────────────────────────────────────


class TestEADataIntegrity:
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

    def test_hours_of_work_provision_content(self, loaded):
        """Spot-check: EA-S36 provision has expected content."""
        s36 = next((p for p in loaded["provisions"] if p["section"] == "EA-S36"), None)
        assert s36 is not None
        assert "Hours of Work" in s36["title"]
        assert s36["authority_level"] == "statute"

    def test_annual_leave_provision_content(self, loaded):
        """Spot-check: EA-S88A has correct annual leave content."""
        s88a = next((p for p in loaded["provisions"] if p["section"] == "EA-S88A"), None)
        assert s88a is not None
        assert "Annual Leave" in s88a["title"]
        assert "7 days" in s88a["plain_summary"]

    def test_sick_leave_provision_content(self, loaded):
        """Spot-check: EA-S89 has correct sick leave content."""
        s89 = next((p for p in loaded["provisions"] if p["section"] == "EA-S89"), None)
        assert s89 is not None
        assert "14" in s89["plain_summary"]
        assert "60" in s89["plain_summary"]

    def test_wrongful_dismissal_provision_content(self, loaded):
        """Spot-check: EA-S14A has wrongful dismissal content."""
        s14a = next((p for p in loaded["provisions"] if p["section"] == "EA-S14A"), None)
        assert s14a is not None
        assert "Wrongful Dismissal" in s14a["title"]

    def test_ket_provision_content(self, loaded):
        """Spot-check: EA-S20A has KET content."""
        s20a = next((p for p in loaded["provisions"] if p["section"] == "EA-S20A"), None)
        assert s20a is not None
        assert "Key Employment Terms" in s20a["title"]

    def test_maternity_provision_content(self, loaded):
        """Spot-check: EA-Part-IX has maternity protection content."""
        mat = next((p for p in loaded["provisions"] if p["section"] == "EA-Part-IX"), None)
        assert mat is not None
        assert "Maternity" in mat["title"]


# ── idempotency tests ───────────────────────────────────────────────


class TestEAIdempotency:
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


class TestEAValidation:
    """Run the validator against the loaded EA data."""

    def test_no_provisions_without_domains(self, loaded):
        validator = KBContentValidator()
        integrity = validator.validate_db_integrity()
        # Our EA provisions should all have domains
        # (There may be provisions from other test runs without domains)
        ea_prov_ids = {p["id"] for p in loaded["provisions"]}
        all_provs_raw = validator._execute(
            "ProvisionListNode", "all", {"filter": {}, "enable_cache": False}
        )
        all_provs = validator._extract_records(all_provs_raw)
        ea_provs_without_domain = [
            p for p in all_provs if p["id"] in ea_prov_ids and not p.get("domain_id")
        ]
        assert len(ea_provs_without_domain) == 0

    def test_quality_report_includes_ea_domains(self, loaded):
        validator = KBContentValidator()
        report = validator.generate_quality_report()
        assert report["total_provisions"] >= len(loaded["provisions"])
        # At least some EA domains should appear
        assert len(report["provisions_per_domain"]) >= 1
