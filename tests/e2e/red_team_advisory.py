#!/usr/bin/env python3
"""Red Team Advisory Engine Test Suite — Browser UI Tests.

Runs 7 tests against the live Arbor advisory chat interface using Playwright.
Each test types a query into the chat, waits for the response, takes a screenshot,
and evaluates the PASS/FAIL criteria.

Usage: python tests/e2e/red_team_advisory.py
"""

import json
import os
import re
import sys
import time
from pathlib import Path
from dataclasses import dataclass, field
from playwright.sync_api import sync_playwright, Page, expect

BASE_URL = os.environ.get("ARBOR_URL", "https://arbor.terrene.foundation")
EMAIL = "test@arbor.dev"
PASSWORD = "TestPass2026"
SCREENSHOT_DIR = Path(__file__).parent / "screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)

# Timeout for advisory responses (LLM calls can take up to 60s)
RESPONSE_TIMEOUT = 90_000  # 90s


@dataclass
class TestResult:
    name: str
    passed: bool
    reason: str
    screenshot: str = ""
    response_text: str = ""


results: list[TestResult] = []


def login(page: Page):
    """Login to Arbor and navigate to the dashboard."""
    print(f"\n{'='*60}")
    print("LOGGING IN")
    print(f"{'='*60}")

    page.goto(f"{BASE_URL}/login", wait_until="networkidle")
    page.wait_for_timeout(2000)

    # Fill in credentials
    email_input = page.locator('input[type="email"], input[name="email"]')
    if email_input.count() == 0:
        # Try alternative selectors
        email_input = page.locator('input[placeholder*="email" i]')
    email_input.fill(EMAIL)

    password_input = page.locator('input[type="password"], input[name="password"]')
    if password_input.count() == 0:
        password_input = page.locator('input[placeholder*="password" i]')
    password_input.fill(PASSWORD)

    # Click submit
    submit = page.locator('button[type="submit"]')
    submit.click()

    # Wait for navigation to dashboard
    page.wait_for_url("**/dashboard**", timeout=15000)
    page.wait_for_timeout(2000)
    print("  -> Logged in successfully, on dashboard")


def navigate_to_advisory(page: Page):
    """Navigate to the advisory chat page."""
    print("  -> Navigating to advisory page")
    page.goto(f"{BASE_URL}/advisory", wait_until="networkidle")
    page.wait_for_timeout(3000)
    print("  -> On advisory page")


def send_message(page: Page, text: str) -> str:
    """Type a message into the chat input and wait for the response.

    Returns the assistant's response text.
    """
    print(f"  -> Sending message: {text[:60]}...")

    # Find the chat input - try multiple selectors
    chat_input = page.locator('textarea, input[type="text"]').last
    chat_input.fill(text)
    page.wait_for_timeout(500)

    # Press Enter to send
    chat_input.press("Enter")

    # Wait for the thinking indicator to appear (confirming message was sent)
    page.wait_for_timeout(1000)

    # Wait for the response to complete (streaming=false means no more bouncing dots)
    # We wait for the assistant message to appear and stop streaming
    # The thinking indicator disappears when streaming completes
    print("  -> Waiting for response...")

    # Wait for the response — look for the assistant's message bubble
    # The SystemMessage component renders the response. Wait until streaming stops.
    # Strategy: wait until no more "animate-bounce" elements (thinking indicator gone)
    # AND at least one assistant message exists

    start_time = time.time()
    response_text = ""
    while time.time() - start_time < RESPONSE_TIMEOUT / 1000:
        # Check if there are still bouncing dots (thinking indicator)
        bouncing = page.locator(".animate-bounce").count()
        # Check if there are any pulse animations (thinking phase text)
        pulsing = page.locator(".animate-pulse").count()

        if bouncing == 0 and pulsing == 0:
            # No more thinking indicators — check for response
            page.wait_for_timeout(1000)
            # Get the last assistant message
            # SystemMessage renders in a div with markdown content
            messages = page.locator('[class*="prose"], [class*="markdown"]').all()
            if messages:
                response_text = messages[-1].inner_text()
                if response_text.strip():
                    break

            # Alternative: look for the last chat bubble that's not from the user
            # User messages are right-aligned, assistant messages are left-aligned
            all_bubbles = page.locator('[class*="rounded"]').all()
            for bubble in reversed(all_bubbles):
                text_content = bubble.inner_text()
                if text_content.strip() and text_content.strip() != text:
                    response_text = text_content.strip()
                    break
            if response_text:
                break

        page.wait_for_timeout(2000)

    if not response_text:
        # Last resort: get all text content and try to find the response
        page.wait_for_timeout(3000)
        full_text = page.locator("main, [class*='chat'], [class*='message']").all_inner_texts()
        response_text = "\n".join(full_text)

    elapsed = time.time() - start_time
    print(f"  -> Response received in {elapsed:.1f}s ({len(response_text)} chars)")
    return response_text


