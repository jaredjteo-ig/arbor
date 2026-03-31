"""Integration tests for T014 -- Knowledge Base Content Pipeline and Tooling.

These tests run against real PostgreSQL with DataFlow workflow nodes.
Docker must be running: docker compose -f docker-compose.dev.yml up -d

Tests cover:
 1. Pipeline basics: Load an act, load a domain, load a provision
 2. Bulk load: Complete content bundle (act + domains + provisions + rules + examples + cross-references)
 3. Validation: Reject provision with missing required fields, warn on missing recommended fields
 4. DB integrity: Detect orphan applicability rules, missing cross-reference targets
 5. Quality report: Coverage stats by domain
 6. Provision update versioning: Update provision, verify old is marked superseded
 7. Rate table loading: Rate tables with temporal dates
 8. Duplicate handling: Idempotent on short_name
 9. Domain hierarchy: Parent + child domains
10. KB stats: Statistics after loading content
"""

import os
from datetime import datetime

import pytest

# Ensure DATABASE_URL is set for tests
os.environ.setdefault("DATABASE_URL", "postgresql://arbor:arbor@localhost:5432/arbor")

pytestmark = pytest.mark.requires_postgres


# ---------------------------------------------------------------------------
# Helper: clean up test data between runs
# ---------------------------------------------------------------------------


def _cleanup_test_data():
    """Remove test data from all KB tables to keep tests isolated.

    Uses raw SQL because we need to delete across foreign keys in the right order.
    """
    import sqlalchemy

    engine = sqlalchemy.create_engine(os.environ["DATABASE_URL"])
    with engine.connect() as conn:
        # Order matters: children first, parents last
        for table in [
            "practical_examples",
            "applicability_rules",
            "cross_references",
            "rate_tables",
            "provisions",
            "domains",
            "acts",
        ]:
            try:
                conn.execute(sqlalchemy.text(f"DELETE FROM {table}"))
            except Exception:
                pass  # Table may not exist yet on first run
        conn.commit()
    engine.dispose()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module", autouse=True)
def clean_db():
    """Clean KB tables before the module runs, and after it finishes."""
    _cleanup_test_data()
    yield
    _cleanup_test_data()


@pytest.fixture(scope="module")
def pipeline():
    """Get a KBContentPipeline instance."""
    from hr_advisory.kb.pipeline import KBContentPipeline

    return KBContentPipeline()


@pytest.fixture(scope="module")
def validator():
    """Get a KBContentValidator instance."""
    from hr_advisory.kb.validator import KBContentValidator

    return KBContentValidator()


@pytest.fixture(scope="module")
def runtime():
    """Get a LocalRuntime for verification queries."""
    from kailash.runtime import LocalRuntime

    return LocalRuntime()


# ---------------------------------------------------------------------------
# Sample data used across tests
# ---------------------------------------------------------------------------

SAMPLE_ACT = {
    "title": "Employment Act 1968",
    "short_name": "EA",
    "authority_type": "statute",
    "issuing_body": "Ministry of Manpower",
    "official_url": "https://sso.agc.gov.sg/Act/EmA1968",
}

SAMPLE_DOMAIN_PARENT = {
    "name": "Working Hours & Rest Days",
    "description": "Regulations on working hours, overtime, and rest days",
}

SAMPLE_DOMAIN_CHILD = {
    "name": "Overtime",
    "description": "Overtime calculation and limits",
    "parent_domain_name": "Working Hours & Rest Days",
}

SAMPLE_PROVISION = {
    "section": "Part IV s38",
    "title": "Hours of work",
    "formal_text": (
        "An employee shall not be required under his contract of service to work "
        "more than 8 hours in one day or more than 44 hours in one week."
    ),
    "plain_summary": "Employees covered by Part IV cannot be required to work more than 8 hours/day or 44 hours/week.",
    "interpretation_notes": (
        "Part IV applies to workmen earning up to $4,500/month and non-workmen earning up to $2,600/month. "
        "Hours do not include meal breaks."
    ),
    "authority_level": "statute",
    "domain_name": "Working Hours & Rest Days",
    "effective_date": "1968-08-01",
}

