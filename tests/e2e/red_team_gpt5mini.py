#!/usr/bin/env python3
"""Red Team: gpt-5-mini Model Quality Evaluation.

Runs 7 tests against the Arbor advisory engine via API, capturing:
- Response time
- Citation specificity
- Response structure (headings, bullets)
- Hallucination checks
- Calculator tool usage
- Raw response text

Usage: python tests/e2e/red_team_gpt5mini.py
"""

import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

import requests

BASE_URL = os.environ.get("ARBOR_URL", "https://arbor.terrene.foundation")
EMAIL = "test@arbor.dev"
PASSWORD = "TestPass2026"


@dataclass
class TestResult:
    name: str
    passed: bool
    reason: str
    response_time: float = 0.0
    response_text: str = ""
    quality: str = ""  # EXCELLENT, GOOD, ACCEPTABLE, POOR
    citations_specific: bool = False
    well_structured: bool = False
    hallucination: str = ""  # any detected hallucination
    used_calculator: bool = False
    llm_info: dict = field(default_factory=dict)
    provisions_cited: list = field(default_factory=list)
    confidence_score: float = 0.0
    risk_tier: str = ""
    conversation_id: Optional[int] = None


results: list[TestResult] = []
token = ""
conversation_ids: list[int] = []


def login():
    global token
    print(f"\n{'='*70}")
    print("LOGGING IN")
    print(f"{'='*70}")
    resp = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
        timeout=15,
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    print(f"  -> Login successful")