def get_page_text(page: Page) -> str:
    """Get all visible text on the page."""
    return page.locator("body").inner_text()


def take_screenshot(page: Page, name: str) -> str:
    """Take a screenshot and return the file path."""
    path = str(SCREENSHOT_DIR / f"{name}.png")
    page.screenshot(path=path, full_page=True)
    print(f"  -> Screenshot: {path}")
    return path


def test_1_cpf_calculation(page: Page):
    """Test 1: CPF Calculation"""
    print(f"\n{'='*60}")
    print("TEST 1: CPF Calculation")
    print(f"{'='*60}")

    navigate_to_advisory(page)
    response = send_message(
        page, "Calculate CPF for a 45-year-old Singapore citizen earning $7,500/month"
    )
    screenshot = take_screenshot(page, "test1_cpf")

    # Check for exact CPF numbers
    # For age 45, citizen, $7,500:
    # Employee: 20% = $1,500
    # Employer: 17% = $1,275
    # Total: $2,775
    text = response.lower()
    has_employer = "1,275" in response or "1275" in response
    has_employee = "1,500" in response or "1500" in response
    has_total = "2,775" in response or "2775" in response

    passed = has_employer and has_employee and has_total
    reason = []
    if not has_employer:
        reason.append("Missing employer $1,275")
    if not has_employee:
        reason.append("Missing employee $1,500")
    if not has_total:
        reason.append("Missing total $2,775")

    result = TestResult(
        name="Test 1: CPF Calculation",
        passed=passed,
        reason="All CPF figures correct" if passed else "; ".join(reason),
        screenshot=screenshot,
        response_text=response[:500],
    )
    results.append(result)
    print(f"  -> {'PASS' if passed else 'FAIL'}: {result.reason}")


def test_2_maternity_leave(page: Page):
    """Test 2: Maternity Leave"""
    print(f"\n{'='*60}")
    print("TEST 2: Maternity Leave")
    print(f"{'='*60}")

    # Start new conversation
    navigate_to_advisory(page)
    response = send_message(page, "How much maternity leave is my employee entitled to?")
    screenshot = take_screenshot(page, "test2_maternity")

    text = response.lower()
    has_16_weeks = "16 week" in text or "16-week" in text
    has_employment_act = "employment act" in text or "part ix" in text.lower() or "cdcsa" in text
    has_citizen_distinction = (
        "citizen" in text or "non-citizen" in text or "singapore citizen" in text or "child" in text
    )

    passed = has_16_weeks and (has_employment_act or has_citizen_distinction)
    reason = []
    if not has_16_weeks:
        reason.append("Missing 16 weeks")
    if not has_employment_act:
        reason.append("Missing Employment Act/Part IX reference")
    if not has_citizen_distinction:
        reason.append("Missing citizen/non-citizen distinction")

    result = TestResult(
        name="Test 2: Maternity Leave",
        passed=passed,
        reason="Maternity leave info correct" if passed else "; ".join(reason),
        screenshot=screenshot,
        response_text=response[:500],
    )
    results.append(result)
    print(f"  -> {'PASS' if passed else 'FAIL'}: {result.reason}")