SAMPLE_APPLICABILITY_RULE = {
    "rule_type": "salary_threshold",
    "criteria_value": {"max_salary": 2600, "worker_type": "non-workman"},
    "notes": "Part IV applies to non-workmen earning up to $2,600/month",
}

SAMPLE_EXAMPLE = {
    "scenario": "An admin assistant earns $2,400/month. Is she covered by Part IV?",
    "calculation": {"monthly_salary": 2400, "threshold": 2600, "covered": True},
    "outcome": "Yes, covered. $2,400 is below the $2,600 threshold for non-workmen.",
}

SAMPLE_RATE_TABLE = {
    "table_type": "cpf_contribution",
    "effective_date": "2024-01-01",
    "criteria": {
        "age_group": "55_and_below",
        "wage_ceiling": 8000,
        "citizenship": "citizen",
    },
    "rate_value": "0.17",
    "source_url": "https://www.cpf.gov.sg/employer/employer-obligations",
}


# ===========================================================================
# 1. Pipeline basics: Load act, domain, provision
# ===========================================================================


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set -- skip DB tests",
)
class TestPipelineBasics:
    """Load individual records through the pipeline."""

    def test_load_act(self, pipeline):
        """Loading an act returns a dict with an 'id' field."""
        result = pipeline.load_act(SAMPLE_ACT)
        assert "id" in result, f"Expected 'id' in result, got: {result}"
        assert result["title"] == "Employment Act 1968"
        assert result["short_name"] == "EA"

    def test_load_domain(self, pipeline):
        """Loading a domain returns a dict with an 'id' field."""
        result = pipeline.load_domain(SAMPLE_DOMAIN_PARENT)
        assert "id" in result, f"Expected 'id' in result, got: {result}"
        assert result["name"] == "Working Hours & Rest Days"

    def test_load_provision(self, pipeline):
        """Loading a provision resolves domain_name to domain_id and act short_name."""
        # The act and domain must exist from prior tests (module scope fixture)
        result = pipeline.load_provision(
            {
                **SAMPLE_PROVISION,
                "act_short_name": "EA",
            }
        )
        assert "id" in result, f"Expected 'id' in result, got: {result}"
        assert result["section"] == "Part IV s38"
        assert result["title"] == "Hours of work"
        assert result["domain_id"] is not None, "domain_id should be resolved from domain_name"
        assert (
            result["source_act_id"] is not None
        ), "source_act_id should be resolved from act_short_name"

    def test_load_applicability_rule(self, pipeline):
        """Loading an applicability rule attached to a provision."""
        # Get provision ID from a fresh lookup
        from kailash.workflow.builder import WorkflowBuilder
        from kailash.runtime import LocalRuntime

        runtime = LocalRuntime()
        wf = WorkflowBuilder()
        wf.add_node(
            "ProvisionListNode",
            "find",
            {"filter": {"section": "Part IV s38"}, "enable_cache": False},
        )
        results, _ = runtime.execute(wf.build())
        raw = results["find"]
        provisions = raw if isinstance(raw, list) else raw.get("records", [])
        assert len(provisions) > 0, "Provision should exist from test_load_provision"
        provision_id = provisions[0]["id"]

        result = pipeline.load_applicability_rule(provision_id, SAMPLE_APPLICABILITY_RULE)
        assert "id" in result, f"Expected 'id' in result, got: {result}"
        assert result["provision_id"] == provision_id

    def test_load_practical_example(self, pipeline):
        """Loading a practical example attached to a provision."""
        from kailash.workflow.builder import WorkflowBuilder
        from kailash.runtime import LocalRuntime

        runtime = LocalRuntime()
        wf = WorkflowBuilder()
        wf.add_node(
            "ProvisionListNode",
            "find",
            {"filter": {"section": "Part IV s38"}, "enable_cache": False},
        )
        results, _ = runtime.execute(wf.build())
        raw = results["find"]
        provs = raw if isinstance(raw, list) else raw.get("records", [])
        provision_id = provs[0]["id"]

        result = pipeline.load_practical_example(provision_id, SAMPLE_EXAMPLE)
        assert "id" in result, f"Expected 'id' in result, got: {result}"
        assert result["provision_id"] == provision_id

    def test_load_rate_table(self, pipeline):
        """Loading a rate table entry."""
        result = pipeline.load_rate_table(SAMPLE_RATE_TABLE)
        assert "id" in result, f"Expected 'id' in result, got: {result}"
        assert result["table_type"] == "cpf_contribution"
        assert result["rate_value"] == "0.17"


