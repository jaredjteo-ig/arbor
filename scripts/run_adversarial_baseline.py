#!/usr/bin/env python3
"""Run adversarial baseline and output detailed results as JSON.

Usage:
    python scripts/run_adversarial_baseline.py
"""

import json
import os
import sys
from pathlib import Path

# Load .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        eq = line.find("=")
        if eq == -1:
            continue
        key = line[:eq].strip()
        val = line[eq + 1 :].strip()
        if key not in os.environ:
            os.environ[key] = val

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from hr_advisory.agents.config import _resolve_provider_and_model, has_llm_available
from hr_advisory.quality.adversarial_runner import AdversarialRunner


def main():
    if not has_llm_available():
        print(
            "ERROR: No LLM provider available. Set OPENAI_API_KEY or run ollama.", file=sys.stderr
        )
        sys.exit(1)

    provider, model = _resolve_provider_and_model()
    print(f"LLM Provider: {provider}")
    print(f"LLM Model: {model}")
    print()

    runner = AdversarialRunner()

    print("=" * 60)
    print("Running adversarial baseline (1 scenario per category)...")
    print("=" * 60)
    print()

    summary = runner.run_baseline(sample_size=8)

    # Print the generated report
    report = runner.generate_report(summary)
    print(report)
    print()

    # Print detailed per-scenario results
    print("=" * 60)
    print("DETAILED PER-SCENARIO RESULTS")
    print("=" * 60)
    print()

    for result in runner._results:
        print(f"--- {result.scenario_id} ({result.category}) ---")
        print(f"  Query: {result.query}")
        if result.error:
            print(f"  ERROR: {result.error}")
        else:
            print(f"  Overall Score: {result.overall_score}")
            print(f"  Passed: {result.passed}")
            print(f"  Risk Tier: {result.risk_tier}")
            print(f"  Duration: {result.duration_seconds:.1f}s")
            print(f"  Scores:")
            for dim, score in sorted(result.scores.items()):
                print(f"    {dim}: {score}")
            print(f"  Details:")
            for dim, detail in sorted(result.details.items()):
                print(f"    {dim}: {detail}")
            if result.response_text:
                # First 300 chars of response
                preview = result.response_text[:300]
                if len(result.response_text) > 300:
                    preview += "..."
                print(f"  Response preview: {preview}")
        print()

    # Print summary as JSON for easy parsing
    summary_dict = {
        "total_scenarios": summary.total_scenarios,
        "scenarios_run": summary.scenarios_run,
        "scenarios_passed": summary.scenarios_passed,
        "scenarios_failed": summary.scenarios_failed,
        "scenarios_errored": summary.scenarios_errored,
        "avg_overall_score": round(summary.avg_overall_score, 2),
        "per_category_avg": {k: round(v, 2) for k, v in summary.per_category_avg.items()},
        "per_dimension_avg": {k: round(v, 2) for k, v in summary.per_dimension_avg.items()},
        "lowest_category": summary.lowest_category,
        "lowest_dimension": summary.lowest_dimension,
        "failing_scenarios": summary.failing_scenarios,
        "duration_seconds": round(summary.duration_seconds, 1),
    }

    print("=" * 60)
    print("SUMMARY JSON")
    print("=" * 60)
    print(json.dumps(summary_dict, indent=2))


if __name__ == "__main__":
    main()