def test_3_spass_quota(page: Page):
    """Test 3: S Pass Quota"""
    print(f"\n{'='*60}")
    print("TEST 3: S Pass Quota")
    print(f"{'='*60}")

    navigate_to_advisory(page)
    response = send_message(
        page, "What is the S Pass quota for a services company with 50 local employees?"
    )
    screenshot = take_screenshot(page, "test3_spass")

    text = response.lower()
    # DRC for services sector: 35% for S Pass
    has_drc = "drc" in text or "dependency ratio" in text or "ratio ceiling" in text
    has_35 = "35%" in text or "35 per" in text
    has_calculation = any(c in text for c in ["headroom", "quota", "maximum", "entitled"])

    passed = (has_drc or has_35) and has_calculation
    reason = []
    if not has_drc and not has_35:
        reason.append("Missing DRC or 35% mention")
    if not has_calculation:
        reason.append("Missing quota/headroom calculation")

    result = TestResult(
        name="Test 3: S Pass Quota",
        passed=passed,
        reason="S Pass quota info correct" if passed else "; ".join(reason),
        screenshot=screenshot,
        response_text=response[:500],
    )
    results.append(result)
    print(f"  -> {'PASS' if passed else 'FAIL'}: {result.reason}")


def test_4_multi_turn(page: Page):
    """Test 4: Multi-Turn Context"""
    print(f"\n{'='*60}")
    print("TEST 4: Multi-Turn Context")
    print(f"{'='*60}")

    navigate_to_advisory(page)

    # First message
    response1 = send_message(page, "What are the notice period rules?")
    take_screenshot(page, "test4_turn1")

    page.wait_for_timeout(2000)

    # Follow-up
    response2 = send_message(page, "What if they've worked for 6 years?")
    screenshot = take_screenshot(page, "test4_turn2")

    text = response2.lower()
    # For 6 years service: 4 weeks notice under EA s.10
    has_4_weeks = "4 week" in text or "four week" in text
    has_context = (
        "notice" in text
        or "termination" in text
        or "employment act" in text
        or "section 10" in text
        or "s.10" in text
        or "s 10" in text
    )
    has_years = "year" in text or "service" in text

    passed = has_4_weeks and has_context
    reason = []
    if not has_4_weeks:
        reason.append("Missing 4 weeks notice period")
    if not has_context:
        reason.append("Missing notice period / EA context")

    result = TestResult(
        name="Test 4: Multi-Turn Context",
        passed=passed,
        reason="Multi-turn context maintained" if passed else "; ".join(reason),
        screenshot=screenshot,
        response_text=response2[:500],
    )
    results.append(result)
    print(f"  -> {'PASS' if passed else 'FAIL'}: {result.reason}")


def test_5_multi_domain(page: Page):
    """Test 5: Multi-Domain (EP + Termination)"""
    print(f"\n{'='*60}")
    print("TEST 5: Multi-Domain (EP + Termination)")
    print(f"{'='*60}")

    navigate_to_advisory(page)
    response = send_message(
        page, "My foreign worker's EP expires next month and I want to terminate them"
    )
    screenshot = take_screenshot(page, "test5_multidomain")

    text = response.lower()
    # Should cover EFMA (work pass) AND Employment Act (termination)
    has_work_pass = any(
        w in text
        for w in [
            "employment pass",
            "work pass",
            "ep",
            "efma",
            "foreign manpower",
            "mom",
            "cancel",
            "repatri",
            "special pass",
            "social visit",
        ]
    )
    has_termination = any(
        w in text
        for w in [
            "terminat",
            "notice period",
            "employment act",
            "last day",
            "final salary",
            "notice",
            "dismiss",
        ]
    )

    passed = has_work_pass and has_termination
    reason = []
    if not has_work_pass:
        reason.append("Missing work pass / EFMA coverage")
    if not has_termination:
        reason.append("Missing termination / EA coverage")

    result = TestResult(
        name="Test 5: Multi-Domain",
        passed=passed,
        reason="Both domains covered" if passed else "; ".join(reason),
        screenshot=screenshot,
        response_text=response[:500],
    )
    results.append(result)
    print(f"  -> {'PASS' if passed else 'FAIL'}: {result.reason}")


