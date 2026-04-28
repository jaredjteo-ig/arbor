"""Advisory engine quality benchmark tests.

Tests that the advisory engine infrastructure (KB search, system prompt,
tool results) is capable of producing ChatGPT-quality responses for
the 5 benchmark queries. Does NOT call the LLM — tests the data pipeline.
"""

import json
import pytest

from hr_advisory.agents.advisory_engine import (
    _build_system_prompt,
    _search_python_kb,
    _execute_tool_call,
)


class TestSystemPrompt:
    """System prompt must set boundaries, not prescriptive rules."""

    def test_identity_is_senior_advisor(self):
        prompt = _build_system_prompt()
        assert "senior HR advisor" in prompt
        assert "Singapore SMEs" in prompt

    def test_anti_flattery_boundary(self):
        prompt = _build_system_prompt()
        assert "Never use flattery" in prompt
        assert "filler phrases" in prompt
        assert "Lead with the answer" in prompt

    def test_confidence_ladder_present(self):
        prompt = _build_system_prompt()
        assert "CONFIDENCE LADDER" in prompt
        assert ">90%" in prompt
        assert "<50%" in prompt

    def test_allows_general_knowledge(self):
        """Engine must NOT be constrained to KB-only answers."""
        prompt = _build_system_prompt()
        assert "you still know the law" in prompt
        assert "answer anyway" in prompt

    def test_user_context_injection(self):
        prompt = _build_system_prompt(user_context={"role": "owner", "name": "Sarah"})
        assert "Sarah" in prompt
        assert "owner" in prompt
        assert "strategic" in prompt.lower() or "decision-maker" in prompt.lower()

    def test_company_context_injection(self):
        prompt = _build_system_prompt(
            company_context={"name": "Acme Pte Ltd", "sector": "Technology"}
        )
        assert "Acme Pte Ltd" in prompt
        assert "Technology" in prompt

    def test_no_prescriptive_template(self):
        """Prompt should NOT contain rigid response templates."""
        prompt = _build_system_prompt()
        assert "MANDATORY RESPONSE TEMPLATE" not in prompt
        assert "MUST follow this structure" not in prompt
        assert "200-350 words" not in prompt


class TestKBSearchBenchmarks:
    """KB search must return relevant provisions for all 5 ChatGPT benchmark topics."""

    def test_final_salary_payment(self):
        """ChatGPT benchmark: 'what do i have to pay employees by their last day of work?'"""
        results = _search_python_kb("salary payment last day termination", limit=5)
        sections = [r["section"] for r in results]
        assert "EA-S21" in sections, "Must find Payment of Salary Timeline"

    def test_maternity_resignation(self):
        """ChatGPT benchmark: flexible maternity leave resignation scenario."""
        results = _search_python_kb("maternity leave resignation flexible", limit=5)
        sections = [r["section"] for r in results]
        assert "CDCSA-ML-RESIGN" in sections, "Must find Maternity Leave and Resignation"
        # Verify the provision has rich interpretation notes
        resign_prov = [r for r in results if r["section"] == "CDCSA-ML-RESIGN"][0]
        assert "forfeited" in resign_prov.get("interpretation_notes", "").lower()
        assert "encashable" in resign_prov.get("interpretation_notes", "").lower()

    def test_collective_agreement_procedures(self):
        """ChatGPT benchmark: 'what do i have to do after concluding a collective agreement?'"""
        results = _search_python_kb("collective agreement union lodge IAC", limit=5)
        sections = [r["section"] for r in results]
        assert "IRA-S17" in sections, "Must find Notification of Collective Agreement"

    def test_retrenchment_unionised(self):
        """ChatGPT benchmark: 'retrenchment in unionised company'."""
        results = _search_python_kb("retrenchment unionised company", limit=5)
        sections = [r["section"] for r in results]
        assert "IRA-RETRENCH-UNION" in sections, "Must find Retrenchment in Unionised Companies"
        # Verify Lazada reference exists in interpretation notes
        union_prov = [r for r in results if r["section"] == "IRA-RETRENCH-UNION"][0]
        notes = union_prov.get("interpretation_notes", "")
        assert "lazada" in notes.lower(), "Must include Lazada lessons"

    def test_retrenchment_benefits_benchmarks(self):
        """ChatGPT benchmark: retrenchment benefits market data."""
        results = _search_python_kb("retrenchment benefits market benchmark", limit=5)
        sections = [r["section"] for r in results]
        assert "IRA-RETRENCH-BENEFITS" in sections, "Must find Retrenchment Benefits"
        benefits_prov = [r for r in results if r["section"] == "IRA-RETRENCH-BENEFITS"][0]
        notes = benefits_prov.get("interpretation_notes", "")
        assert "2 weeks" in notes, "Must include market benchmark ranges"
        assert "1 month" in notes


class TestToolResultEnrichment:
    """Tool results must include interpretation_notes and practical_examples."""

    def test_search_kb_includes_interpretation_notes(self):
        result_json = _execute_tool_call("search_kb", {"query": "CPF contribution rates"})
        results = json.loads(result_json)
        # At least one result should have interpretation_notes
        has_notes = any(r.get("interpretation_notes") for r in results)
        assert has_notes, "search_kb must include interpretation_notes in results"

    def test_search_kb_includes_practical_examples(self):
        # Use a query whose top-matched provisions have practical_examples in
        # the seeded KB ("annual leave" — provision 4 has 2 examples in the
        # current production KB; "maternity leave" provisions have none yet).
        result_json = _execute_tool_call("search_kb", {"query": "annual leave entitlement"})
        results = json.loads(result_json)
        has_examples = any(r.get("practical_examples") for r in results)
        assert has_examples, "search_kb must include practical_examples in results"

    def test_search_kb_result_structure(self):
        result_json = _execute_tool_call("search_kb", {"query": "annual leave"})
        results = json.loads(result_json)
        assert len(results) > 0
        first = results[0]
        assert "section" in first
        assert "title" in first
        assert "plain_summary" in first
        assert "authority_level" in first


class TestIRActCoverage:
    """Industrial Relations Act must be searchable and complete."""

    def test_ir_act_provisions_exist(self):
        from hr_advisory.kb.content.industrial_relations import get_bundle

        bundle = get_bundle()
        assert len(bundle["provisions"]) >= 9

    def test_ir_act_domains(self):
        from hr_advisory.kb.content.industrial_relations import get_bundle

        bundle = get_bundle()
        domain_names = [d["name"] for d in bundle["domains"]]
        assert "Collective Bargaining" in domain_names
        assert "Industrial Disputes" in domain_names
        assert "Retrenchment" in domain_names

    def test_ir_act_cross_references(self):
        from hr_advisory.kb.content.industrial_relations import get_bundle

        bundle = get_bundle()
        assert len(bundle["cross_references"]) >= 2

    def test_retrenchment_domain_searchable(self):
        """The 'Retrenchment' domain filter must work."""
        results = _search_python_kb("retrenchment benefits", domain="Retrenchment", limit=5)
        assert len(results) > 0
        sections = [r["section"] for r in results]
        assert any(s.startswith("IRA-RETRENCH") for s in sections)
