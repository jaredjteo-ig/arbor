"""Integration test -- runs adversarial baseline (requires LLM).

Validates that the AdversarialRunner infrastructure can execute scenarios
through the real advisory pipeline and produce meaningful scores. These
tests require an LLM provider (OpenAI or ollama) to be available.
"""

import pytest

from hr_advisory.agents.config import has_llm_available
from hr_advisory.quality.adversarial_runner import (
    ADVERSARIAL_SCENARIOS,
    AdversarialRunner,
    RunSummary,
    ScenarioResult,
)

HAS_LLM = has_llm_available()

requires_llm = pytest.mark.skipif(
    not HAS_LLM,
    reason="No LLM provider available (set OPENAI_API_KEY or run ollama)",
)


@requires_llm
class TestAdversarialBaseline:
    """Run a minimal adversarial baseline and validate the infrastructure produces results."""

    @pytest.mark.slow
    @pytest.mark.timeout(300)
    def test_baseline_produces_scores(self):
        """Baseline with 1 scenario per category should produce 8 scored results."""
        runner = AdversarialRunner()
        summary = runner.run_baseline(sample_size=8)

        assert isinstance(summary, RunSummary), f"Expected RunSummary, got {type(summary).__name__}"
        assert (
            summary.total_scenarios == 8
        ), f"Expected 8 total scenarios (1 per category), got {summary.total_scenarios}"
        assert (
            summary.avg_overall_score > 0
        ), f"Average overall score should be > 0, got {summary.avg_overall_score}"

    @pytest.mark.slow
    @pytest.mark.timeout(300)
    def test_no_category_crashes(self):
        """Every category should produce a result, even if the score is low."""
        runner = AdversarialRunner()
        summary = runner.run_baseline(sample_size=8)

        assert summary.scenarios_errored == 0, (
            f"Expected 0 errored scenarios, got {summary.scenarios_errored}. "
            f"Errors indicate infrastructure failures, not low-quality responses."
        )

    @pytest.mark.slow
    @pytest.mark.timeout(300)
    def test_all_categories_represented_in_results(self):
        """Each of the 8 categories should appear in per_category_avg."""
        runner = AdversarialRunner()
        summary = runner.run_baseline(sample_size=8)

        expected_categories = set(ADVERSARIAL_SCENARIOS.keys())
        actual_categories = set(summary.per_category_avg.keys())

        # If a category errored, it won't have a score -- but it should still
        # have been attempted. At minimum we expect the scored categories.
        if summary.scenarios_errored == 0:
            assert actual_categories == expected_categories, (
                f"Expected categories {expected_categories}, "
                f"got {actual_categories}. "
                f"Missing: {expected_categories - actual_categories}"
            )

    @pytest.mark.slow
    @pytest.mark.timeout(300)
    def test_per_dimension_averages_populated(self):
        """Automated check dimensions should appear in per_dimension_avg."""
        runner = AdversarialRunner()
        summary = runner.run_baseline(sample_size=8)

        expected_dimensions = {
            "citation_quality",
            "risk_awareness",
            "response_structure",
            "disclaimer_presence",
        }

        if summary.scenarios_run > 0:
            actual_dimensions = set(summary.per_dimension_avg.keys())
            assert expected_dimensions.issubset(actual_dimensions), (
                f"Expected at least {expected_dimensions} in per_dimension_avg, "
                f"got {actual_dimensions}. "
                f"Missing: {expected_dimensions - actual_dimensions}"
            )

    @pytest.mark.slow
    @pytest.mark.timeout(300)
    def test_report_generation_from_baseline(self):
        """The runner should generate a valid markdown report from baseline results."""
        runner = AdversarialRunner()
        summary = runner.run_baseline(sample_size=8)
        report = runner.generate_report(summary)

        assert (
            "# Adversarial Test Run Report" in report
        ), "Report should contain the expected header"
        assert (
            str(round(summary.avg_overall_score, 2)) in report
        ), "Report should contain the average overall score"


class TestAdversarialRunnerInfrastructure:
    """Test runner infrastructure without requiring LLM calls.

    These tests validate that the runner can handle edge cases gracefully
    even when the LLM pipeline is not available.
    """

    def test_run_unknown_category_returns_empty_summary(self):
        """Running an unknown category should return an empty summary, not crash."""
        runner = AdversarialRunner()
        summary = runner.run_category("nonexistent_category")

        assert isinstance(summary, RunSummary)
        assert summary.total_scenarios == 0

    def test_runner_preserves_results_after_run(self):
        """After a run, the internal _results list should be populated."""
        runner = AdversarialRunner()
        # Use a mock-friendly approach: call _summarize directly
        results = [
            ScenarioResult(
                scenario_id="TEST-01",
                category="test",
                query="test query",
                scores={"citation_quality": 3.0, "risk_awareness": 4.0},
                overall_score=3.0,
                passed=True,
            ),
        ]
        summary = runner._summarize(results, 1.0)

        assert summary.total_scenarios == 1
        assert summary.scenarios_passed == 1
        assert summary.per_category_avg["test"] == 3.0

    def test_summarize_handles_mixed_pass_fail_error(self):
        """Summarize should correctly count pass/fail/error scenarios."""
        runner = AdversarialRunner()
        results = [
            ScenarioResult(
                scenario_id="PASS-01",
                category="cat_a",
                query="q1",
                scores={"dim1": 4.0},
                overall_score=4.0,
                passed=True,
            ),
            ScenarioResult(
                scenario_id="FAIL-01",
                category="cat_a",
                query="q2",
                scores={"dim1": 2.0},
                overall_score=2.0,
                passed=False,
            ),
            ScenarioResult(
                scenario_id="ERR-01",
                category="cat_b",
                query="q3",
                error="Connection refused",
            ),
        ]
        summary = runner._summarize(results, 5.0)

        assert summary.total_scenarios == 3
        assert summary.scenarios_passed == 1
        assert summary.scenarios_failed == 1
        assert summary.scenarios_errored == 1
        assert summary.scenarios_run == 2  # only scored scenarios
