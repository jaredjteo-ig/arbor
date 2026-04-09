#!/usr/bin/env python3
"""Seed the Knowledge Base with Singapore employment law provisions.

Loads all content bundles from hr_advisory.kb.content into the database.
Idempotent — safe to run multiple times (checks for existing records).

Usage:
    python scripts/seed_kb.py
    python scripts/seed_kb.py --api-url http://localhost:8000
"""

import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()


def main():
    print("=" * 60)
    print("Arbor HRIS — Knowledge Base Seeder")
    print("=" * 60)

    from hr_advisory.kb.pipeline import KBContentPipeline
    from hr_advisory.kb.content import (
        employment_act,
        cpf,
        foreign_manpower,
        tafep,
        remaining_domains,
        industrial_relations,
    )

    pipeline = KBContentPipeline()

    modules = [
        ("Employment Act", employment_act),
        ("CPF Act", cpf),
        ("Foreign Manpower (EFMA)", foreign_manpower),
        ("TAFEP Guidelines", tafep),
        ("Remaining Domains (WSH, Tax, etc.)", remaining_domains),
        ("Industrial Relations Act", industrial_relations),
    ]

    total_provisions = 0
    total_domains = 0

    for name, module in modules:
        print(f"\n--- Loading: {name} ---")
        try:
            bundle = module.get_bundle()
            summary = pipeline.bulk_load(bundle)

            act = summary.get("act")
            provisions = summary.get("provisions", [])
            domains = summary.get("domains", [])
            xrefs = summary.get("cross_references", [])
            rules = summary.get("applicability_rules", [])
            examples = summary.get("practical_examples", [])

            act_name = act.get("short_name", "?") if act else "?"
            print(f"  Act: {act_name}")
            print(f"  Domains: {len(domains)}")
            print(f"  Provisions: {len(provisions)}")
            print(f"  Cross-references: {len(xrefs)}")
            print(f"  Applicability rules: {len(rules)}")
            print(f"  Practical examples: {len(examples)}")

            total_provisions += len(provisions)
            total_domains += len(domains)

        except Exception as exc:
            print(f"  ERROR: {exc}")
            import traceback
            traceback.print_exc()

    print(f"\n{'=' * 60}")
    print(f"DONE: {total_provisions} provisions across {total_domains} domains")
    print("=" * 60)

    # Verify
    try:
        from hr_advisory.kb.admin import get_kb_stats
        stats = get_kb_stats()
        print(f"\nVerification: {stats}")
    except Exception:
        print("\n(Verification skipped — get_kb_stats not available)")


if __name__ == "__main__":
    main()
