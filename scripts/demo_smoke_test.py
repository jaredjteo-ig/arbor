#!/usr/bin/env python3
"""
Demo Smoke Test — Pre-flight verification for Arbor demo.

Run this the morning of a demo to verify all systems are operational.
Exits 0 if all checks pass, 1 if any fail.

Usage:
    python scripts/demo_smoke_test.py
    python scripts/demo_smoke_test.py --api-url https://arbor.terrene.foundation
"""

# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any

try:
    import httpx
except ImportError:
    print("ERROR: httpx is required. Install with: pip install httpx")
    sys.exit(1)


def check(name: str, passed: bool, detail: str = "") -> bool:
    """Print a check result and return pass/fail."""
    icon = "PASS" if passed else "FAIL"
    msg = f"  [{icon}] {name}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    return passed


def run_smoke_test(api_url: str, email: str, password: str) -> bool:
    """Run all smoke test checks. Returns True if all pass."""
    base = api_url.rstrip("/")
    results: list[bool] = []
    client = httpx.Client(timeout=30.0)

    print(f"\nArbor Demo Smoke Test")
    print(f"Target: {base}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print("=" * 60)

    # 1. Health endpoint
    print("\n1. Infrastructure")
    try:
        r = client.get(f"{base}/api/health")
        data = r.json()
        results.append(check("Health endpoint", r.status_code == 200, f"{r.status_code}"))
        results.append(check(
            "Workflows healthy",
            all(v == "healthy" for v in data.get("workflows", {}).values()),
            json.dumps(data.get("workflows", {})),
        ))
    except Exception as e:
        results.append(check("Health endpoint", False, str(e)))
        print("\n  CRITICAL: Cannot reach the server. Aborting remaining checks.")
        return False

    # 2. Frontend
    try:
        r = client.get(base, follow_redirects=True)
        results.append(check("Frontend loads", r.status_code == 200, f"{r.status_code}"))
    except Exception as e:
        results.append(check("Frontend loads", False, str(e)))

    # 3. Auth flow
    print("\n2. Authentication")
    token = None
    try:
        r = client.post(f"{base}/api/auth/login", json={"email": email, "password": password})
        if r.status_code == 200:
            token = r.json().get("access_token")
            results.append(check("Login", True, f"token received"))
        else:
            results.append(check("Login", False, f"{r.status_code}: {r.text[:200]}"))
    except Exception as e:
        results.append(check("Login", False, str(e)))

    if not token:
        print("\n  WARNING: Cannot authenticate. Skipping authenticated checks.")
        print("  Create a demo account first, then re-run.")
        results.append(False)
    else:
        headers = {"Authorization": f"Bearer {token}"}

        # 4. Advisory query
        print("\n3. Advisory Engine")
        try:
            r = client.post(
                f"{base}/api/advisory/query",
                json={"query": "What is the minimum annual leave in Singapore?"},
                headers=headers,
                timeout=30.0,
            )
            if r.status_code == 200:
                resp_data = r.json()
                has_response = bool(resp_data.get("response") or resp_data.get("content"))
                results.append(check("Advisory query", has_response, "response received"))
            else:
                results.append(check("Advisory query", False, f"{r.status_code}: {r.text[:200]}"))
        except Exception as e:
            results.append(check("Advisory query", False, str(e)))

        # 5. Calculator
        print("\n4. Calculators")
        try:
            r = client.post(
                f"{base}/api/calculator/cpf",
                json={
                    "age": 35,
                    "citizenship_status": "citizen",
                    "ordinary_wages": 5000,
                    "additional_wages": 0,
                },
                headers=headers,
            )
            results.append(check(
                "CPF calculator",
                r.status_code == 200,
                f"{r.status_code}",
            ))
        except Exception as e:
            results.append(check("CPF calculator", False, str(e)))

        # 6. Shadow context
        print("\n5. Shadow Agent")
        try:
            r = client.get(f"{base}/api/shadow/context", headers=headers)
            results.append(check(
                "Shadow context",
                r.status_code in (200, 404),
                f"{r.status_code}",
            ))
        except Exception as e:
            results.append(check("Shadow context", False, str(e)))

        # 7. Employee list (verify seed data)
        print("\n6. Demo Data")
        try:
            r = client.get(f"{base}/api/employees/", headers=headers)
            if r.status_code == 200:
                employees = r.json()
                count = len(employees) if isinstance(employees, list) else employees.get("total", 0)
                results.append(check(
                    "Employees seeded",
                    count > 0,
                    f"{count} employees found",
                ))
            else:
                results.append(check("Employees seeded", False, f"{r.status_code}"))
        except Exception as e:
            results.append(check("Employees seeded", False, str(e)))

    # Summary
    print("\n" + "=" * 60)
    passed = sum(1 for r in results if r)
    total = len(results)
    all_pass = all(results)

    if all_pass:
        print(f"RESULT: ALL {total} CHECKS PASSED — Demo ready!")
    else:
        failed = total - passed
        print(f"RESULT: {failed}/{total} CHECKS FAILED — Fix before demo!")

    print("=" * 60)
    return all_pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Arbor Demo Smoke Test")
    parser.add_argument(
        "--api-url",
        default=os.environ.get("ARBOR_API_URL", "https://central.kailash.ai"),
        help="API base URL (default: https://central.kailash.ai)",
    )
    parser.add_argument(
        "--email",
        default=os.environ.get("DEMO_EMAIL", "demo@central.kailash.ai"),
        help="Demo account email",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("DEMO_PASSWORD", ""),
        help="Demo account password",
    )
    args = parser.parse_args()

    if not args.password:
        print("ERROR: --password is required (or set DEMO_PASSWORD env var)")
        sys.exit(1)

    success = run_smoke_test(args.api_url, args.email, args.password)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