# ===========================================================================
# 2. Bulk load: Complete content bundle
# ===========================================================================


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set -- skip DB tests",
)
class TestBulkLoad:
    """Load a complete content bundle in one call."""

    def test_bulk_load_complete_bundle(self, pipeline):
        """bulk_load accepts a structured dict and loads everything."""
        _cleanup_test_data()  # Start clean for bulk test

        bundle = {
            "act": {
                "title": "Central Provident Fund Act",
                "short_name": "CPFA",
                "authority_type": "statute",
                "issuing_body": "Ministry of Manpower",
            },
            "domains": [
                {"name": "CPF", "description": "Central Provident Fund"},
                {
                    "name": "CPF Contribution Rates",
                    "description": "Employer and employee contribution rates",
                    "parent_domain_name": "CPF",
                },
            ],
            "provisions": [
                {
                    "section": "s7",
                    "title": "Payment of contributions",
                    "formal_text": "Every employer shall pay CPF contributions.",
                    "plain_summary": "All employers must pay CPF for their employees.",
                    "interpretation_notes": "Applies to all employees who are Singapore citizens or PRs.",
                    "authority_level": "statute",
                    "domain_name": "CPF",
                    "effective_date": "1953-07-01",
                    "applicability_rules": [
                        {
                            "rule_type": "worker_type",
                            "criteria_value": {"citizenship": ["citizen", "pr"]},
                            "notes": "Only citizens and PRs are covered",
                        },
                    ],
                    "practical_examples": [
                        {
                            "scenario": "Company hires a Singaporean. Must they pay CPF?",
                            "calculation": {"citizenship": "citizen", "cpf_required": True},
                            "outcome": "Yes, CPF contributions are mandatory for citizens.",
                        },
                    ],
                },
                {
                    "section": "s7A",
                    "title": "Additional contributions for older workers",
                    "formal_text": "Additional CPF contributions apply to employees aged 55 and above.",
                    "plain_summary": "CPF rates change when employees turn 55.",
                    "authority_level": "statute",
                    "domain_name": "CPF Contribution Rates",
                    "effective_date": "2024-01-01",
                },
            ],
            "cross_references": [
                {
                    "source_section": "s7",
                    "target_section": "s7A",
                    "relationship_type": "supplements",
                    "notes": "s7A supplements s7 for older workers",
                },
            ],
            "rate_tables": [
                {
                    "table_type": "cpf_contribution",
                    "effective_date": "2024-01-01",
                    "criteria": {"age_group": "55_and_below", "citizenship": "citizen"},
                    "rate_value": "0.37",
                    "source_url": "https://www.cpf.gov.sg",
                },
            ],
        }

        result = pipeline.bulk_load(bundle)

        # Result should contain summary of what was loaded
        assert (
            "act" in result
        ), f"Expected 'act' in bulk_load result, got keys: {list(result.keys())}"
        assert result["act"]["id"] is not None
        assert result["act"]["short_name"] == "CPFA"

        assert "domains" in result
        assert len(result["domains"]) == 2

        assert "provisions" in result
        assert len(result["provisions"]) == 2

        assert "applicability_rules" in result
        assert len(result["applicability_rules"]) >= 1

        assert "practical_examples" in result
        assert len(result["practical_examples"]) >= 1

        assert "cross_references" in result
        assert len(result["cross_references"]) == 1

        assert "rate_tables" in result
        assert len(result["rate_tables"]) == 1

    def test_bulk_load_resolves_cross_references_by_section(self, pipeline):
        """Cross-references specified by section name are resolved to provision IDs."""
        from kailash.workflow.builder import WorkflowBuilder
        from kailash.runtime import LocalRuntime

        runtime = LocalRuntime()

        # Verify cross-reference was created
        wf = WorkflowBuilder()
        wf.add_node("CrossReferenceListNode", "xrefs", {"filter": {}, "enable_cache": False})
        results, _ = runtime.execute(wf.build())
        raw_xrefs = results["xrefs"]
        xrefs = raw_xrefs if isinstance(raw_xrefs, list) else raw_xrefs.get("records", [])
        assert len(xrefs) >= 1, "At least one cross-reference should exist"

        # Find the one linking s7 -> s7A
        wf2 = WorkflowBuilder()
        wf2.add_node(
            "ProvisionListNode", "find_s7", {"filter": {"section": "s7"}, "enable_cache": False}
        )
        results2, _ = runtime.execute(wf2.build())
        raw_s7 = results2["find_s7"]
        s7_list = raw_s7 if isinstance(raw_s7, list) else raw_s7.get("records", [])
        s7_id = s7_list[0]["id"]

        matching = [x for x in xrefs if x["source_provision_id"] == s7_id]
        assert len(matching) == 1, f"Expected 1 cross-ref from s7, found {len(matching)}"
        assert matching[0]["relationship_type"] == "supplements"


