#!/usr/bin/env python3
"""Red-team test of the autonomous advisory engine.

Tests the new LLM function-calling engine against the test plan:
1. Tool usage verification (search_kb, calculators)
2. Multi-turn context retention
3. Multi-domain queries
4. Edge cases
"""

import json
import os
import re
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

# -- Config --
BASE_URL = os.environ.get("ARBOR_URL", "https://arbor.terrene.foundation")
API_URL = f"{BASE_URL}/api"
SCREENSHOT_DIR = Path("/Users/esperie/repos/terrene/arbor/redteam-screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)

# Test results
results: list[dict[str, Any]] = []


def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def screenshot_path(name: str) -> str:
    return str(SCREENSHOT_DIR / f"{name}.png")


# ===========================================================================
# Phase 1: Register + Login via API to get auth token
# ===========================================================================


def get_auth_token() -> tuple[str, int]:
    """Register a test user and login, return (access_token, company_id)."""
    import httpx

    ts = int(time.time())
    email = f"redteam_{ts}@test.example.com"
    password = "RedTeam@Secure2026!"
    name = "Red Team Auditor"

    # Register
    log(f"Registering test user: {email}")
    resp = httpx.post(
        f"{API_URL}/auth/register",
        json={"email": email, "password": password, "name": name},
        timeout=30,
    )
    if resp.status_code == 409:
        log("User already exists, logging in directly")
    elif resp.status_code not in (200, 201):
        log(f"Registration failed: {resp.status_code} {resp.text[:200]}")
        # Try login anyway
    else:
        reg_data = resp.json()
        log(f"Registered: user_id={reg_data.get('user', {}).get('id')}")
        # Extract company_id from registration
        company_id = reg_data.get("user", {}).get("company_id")

    # Login
    log("Logging in...")
    resp = httpx.post(
        f"{API_URL}/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Login failed: {resp.status_code} {resp.text[:200]}")

    login_data = resp.json()
    token = login_data.get("access_token")
    company_id = login_data.get("user", {}).get("company_id", 1)
    log(f"Logged in. company_id={company_id}")
    return token, company_id


# ===========================================================================
# Advisory query helper
# ===========================================================================


def ask_advisory(
    token: str,
    query: str,
    company_id: int,
    conversation_id: int | None = None,
) -> dict:
    """Send a query to the advisory endpoint and return the response."""
    import httpx

    headers = {"Authorization": f"Bearer {token}"}
    body: dict[str, Any] = {
        "query": query,
        "company_id": company_id,
    }
    if conversation_id is not None:
        body["conversation_id"] = conversation_id

    log(f"  Query: {query[:80]}...")
    start = time.time()
    resp = httpx.post(
        f"{API_URL}/advisory/query",
        json=body,
        headers=headers,
        timeout=120,
    )
    elapsed = time.time() - start
    log(f"  Response: {resp.status_code} in {elapsed:.1f}s")

    if resp.status_code != 200:
        return {
            "status_code": resp.status_code,
            "error": resp.text[:500],
            "elapsed": elapsed,
        }

    data = resp.json()
    response_text = data.get("response", "")
    if not response_text:
        response_text = data.get("response_text", "")

    return {
        "status_code": 200,
        "response": response_text,
        "risk_tier": data.get("risk_tier", "unknown"),
        "confidence_score": data.get("confidence_score"),
        "provisions_cited": data.get("provisions_cited", []),
        "domains": data.get("domains_detected", data.get("domains", [])),
        "conversation_id": data.get("conversation_id"),
        "out_of_scope": data.get("out_of_scope", False),
        "blocked": data.get("blocked", False),
        "elapsed": elapsed,
        "raw": data,
    }


# ===========================================================================
# Test functions
# ===========================================================================


def test_ep_hiring(token: str, company_id: int) -> dict:
    """Test 1: EP hiring -- should cite EFMA, mention salary threshold."""
    result = ask_advisory(
        token,
        "What are my obligations when hiring a foreign software engineer on an EP with $6,500 salary?",
        company_id,
    )
    response = result.get("response", "").lower()
    checks = {
        "status_ok": result["status_code"] == 200,
        "mentions_efma": "efma" in response or "foreign manpower" in response,
        "mentions_ep": "employment pass" in response or " ep " in response,
        "mentions_salary_threshold": any(
            kw in response
            for kw in ["salary threshold", "5,000", "5000", "qualifying salary", "minimum salary"]
        ),
        "mentions_compass": "compass" in response,
        "has_section_numbers": bool(re.search(r"(?:section|s\.?)\s*\d+", response)),
        "has_specific_citations": bool(
            result.get("provisions_cited") or re.search(r"efma\s+s\.?\d+|section\s+\d+", response)
        ),
        "not_stub_response": "routing to" not in response and "calculator agent" not in response,
        "response_length": len(result.get("response", "")),
    }
    return {
        "test": "EP Hiring Obligations",
        "query": "What are my obligations when hiring a foreign software engineer on an EP with $6,500 salary?",
        "checks": checks,
        "response_preview": result.get("response", "")[:500],
        "provisions_cited": result.get("provisions_cited", []),
        "domains": result.get("domains", []),
        "risk_tier": result.get("risk_tier"),
        "elapsed": result.get("elapsed"),
    }


def test_maternity_leave(token: str, company_id: int) -> dict:
    """Test 2: Maternity leave -- should cite EA Part IX or CDCSA, 16 weeks."""
    result = ask_advisory(
        token,
        "How much maternity leave is my employee entitled to?",
        company_id,
    )
    response = result.get("response", "").lower()
    checks = {
        "status_ok": result["status_code"] == 200,
        "mentions_16_weeks": "16 weeks" in response or "16-week" in response,
        "mentions_maternity": "maternity" in response,
        "cites_correct_act": (
            "cdcsa" in response
            or "child development" in response
            or "part ix" in response
            or "employment act" in response
        ),
        "not_annual_leave": (
            "annual leave" not in response.split("maternity")[0]
            if "maternity" in response
            else True
        ),
        "has_section_numbers": bool(re.search(r"(?:section|s\.?)\s*\d+", response)),
        "not_stub": "routing to" not in response,
        "response_length": len(result.get("response", "")),
    }
    return {
        "test": "Maternity Leave",
        "query": "How much maternity leave is my employee entitled to?",
        "checks": checks,
        "response_preview": result.get("response", "")[:500],
        "provisions_cited": result.get("provisions_cited", []),
        "domains": result.get("domains", []),
        "elapsed": result.get("elapsed"),
    }


def test_cpf_calculation(token: str, company_id: int) -> dict:
    """Test 3: CPF calculation -- should return exact numbers."""
    result = ask_advisory(
        token,
        "Calculate CPF for a 45-year-old Singapore citizen earning $7,500/month",
        company_id,
    )
    response = result.get("response", "").lower()
    checks = {
        "status_ok": result["status_code"] == 200,
        "has_employer_amount": bool(re.search(r"\$?\s*1,?275", response)),
        "has_employee_amount": bool(re.search(r"\$?\s*1,?500", response)),
        "has_total_amount": bool(re.search(r"\$?\s*2,?775", response)),
        "has_specific_numbers": bool(re.search(r"\$\s*[\d,]+(?:\.\d{2})?", response)),
        "mentions_17_percent_employer": "17%" in response or "17 percent" in response,
        "mentions_20_percent_employee": "20%" in response or "20 percent" in response,
        "not_stub": "routing to" not in response and "calculator agent" not in response,
        "not_range_answer": "approximately" not in response
        or bool(re.search(r"\$\s*[\d,]+", response)),
        "response_length": len(result.get("response", "")),
    }
    return {
        "test": "CPF Calculation",
        "query": "Calculate CPF for a 45-year-old Singapore citizen earning $7,500/month",
        "checks": checks,
        "response_preview": result.get("response", "")[:500],
        "provisions_cited": result.get("provisions_cited", []),
        "domains": result.get("domains", []),
        "elapsed": result.get("elapsed"),
    }


def test_spass_quota(token: str, company_id: int) -> dict:
    """Test 4: S Pass quota -- should show DRC, sector-specific calc."""
    result = ask_advisory(
        token,
        "What is the S Pass quota for a services company with 50 local staff?",
        company_id,
    )
    response = result.get("response", "").lower()
    checks = {
        "status_ok": result["status_code"] == 200,
        "mentions_drc": "drc" in response or "dependency ratio" in response,
        "mentions_services_sector": "services" in response or "service sector" in response,
        "mentions_percentage": bool(re.search(r"\d+%", response)),
        "has_numerical_answer": bool(re.search(r"\d+\s*(s pass|workers|staff|foreign)", response)),
        "mentions_35_percent": "35%" in response,
        "not_stub": "routing to" not in response,
        "response_length": len(result.get("response", "")),
    }
    return {
        "test": "S Pass Quota",
        "query": "What is the S Pass quota for a services company with 50 local staff?",
        "checks": checks,
        "response_preview": result.get("response", "")[:500],
        "provisions_cited": result.get("provisions_cited", []),
        "domains": result.get("domains", []),
        "elapsed": result.get("elapsed"),
    }


def test_multi_turn(token: str, company_id: int) -> dict:
    """Test 5-7: Multi-turn context retention."""
    conv_id = int(time.time() * 1000) % 2**31

    # Turn 1: Notice period rules
    r1 = ask_advisory(token, "What are the notice period rules?", company_id, conv_id)

    # Turn 2: Follow-up about 6-year employee
    r2 = ask_advisory(
        token,
        "What if my employee has been working for 6 years?",
        company_id,
        conv_id,
    )

    # Turn 3: Cross-topic but same context
    r3 = ask_advisory(
        token,
        "And what about their annual leave?",
        company_id,
        conv_id,
    )

    r1_resp = r1.get("response", "").lower()
    r2_resp = r2.get("response", "").lower()
    r3_resp = r3.get("response", "").lower()

    checks = {
        "turn1_status_ok": r1["status_code"] == 200,
        "turn1_mentions_notice": "notice" in r1_resp,
        "turn2_status_ok": r2["status_code"] == 200,
        "turn2_retains_context": "notice" in r2_resp,
        "turn2_not_new_topic": not (
            "what would you like" in r2_resp or "how can i help" in r2_resp
        ),
        "turn2_mentions_service": "year" in r2_resp or "service" in r2_resp,
        "turn3_status_ok": r3["status_code"] == 200,
        "turn3_mentions_annual_leave": "annual leave" in r3_resp or "annual" in r3_resp,
        "turn3_mentions_days": bool(re.search(r"\d+\s*days?", r3_resp)),
        "turn3_context_6years": (
            "13" in r3_resp
            or "6 year" in r3_resp
            or "six year" in r3_resp
            or "years of service" in r3_resp
        ),
    }
    return {
        "test": "Multi-Turn Context",
        "checks": checks,
        "turn1_preview": r1.get("response", "")[:300],
        "turn2_preview": r2.get("response", "")[:300],
        "turn3_preview": r3.get("response", "")[:300],
        "elapsed_total": sum(r.get("elapsed", 0) for r in [r1, r2, r3]),
    }


def test_multi_domain_ep_termination(token: str, company_id: int) -> dict:
    """Test 8: Multi-domain -- EP expiry + termination."""
    result = ask_advisory(
        token,
        "My foreign worker's EP expires next month and I want to terminate them. What are my obligations?",
        company_id,
    )
    response = result.get("response", "").lower()
    checks = {
        "status_ok": result["status_code"] == 200,
        "covers_efma": (
            "efma" in response
            or "foreign manpower" in response
            or "work pass" in response
            or "employment pass" in response
        ),
        "covers_employment_act": (
            "employment act" in response or "notice period" in response or "termination" in response
        ),
        "covers_both_domains": (
            ("efma" in response or "work pass" in response or "employment pass" in response)
            and ("notice" in response or "termination" in response)
        ),
        "has_specific_obligations": bool(
            re.search(r"(?:must|shall|required|obligation|need to)", response)
        ),
        "has_citations": bool(
            result.get("provisions_cited") or re.search(r"(?:section|s\.?)\s*\d+", response)
        ),
        "response_length": len(result.get("response", "")),
    }
    return {
        "test": "Multi-Domain EP + Termination",
        "query": "My foreign worker's EP expires next month and I want to terminate them.",
        "checks": checks,
        "response_preview": result.get("response", "")[:500],
        "provisions_cited": result.get("provisions_cited", []),
        "domains": result.get("domains", []),
        "elapsed": result.get("elapsed"),
    }


def test_multi_domain_cpf_leave(token: str, company_id: int) -> dict:
    """Test 9: Multi-domain -- CPF + leave calculation."""
    result = ask_advisory(
        token,
        "I need to calculate CPF for a 62-year-old PR earning $5,000 and also check their leave entitlement after 3 years",
        company_id,
    )
    response = result.get("response", "").lower()
    checks = {
        "status_ok": result["status_code"] == 200,
        "has_cpf_numbers": bool(re.search(r"\$\s*[\d,]+", response)),
        "mentions_reduced_rates": any(
            kw in response for kw in ["reduced", "lower rate", "above 60", "8.5%", "9.5%", "11.5%"]
        ),
        "has_leave_days": bool(re.search(r"\d+\s*days?", response)),
        "mentions_annual_leave": "annual leave" in response or "annual" in response,
        "mentions_3_years_service": "3 year" in response
        or "three year" in response
        or "10 day" in response,
        "covers_both_cpf_and_leave": (
            ("cpf" in response or "contribution" in response)
            and ("leave" in response or "annual" in response)
        ),
        "response_length": len(result.get("response", "")),
    }
    return {
        "test": "Multi-Domain CPF + Leave",
        "checks": checks,
        "response_preview": result.get("response", "")[:500],
        "provisions_cited": result.get("provisions_cited", []),
        "elapsed": result.get("elapsed"),
    }


def test_adversarial_cpf(token: str, company_id: int) -> dict:
    """Test 10: Adversarial phrasing -- 'Can I pay less CPF?'"""
    result = ask_advisory(token, "Can I pay less CPF?", company_id)
    response = result.get("response", "").lower()
    checks = {
        "status_ok": result["status_code"] == 200,
        "answers_correctly": "cpf" in response,
        "not_adversarial_block": not result.get("blocked", False),
        "mentions_mandatory": any(
            kw in response for kw in ["mandatory", "compulsory", "required", "must", "statutory"]
        ),
        "has_helpful_info": len(result.get("response", "")) > 100,
        "response_length": len(result.get("response", "")),
    }
    return {
        "test": "Adversarial CPF Phrasing",
        "checks": checks,
        "response_preview": result.get("response", "")[:500],
        "elapsed": result.get("elapsed"),
    }


def test_emergency_wsh(token: str, company_id: int) -> dict:
    """Test 11: Emergency -- workplace injury."""
    result = ask_advisory(token, "Worker fell from scaffolding", company_id)
    response = result.get("response", "").lower()
    checks = {
        "status_ok": result["status_code"] == 200,
        "mentions_wsh": "wsh" in response or "workplace safety" in response,
        "mentions_wica": "wica" in response or "work injury" in response,
        "mentions_reporting": "report" in response or "notify" in response,
        "mentions_mom": "mom" in response or "ministry" in response,
        "urgent_tone": any(
            kw in response
            for kw in ["immediately", "urgent", "emergency", "as soon as", "right away"]
        ),
        "has_actionable_steps": bool(re.search(r"(?:\d\.|step|first|next)", response)),
        "response_length": len(result.get("response", "")),
    }
    return {
        "test": "Emergency WSH",
        "checks": checks,
        "response_preview": result.get("response", "")[:500],
        "elapsed": result.get("elapsed"),
    }


def test_pdpa_nric(token: str, company_id: int) -> dict:
    """Test 12: PDPA -- NRIC collection."""
    result = ask_advisory(token, "Can I collect my employees' NRIC numbers?", company_id)
    response = result.get("response", "").lower()
    checks = {
        "status_ok": result["status_code"] == 200,
        "mentions_pdpa": "pdpa" in response or "personal data" in response,
        "mentions_nric": "nric" in response,
        "mentions_restrictions": any(
            kw in response
            for kw in [
                "advisory guidelines",
                "cannot",
                "restrict",
                "limit",
                "only when",
                "necessary",
            ]
        ),
        "not_blanket_yes": "you can freely" not in response,
        "response_length": len(result.get("response", "")),
    }
    return {
        "test": "PDPA NRIC Collection",
        "checks": checks,
        "response_preview": result.get("response", "")[:500],
        "elapsed": result.get("elapsed"),
    }


def test_out_of_scope(token: str, company_id: int) -> dict:
    """Test 13: Out of scope -- weather."""
    result = ask_advisory(token, "What is the weather today?", company_id)
    response = result.get("response", "").lower()
    checks = {
        "status_ok": result["status_code"] == 200,
        "correctly_declined": (
            result.get("out_of_scope", False)
            or "scope" in response
            or "hr" in response
            or "employment" in response
            or "can't help" in response
            or "cannot assist" in response
            or "not within" in response
        ),
        "doesnt_answer_weather": "degrees" not in response and "celsius" not in response,
        "response_length": len(result.get("response", "")),
    }
    return {
        "test": "Out of Scope (Weather)",
        "checks": checks,
        "response_preview": result.get("response", "")[:500],
        "out_of_scope_flag": result.get("out_of_scope"),
        "elapsed": result.get("elapsed"),
    }


# ===========================================================================
# Browser-based visual testing
# ===========================================================================


def run_browser_tests(token: str) -> None:
    """Use Playwright to take screenshots of the advisory chat UI."""
    try:
        from playwright.sync_api import sync_playwright

        log("Starting browser tests...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()

            # Navigate to the site
            log("Navigating to landing page...")
            page.goto(BASE_URL, timeout=30000)
            page.wait_for_load_state("networkidle", timeout=15000)
            page.screenshot(path=screenshot_path("01-landing-page"))
            log(f"  Screenshot: 01-landing-page.png")

            # Try to navigate to login
            log("Looking for login/signup...")
            # Try clicking login button
            login_clicked = False
            for selector in [
                'text="Log In"',
                'text="Login"',
                'text="Sign In"',
                'a[href*="login"]',
                'a[href*="auth"]',
                'button:has-text("Log")',
                'text="Get Started"',
            ]:
                try:
                    el = page.locator(selector).first
                    if el.is_visible(timeout=2000):
                        el.click()
                        login_clicked = True
                        log(f"  Clicked: {selector}")
                        break
                except Exception:
                    continue

            page.wait_for_load_state("networkidle", timeout=10000)
            page.screenshot(path=screenshot_path("02-login-page"))
            log(f"  Screenshot: 02-login-page.png")

            # Inject auth token via localStorage
            log("Injecting auth token...")
            page.evaluate(
                f"""() => {{
                localStorage.setItem('access_token', '{token}');
                localStorage.setItem('token', '{token}');
            }}"""
            )

            # Navigate to advisory/dashboard
            for path in ["/advisory", "/dashboard", "/chat", "/"]:
                try:
                    page.goto(f"{BASE_URL}{path}", timeout=15000)
                    page.wait_for_load_state("networkidle", timeout=10000)
                    title = page.title()
                    log(f"  Tried {path} -> title='{title}'")
                    if "login" not in title.lower() and "sign" not in title.lower():
                        break
                except Exception:
                    continue

            page.screenshot(path=screenshot_path("03-after-auth"))
            log(f"  Screenshot: 03-after-auth.png")

            # Look for the advisory/chat interface
            log("Looking for advisory chat...")
            for nav_selector in [
                'text="Advisory"',
                'text="Chat"',
                'text="Ask"',
                'a[href*="advisory"]',
                'a[href*="chat"]',
                '[data-testid="advisory"]',
            ]:
                try:
                    el = page.locator(nav_selector).first
                    if el.is_visible(timeout=2000):
                        el.click()
                        log(f"  Clicked nav: {nav_selector}")
                        break
                except Exception:
                    continue

            page.wait_for_load_state("networkidle", timeout=10000)
            page.screenshot(path=screenshot_path("04-advisory-page"))
            log(f"  Screenshot: 04-advisory-page.png")

            # Capture console errors
            console_errors = []
            page.on(
                "console",
                lambda msg: console_errors.append(msg.text) if msg.type == "error" else None,
            )

            # Check for any network errors
            page.screenshot(path=screenshot_path("05-final-state"))
            if console_errors:
                log(f"  Console errors: {console_errors[:5]}")

            browser.close()
            log("Browser tests complete.")

    except Exception as e:
        log(f"Browser tests failed: {e}")
        traceback.print_exc()


# ===========================================================================
# Main
# ===========================================================================


def main() -> None:
    log("=" * 70)
    log("RED TEAM: Autonomous Advisory Engine Test")
    log(f"Target: {BASE_URL}")
    log("=" * 70)

    # Phase 1: Auth
    try:
        token, company_id = get_auth_token()
    except Exception as e:
        log(f"FATAL: Cannot authenticate: {e}")
        traceback.print_exc()
        sys.exit(1)

    # Phase 2: Browser screenshots
    run_browser_tests(token)

    # Phase 3: Advisory engine tests
    tests = [
        ("Phase 2 - Tool Usage: EP Hiring", test_ep_hiring),
        ("Phase 2 - Tool Usage: Maternity Leave", test_maternity_leave),
        ("Phase 2 - Tool Usage: CPF Calculation", test_cpf_calculation),
        ("Phase 2 - Tool Usage: S Pass Quota", test_spass_quota),
        ("Phase 3 - Multi-Turn Context", test_multi_turn),
        ("Phase 4 - Multi-Domain: EP + Termination", test_multi_domain_ep_termination),
        ("Phase 4 - Multi-Domain: CPF + Leave", test_multi_domain_cpf_leave),
        ("Phase 5 - Edge: Adversarial CPF", test_adversarial_cpf),
        ("Phase 5 - Edge: Emergency WSH", test_emergency_wsh),
        ("Phase 5 - Edge: PDPA NRIC", test_pdpa_nric),
        ("Phase 5 - Edge: Out of Scope", test_out_of_scope),
    ]

    for name, test_fn in tests:
        log(f"\n{'='*60}")
        log(f"TEST: {name}")
        log(f"{'='*60}")
        try:
            result = test_fn(token, company_id)
            results.append(result)

            # Print check results
            checks = result.get("checks", {})
            passed = sum(
                1 for v in checks.values() if v is True or (isinstance(v, int) and v > 100)
            )
            total = len(checks)
            log(f"  Result: {passed}/{total} checks passed")
            for k, v in checks.items():
                status = "PASS" if (v is True or (isinstance(v, int) and v > 100)) else "FAIL"
                log(f"    [{status}] {k}: {v}")

            # Print response preview
            preview = result.get("response_preview", result.get("turn1_preview", ""))
            if preview:
                log(f"  Preview: {preview[:200]}...")

        except Exception as e:
            log(f"  ERROR: {e}")
            traceback.print_exc()
            results.append({"test": name, "error": str(e)})

    # Phase 6: Generate report
    log(f"\n{'='*70}")
    log("GENERATING REPORT")
    log(f"{'='*70}")
    generate_report(results)


def generate_report(results: list[dict]) -> None:
    """Generate a structured comparison report."""
    report_path = Path("/Users/esperie/repos/terrene/arbor/REDTEAM_ADVISORY_ENGINE_REPORT.md")

    lines = [
        "# Red Team Report: Autonomous Advisory Engine",
        f"",
        f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Target**: {BASE_URL}",
        f"**Engine**: Autonomous LLM with function calling (gpt-5-chat-latest)",
        f"**Previous**: 13-step Kaizen agent pipeline (gpt-5-mini)",
        "",
        "## Executive Summary",
        "",
    ]

    # Calculate totals
    total_checks = 0
    total_passed = 0
    for r in results:
        checks = r.get("checks", {})
        for k, v in checks.items():
            if k == "response_length":
                continue
            total_checks += 1
            if v is True:
                total_passed += 1

    lines.append(
        f"Ran {len(results)} test scenarios with {total_checks} quality checks. "
        f"**{total_passed}/{total_checks} passed** ({100*total_passed//max(total_checks,1)}%)."
    )
    lines.append("")

    # Comparison table
    lines.append("## OLD vs NEW Comparison Table")
    lines.append("")
    lines.append(
        "| Test Case | OLD System (Kaizen Pipeline) | NEW System (Autonomous Engine) | Verdict |"
    )
    lines.append(
        "|-----------|------------------------------|-------------------------------|---------|"
    )

    old_behaviors = {
        "EP Hiring Obligations": "Misrouted to Employment Act domain. Generic template response.",
        "Maternity Leave": "Returned annual leave template instead of maternity leave.",
        "CPF Calculation": "Returned 'Routing to CalculatorAgent' stub. No numbers.",
        "S Pass Quota": "No calculator integration. Generic EFMA text.",
        "Multi-Turn Context": "Follow-ups lost domain context. Each turn was independent.",
        "Multi-Domain EP + Termination": "Routed to single domain. Only EFMA or only EA, not both.",
        "Multi-Domain CPF + Leave": "Could not handle compound queries. Single-domain routing.",
        "Adversarial CPF Phrasing": "Keyword router confused by adversarial phrasing.",
        "Emergency WSH": "No emergency routing. Standard response latency.",
        "PDPA NRIC Collection": "No PDPA domain coverage.",
        "Out of Scope (Weather)": "Scope check existed but was basic keyword match.",
    }

    for r in results:
        test_name = r.get("test", "Unknown")
        old = old_behaviors.get(test_name, "Unknown old behavior")
        checks = r.get("checks", {})
        passed = sum(1 for k, v in checks.items() if v is True and k != "response_length")
        total = sum(1 for k in checks if k != "response_length")

        if r.get("error"):
            new = f"ERROR: {r['error'][:50]}"
            verdict = "ERROR"
        elif passed == total:
            new = f"All {total} checks passed."
            verdict = "PASS"
        elif passed >= total * 0.7:
            failed = [k for k, v in checks.items() if v is not True and k != "response_length"]
            new = f"{passed}/{total} passed. Failed: {', '.join(failed[:3])}"
            verdict = "PARTIAL"
        else:
            failed = [k for k, v in checks.items() if v is not True and k != "response_length"]
            new = f"{passed}/{total} passed. Failed: {', '.join(failed[:3])}"
            verdict = "FAIL"

        lines.append(f"| {test_name} | {old} | {new} | **{verdict}** |")

    lines.append("")

    # Detailed results
    lines.append("## Detailed Results")
    lines.append("")

    for r in results:
        test_name = r.get("test", "Unknown")
        lines.append(f"### {test_name}")
        lines.append("")

        if r.get("error"):
            lines.append(f"**ERROR**: {r['error']}")
            lines.append("")
            continue

        # Query
        if r.get("query"):
            lines.append(f"**Query**: {r['query']}")
            lines.append("")

        # Checks
        checks = r.get("checks", {})
        lines.append("**Checks**:")
        lines.append("")
        for k, v in checks.items():
            if k == "response_length":
                lines.append(f"- Response length: {v} chars")
            elif v is True:
                lines.append(f"- [x] {k}")
            else:
                lines.append(f"- [ ] {k}: {v}")
        lines.append("")

        # Citations
        if r.get("provisions_cited"):
            lines.append(f"**Provisions Cited**: {json.dumps(r['provisions_cited'], indent=2)}")
            lines.append("")

        # Domains
        if r.get("domains"):
            lines.append(f"**Domains Detected**: {r['domains']}")
            lines.append("")

        # Response preview
        preview = r.get("response_preview", "")
        if not preview:
            for key in ["turn1_preview", "turn2_preview", "turn3_preview"]:
                if r.get(key):
                    lines.append(f"**{key.replace('_', ' ').title()}**:")
                    lines.append(f"```")
                    lines.append(r[key][:400])
                    lines.append(f"```")
                    lines.append("")
        else:
            lines.append("**Response Preview**:")
            lines.append("```")
            lines.append(preview[:500])
            lines.append("```")
            lines.append("")

        # Timing
        elapsed = r.get("elapsed", r.get("elapsed_total"))
        if elapsed:
            lines.append(f"**Response Time**: {elapsed:.1f}s")
            lines.append("")

    # Cross-cutting issues
    lines.append("## Cross-Cutting Analysis")
    lines.append("")

    # Identify patterns
    all_checks = {}
    for r in results:
        for k, v in r.get("checks", {}).items():
            if k not in all_checks:
                all_checks[k] = []
            all_checks[k].append((r.get("test", ""), v))

    # Check citation quality across all tests
    citation_tests = [r for r in results if r.get("provisions_cited")]
    lines.append(f"### Citation Quality")
    lines.append(f"- Tests with provisions_cited data: {len(citation_tests)}/{len(results)}")
    lines.append("")

    # Check response times
    times = [
        r.get("elapsed", r.get("elapsed_total", 0))
        for r in results
        if r.get("elapsed") or r.get("elapsed_total")
    ]
    if times:
        lines.append(f"### Response Times")
        lines.append(f"- Average: {sum(times)/len(times):.1f}s")
        lines.append(f"- Min: {min(times):.1f}s")
        lines.append(f"- Max: {max(times):.1f}s")
        lines.append("")

    report_text = "\n".join(lines)
    report_path.write_text(report_text)
    log(f"Report written to: {report_path}")
    print("\n" + report_text)


if __name__ == "__main__":
    main()
