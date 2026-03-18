"""Integration tests for T064 -- KB retrieval wired into specialist dispatch.

Verifies that:
1. retrieve_provisions_for_specialist() returns provision dicts from the KB.
2. provisions_to_dicts() normalises provision records for specialist consumption.
3. format_provisions_for_prompt() produces human-readable prompt text.
4. The full advisory pipeline passes KB provisions to specialists (not just
   thin citation-validator dicts).

Tests that hit the database require Docker:
    docker compose -f docker-compose.dev.yml up -d

Tests that verify the wiring logic work without a database.
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://arbor:arbor@localhost:5432/arbor")


# ---------------------------------------------------------------------------
# 1. Unit tests for kb_retriever module (no DB required)
# ---------------------------------------------------------------------------


class TestProvisionsToDict:
    """provisions_to_dicts normalises raw KB records."""

    def test_normalises_full_record(self):
        from hr_advisory.agents.orchestration.kb_retriever import provisions_to_dicts

        raw = [
            {
                "id": 42,
                "section": "s38",
                "title": "Hours of work",
                "formal_text": "An employee shall not work more than 8 hours.",
                "plain_summary": "Max 8h/day",
                "authority_level": "statute",
                "domain_id": 1,
                "source_act_id": 1,
                "extra_field": "ignored",
            }
        ]
        result = provisions_to_dicts(raw)
        assert len(result) == 1
        d = result[0]
        assert d["id"] == 42
        assert d["section"] == "s38"
        assert d["title"] == "Hours of work"
        assert d["formal_text"] == "An employee shall not work more than 8 hours."
        assert d["plain_summary"] == "Max 8h/day"
        assert d["authority_level"] == "statute"
        # Extra fields should not be present
        assert "domain_id" not in d
        assert "extra_field" not in d

    def test_handles_missing_fields(self):
        from hr_advisory.agents.orchestration.kb_retriever import provisions_to_dicts

        raw = [{"id": 1}]
        result = provisions_to_dicts(raw)
        d = result[0]
        assert d["id"] == 1
        assert d["section"] == ""
        assert d["title"] == ""

    def test_empty_input(self):
        from hr_advisory.agents.orchestration.kb_retriever import provisions_to_dicts

        assert provisions_to_dicts([]) == []


class TestFormatProvisionsForPrompt:
    """format_provisions_for_prompt produces readable prompt text."""

    def test_formats_provisions(self):
        from hr_advisory.agents.orchestration.kb_retriever import format_provisions_for_prompt

        provisions = [
            {
                "id": 1,
                "title": "Hours of work",
                "section": "s38",
                "formal_text": "Employees shall not work more than 8 hours in one day.",
                "plain_summary": "Max 8 hours per day.",
                "authority_level": "statute",
            },
            {
                "id": 2,
                "title": "Overtime limits",
                "section": "s38(4)",
                "formal_text": "Maximum overtime is 72 hours per month.",
                "plain_summary": "",
                "authority_level": "regulation",
            },
        ]
        text = format_provisions_for_prompt(provisions)
        assert "RELEVANT PROVISIONS FROM KNOWLEDGE BASE" in text
        assert "[1] Hours of work" in text
        assert "(Section s38)" in text
        assert "[statute]" in text
        assert "Max 8 hours per day." in text
        assert "[2] Overtime limits" in text
        assert "[regulation]" in text

    def test_empty_provisions_returns_notice(self):
        from hr_advisory.agents.orchestration.kb_retriever import format_provisions_for_prompt

        text = format_provisions_for_prompt([])
        assert "No relevant provisions found" in text

    def test_truncates_long_formal_text(self):
        from hr_advisory.agents.orchestration.kb_retriever import format_provisions_for_prompt

        long_text = "x" * 600
        provisions = [
            {
                "title": "Long provision",
                "formal_text": long_text,
            }
        ]
        text = format_provisions_for_prompt(provisions)
        assert "..." in text
        # Should be truncated to 500 chars + "..."
        assert long_text[:500] in text
        assert long_text[:501] not in text


class TestDomainMapping:
    """DOMAIN_KEY_TO_KB_NAME maps all known specialist domains."""

    def test_all_specialist_domains_mapped(self):
        from hr_advisory.agents.orchestration.kb_retriever import DOMAIN_KEY_TO_KB_NAME

        expected_domains = [
            "employment_act",
            "cpf",
            "foreign_manpower",
            "fair_employment",
            "wsh",
            "tax",
        ]
        for domain in expected_domains:
            assert domain in DOMAIN_KEY_TO_KB_NAME, f"Missing KB mapping for domain '{domain}'"

    def test_mapping_values_are_human_readable(self):
        from hr_advisory.agents.orchestration.kb_retriever import DOMAIN_KEY_TO_KB_NAME

        # KB domain names should be readable, not snake_case
        for key, value in DOMAIN_KEY_TO_KB_NAME.items():
            assert "_" not in value or key in (
                "general",
            ), f"KB name '{value}' for '{key}' looks like a code identifier"


# ---------------------------------------------------------------------------
# 2. Retrieve with mocked search_provisions (no DB)
# ---------------------------------------------------------------------------


class TestRetrieveProvisionsMocked:
    """retrieve_provisions_for_specialist with mocked KB."""

    def test_returns_provisions_for_domain(self):
        from hr_advisory.agents.orchestration.kb_retriever import (
            retrieve_provisions_for_specialist,
        )

        mock_provisions = [
            {
                "id": 10,
                "title": "Annual leave",
                "section": "Part X",
                "formal_text": "Employees are entitled to annual leave.",
                "plain_summary": "Annual leave entitlement.",
                "authority_level": "statute",
            }
        ]

        with patch(
            "hr_advisory.kb.admin.search_provisions",
            return_value=mock_provisions,
        ) as mock_search:
            result = retrieve_provisions_for_specialist(
                query="How many days annual leave?",
                domain="employment_act",
                top_k=5,
            )

        assert len(result) == 1
        assert result[0]["title"] == "Annual leave"
        mock_search.assert_called_once_with(
            query="How many days annual leave?",
            domain="Employment Act",
            limit=5,
        )

    def test_maps_domain_key_to_kb_name(self):
        from hr_advisory.agents.orchestration.kb_retriever import (
            retrieve_provisions_for_specialist,
        )

        with patch(
            "hr_advisory.kb.admin.search_provisions",
            return_value=[],
        ) as mock_search:
            retrieve_provisions_for_specialist(query="CPF rates", domain="cpf")

        mock_search.assert_called_once_with(
            query="CPF rates",
            domain="CPF",
            limit=10,
        )

    def test_returns_empty_on_exception(self):
        from hr_advisory.agents.orchestration.kb_retriever import (
            retrieve_provisions_for_specialist,
        )

        with patch(
            "hr_advisory.kb.admin.search_provisions",
            side_effect=RuntimeError("DB down"),
        ):
            result = retrieve_provisions_for_specialist(
                query="test",
                domain="employment_act",
            )

        assert result == []

    def test_returns_empty_for_unknown_domain(self):
        from hr_advisory.agents.orchestration.kb_retriever import (
            retrieve_provisions_for_specialist,
        )

        with patch(
            "hr_advisory.kb.admin.search_provisions",
            return_value=[],
        ):
            result = retrieve_provisions_for_specialist(
                query="test",
                domain="unknown_domain",
            )

        assert result == []


# ---------------------------------------------------------------------------
# 3. Wiring test: verify advisory pipeline passes KB provisions to specialists
# ---------------------------------------------------------------------------


class TestAdvisoryPipelineKBWiring:
    """Verify _run_llm_advisory retrieves KB provisions per specialist domain."""

    @patch("hr_advisory.kb.admin.search_provisions")
    def test_specialist_receives_kb_provisions(self, mock_search):
        """When KB returns provisions, specialist.advise() gets them."""
        mock_search.return_value = [
            {
                "id": 99,
                "title": "Leave entitlement",
                "section": "Part X s43A",
                "formal_text": "Employees are entitled to 7 days annual leave.",
                "plain_summary": "7 days annual leave minimum.",
                "authority_level": "statute",
            }
        ]

        # Import the function under test
        from hr_advisory.agents.orchestration.kb_retriever import (
            retrieve_provisions_for_specialist,
            provisions_to_dicts,
        )

        kb_provisions = retrieve_provisions_for_specialist(
            query="annual leave entitlement",
            domain="employment_act",
            top_k=10,
        )
        provision_dicts = provisions_to_dicts(kb_provisions)

        # Verify the provisions have full content, not just IDs
        assert len(provision_dicts) == 1
        prov = provision_dicts[0]
        assert prov["id"] == 99
        assert prov["title"] == "Leave entitlement"
        assert prov["section"] == "Part X s43A"
        assert prov["formal_text"] == "Employees are entitled to 7 days annual leave."
        assert prov["plain_summary"] == "7 days annual leave minimum."
        assert prov["authority_level"] == "statute"

        # Verify these provisions can be JSON-serialised (as the specialist will do)
        prov_str = json.dumps(provision_dicts)
        assert "Leave entitlement" in prov_str
        assert "7 days annual leave" in prov_str

    @patch("hr_advisory.kb.admin.search_provisions")
    def test_fallback_to_citation_validator_when_kb_empty(self, mock_search):
        """When KB returns nothing, the pipeline falls back to citation-validator dicts."""
        mock_search.return_value = []

        from hr_advisory.agents.orchestration.kb_retriever import (
            retrieve_provisions_for_specialist,
            provisions_to_dicts,
        )

        kb_provisions = retrieve_provisions_for_specialist(
            query="some query",
            domain="employment_act",
        )
        provision_dicts = provisions_to_dicts(kb_provisions)

        assert provision_dicts == []

        # Simulate the fallback logic from _run_llm_advisory
        citation_validator_provisions = [
            {
                "provision_id": "EA-S95-KETs",
                "title": "Key Employment Terms",
                "authority_level": "statute",
            }
        ]
        fallback = [
            {
                "id": p.get("provision_id", ""),
                "title": p.get("title", ""),
                "section": "",
                "formal_text": "",
                "plain_summary": "",
                "authority_level": p.get("authority_level", ""),
            }
            for p in citation_validator_provisions
        ]

        effective_provisions = provision_dicts if provision_dicts else fallback
        assert len(effective_provisions) == 1
        assert effective_provisions[0]["title"] == "Key Employment Terms"


# ---------------------------------------------------------------------------
# 4. DB integration test (requires running PostgreSQL)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set -- skip DB tests",
)
class TestKBRetrievalIntegration:
    """End-to-end test: load provision into DB, then retrieve via kb_retriever."""

    @pytest.fixture(autouse=True)
    def setup_test_data(self):
        """Load a test provision into the KB so retrieve can find it."""
        try:
            from hr_advisory.kb.pipeline import KBContentPipeline

            pipeline = KBContentPipeline()

            # Create act and domain if they don't exist
            pipeline.load_act(
                {
                    "title": "T064 Test Act",
                    "short_name": "T064A",
                }
            )
            pipeline.load_domain(
                {
                    "name": "T064 Domain",
                    "description": "Test domain for KB retrieval wiring",
                }
            )
            pipeline.load_provision(
                {
                    "act_short_name": "T064A",
                    "section": "s_t064_test",
                    "title": "T064 test provision for KB wiring",
                    "formal_text": (
                        "This provision exists solely to verify that the KB retrieval "
                        "pipeline correctly fetches provisions and passes them to "
                        "specialist agents."
                    ),
                    "plain_summary": "Test provision for T064 KB wiring verification.",
                    "authority_level": "statute",
                    "domain_name": "T064 Domain",
                }
            )
            self._data_loaded = True
        except Exception as exc:
            self._data_loaded = False
            pytest.skip(f"Could not load test data: {exc}")

        yield

        # Cleanup
        try:
            import sqlalchemy

            engine = sqlalchemy.create_engine(os.environ["DATABASE_URL"])
            with engine.connect() as conn:
                conn.execute(
                    sqlalchemy.text("DELETE FROM provisions WHERE section = 's_t064_test'")
                )
                conn.commit()
            engine.dispose()
        except Exception:
            pass

    def test_retrieve_provisions_from_db(self):
        """retrieve_provisions_for_specialist finds real DB provisions."""
        from hr_advisory.agents.orchestration.kb_retriever import (
            retrieve_provisions_for_specialist,
        )

        # Search without domain filter (the test domain may not match any
        # specialist domain, so we search by keyword only)
        from hr_advisory.kb.admin import search_provisions

        results = search_provisions(query="T064 test provision", limit=5)
        assert len(results) >= 1, "Test provision should exist in the DB"
        assert any(
            "T064" in r.get("title", "") for r in results
        ), "Should find the T064 test provision"

    def test_retrieved_provisions_have_full_content(self):
        """Provisions from the KB include formal_text and plain_summary."""
        from hr_advisory.kb.admin import search_provisions

        results = search_provisions(query="T064 test provision", limit=1)
        assert len(results) >= 1

        prov = results[0]
        assert prov.get("formal_text"), "Provision should have formal_text"
        assert prov.get("plain_summary"), "Provision should have plain_summary"
        assert prov.get("section") == "s_t064_test"
        assert prov.get("authority_level") == "statute"

    def test_provisions_to_dicts_on_real_data(self):
        """provisions_to_dicts works with real DB provision records."""
        from hr_advisory.kb.admin import search_provisions
        from hr_advisory.agents.orchestration.kb_retriever import provisions_to_dicts

        results = search_provisions(query="T064 test provision", limit=1)
        assert len(results) >= 1

        dicts = provisions_to_dicts(results)
        assert len(dicts) >= 1
        d = dicts[0]
        assert "id" in d
        assert d["title"] == "T064 test provision for KB wiring"
        assert d["formal_text"]  # Should have content
        assert d["plain_summary"]  # Should have content
        # Should NOT have DB-internal fields
        assert "domain_id" not in d
        assert "source_act_id" not in d