# ===========================================================================
# 3. Validation: Required/recommended fields
# ===========================================================================


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set -- skip DB tests",
)
class TestValidation:
    """Content validation before loading."""

    def test_validate_provision_missing_required_fields(self, validator):
        """Reject provision missing required fields: section, title, formal_text, authority_level, domain_name."""
        errors = validator.validate_provision({})
        assert len(errors) > 0, "Empty provision should have validation errors"
        # Check that all required fields are flagged
        error_text = " ".join(errors).lower()
        for field in ["section", "title", "formal_text", "authority_level", "domain_name"]:
            assert field in error_text, f"Missing required field '{field}' should be flagged"

    def test_validate_provision_valid(self, validator):
        """Valid provision should have no errors."""
        errors = validator.validate_provision(
            {
                "section": "s1",
                "title": "Test",
                "formal_text": "Some text",
                "authority_level": "statute",
                "domain_name": "Test Domain",
            }
        )
        assert len(errors) == 0, f"Valid provision should have no errors, got: {errors}"

    def test_validate_provision_warns_on_missing_recommended(self, validator):
        """Warn on missing recommended fields: plain_summary, interpretation_notes, effective_date."""
        result = validator.validate_bundle(
            {
                "act": {"title": "Test", "short_name": "TST"},
                "domains": [{"name": "Test Domain"}],
                "provisions": [
                    {
                        "section": "s1",
                        "title": "Test",
                        "formal_text": "Some text",
                        "authority_level": "statute",
                        "domain_name": "Test Domain",
                        # Missing: plain_summary, interpretation_notes, effective_date
                    },
                ],
            }
        )
        assert (
            "warnings" in result
        ), f"Expected 'warnings' in result, got keys: {list(result.keys())}"
        assert len(result["warnings"]) > 0, "Should warn about missing recommended fields"
        warning_text = " ".join(result["warnings"]).lower()
        for field in ["plain_summary", "interpretation_notes", "effective_date"]:
            assert (
                field in warning_text
            ), f"Missing recommended field '{field}' should produce a warning"

    def test_validate_bundle_with_errors(self, validator):
        """Bundle with invalid provisions returns errors."""
        result = validator.validate_bundle(
            {
                "act": {"title": "Test", "short_name": "TST"},
                "domains": [],
                "provisions": [
                    {"section": "s1"},  # Missing title, formal_text, authority_level, domain_name
                ],
            }
        )
        assert "errors" in result
        assert len(result["errors"]) > 0

    def test_validate_provision_invalid_authority_level(self, validator):
        """Invalid authority_level should be flagged."""
        errors = validator.validate_provision(
            {
                "section": "s1",
                "title": "Test",
                "formal_text": "Some text",
                "authority_level": "invalid_level",
                "domain_name": "Test Domain",
            }
        )
        assert len(errors) > 0, "Invalid authority_level should be flagged"
        assert any("authority_level" in e.lower() for e in errors)