def query(text: str, conversation_id: Optional[int] = None) -> tuple[dict, float]:
    """Send a query and return (response_dict, elapsed_seconds)."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {"query": text, "conversation_id": conversation_id}
    start = time.time()
    resp = requests.post(
        f"{BASE_URL}/api/advisory/query",
        json=payload,
        headers=headers,
        timeout=120,
    )
    elapsed = time.time() - start
    resp.raise_for_status()
    return resp.json(), elapsed


def check_citations(text: str, provisions: list) -> tuple[bool, str]:
    """Check if citations are specific (section numbers) vs vague."""
    import re

    specific_patterns = [
        r"[Ss]ection\s+\d+",
        r"[Ss]\.\s*\d+",
        r"[Pp]art\s+[IVXLC]+",
        r"[Rr]egulation\s+\d+",
        r"[Rr]ule\s+\d+",
        r"[Cc]lause\s+\d+",
        r"[Ss]chedule\s+\d+",
        r"[Cc]hapter\s+\d+",
        r"EA\s+[Ss]\.\s*\d+",
    ]
    found = []
    for p in specific_patterns:
        matches = re.findall(p, text)
        found.extend(matches)

    has_specific = len(found) > 0 or len(provisions) > 0
    detail = f"Found: {found}" if found else "No specific section numbers cited"
    return has_specific, detail


def check_structure(text: str) -> tuple[bool, str]:
    """Check if response uses headings, bullets, numbered lists."""
    has_headings = "##" in text or "**" in text
    has_bullets = any(text.count(b) >= 2 for b in ["- ", "* ", "1.", "2."])
    has_newlines = text.count("\n") >= 3
    structured = (has_headings or has_bullets) and has_newlines
    parts = []
    if has_headings:
        parts.append("headings/bold")
    if has_bullets:
        parts.append("bullets/lists")
    if has_newlines:
        parts.append("paragraphs")
    return structured, ", ".join(parts) if parts else "unstructured wall of text"


def check_hallucination_cpf(text: str) -> str:
    """Check CPF-specific hallucinations."""
    import re

    issues = []
    # Wrong rates for age 45 citizen
    if "37%" in text and "total" in text.lower():
        pass  # 37% total is correct (17% + 20%)
    # Check for obviously wrong numbers
    if "1,350" in text or "1350" in text:
        issues.append("Wrong employer contribution ($1,350 instead of $1,275)")
    if "1,600" in text or "1600" in text:
        issues.append("Wrong employee contribution ($1,600 instead of $1,500)")
    return "; ".join(issues) if issues else ""


def assess_quality(result: TestResult) -> str:
    """Assign EXCELLENT/GOOD/ACCEPTABLE/POOR."""
    score = 0
    if result.passed:
        score += 40
    if result.citations_specific:
        score += 20
    if result.well_structured:
        score += 15
    if not result.hallucination:
        score += 15
    if result.response_time < 15:
        score += 5
    elif result.response_time < 30:
        score += 3
    if result.confidence_score >= 0.8:
        score += 5

    if score >= 85:
        return "EXCELLENT"
    elif score >= 65:
        return "GOOD"
    elif score >= 45:
        return "ACCEPTABLE"
    else:
        return "POOR"


# -----------------------------------------------------------------------
# Test Functions
# -----------------------------------------------------------------------


def test_1_cpf():
    print(f"\n{'='*70}")
    print("TEST 1: CPF Calculation")
    print(f"{'='*70}")

    data, elapsed = query("Calculate CPF for a 45-year-old Singapore citizen earning $7,500/month")
    text = data.get("response", "")
    provisions = data.get("provisions_cited", [])
    llm_info = data.get("llm_info", {})

    print(f"  Response time: {elapsed:.1f}s")
    print(f"  Model: {llm_info}")
    print(f"  Provisions: {provisions}")
    print(f"  Confidence: {data.get('confidence_score')}")
    print(f"  Response ({len(text)} chars): {text[:200]}...")

    has_employer = "1,275" in text or "1275" in text
    has_employee = "1,500" in text or "1500" in text
    has_total = "2,775" in text or "2775" in text
    passed = has_employer and has_employee and has_total

    citations_ok, citation_detail = check_citations(text, provisions)
    structured, structure_detail = check_structure(text)
    hallucination = check_hallucination_cpf(text)

    # Check if calculator was used (look for tool usage indicators)
    used_calc = "calculator" in text.lower() or data.get("risk_tier") == "green"

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
        response_time=elapsed,
        response_text=text,
        citations_specific=citations_ok,
        well_structured=structured,
        hallucination=hallucination,
        used_calculator=used_calc,
        llm_info=llm_info,
        provisions_cited=provisions,
        confidence_score=data.get("confidence_score", 0),
        risk_tier=data.get("risk_tier", ""),
        conversation_id=data.get("conversation_id"),
    )
    result.quality = assess_quality(result)
    results.append(result)
    if result.conversation_id:
        conversation_ids.append(result.conversation_id)
    print(f"  -> {'PASS' if passed else 'FAIL'} | Quality: {result.quality}")
    print(f"  -> Citations: {citation_detail}")
    print(f"  -> Structure: {structure_detail}")
    if hallucination:
        print(f"  -> HALLUCINATION: {hallucination}")


def test_2_maternity():
    print(f"\n{'='*70}")
    print("TEST 2: Maternity Leave")
    print(f"{'='*70}")

    data, elapsed = query("How much maternity leave is my employee entitled to?")
    text = data.get("response", "")
    provisions = data.get("provisions_cited", [])
    llm_info = data.get("llm_info", {})

    print(f"  Response time: {elapsed:.1f}s")
    print(f"  Model: {llm_info}")
    print(f"  Response ({len(text)} chars): {text[:200]}...")

    text_lower = text.lower()
    has_16_weeks = "16 week" in text_lower or "16-week" in text_lower
    has_ea = (
        "employment act" in text_lower
        or "part ix" in text_lower
        or "cdcsa" in text_lower
        or "child development" in text_lower
    )
    has_citizen = "citizen" in text_lower or "non-citizen" in text_lower or "child" in text_lower
    has_gpml = (
        "gpml" in text_lower or "government-paid" in text_lower or "government paid" in text_lower
    )

    passed = has_16_weeks and (has_ea or has_citizen)

    citations_ok, citation_detail = check_citations(text, provisions)
    structured, structure_detail = check_structure(text)

    # Hallucination check: common wrong info
    hallucination = ""
    if "12 week" in text_lower and "16 week" not in text_lower:
        hallucination = "States 12 weeks instead of 16 weeks"
    if "8 week" in text_lower and "first" not in text_lower:
        hallucination = "States 8 weeks without context of first 8 weeks employer-paid"

    reason = []
    if not has_16_weeks:
        reason.append("Missing 16 weeks")
    if not has_ea:
        reason.append("Missing Employment Act/Part IX/CDCSA")
    if not has_citizen:
        reason.append("Missing citizen distinction")

    result = TestResult(
        name="Test 2: Maternity Leave",
        passed=passed,
        reason="Maternity leave info correct" if passed else "; ".join(reason),
        response_time=elapsed,
        response_text=text,
        citations_specific=citations_ok,
        well_structured=structured,
        hallucination=hallucination,
        llm_info=llm_info,
        provisions_cited=provisions,
        confidence_score=data.get("confidence_score", 0),
        risk_tier=data.get("risk_tier", ""),
        conversation_id=data.get("conversation_id"),
    )
    result.quality = assess_quality(result)
    results.append(result)
    if result.conversation_id:
        conversation_ids.append(result.conversation_id)
    print(f"  -> {'PASS' if passed else 'FAIL'} | Quality: {result.quality}")
    print(f"  -> Citations: {citation_detail}")
    print(f"  -> Structure: {structure_detail}")
    print(f"  -> GPML mentioned: {has_gpml}")
    if hallucination:
        print(f"  -> HALLUCINATION: {hallucination}")


def test_3_spass():
    print(f"\n{'='*70}")
    print("TEST 3: S Pass Quota")
    print(f"{'='*70}")

    data, elapsed = query(
        "What is the S Pass quota for a services company with 50 local employees?"
    )
    text = data.get("response", "")
    provisions = data.get("provisions_cited", [])
    llm_info = data.get("llm_info", {})

    print(f"  Response time: {elapsed:.1f}s")
    print(f"  Model: {llm_info}")
    print(f"  Response ({len(text)} chars): {text[:200]}...")

    text_lower = text.lower()
    has_drc = (
        "drc" in text_lower
        or "dependency ratio" in text_lower
        or "ratio ceiling" in text_lower
        or "foreign worker" in text_lower
    )
    has_35 = "35%" in text_lower or "35 per" in text_lower
    has_calc = any(w in text_lower for w in ["headroom", "quota", "maximum", "entitled", "cap"])
    has_number = any(str(n) in text for n in range(10, 30))  # Should calculate ~17-19

    passed = (has_drc or has_35) and has_calc

    citations_ok, citation_detail = check_citations(text, provisions)
    structured, structure_detail = check_structure(text)

    hallucination = ""
    # Check for obviously wrong quota info
    if "10%" in text_lower and "s pass" in text_lower:
        hallucination = "States 10% S Pass quota (incorrect for services)"
    if "50%" in text_lower:
        hallucination = "States 50% quota (too high)"

    reason = []
    if not has_drc and not has_35:
        reason.append("Missing DRC or 35%")
    if not has_calc:
        reason.append("Missing quota calculation")

    result = TestResult(
        name="Test 3: S Pass Quota",
        passed=passed,
        reason="S Pass quota correct" if passed else "; ".join(reason),
        response_time=elapsed,
        response_text=text,
        citations_specific=citations_ok,
        well_structured=structured,
        hallucination=hallucination,
        llm_info=llm_info,
        provisions_cited=provisions,
        confidence_score=data.get("confidence_score", 0),
        risk_tier=data.get("risk_tier", ""),
        conversation_id=data.get("conversation_id"),
    )
    result.quality = assess_quality(result)
    results.append(result)
    if result.conversation_id:
        conversation_ids.append(result.conversation_id)
    print(f"  -> {'PASS' if passed else 'FAIL'} | Quality: {result.quality}")
    print(f"  -> Citations: {citation_detail}")
    print(f"  -> Structure: {structure_detail}")
    print(f"  -> Specific number provided: {has_number}")
    if hallucination:
        print(f"  -> HALLUCINATION: {hallucination}")


def test_4_multiturn():
    print(f"\n{'='*70}")
    print("TEST 4: Multi-Turn Context")
    print(f"{'='*70}")

    # Turn 1
    data1, elapsed1 = query("What are the notice period rules?")
    conv_id = data1.get("conversation_id")
    text1 = data1.get("response", "")
    print(f"  Turn 1 time: {elapsed1:.1f}s")
    print(f"  Turn 1 ({len(text1)} chars): {text1[:150]}...")
    print(f"  Conversation ID: {conv_id}")

    # Turn 2 — use same conversation
    data2, elapsed2 = query("What if they've worked for 6 years?", conversation_id=conv_id)
    text2 = data2.get("response", "")
    provisions = data2.get("provisions_cited", [])
    llm_info = data2.get("llm_info", {})

    print(f"  Turn 2 time: {elapsed2:.1f}s")
    print(f"  Turn 2 ({len(text2)} chars): {text2[:200]}...")

    text_lower = text2.lower()
    has_4_weeks = "4 week" in text_lower or "four week" in text_lower
    has_context = any(
        w in text_lower
        for w in ["notice", "termination", "employment act", "section 10", "s.10", "s 10"]
    )

    # Critical: did it maintain context about notice periods?
    maintained_context = "notice" in text_lower or "terminat" in text_lower

    passed = has_4_weeks and has_context

    citations_ok, citation_detail = check_citations(text2, provisions)
    structured, structure_detail = check_structure(text2)

    hallucination = ""
    if "2 week" in text_lower and "4 week" not in text_lower:
        hallucination = "States 2 weeks for 6 years service (should be 4 weeks)"
    if "1 month" in text_lower and "4 week" not in text_lower:
        hallucination = "States 1 month without clarifying 4 weeks"

    reason = []
    if not has_4_weeks:
        reason.append("Missing 4 weeks notice")
    if not has_context:
        reason.append("Missing notice/EA context")
    if not maintained_context:
        reason.append("LOST CONTEXT: not about notice periods anymore")

    result = TestResult(
        name="Test 4: Multi-Turn Context",
        passed=passed,
        reason="Context maintained, 4 weeks correct" if passed else "; ".join(reason),
        response_time=elapsed1 + elapsed2,
        response_text=f"TURN 1:\n{text1}\n\nTURN 2:\n{text2}",
        citations_specific=citations_ok,
        well_structured=structured,
        hallucination=hallucination,
        llm_info=llm_info,
        provisions_cited=provisions,
        confidence_score=data2.get("confidence_score", 0),
        risk_tier=data2.get("risk_tier", ""),
        conversation_id=conv_id,
    )
    result.quality = assess_quality(result)
    results.append(result)
    if conv_id:
        conversation_ids.append(conv_id)
    print(f"  -> {'PASS' if passed else 'FAIL'} | Quality: {result.quality}")
    print(f"  -> Context maintained: {maintained_context}")
    print(f"  -> Citations: {citation_detail}")
    if hallucination:
        print(f"  -> HALLUCINATION: {hallucination}")


def test_5_multidomain():
    print(f"\n{'='*70}")
    print("TEST 5: Multi-Domain (EP + Termination)")
    print(f"{'='*70}")

    data, elapsed = query("My foreign worker's EP expires next month and I want to terminate them")
    text = data.get("response", "")
    provisions = data.get("provisions_cited", [])
    llm_info = data.get("llm_info", {})

    print(f"  Response time: {elapsed:.1f}s")
    print(f"  Response ({len(text)} chars): {text[:200]}...")

    text_lower = text.lower()
    has_wp = any(
        w in text_lower
        for w in [
            "employment pass",
            "work pass",
            "efma",
            "foreign manpower",
            "mom",
            "cancel",
            "repatri",
            "special pass",
            "social visit",
        ]
    )
    has_term = any(
        w in text_lower
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

    passed = has_wp and has_term

    citations_ok, citation_detail = check_citations(text, provisions)
    structured, structure_detail = check_structure(text)

    hallucination = ""
    # Check for wrong EP validity info
    if "2 year" in text_lower and "valid" in text_lower and "renew" not in text_lower:
        hallucination = "May have wrong EP validity period"

    reason = []
    if not has_wp:
        reason.append("Missing work pass/EFMA coverage")
    if not has_term:
        reason.append("Missing termination/EA coverage")

    result = TestResult(
        name="Test 5: Multi-Domain",
        passed=passed,
        reason="Both domains covered" if passed else "; ".join(reason),
        response_time=elapsed,
        response_text=text,
        citations_specific=citations_ok,
        well_structured=structured,
        hallucination=hallucination,
        llm_info=llm_info,
        provisions_cited=provisions,
        confidence_score=data.get("confidence_score", 0),
        risk_tier=data.get("risk_tier", ""),
        conversation_id=data.get("conversation_id"),
    )
    result.quality = assess_quality(result)
    results.append(result)
    if result.conversation_id:
        conversation_ids.append(result.conversation_id)
    print(f"  -> {'PASS' if passed else 'FAIL'} | Quality: {result.quality}")
    print(f"  -> Citations: {citation_detail}")
    print(f"  -> Structure: {structure_detail}")
    if hallucination:
        print(f"  -> HALLUCINATION: {hallucination}")


def test_6_outofscope():
    print(f"\n{'='*70}")
    print("TEST 6: Out-of-Scope Decline")
    print(f"{'='*70}")

    data, elapsed = query("What is the weather today?")
    text = data.get("response", "")
    llm_info = data.get("llm_info", {})

    print(f"  Response time: {elapsed:.1f}s")
    print(f"  Response ({len(text)} chars): {text}")

    text_lower = text.lower()
    is_error = (
        "something went wrong" in text_lower or "error" in text_lower or "failed" in text_lower
    )
    is_decline = any(
        d in text_lower
        for d in [
            "hr",
            "employment",
            "payroll",
            "leave",
            "can only help",
            "workplace",
            "rephrase",
            "singapore",
            "not able to help",
            "outside",
            "scope",
            "assist with",
        ]
    )

    passed = is_decline and not is_error

    reason = []
    if is_error:
        reason.append("Shows error instead of decline")
    if not is_decline:
        reason.append("No polite decline")
    if not text.strip():
        reason.append("Empty response")
        passed = False

    result = TestResult(
        name="Test 6: Out-of-Scope",
        passed=passed,
        reason="Polite decline" if passed else "; ".join(reason),
        response_time=elapsed,
        response_text=text,
        llm_info=llm_info,
        confidence_score=data.get("confidence_score", 0),
        risk_tier=data.get("risk_tier", ""),
        conversation_id=data.get("conversation_id"),
    )
    result.quality = "GOOD" if passed else "POOR"
    results.append(result)
    if result.conversation_id:
        conversation_ids.append(result.conversation_id)
    print(f"  -> {'PASS' if passed else 'FAIL'} | Quality: {result.quality}")


def test_7_persistence():
    print(f"\n{'='*70}")
    print("TEST 7: Conversation Persistence")
    print(f"{'='*70}")

    headers = {"Authorization": f"Bearer {token}"}

    # List conversations
    resp = requests.get(
        f"{BASE_URL}/api/advisory/conversations",
        headers=headers,
        timeout=15,
    )
    if resp.status_code == 200:
        raw = resp.json()
        # Handle both list and dict response formats
        if isinstance(raw, dict):
            convos = raw.get("conversations", [])
            total = raw.get("total", len(convos))
        elif isinstance(raw, list):
            convos = raw
            total = len(convos)
        else:
            convos = []
            total = 0

        print(f"  Found {total} conversations")
        for c in convos[:10]:
            print(f"    - ID {c.get('id')}: {c.get('title', 'no title')}")

        # Check if our test conversations are there
        all_titles = " ".join(c.get("title", "").lower() for c in convos)
        has_test_convos = any(
            kw in all_titles
            for kw in [
                "cpf",
                "maternity",
                "leave",
                "notice",
                "weather",
                "foreign",
                "s pass",
                "terminat",
            ]
        )

        passed = has_test_convos and total > 0

        result = TestResult(
            name="Test 7: Persistence",
            passed=passed,
            reason=(
                f"{total} conversations found, titles match"
                if passed
                else f"Only {total} conversations, no matching titles"
            ),
            response_time=0,
            response_text=json.dumps(convos[:5], indent=2),
        )
        result.quality = "GOOD" if passed else "POOR"
        results.append(result)
    else:
        print(f"  Conversations endpoint returned {resp.status_code}")
        # Try via the conversation IDs we collected
        passed = len(conversation_ids) >= 5
        result = TestResult(
            name="Test 7: Persistence",
            passed=passed,
            reason=(
                f"Collected {len(conversation_ids)} conversation IDs during tests"
                if passed
                else "Could not verify persistence"
            ),
            response_time=0,
        )
        result.quality = "ACCEPTABLE" if passed else "POOR"
        results.append(result)

    print(f"  -> {'PASS' if result.passed else 'FAIL'} | Quality: {result.quality}")


# -----------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------


def print_summary():
    print(f"\n{'='*70}")
    print("FINAL RESULTS — gpt-5-mini Red Team Evaluation")
    print(f"{'='*70}")
    print(
        f"{'Test':<35} {'Pass?':<7} {'Quality':<12} {'Time':<8} {'Citations':<10} {'Structure':<10} {'Halluc?'}"
    )
    print(f"{'-'*35} {'-'*7} {'-'*12} {'-'*8} {'-'*10} {'-'*10} {'-'*10}")

    pass_count = 0
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        if r.passed:
            pass_count += 1
        time_str = f"{r.response_time:.1f}s" if r.response_time > 0 else "n/a"
        cite = "YES" if r.citations_specific else "NO"
        struct = "YES" if r.well_structured else "NO"
        halluc = r.hallucination[:15] if r.hallucination else "none"
        print(
            f"{r.name:<35} {status:<7} {r.quality:<12} {time_str:<8} {cite:<10} {struct:<10} {halluc}"
        )

    fail_count = len(results) - pass_count
    print(f"\n{'='*70}")
    print(f"TOTAL: {pass_count} PASS, {fail_count} FAIL out of {len(results)} tests")
    print(f"PASS RATE: {pass_count / len(results) * 100:.0f}%")
    print(f"Model: {results[0].llm_info if results else 'unknown'}")

    avg_time = sum(r.response_time for r in results if r.response_time > 0) / max(
        sum(1 for r in results if r.response_time > 0), 1
    )
    print(f"Avg response time: {avg_time:.1f}s")
    print(f"{'='*70}")

    if fail_count > 0:
        print("\n--- FAILED TESTS ---")
        for r in results:
            if not r.passed:
                print(f"\n{r.name}:")
                print(f"  Reason: {r.reason}")
                print(f"  Response: {r.response_text[:400]}")

    # Print full responses for analysis
    print(f"\n{'='*70}")
    print("FULL RESPONSES (for manual review)")
    print(f"{'='*70}")
    for r in results:
        print(f"\n--- {r.name} ---")
        print(f"Time: {r.response_time:.1f}s | Quality: {r.quality}")
        print(f"Provisions cited: {r.provisions_cited}")
        print(f"Confidence: {r.confidence_score} | Risk: {r.risk_tier}")
        print(f"Response:\n{r.response_text[:1500]}")
        print()

    return fail_count == 0


def main():
    login()
    test_1_cpf()
    test_2_maternity()
    test_3_spass()
    test_4_multiturn()
    test_5_multidomain()
    test_6_outofscope()
    test_7_persistence()
    all_passed = print_summary()
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
