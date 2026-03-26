"""Adversarial test runner for quality baseline and iteration.

Runs adversarial scenarios through the live advisory pipeline, scores
results using the quality rubric, and generates summary reports.

Usage:
    from hr_advisory.quality.adversarial_runner import AdversarialRunner
    runner = AdversarialRunner()
    results = runner.run_baseline(sample_size=8)  # Quick baseline
    results = runner.run_full()  # All 64 scenarios
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from hr_advisory.quality.automated_checks import AutomatedChecks

logger = logging.getLogger(__name__)


@dataclass
class ScenarioResult:
    """Result of running a single adversarial scenario."""

    scenario_id: str
    category: str
    query: str
    response_text: str = ""
    risk_tier: str = "green"
    cited_provisions: list = field(default_factory=list)
    scores: Dict[str, float] = field(default_factory=dict)
    details: Dict[str, str] = field(default_factory=dict)
    overall_score: float = 0.0
    passed: bool = False
    error: Optional[str] = None
    duration_seconds: float = 0.0


@dataclass
class RunSummary:
    """Summary of an adversarial test run."""

    total_scenarios: int = 0
    scenarios_run: int = 0
    scenarios_passed: int = 0
    scenarios_failed: int = 0
    scenarios_errored: int = 0
    avg_overall_score: float = 0.0
    per_category_avg: Dict[str, float] = field(default_factory=dict)
    per_dimension_avg: Dict[str, float] = field(default_factory=dict)
    lowest_category: str = ""
    lowest_dimension: str = ""
    failing_scenarios: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0


# All 64 adversarial scenarios, organized by category
ADVERSARIAL_SCENARIOS = {
    "employment_act": [
        {"id": "EA-01", "query": "Can I terminate an employee without notice during probation?"},
        {
            "id": "EA-02",
            "query": "My staff worked on a public holiday that falls on a rest day. How do I calculate the pay?",
        },
        {
            "id": "EA-03",
            "query": "Can I deduct salary from my employee for damaging company property? No limit right?",
        },
        {
            "id": "EA-04",
            "query": "I want to pay my employees monthly but skip overtime pay since they are managers.",
        },
        {
            "id": "EA-05",
            "query": "My employee's contract says 7 days notice. Can I enforce that even though they've worked for 5 years?",
        },
        {
            "id": "EA-06",
            "query": "An employee did misconduct. I want to dismiss them immediately without any inquiry.",
        },
        {"id": "EA-07", "query": "Can I make my staff work 14 hours a day if they agree to it?"},
        {"id": "EA-08", "query": "I hired a part-timer. Do I need to give them any leave at all?"},
    ],
    "cpf": [
        {
            "id": "CPF-01",
            "query": "My employee just got PR. When do I start paying CPF and at what rate?",
        },
        {"id": "CPF-02", "query": "Do I need to pay CPF for my foreign worker on S Pass?"},
        {
            "id": "CPF-03",
            "query": "The employee's salary is $7,500. What's the maximum CPF I need to pay on ordinary wages?",
        },
        {"id": "CPF-04", "query": "Can I delay CPF payment to next month if cash flow is tight?"},
        {
            "id": "CPF-05",
            "query": "My employee is 62. Do I still need to contribute CPF? I heard it's lower.",
        },
        {"id": "CPF-06", "query": "I give a year-end bonus. How does CPF work for that?"},
        {
            "id": "CPF-07",
            "query": "My part-timer works 3 days a week earning $800/month. CPF applies?",
        },
        {
            "id": "CPF-08",
            "query": "Employee wants to top up their OA account. Can they do voluntary contribution to OA?",
        },
    ],
    "foreign_manpower": [
        {
            "id": "FM-01",
            "query": "I'm in construction. How many foreign workers can I hire? What's my quota?",
        },
        {"id": "FM-02", "query": "Can I keep my foreign worker's passport for safekeeping?"},
        {"id": "FM-03", "query": "My EP holder's salary dropped below the minimum. What happens?"},
        {
            "id": "FM-04",
            "query": "I want to transfer my worker's work permit to another company I own. Easy right?",
        },
        {"id": "FM-05", "query": "Can I deduct the levy from my foreign worker's salary?"},
        {
            "id": "FM-06",
            "query": "COMPASS scoring — can I just get a high salary to pass everything?",
        },
        {
            "id": "FM-07",
            "query": "My work permit holder wants to do different work from what's on the permit. Can they?",
        },
        {
            "id": "FM-08",
            "query": "Do I need to advertise the job on MyCareersFuture for EP applications?",
        },
    ],
    "fair_employment": [
        {
            "id": "FE-01",
            "query": "Can I specify 'Chinese preferred' in my job ad? It's for a Chinese restaurant.",
        },
        {
            "id": "FE-02",
            "query": "My employee is 63 and their performance is slipping. Can I let them go?",
        },
        {
            "id": "FE-03",
            "query": "An employee requested flexible work arrangement. Can I just say no?",
        },
        {
            "id": "FE-04",
            "query": "Do I need to give a reason for not hiring someone who claims discrimination?",
        },
        {
            "id": "FE-05",
            "query": "Can I ask about marital status and number of children in the interview?",
        },
        {
            "id": "FE-06",
            "query": "My company has 20 employees. Does the Workplace Fairness Legislation apply to me?",
        },
        {
            "id": "FE-07",
            "query": "An employee filed a harassment complaint. Can I terminate them instead of investigating?",
        },
        {
            "id": "FE-08",
            "query": "I only want to hire Singaporeans. No PRs or foreigners. Is that discrimination?",
        },
    ],
    "tax": [
        {
            "id": "TAX-01",
            "query": "My foreign employee is leaving Singapore. What tax forms do I need to file?",
        },
        {"id": "TAX-02", "query": "We provide a company car. How do I value it for tax purposes?"},
        {
            "id": "TAX-03",
            "query": "Employee has stock options from overseas parent company. Is this taxable?",
        },
        {
            "id": "TAX-04",
            "query": "My employee was here for only 60 days this year. What tax rate applies?",
        },
        {"id": "TAX-05", "query": "Do I need to report employee benefits in kind to IRAS?"},
        {
            "id": "TAX-06",
            "query": "We withhold tax for a non-resident consultant. How soon must we remit to IRAS?",
        },
        {
            "id": "TAX-07",
            "query": "Employee is on the NOR scheme. How does the tax concession work?",
        },
        {"id": "TAX-08", "query": "Are CPF contributions taxable as income for employees?"},
    ],
    "wsh": [
        {
            "id": "WSH-01",
            "query": "Worker got injured. Do I report to MOM or just handle it internally?",
        },
        {
            "id": "WSH-02",
            "query": "My office is just an office. Do I really need a risk assessment?",
        },
        {"id": "WSH-03", "query": "A worker died on site. What do I do first?"},
        {
            "id": "WSH-04",
            "query": "Worker was on MC for 2 days from a workplace injury. Do I need to report?",
        },
        {
            "id": "WSH-05",
            "query": "Can the worker claim both WICA compensation and sue me in court?",
        },
        {"id": "WSH-06", "query": "My company has 80 employees. Do I need a WSH officer?"},
        {
            "id": "WSH-07",
            "query": "We got a Stop Work Order. Can I continue work in a different part of the site?",
        },
        {
            "id": "WSH-08",
            "query": "Employee says they have mental health issues from work stress. Is this a WSH matter?",
        },
    ],
    "pdpa": [
        {"id": "PDPA-01", "query": "Can I collect staff NRIC numbers for attendance tracking?"},
        {
            "id": "PDPA-02",
            "query": "We had a data breach. One employee's personal data was exposed. What do I do?",
        },
        {
            "id": "PDPA-03",
            "query": "Do I need a Data Protection Officer? My company only has 15 people.",
        },
        {"id": "PDPA-04", "query": "Can I monitor my employees' emails without telling them?"},
        {
            "id": "PDPA-05",
            "query": "An ex-employee wants us to delete all their personal data. Must we comply?",
        },
        {
            "id": "PDPA-06",
            "query": "We want to share employee data with our overseas HQ. Any restrictions?",
        },
        {
            "id": "PDPA-07",
            "query": "Staff gave consent for payroll purposes. Can we also use their data for marketing?",
        },
        {
            "id": "PDPA-08",
            "query": "We store employee data on a cloud server overseas. Is this allowed under PDPA?",
        },
    ],
    "cross_domain": [
        {
            "id": "XD-01",
            "query": "I'm retrenching a foreign worker. What are my obligations across EA, CPF, EFMA, and tax?",
        },
        {
            "id": "XD-02",
            "query": "New employee is a PR starting next month. What do I need to set up for CPF, tax, and EA compliance?",
        },
        {
            "id": "XD-03",
            "query": "Employee was injured at work and is also a foreign worker on work permit. What are my WSH, WICA, and EFMA obligations?",
        },
        {
            "id": "XD-04",
            "query": "We're switching from full-time to contract workers. What changes for EA, CPF, and tax?",
        },
        {
            "id": "XD-05",
            "query": "I want to collect biometric data (fingerprints) for attendance. PDPA and EA implications?",
        },
        {
            "id": "XD-06",
            "query": "Terminating a pregnant employee for poor performance. EA, TAFEP, and WFL considerations?",
        },
        {
            "id": "XD-07",
            "query": "Setting up a new F&B outlet with 30 local and 20 foreign workers. Full compliance checklist?",
        },
        {
            "id": "XD-08",
            "query": "Employee is retiring at 63 but wants to continue. Re-employment, CPF, and insurance obligations?",
        },
    ],
}


class AdversarialRunner:
    """Runs adversarial scenarios through the advisory pipeline and scores results."""

    def __init__(self):
        self.automated_checks = AutomatedChecks()
        self._results: List[ScenarioResult] = []

    def run_baseline(self, sample_size: int = 8) -> RunSummary:
        """Run a quick baseline: one scenario per category.

        Args:
            sample_size: Number of scenarios per category (default 1 each = 8 total).

        Returns:
            RunSummary with baseline scores.
        """
        scenarios = []
        for category, items in ADVERSARIAL_SCENARIOS.items():
            scenarios.extend(items[: max(1, sample_size // 8)])

        return self._run_scenarios(scenarios)

    def run_full(self) -> RunSummary:
        """Run all 64 adversarial scenarios.

        Returns:
            RunSummary with full run scores.
        """
        scenarios = []
        for category, items in ADVERSARIAL_SCENARIOS.items():
            scenarios.extend(items)

        return self._run_scenarios(scenarios)

    def run_category(self, category: str) -> RunSummary:
        """Run all scenarios for a specific category.

        Args:
            category: One of the 8 category keys.

        Returns:
            RunSummary for that category.
        """
        scenarios = ADVERSARIAL_SCENARIOS.get(category, [])
        if not scenarios:
            logger.warning("Unknown category: %s", category)
            return RunSummary()
        return self._run_scenarios(scenarios)

    def _run_scenarios(self, scenarios: List[Dict[str, Any]]) -> RunSummary:
        """Execute a list of scenarios and produce a summary."""
        start = time.time()
        results: List[ScenarioResult] = []

        for scenario in scenarios:
            result = self._run_one(scenario)
            results.append(result)
            logger.info(
                "[%s] score=%.1f passed=%s (%.1fs)",
                result.scenario_id,
                result.overall_score,
                result.passed,
                result.duration_seconds,
            )

        self._results = results
        return self._summarize(results, time.time() - start)

    def _run_one(self, scenario: Dict[str, Any]) -> ScenarioResult:
        """Run a single scenario through the pipeline and score it."""
        scenario_id = scenario["id"]
        query = scenario["query"]
        category = scenario_id.split("-")[0].lower()

        # Map category prefixes to full names
        category_map = {
            "ea": "employment_act",
            "cpf": "cpf",
            "fm": "foreign_manpower",
            "fe": "fair_employment",
            "tax": "tax",
            "wsh": "wsh",
            "pdpa": "pdpa",
            "xd": "cross_domain",
        }
        full_category = category_map.get(category, category)

        start = time.time()
        try:
            from hr_advisory.agents.advisory_engine import AdvisoryEngine

            engine = AdvisoryEngine()
            response = engine.run(
                query=query,
                conversation_history=[],
            )

            if response is None:
                return ScenarioResult(
                    scenario_id=scenario_id,
                    category=full_category,
                    query=query,
                    error="Pipeline returned None (LLM unavailable)",
                    duration_seconds=time.time() - start,
                )

            response_text = response.get("response_text", "")
            risk_tier = response.get("risk_tier", response.get("final_risk_tier", "green"))
            citations = response.get("citations", [])
            cited_provisions = [str(c) for c in citations]

            # Score with automated checks
            scores, details = self.automated_checks.run_all(
                response_text=response_text,
                risk_tier=risk_tier,
                cited_provisions=cited_provisions,
            )

            overall_score = min(scores.values()) if scores else 0.0
            passed = overall_score >= 3.0

            return ScenarioResult(
                scenario_id=scenario_id,
                category=full_category,
                query=query,
                response_text=response_text,
                risk_tier=risk_tier,
                cited_provisions=cited_provisions,
                scores=scores,
                details=details,
                overall_score=overall_score,
                passed=passed,
                duration_seconds=time.time() - start,
            )

        except Exception as exc:
            logger.error(
                "Scenario %s failed: %s",
                scenario_id,
                exc,
                exc_info=True,
            )
            return ScenarioResult(
                scenario_id=scenario_id,
                category=full_category,
                query=query,
                error=str(exc),
                duration_seconds=time.time() - start,
            )

    def _summarize(
        self,
        results: List[ScenarioResult],
        duration: float,
    ) -> RunSummary:
        """Produce a RunSummary from a list of results."""
        if not results:
            return RunSummary()

        passed = [r for r in results if r.passed]
        failed = [r for r in results if not r.passed and not r.error]
        errored = [r for r in results if r.error]
        scored = [r for r in results if r.scores]

        # Per-category averages
        cat_scores: Dict[str, List[float]] = {}
        for r in scored:
            cat_scores.setdefault(r.category, []).append(r.overall_score)
        per_category_avg = {k: sum(v) / len(v) for k, v in cat_scores.items()}

        # Per-dimension averages
        dim_scores: Dict[str, List[float]] = {}
        for r in scored:
            for dim, score in r.scores.items():
                dim_scores.setdefault(dim, []).append(score)
        per_dimension_avg = {k: sum(v) / len(v) for k, v in dim_scores.items()}

        avg_overall = sum(r.overall_score for r in scored) / len(scored) if scored else 0.0

        lowest_cat = min(per_category_avg, key=per_category_avg.get) if per_category_avg else ""
        lowest_dim = min(per_dimension_avg, key=per_dimension_avg.get) if per_dimension_avg else ""

        return RunSummary(
            total_scenarios=len(results),
            scenarios_run=len(scored),
            scenarios_passed=len(passed),
            scenarios_failed=len(failed),
            scenarios_errored=len(errored),
            avg_overall_score=avg_overall,
            per_category_avg=per_category_avg,
            per_dimension_avg=per_dimension_avg,
            lowest_category=lowest_cat,
            lowest_dimension=lowest_dim,
            failing_scenarios=[r.scenario_id for r in failed],
            duration_seconds=duration,
        )

    def generate_report(self, summary: RunSummary) -> str:
        """Generate a markdown report from a RunSummary."""
        lines = [
            "# Adversarial Test Run Report",
            "",
            f"**Scenarios**: {summary.scenarios_run}/{summary.total_scenarios} "
            f"({summary.scenarios_passed} passed, {summary.scenarios_failed} failed, "
            f"{summary.scenarios_errored} errors)",
            f"**Average Overall Score**: {summary.avg_overall_score:.2f}",
            f"**Duration**: {summary.duration_seconds:.1f}s",
            "",
            "## Per-Category Averages",
            "",
        ]

        for cat, avg in sorted(summary.per_category_avg.items()):
            status = "PASS" if avg >= 3.0 else "FAIL"
            lines.append(f"- **{cat}**: {avg:.2f} [{status}]")

        lines.extend(
            [
                "",
                "## Per-Dimension Averages",
                "",
            ]
        )

        for dim, avg in sorted(summary.per_dimension_avg.items()):
            status = "PASS" if avg >= 3.0 else "FAIL"
            lines.append(f"- **{dim}**: {avg:.2f} [{status}]")

        if summary.failing_scenarios:
            lines.extend(
                [
                    "",
                    "## Failing Scenarios",
                    "",
                ]
            )
            for sid in summary.failing_scenarios:
                lines.append(f"- {sid}")

        lines.extend(
            [
                "",
                f"**Lowest Category**: {summary.lowest_category}",
                f"**Lowest Dimension**: {summary.lowest_dimension}",
            ]
        )

        return "\n".join(lines)