# ===========================================================================
# 4. DB integrity checks
# ===========================================================================


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set -- skip DB tests",
)
class TestDBIntegrity:
    """Check database integrity after loading content."""

    def test_validate_db_integrity(self, validator):
        """DB integrity check returns structured results."""
        result = validator.validate_db_integrity()
        assert (
            "orphan_rules" in result
        ), f"Expected 'orphan_rules' in result, got keys: {list(result.keys())}"
        assert "missing_cross_ref_targets" in result
        assert "provisions_without_domains" in result
        assert "rate_tables_without_source_url" in result

    def test_detect_provisions_without_domains(self, validator, pipeline):
        """Provisions without domain_id should be flagged."""
        # Create a provision without a domain directly via pipeline internal
        from kailash.workflow.builder import WorkflowBuilder
        from kailash.runtime import LocalRuntime

        runtime = LocalRuntime()

        # Ensure an act exists
        wf_act = WorkflowBuilder()
        wf_act.add_node(
            "ActListNode", "find", {"filter": {"short_name": "CPFA"}, "enable_cache": False}
        )
        results, _ = runtime.execute(wf_act.build())
        raw_acts = results["find"]
        acts = raw_acts if isinstance(raw_acts, list) else raw_acts.get("records", [])
        if not acts:
            wf_create = WorkflowBuilder()
            wf_create.add_node(
                "ActCreateNode",
                "create",
                {
                    "title": "Test Act for Integrity",
                    "short_name": "TAFI",
                },
            )
            r, _ = runtime.execute(wf_create.build())
            act_id = r["create"]["id"]
        else:
            act_id = acts[0]["id"]

        # Create a provision WITHOUT domain_id
        wf_prov = WorkflowBuilder()
        wf_prov.add_node(
            "ProvisionCreateNode",
            "prov",
            {
                "source_act_id": act_id,
                "section": "s_orphan_test",
                "title": "Orphan domain test",
                "formal_text": "This provision has no domain assigned",
            },
        )
        runtime.execute(wf_prov.build())

        result = validator.validate_db_integrity()
        assert (
            result["provisions_without_domains"] >= 1
        ), f"Expected at least 1 provision without domain, got {result['provisions_without_domains']}"


# ===========================================================================
# 5. Quality report
# ===========================================================================


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set -- skip DB tests",
)
class TestQualityReport:
    """Generate and verify quality reports."""

    def test_generate_quality_report(self, validator):
        """Quality report should show coverage statistics."""
        report = validator.generate_quality_report()
        assert (
            "total_provisions" in report
        ), f"Expected 'total_provisions', got keys: {list(report.keys())}"
        assert "provisions_per_domain" in report
        assert "provisions_with_examples" in report
        assert "provisions_without_examples" in report
        assert isinstance(report["provisions_per_domain"], dict)

    def test_quality_report_counts_are_accurate(self, validator):
        """Report counts should match what we loaded."""
        report = validator.generate_quality_report()
        # We loaded at least some provisions (from bulk_load test and basics test)
        assert report["total_provisions"] > 0, "Should have some provisions loaded"


# ===========================================================================
# 6. Provision update versioning
# ===========================================================================


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set -- skip DB tests",
)
class TestProvisionVersioning:
    """Verify provision update creates new version and marks old as superseded."""

    def test_update_provision_creates_new_version(self, pipeline):
        """Updating a provision should create a new version and supersede the old one."""
        from hr_advisory.kb.admin import update_provision

        from kailash.workflow.builder import WorkflowBuilder
        from kailash.runtime import LocalRuntime

        runtime = LocalRuntime()

        # First, load an act and a provision
        _cleanup_test_data()
        act_result = pipeline.load_act(
            {
                "title": "Versioning Test Act",
                "short_name": "VTA",
            }
        )

        domain_result = pipeline.load_domain(
            {
                "name": "Versioning Domain",
                "description": "For testing versioning",
            }
        )

        provision_result = pipeline.load_provision(
            {
                "act_short_name": "VTA",
                "section": "s_version_test",
                "title": "Original title",
                "formal_text": "Original formal text",
                "authority_level": "statute",
                "domain_name": "Versioning Domain",
            }
        )
        old_id = provision_result["id"]

        # Update the provision
        updated = update_provision(
            provision_id=old_id,
            updates={
                "title": "Updated title",
                "formal_text": "Updated formal text with new guidance",
            },
            reason="Annual review 2024",
        )
        new_id = updated["id"]
        assert new_id != old_id, "Update should create a new provision record"

        # Verify old provision is marked superseded
        wf = WorkflowBuilder()
        wf.add_node("ProvisionReadNode", "read_old", {"conditions": {"id": old_id}})
        results, _ = runtime.execute(wf.build())
        old_prov = results["read_old"]
        assert old_prov["is_active"] is False, "Old provision should be deactivated"
        assert old_prov["superseded_by_id"] == new_id, "Old provision should point to new version"

        # Verify new provision is active with updated fields
        wf2 = WorkflowBuilder()
        wf2.add_node("ProvisionReadNode", "read_new", {"conditions": {"id": new_id}})
        results2, _ = runtime.execute(wf2.build())
        new_prov = results2["read_new"]
        assert new_prov["is_active"] is True
        assert new_prov["title"] == "Updated title"
        assert new_prov["formal_text"] == "Updated formal text with new guidance"


