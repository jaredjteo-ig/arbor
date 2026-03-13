"""Unit tests for the adversarial runner infrastructure.

Tests the runner's scenario management, scoring aggregation, and report
generation — NOT the actual LLM pipeline (that requires integration tests).
"""

from __future__ import annotations

import pytest

from hr_advisory.quality.adversarial_runner import (
    ADVERSARIAL_SCENARIOS,
    AdversarialRunner,
    RunSummary,
    ScenarioResult,
)


# ---------------------------------------------------------------------------
# Scenario coverage
# ---------------------------------------------------------------------------


class TestScenarioCoverage:
    """Verify that all 8 categories have 8 scenarios each."""

    def test_eight_categories(self) -> None:
        assert len(ADVERSARIAL_SCENARIOS) == 8

    def test_eight_scenarios_per_category(self) -> None:
        for category, items in ADVERSARIAL_SCENARIOS.items():
            assert len(items) == 8, f"{category} has {len(items)} scenarios, expected 8"

    def test_total_64_scenarios(self) -> None:
        total = sum(len(items) for items in ADVERSARIAL_SCENARIOS.values())
        assert total == 64

    def test_scenario_ids_unique(self) -> None:
        ids = []
        for items in ADVERSARIAL_SCENARIOS.values():
            for item in items:
                ids.append(item["id"])
        assert len(ids) == len(set(ids)), "Duplicate scenario IDs found"

    def test_all_scenarios_have_id_and_query(self) -> None:
        for category, items in ADVERSARIAL_SCENARIOS.items():
            for item in items:
                assert "id" in item, f"Missing id in {category}"
                assert "query" in item, f"Missing query in {category}"
                assert len(item["query"]) > 10, f"Query too short in {category}: {item['id']}"

    def test_expected_categories(self) -> None:
        expected = {
            "employment_act",
            "cpf",
            "foreign_manpower",
            "fair_employment",
            "tax",
            "wsh",
            "pdpa",
            "cross_domain",
        }
        assert set(ADVERSARIAL_SCENARIOS.keys()) == expected


# ---------------------------------------------------------------------------
# ScenarioResult
# ---------------------------------------------------------------------------


class TestScenarioResult:
    """Test ScenarioResult dataclass."""

    def test_create_result(self) -> None:
        result = ScenarioResult(
            scenario_id="EA-01",
            category="employment_act",
            query="Can I terminate?",
        )
        assert result.scenario_id == "EA-01"
        assert result.overall_score == 0.0
        assert result.passed is False
        assert result.error is None

    def test_result_with_scores(self) -> None:
        result = ScenarioResult(
            scenario_id="EA-01",
            category="employment_act",
            query="Can I terminate?",
            scores={"citation_quality": 4.0, "risk_awareness": 5.0},
            overall_score=4.0,
            passed=True,
        )
        assert result.passed is True
        assert result.overall_score == 4.0

    def test_result_with_error(self) -> None:
        result = ScenarioResult(
            scenario_id="EA-01",
            category="employment_act",
            query="Can I terminate?",
            error="LLM timeout",
        )
        assert result.error == "LLM timeout"
        assert result.passed is False


# ---------------------------------------------------------------------------
# RunSummary
# ---------------------------------------------------------------------------


class TestRunSummary:
    """Test RunSummary dataclass."""

    def test_empty_summary(self) -> None:
        summary = RunSummary()
        assert summary.total_scenarios == 0
        assert summary.avg_overall_score == 0.0

    def test_summary_with_data(self) -> None:
        summary = RunSummary(
            total_scenarios=8,
            scenarios_run=8,
            scenarios_passed=6,
            scenarios_failed=2,
            avg_overall_score=3.8,
            per_category_avg={"employment_act": 4.0, "cpf": 3.5},
            per_dimension_avg={"citation_quality": 3.5, "risk_awareness": 4.2},
            lowest_category="cpf",
            lowest_dimension="citation_quality",
        )
        assert summary.scenarios_passed == 6
        assert summary.lowest_category == "cpf"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


class TestAdversarialRunner:
    """Test the runner's internal summarization logic."""

    def test_runner_init(self) -> None:
        runner = AdversarialRunner()
        assert runner._results == []

    def test_summarize_empty(self) -> None:
        runner = AdversarialRunner()
        summary = runner._summarize([], 0.0)
        assert summary.total_scenarios == 0

    def test_summarize_with_results(self) -> None:
        runner = AdversarialRunner()
        results = [
            ScenarioResult(
                scenario_id="EA-01",
                category="employment_act",
                query="q1",
                scores={"citation_quality": 4.0, "risk_awareness": 5.0},
                overall_score=4.0,
                passed=True,
            ),
            ScenarioResult(
                scenario_id="CPF-01",
                category="cpf",
                query="q2",
                scores={"citation_quality": 2.0, "risk_awareness": 3.0},
                overall_score=2.0,
                passed=False,
            ),
        ]
        summary = runner._summarize(results, 10.0)
        assert summary.total_scenarios == 2
        assert summary.scenarios_passed == 1
        assert summary.scenarios_failed == 1
        assert summary.avg_overall_score == 3.0
        assert summary.per_category_avg["employment_act"] == 4.0
        assert summary.per_category_avg["cpf"] == 2.0
        assert summary.lowest_category == "cpf"
        assert summary.duration_seconds == 10.0

    def test_summarize_with_errors(self) -> None:
        runner = AdversarialRunner()
        results = [
            ScenarioResult(
                scenario_id="EA-01",
                category="employment_act",
                query="q1",
                error="Timeout",
            ),
        ]
        summary = runner._summarize(results, 1.0)
        assert summary.total_scenarios == 1
        assert summary.scenarios_errored == 1
        assert summary.scenarios_run == 0

    def test_generate_report(self) -> None:
        runner = AdversarialRunner()
        summary = RunSummary(
            total_scenarios=8,
            scenarios_run=8,
            scenarios_passed=6,
            scenarios_failed=2,
            avg_overall_score=3.8,
            per_category_avg={"employment_act": 4.0, "cpf": 3.5},
            per_dimension_avg={"citation_quality": 3.5, "risk_awareness": 4.2},
            lowest_category="cpf",
            lowest_dimension="citation_quality",
            failing_scenarios=["EA-03", "CPF-04"],
            duration_seconds=120.0,
        )
        report = runner.generate_report(summary)
        assert "# Adversarial Test Run Report" in report
        assert "3.80" in report
        assert "cpf" in report.lower()
        assert "EA-03" in report
        assert "CPF-04" in report
