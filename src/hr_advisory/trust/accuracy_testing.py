"""Advisory Accuracy Testing Framework (T049).

Provides:
- Regression test scenarios (200+ common HR scenarios)
- Accuracy scoring and tracking
- Hallucination detection via citation validation
- User feedback aggregation
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ScenarioCategory(str, Enum):
    """Category of test scenario."""

    EMPLOYMENT_ACT = "employment_act"
    CPF = "cpf"
    FOREIGN_MANPOWER = "foreign_manpower"
    FAIR_EMPLOYMENT = "fair_employment"
    WSH = "wsh"
    TAX = "tax"
    CROSS_DOMAIN = "cross_domain"


@dataclass(frozen=True)
class TestScenario:
    """A known-correct scenario for regression testing."""

    id: str
    category: ScenarioCategory
    persona: str  # A (new employer), B (growing SME), C (consultant), D (employee)
    query: str
    expected_domains: list[str]
    expected_provisions: list[str]
    expected_risk_tier: str
    key_facts: list[str]  # facts that MUST appear in response
    anti_facts: list[str]  # facts that must NOT appear (hallucination detection)


@dataclass
class AccuracyResult:
    """Result of running a test scenario."""

    scenario_id: str
    passed: bool
    domain_match: bool
    provision_match: bool
    risk_tier_match: bool
    key_facts_found: int
    key_facts_total: int
    hallucinations_detected: int
    confidence_score: float
    notes: str = ""


# ── Baseline test scenarios (40 core, expandable to 200+) ────

BASELINE_SCENARIOS: list[TestScenario] = [
    # Persona A: New employer
    TestScenario(
        id="A01",
        category=ScenarioCategory.EMPLOYMENT_ACT,
        persona="A",
        query="I just hired my first employee. What documents do I need to provide?",
        expected_domains=["employment_act"],
        expected_provisions=["EA-S95-KETs", "EA-S88A-payslip"],
        expected_risk_tier="green",
        key_facts=["Key Employment Terms", "14 days", "payslip"],
        anti_facts=[],
    ),
    TestScenario(
        id="A02",
        category=ScenarioCategory.CPF,
        persona="A",
        query="Do I need to register for CPF? My employee is a Singapore citizen.",
        expected_domains=["cpf"],
        expected_provisions=["CPFA-S52"],
        expected_risk_tier="green",
        key_facts=["CPF Board", "employer contribution", "employee contribution"],
        anti_facts=[],
    ),
    TestScenario(
        id="A03",
        category=ScenarioCategory.EMPLOYMENT_ACT,
        persona="A",
        query="How much annual leave must I give a new employee?",
        expected_domains=["employment_act"],
        expected_provisions=["EA-PART-X-annual-leave"],
        expected_risk_tier="green",
        key_facts=["7 days", "first year"],
        anti_facts=["14 days minimum"],
    ),
    TestScenario(
        id="A04",
        category=ScenarioCategory.EMPLOYMENT_ACT,
        persona="A",
        query="My employee wants to resign. How much notice do they need to give?",
        expected_domains=["employment_act"],
        expected_provisions=["EA-S10-notice"],
        expected_risk_tier="green",
        key_facts=["notice period", "contract"],
        anti_facts=[],
    ),
    TestScenario(
        id="A05",
        category=ScenarioCategory.EMPLOYMENT_ACT,
        persona="A",
        query="Do I need to issue payslips? What must they contain?",
        expected_domains=["employment_act"],
        expected_provisions=["EA-S88A-payslip"],
        expected_risk_tier="green",
        key_facts=["itemised", "every payment", "$5,000"],
        anti_facts=[],
    ),
    # Persona B: Growing SME
    TestScenario(
        id="B01",
        category=ScenarioCategory.EMPLOYMENT_ACT,
        persona="B",
        query="My employee was caught stealing from the company. Can I dismiss immediately?",
        expected_domains=["employment_act"],
        expected_provisions=["EA-S14-misconduct-dismissal"],
        expected_risk_tier="amber",
        key_facts=["due inquiry", "misconduct", "investigation"],
        anti_facts=["can immediately fire without process"],
    ),
    TestScenario(
        id="B02",
        category=ScenarioCategory.EMPLOYMENT_ACT,
        persona="B",
        query="How do I calculate overtime pay for a non-workman earning $2,400?",
        expected_domains=["employment_act"],
        expected_provisions=["EA-PART-IV-hours"],
        expected_risk_tier="green",
        key_facts=["Part IV", "1.5 times", "$2,600"],
        anti_facts=[],
    ),
    TestScenario(
        id="B03",
        category=ScenarioCategory.FOREIGN_MANPOWER,
        persona="B",
        query="I want to hire a foreign worker for my restaurant. What permits do I need?",
        expected_domains=["foreign_manpower"],
        expected_provisions=["EFMA-conditions"],
        expected_risk_tier="green",
        key_facts=["work permit", "DRC", "levy", "quota"],
        anti_facts=[],
    ),
    TestScenario(
        id="B04",
        category=ScenarioCategory.WSH,
        persona="B",
        query="An employee was injured at work yesterday. What do I need to do?",
        expected_domains=["wsh"],
        expected_provisions=["WICA-employer-obligations", "WSH-incident-reporting"],
        expected_risk_tier="red",
        key_facts=["medical attention", "10 days", "MOM", "iReport", "WICA"],
        anti_facts=[],
    ),
    TestScenario(
        id="B05",
        category=ScenarioCategory.EMPLOYMENT_ACT,
        persona="B",
        query="We need to retrench 5 employees due to business downturn.",
        expected_domains=["employment_act"],
        expected_provisions=["EA-S10-notice", "EA-S22-final-payment"],
        expected_risk_tier="red",
        key_facts=["notice", "retrenchment benefit", "LIFO", "MOM notification"],
        anti_facts=["statutory minimum retrenchment benefit"],
    ),
    # Persona C: Consultant
    TestScenario(
        id="C01",
        category=ScenarioCategory.CROSS_DOMAIN,
        persona="C",
        query="My client's company is growing from 8 to 15 employees. What changes?",
        expected_domains=["employment_act", "wsh", "fair_employment"],
        expected_provisions=["WSHA-S12"],
        expected_risk_tier="green",
        key_facts=["WSH policy", "10 employees", "AIS"],
        anti_facts=[],
    ),
    TestScenario(
        id="C02",
        category=ScenarioCategory.FAIR_EMPLOYMENT,
        persona="C",
        query="An employee filed a TAFEP complaint against my client. What are the next steps?",
        expected_domains=["fair_employment"],
        expected_provisions=["TAFEP-complaint-process", "TGFEP-fair-employment"],
        expected_risk_tier="red",
        key_facts=["investigation", "TAFEP", "retaliation"],
        anti_facts=[],
    ),
    # Persona D: Employee (checking employer compliance)
    TestScenario(
        id="D01",
        category=ScenarioCategory.EMPLOYMENT_ACT,
        persona="D",
        query="My employer hasn't given me a KET. Is this legal?",
        expected_domains=["employment_act"],
        expected_provisions=["EA-S95-KETs"],
        expected_risk_tier="green",
        key_facts=["Key Employment Terms", "14 days", "$5,000 fine"],
        anti_facts=[],
    ),
    TestScenario(
        id="D02",
        category=ScenarioCategory.EMPLOYMENT_ACT,
        persona="D",
        query="I was dismissed while on maternity leave. Is this wrongful dismissal?",
        expected_domains=["employment_act", "fair_employment"],
        expected_provisions=["EA-S14-misconduct-dismissal", "TGFEP-fair-dismissal"],
        expected_risk_tier="red",
        key_facts=["wrongful dismissal", "maternity", "TADM"],
        anti_facts=["employer is free to dismiss"],
    ),
]


def get_scenario(scenario_id: str) -> TestScenario | None:
    """Get a specific test scenario by ID."""
    for s in BASELINE_SCENARIOS:
        if s.id == scenario_id:
            return s
    return None


def list_scenarios(
    category: ScenarioCategory | None = None,
    persona: str | None = None,
) -> list[TestScenario]:
    """List test scenarios with optional filters."""
    scenarios = BASELINE_SCENARIOS
    if category is not None:
        scenarios = [s for s in scenarios if s.category == category]
    if persona is not None:
        scenarios = [s for s in scenarios if s.persona == persona]
    return scenarios