# ===========================================================================
# 7. Rate table loading
# ===========================================================================


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set -- skip DB tests",
)
class TestRateTableLoading:
    """Load rate tables with temporal dates."""

    def test_load_rate_table_with_dates(self, pipeline):
        """Rate tables support effective_date and expiry_date."""
        result = pipeline.load_rate_table(
            {
                "table_type": "levy_rate",
                "effective_date": "2024-01-01",
                "expiry_date": "2024-12-31",
                "criteria": {"pass_type": "s_pass", "tier": 1},
                "rate_value": "650",
                "source_url": "https://www.mom.gov.sg/passes-and-permits",
            }
        )
        assert "id" in result
        assert result["table_type"] == "levy_rate"
        assert result["rate_value"] == "650"

    def test_load_multiple_rate_tables(self, pipeline):
        """Multiple rate table entries for different criteria."""
        rates = [
            {
                "table_type": "cpf_contribution",
                "effective_date": "2024-01-01",
                "criteria": {"age_group": "55_and_below"},
                "rate_value": "0.37",
            },
            {
                "table_type": "cpf_contribution",
                "effective_date": "2024-01-01",
                "criteria": {"age_group": "above_55_to_60"},
                "rate_value": "0.295",
            },
            {
                "table_type": "cpf_contribution",
                "effective_date": "2024-01-01",
                "criteria": {"age_group": "above_60_to_65"},
                "rate_value": "0.205",
            },
        ]
        for rate_data in rates:
            result = pipeline.load_rate_table(rate_data)
            assert "id" in result


# ===========================================================================
# 8. Duplicate handling / idempotent loading
# ===========================================================================


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set -- skip DB tests",
)
class TestDuplicateHandling:
    """Loading the same entity twice should not create duplicates."""

    def test_load_act_twice_is_idempotent(self, pipeline):
        """Loading an act with the same short_name twice returns the existing record."""
        _cleanup_test_data()

        result1 = pipeline.load_act(
            {
                "title": "Idempotent Test Act",
                "short_name": "ITA",
                "authority_type": "statute",
            }
        )
        result2 = pipeline.load_act(
            {
                "title": "Idempotent Test Act",
                "short_name": "ITA",
                "authority_type": "statute",
            }
        )
        assert (
            result1["id"] == result2["id"]
        ), f"Same short_name should return same record: {result1['id']} != {result2['id']}"

    def test_load_domain_twice_is_idempotent(self, pipeline):
        """Loading a domain with the same name twice returns the existing record."""
        result1 = pipeline.load_domain({"name": "Idempotent Domain", "description": "Test"})
        result2 = pipeline.load_domain({"name": "Idempotent Domain", "description": "Test"})
        assert (
            result1["id"] == result2["id"]
        ), f"Same domain name should return same record: {result1['id']} != {result2['id']}"


# ===========================================================================
# 9. Domain hierarchy
# ===========================================================================


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set -- skip DB tests",
)
class TestDomainHierarchy:
    """Load parent + child domains and verify relationship."""

    def test_domain_hierarchy_via_parent_name(self, pipeline):
        """Child domains can reference parents by name, not just ID."""
        _cleanup_test_data()

        parent = pipeline.load_domain(
            {
                "name": "Employment",
                "description": "Employment regulations",
            }
        )
        child = pipeline.load_domain(
            {
                "name": "Leave",
                "description": "Leave entitlements",
                "parent_domain_name": "Employment",
            }
        )

        assert (
            child["parent_domain_id"] == parent["id"]
        ), f"Child domain should reference parent: {child['parent_domain_id']} != {parent['id']}"

    def test_nested_domain_hierarchy(self, pipeline):
        """Three-level hierarchy: grandparent > parent > child."""
        grandparent = pipeline.load_domain(
            {
                "name": "Compensation",
                "description": "All compensation related",
            }
        )
        parent = pipeline.load_domain(
            {
                "name": "CPF System",
                "description": "CPF contributions and accounts",
                "parent_domain_name": "Compensation",
            }
        )
        child = pipeline.load_domain(
            {
                "name": "CPF Rates",
                "description": "Contribution rate tables",
                "parent_domain_name": "CPF System",
            }
        )

        assert parent["parent_domain_id"] == grandparent["id"]
        assert child["parent_domain_id"] == parent["id"]