def test_6_out_of_scope(page: Page):
    """Test 6: Out-of-Scope Decline (CRITICAL — the bug we just fixed)"""
    print(f"\n{'='*60}")
    print("TEST 6: Out-of-Scope Decline (CRITICAL)")
    print(f"{'='*60}")

    navigate_to_advisory(page)
    response = send_message(page, "What is the weather today?")
    screenshot = take_screenshot(page, "test6_outofscope")

    text = response.lower()
    # Should show polite decline, NOT "Something went wrong"
    is_error = "something went wrong" in text or "error" in text or "failed" in text
    is_decline = any(
        d in text
        for d in [
            "hr",
            "employment",
            "payroll",
            "leave",
            "can only help",
            "workplace",
            "rephrase",
            "singapore",
            "not able to help with that",
            "outside",
            "scope",
        ]
    )

    passed = is_decline and not is_error
    reason = []
    if is_error:
        reason.append("Shows error message instead of decline")
    if not is_decline:
        reason.append("No polite decline message visible")
    if not response.strip():
        reason.append("Empty response (thinking indicator never resolved)")
        passed = False

    result = TestResult(
        name="Test 6: Out-of-Scope Decline (CRITICAL)",
        passed=passed,
        reason="Polite decline shown correctly" if passed else "; ".join(reason),
        screenshot=screenshot,
        response_text=response[:500],
    )
    results.append(result)
    print(f"  -> {'PASS' if passed else 'FAIL'}: {result.reason}")


def test_7_conversation_persistence(page: Page):
    """Test 7: Conversation Persistence"""
    print(f"\n{'='*60}")
    print("TEST 7: Conversation Persistence")
    print(f"{'='*60}")

    # Navigate away from advisory
    page.goto(f"{BASE_URL}/dashboard", wait_until="networkidle")
    page.wait_for_timeout(3000)

    # Navigate back to advisory
    page.goto(f"{BASE_URL}/advisory", wait_until="networkidle")
    page.wait_for_timeout(3000)
    screenshot = take_screenshot(page, "test7_persistence")

    # Check sidebar for conversation titles
    page_text = get_page_text(page)
    text = page_text.lower()

    # Look for auto-generated conversation titles in sidebar
    has_conversations = any(
        kw in text
        for kw in [
            "cpf",
            "maternity",
            "leave",
            "notice",
            "weather",
            "foreign",
            "s pass",
            "quota",
            "terminate",
            "termination",
        ]
    )

    # Also check for sidebar elements
    sidebar_items = page.locator(
        '[class*="sidebar"] button, [class*="sidebar"] a, [class*="sidebar"] [role="button"]'
    ).count()

    passed = has_conversations or sidebar_items > 1
    reason = []
    if not has_conversations:
        reason.append("No conversation titles found matching test queries")
    if sidebar_items <= 1:
        reason.append(f"Only {sidebar_items} sidebar items found")

    result = TestResult(
        name="Test 7: Conversation Persistence",
        passed=passed,
        reason="Conversations persist and show titles" if passed else "; ".join(reason),
        screenshot=screenshot,
        response_text=page_text[:500],
    )
    results.append(result)
    print(f"  -> {'PASS' if passed else 'FAIL'}: {result.reason}")


def print_summary():
    """Print the final summary table."""
    print(f"\n{'='*60}")
    print("FINAL RESULTS")
    print(f"{'='*60}")
    print(f"{'Test':<45} {'Result':<8} {'Reason'}")
    print(f"{'-'*45} {'-'*8} {'-'*40}")

    pass_count = 0
    fail_count = 0
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        if r.passed:
            pass_count += 1
        else:
            fail_count += 1
        print(f"{r.name:<45} {status:<8} {r.reason[:60]}")

    print(f"\n{'='*60}")
    print(f"TOTAL: {pass_count} PASS, {fail_count} FAIL out of {len(results)} tests")
    rate = pass_count / len(results) * 100 if results else 0
    print(f"PASS RATE: {rate:.0f}%")
    print(f"{'='*60}")

    if fail_count > 0:
        print("\nFailed test responses:")
        for r in results:
            if not r.passed:
                print(f"\n--- {r.name} ---")
                print(f"Response excerpt: {r.response_text[:300]}")
                print(f"Screenshot: {r.screenshot}")

    return fail_count == 0


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        )
        page = context.new_page()

        try:
            login(page)

            test_1_cpf_calculation(page)
            test_2_maternity_leave(page)
            test_3_spass_quota(page)
            test_4_multi_turn(page)
            test_5_multi_domain(page)
            test_6_out_of_scope(page)
            test_7_conversation_persistence(page)

        except Exception as e:
            print(f"\n*** FATAL ERROR: {e}")
            take_screenshot(page, "fatal_error")
            raise
        finally:
            all_passed = print_summary()
            browser.close()

        sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