# ===========================================================================
# 10. KB stats
# ===========================================================================


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set -- skip DB tests",
)
class TestKBStats:
    """Get statistics after loading content."""

    def test_get_kb_stats(self):
        """KB stats returns counts for all entity types."""
        from hr_advisory.kb.admin import get_kb_stats

        stats = get_kb_stats()
        assert "acts" in stats, f"Expected 'acts' in stats, got keys: {list(stats.keys())}"
        assert "domains" in stats
        assert "provisions" in stats
        assert "applicability_rules" in stats
        assert "practical_examples" in stats
        assert "cross_references" in stats
        assert "rate_tables" in stats
        # All should be integers >= 0
        for key, value in stats.items():
            if isinstance(value, int):
                assert value >= 0, f"{key} should be >= 0, got {value}"

    def test_kb_stats_after_loading(self, pipeline):
        """Stats should reflect loaded data."""
        _cleanup_test_data()

        pipeline.load_act({"title": "Stats Test Act", "short_name": "STA"})
        pipeline.load_domain({"name": "Stats Domain", "description": "For stats test"})

        from hr_advisory.kb.admin import get_kb_stats

        stats = get_kb_stats()
        assert stats["acts"] >= 1
        assert stats["domains"] >= 1


# ===========================================================================
# 11. Admin: add_provision and search_provisions
# ===========================================================================


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set -- skip DB tests",
)
class TestAdminFunctions:
    """Test admin CLI-style functions."""

    def test_add_provision_by_act_short_name(self, pipeline):
        """add_provision resolves act by short_name."""
        from hr_advisory.kb.admin import add_provision

        _cleanup_test_data()
        pipeline.load_act({"title": "Admin Test Act", "short_name": "ATA"})
        pipeline.load_domain({"name": "Admin Domain", "description": "For admin test"})

        result = add_provision(
            "ATA",
            {
                "section": "s_admin_test",
                "title": "Admin test provision",
                "formal_text": "This is a test provision for admin functions",
                "authority_level": "statute",
                "domain_name": "Admin Domain",
            },
        )
        assert "id" in result
        assert result["section"] == "s_admin_test"

    def test_search_provisions(self, pipeline):
        """search_provisions finds provisions by keyword."""
        from hr_advisory.kb.admin import search_provisions

        results = search_provisions("admin test")
        assert isinstance(results, list)
        # Should find the provision we just created
        assert len(results) >= 1, f"Expected at least 1 result for 'admin test', got {len(results)}"
        # Verify the result has expected structure
        assert "id" in results[0]
        assert "title" in results[0]

    def test_search_provisions_with_domain_filter(self, pipeline):
        """search_provisions can filter by domain."""
        from hr_advisory.kb.admin import search_provisions

        results = search_provisions("admin test", domain="Admin Domain")
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_search_provisions_no_results(self):
        """search_provisions returns empty list for no matches."""
        from hr_advisory.kb.admin import search_provisions

        results = search_provisions("xyzzy_nonexistent_query_12345")
        assert isinstance(results, list)
        assert len(results) == 0


# ===========================================================================
# 12. Embedding pipeline (graceful without API key)
# ===========================================================================


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set -- skip DB tests",
)
class TestEmbeddingPipeline:
    """Test embedding pipeline gracefully handles missing API key."""

    def test_generate_provision_text(self):
        """generate_provision_text combines fields into embeddable text."""
        from hr_advisory.kb.embeddings import EmbeddingPipeline

        ep = EmbeddingPipeline()
        text = ep.generate_provision_text(
            {
                "section": "s38",
                "title": "Hours of work",
                "plain_summary": "Max 8 hours/day",
                "formal_text": "An employee shall not work more than 8 hours.",
            }
        )
        assert "s38" in text
        assert "Hours of work" in text
        assert "Max 8 hours/day" in text
        assert "An employee shall not work more than 8 hours." in text

    def test_embed_all_provisions_without_api_key(self):
        """embed_all_provisions should skip gracefully without OpenAI API key."""
        from hr_advisory.kb.embeddings import EmbeddingPipeline

        # Force no API key
        import os

        original_key = os.environ.get("OPENAI_API_KEY", "")
        os.environ["OPENAI_API_KEY"] = ""
        try:
            ep = EmbeddingPipeline()
            result = ep.embed_all_provisions()
            assert (
                "skipped" in result or "error" in result or "total" in result
            ), f"Should return status dict, got: {result}"
            # Should not raise an error
        finally:
            if original_key:
                os.environ["OPENAI_API_KEY"] = original_key
            else:
                os.environ.pop("OPENAI_API_KEY", None)

    def test_embedding_pipeline_instantiation_with_model(self):
        """EmbeddingPipeline accepts a model parameter."""
        from hr_advisory.kb.embeddings import EmbeddingPipeline

        ep = EmbeddingPipeline(model="text-embedding-3-small")
        assert ep.model == "text-embedding-3-small"

    def test_embedding_pipeline_default_model(self):
        """EmbeddingPipeline has a default model."""
        from hr_advisory.kb.embeddings import EmbeddingPipeline

        ep = EmbeddingPipeline()
        assert ep.model == "text-embedding-3-small"


# ===========================================================================
# 13. Cross-reference loading
# ===========================================================================


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set -- skip DB tests",
)
class TestCrossReferenceLoading:
    """Load cross-references between provisions."""

    def test_load_cross_reference(self, pipeline):
        """Create a cross-reference between two provisions."""
        _cleanup_test_data()

        act = pipeline.load_act({"title": "Xref Test Act", "short_name": "XTA"})
        domain = pipeline.load_domain({"name": "Xref Domain"})

        prov1 = pipeline.load_provision(
            {
                "act_short_name": "XTA",
                "section": "s_xref_1",
                "title": "Source provision",
                "formal_text": "Source text",
                "authority_level": "statute",
                "domain_name": "Xref Domain",
            }
        )
        prov2 = pipeline.load_provision(
            {
                "act_short_name": "XTA",
                "section": "s_xref_2",
                "title": "Target provision",
                "formal_text": "Target text",
                "authority_level": "statute",
                "domain_name": "Xref Domain",
            }
        )

        result = pipeline.load_cross_reference(
            source_provision_id=prov1["id"],
            target_provision_id=prov2["id"],
            relationship_type="supplements",
            notes="s_xref_1 supplements s_xref_2",
        )
        assert "id" in result
        assert result["source_provision_id"] == prov1["id"]
        assert result["target_provision_id"] == prov2["id"]
        assert result["relationship_type"] == "supplements"


# ===========================================================================
# 14. Error handling
# ===========================================================================


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set -- skip DB tests",
)
class TestErrorHandling:
    """Pipeline should raise clear errors, not fail silently."""

    def test_load_provision_without_act_raises(self, pipeline):
        """Loading a provision with a nonexistent act short_name should raise ValueError."""
        with pytest.raises(ValueError, match="act"):
            pipeline.load_provision(
                {
                    "act_short_name": "NONEXISTENT_ACT_XYZ",
                    "section": "s1",
                    "title": "Test",
                    "formal_text": "Test text",
                    "authority_level": "statute",
                    "domain_name": "Test Domain",
                }
            )

    def test_load_provision_without_domain_raises(self, pipeline):
        """Loading a provision with a nonexistent domain name should raise ValueError."""
        _cleanup_test_data()
        pipeline.load_act({"title": "Error Test Act", "short_name": "ERTA"})

        with pytest.raises(ValueError, match="domain"):
            pipeline.load_provision(
                {
                    "act_short_name": "ERTA",
                    "section": "s1",
                    "title": "Test",
                    "formal_text": "Test text",
                    "authority_level": "statute",
                    "domain_name": "NONEXISTENT_DOMAIN_XYZ",
                }
            )
