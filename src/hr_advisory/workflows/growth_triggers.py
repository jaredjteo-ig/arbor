"""Growth-Stage Triggers (T052).

Proactive advisory that fires when a company's profile crosses
regulatory thresholds. Triggers are evaluated whenever a user
updates their company profile (employee count, first foreign hire,
first EP hire, etc.).

Each trigger:
- Has a condition function evaluated against company profile
- Produces an alert with title, summary, and relevant provisions
- Links to detailed advisory content
- Fires once per threshold crossing (idempotent)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional


class TriggerCategory(str, Enum):
    """Category of growth trigger."""

    HEADCOUNT = "headcount"
    FOREIGN_WORKER = "foreign_worker"
    COMPLIANCE = "compliance"


class TriggerPriority(str, Enum):
    """Priority level for the trigger alert."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class TriggerAlert:
    """Alert produced when a growth trigger fires."""

    trigger_id: str
    category: TriggerCategory
    priority: TriggerPriority
    title: str
    summary: str
    details: list[str]
    relevant_provisions: list[str]
    suggested_actions: list[str]
    advisory_query: str  # suggested query to ask the advisor


@dataclass(frozen=True)
class CompanyProfile:
    """Minimal company profile snapshot for trigger evaluation.

    In production, populated from the DataFlow Company model.
    """

    employee_count: int
    has_foreign_workers: bool = False
    foreign_worker_count: int = 0
    has_ep_holders: bool = False
    ep_holder_count: int = 0
    sector: str = ""
    previous_employee_count: int = 0  # for detecting threshold crossing


# ── Trigger definitions ──────────────────────────────────────

# Each trigger is a tuple of:
# (trigger_id, condition_fn, alert_factory_fn)

TriggerCondition = Callable[[CompanyProfile], bool]
AlertFactory = Callable[[CompanyProfile], TriggerAlert]


def _crossed_threshold(profile: CompanyProfile, threshold: int) -> bool:
    """Check if employee count just crossed a threshold upward."""
    return profile.employee_count >= threshold and profile.previous_employee_count < threshold


# ── 5 employees ──────────────────────────────────────────────


def _condition_5(profile: CompanyProfile) -> bool:
    return _crossed_threshold(profile, 5)


def _alert_5(profile: CompanyProfile) -> TriggerAlert:
    _ = profile
    return TriggerAlert(
        trigger_id="GROWTH-5",
        category=TriggerCategory.HEADCOUNT,
        priority=TriggerPriority.LOW,
        title="You now have 5+ employees",
        summary=(
            "With 5 or more employees, you should ensure all basic employment "
            "documentation is in place. While most statutory obligations start "
            "from the first employee, 5+ is a good checkpoint."
        ),
        details=[
            "Ensure all employees have Key Employment Terms (KET) issued within 14 days of start",
            "Verify all employees receive itemised payslips",
            "Confirm CPF contributions are set up correctly for all local employees",
            "Consider formalising leave and attendance tracking",
        ],
        relevant_provisions=["EA-S95-KETs", "EA-S88A-payslip", "CPFA-S52"],
        suggested_actions=[
            "Review all employee KETs for completeness",
            "Set up systematic payslip generation",
            "Verify CPF submission records are current",
        ],
        advisory_query="What documentation do I need for 5 employees?",
    )


# ── 10 employees ─────────────────────────────────────────────


def _condition_10(profile: CompanyProfile) -> bool:
    return _crossed_threshold(profile, 10)


def _alert_10(profile: CompanyProfile) -> TriggerAlert:
    _ = profile
    return TriggerAlert(
        trigger_id="GROWTH-10",
        category=TriggerCategory.HEADCOUNT,
        priority=TriggerPriority.MEDIUM,
        title="You now have 10+ employees — new obligations apply",
        summary=(
            "Crossing the 10-employee threshold triggers several new "
            "regulatory requirements including workplace safety policies "
            "and enhanced record-keeping."
        ),
        details=[
            "Must implement a WSH policy (Workplace Safety and Health Act, Section 12)",
            "Auto-Inclusion Scheme (AIS) submission to IRAS required — employee income reported electronically",
            "Enhanced record-keeping: maintain employment records for all current + 2 years post-exit",
            "Consider appointing a workplace safety coordinator",
        ],
        relevant_provisions=["WSHA-S12", "EA-S95-KETs"],
        suggested_actions=[
            "Draft and implement a WSH policy",
            "Register for AIS with IRAS",
            "Set up a 2-year record retention system",
        ],
        advisory_query="My company just reached 10 employees. What changes?",
    )


# ── 25 employees ─────────────────────────────────────────────


def _condition_25(profile: CompanyProfile) -> bool:
    return _crossed_threshold(profile, 25)


def _alert_25(profile: CompanyProfile) -> TriggerAlert:
    _ = profile
    return TriggerAlert(
        trigger_id="GROWTH-25",
        category=TriggerCategory.HEADCOUNT,
        priority=TriggerPriority.MEDIUM,
        title="You now have 25+ employees — enhanced compliance requirements",
        summary=(
            "At 25+ employees, your company faces increased regulatory "
            "scrutiny and additional obligations around fair employment "
            "and retrenchment notification."
        ),
        details=[
            "TAFEP scrutiny increases — ensure all hiring practices comply with fair employment guidelines",
            "Fair Consideration Framework (FCF) — must advertise on MyCareersFuture for 14 days before EP applications",
            "Retrenchment: if retrenching 5+ employees in 6 months, must notify MOM",
            "Consider engaging an HR practitioner or consultant",
        ],
        relevant_provisions=["TGFEP-fair-employment", "EFMA-conditions", "EA-S10-notice"],
        suggested_actions=[
            "Audit hiring practices against TAFEP guidelines",
            "Set up MyCareersFuture job posting process",
            "Document retrenchment notification procedures",
        ],
        advisory_query="We've grown to 25 employees. What new rules apply?",
    )


# ── 50 employees ─────────────────────────────────────────────


def _condition_50(profile: CompanyProfile) -> bool:
    return _crossed_threshold(profile, 50)


def _alert_50(profile: CompanyProfile) -> TriggerAlert:
    _ = profile
    return TriggerAlert(
        trigger_id="GROWTH-50",
        category=TriggerCategory.HEADCOUNT,
        priority=TriggerPriority.HIGH,
        title="You now have 50+ employees — significant compliance milestone",
        summary=(
            "50 employees is a major regulatory milestone. Depending on your "
            "sector, you may need a designated WSH Officer and enhanced "
            "MOM reporting."
        ),
        details=[
            "WSH Officer requirement — mandatory for certain sectors (construction, manufacturing, marine)",
            "Enhanced MOM reporting obligations",
            "Should consider formalising HR policies (employee handbook)",
            "Consider employment practices certification or HR audit",
            "Tripartite Alliance for Dispute Management (TADM) access for employees",
        ],
        relevant_provisions=["WSHA-S12", "WSH-incident-reporting", "TADM-mediation"],
        suggested_actions=[
            "Check if your sector requires a WSH Officer",
            "Create or update employee handbook",
            "Conduct an HR compliance audit",
        ],
        advisory_query="We have 50 employees now. Do I need a WSH Officer?",
    )


# ── 100 employees ────────────────────────────────────────────


def _condition_100(profile: CompanyProfile) -> bool:
    return _crossed_threshold(profile, 100)


def _alert_100(profile: CompanyProfile) -> TriggerAlert:
    _ = profile
    return TriggerAlert(
        trigger_id="GROWTH-100",
        category=TriggerCategory.HEADCOUNT,
        priority=TriggerPriority.HIGH,
        title="You now have 100+ employees — enterprise compliance expectations",
        summary=(
            "At 100+ employees, regulatory bodies expect mature HR "
            "practices and proactive compliance. Consider engaging "
            "professional HR support."
        ),
        details=[
            "Enhanced compliance expectations from MOM and TAFEP",
            "Should have formalised grievance handling procedures",
            "Annual compliance self-assessment recommended",
            "Consider IHRP-certified HR professional on staff",
            "Data protection: PDPA compliance becomes more critical with larger employee database",
        ],
        relevant_provisions=["TGFEP-fair-employment", "PDPA-obligations"],
        suggested_actions=[
            "Hire or engage an IHRP-certified HR professional",
            "Implement formal grievance handling process",
            "Conduct annual PDPA compliance review",
        ],
        advisory_query="We've reached 100 employees. What should we focus on?",
    )


# ── First foreign worker ────────────────────────────────────


def _condition_first_foreign(profile: CompanyProfile) -> bool:
    return profile.has_foreign_workers and profile.foreign_worker_count == 1


def _alert_first_foreign(profile: CompanyProfile) -> TriggerAlert:
    sector_note = (
        f" Your sector ({profile.sector}) has specific DRC limits." if profile.sector else ""
    )
    return TriggerAlert(
        trigger_id="GROWTH-FIRST-FW",
        category=TriggerCategory.FOREIGN_WORKER,
        priority=TriggerPriority.HIGH,
        title="First foreign worker hired — key obligations",
        summary=(
            "Hiring your first foreign worker triggers several new "
            "employer obligations around permits, levies, and quotas." + sector_note
        ),
        details=[
            "Work permit or S Pass must be obtained before employment starts",
            "Dependency Ratio Ceiling (DRC) — your foreign worker count is limited by local headcount",
            "Foreign worker levy is payable monthly to MOM",
            "Must provide adequate housing and medical insurance",
            "Cannot retain worker's passport or personal belongings",
            "Must send worker home at own cost upon work permit cancellation",
        ],
        relevant_provisions=["EFMA-conditions"],
        suggested_actions=[
            "Understand your sector's DRC quota limits",
            "Set up monthly levy payment",
            "Arrange medical insurance and accommodation",
            "Review EFMA employer responsibilities",
        ],
        advisory_query="I just hired my first foreign worker. What do I need to know?",
    )


# ── First EP hire ────────────────────────────────────────────


def _condition_first_ep(profile: CompanyProfile) -> bool:
    return profile.has_ep_holders and profile.ep_holder_count == 1


def _alert_first_ep(profile: CompanyProfile) -> TriggerAlert:
    _ = profile
    return TriggerAlert(
        trigger_id="GROWTH-FIRST-EP",
        category=TriggerCategory.FOREIGN_WORKER,
        priority=TriggerPriority.MEDIUM,
        title="First Employment Pass holder — COMPASS and FCF requirements",
        summary=(
            "Hiring your first EP holder means you need to comply with "
            "the COMPASS framework and Fair Consideration Framework."
        ),
        details=[
            "COMPASS — EP applications assessed on salary, qualifications, diversity, and strategic skills",
            "Fair Consideration Framework — must advertise on MyCareersFuture for 14 days before EP application",
            "Minimum qualifying salary: $5,000 (higher for financial services)",
            "EP holders are not covered by Part IV of Employment Act (no overtime rules)",
            "CPF is payable for Singapore PRs on EP, not for foreigners",
        ],
        relevant_provisions=["EFMA-conditions", "TGFEP-fair-employment", "CPFA-S52"],
        suggested_actions=[
            "Register on MyCareersFuture for job advertising",
            "Verify EP salary meets COMPASS minimum",
            "Check COMPASS eligibility before applying",
        ],
        advisory_query="I'm hiring my first EP holder. What are the COMPASS requirements?",
    )


# ── Trigger registry ────────────────────────────────────────

_TRIGGERS: list[tuple[str, TriggerCondition, AlertFactory]] = [
    ("GROWTH-5", _condition_5, _alert_5),
    ("GROWTH-10", _condition_10, _alert_10),
    ("GROWTH-25", _condition_25, _alert_25),
    ("GROWTH-50", _condition_50, _alert_50),
    ("GROWTH-100", _condition_100, _alert_100),
    ("GROWTH-FIRST-FW", _condition_first_foreign, _alert_first_foreign),
    ("GROWTH-FIRST-EP", _condition_first_ep, _alert_first_ep),
]

# Track which triggers have already fired per company (in-memory).
# In production, backed by DataFlow model.
_fired_triggers: dict[str, set[str]] = {}  # company_id → set of trigger_ids


# ── Public API ───────────────────────────────────────────────


def evaluate_triggers(
    company_id: str,
    profile: CompanyProfile,
) -> list[TriggerAlert]:
    """Evaluate all triggers against a company profile.

    Returns list of newly-fired trigger alerts. Each trigger only
    fires once per company (idempotent).
    """
    fired = _fired_triggers.get(company_id, set())
    new_alerts: list[TriggerAlert] = []

    for trigger_id, condition_fn, alert_fn in _TRIGGERS:
        if trigger_id in fired:
            continue
        if condition_fn(profile):
            alert = alert_fn(profile)
            new_alerts.append(alert)
            fired.add(trigger_id)

    _fired_triggers[company_id] = fired
    return new_alerts


def get_fired_triggers(company_id: str) -> list[str]:
    """Get list of trigger IDs that have already fired for a company."""
    return list(_fired_triggers.get(company_id, set()))


def reset_triggers(company_id: str) -> None:
    """Reset fired triggers for a company (for testing)."""
    _fired_triggers.pop(company_id, None)


def get_all_trigger_ids() -> list[str]:
    """Get all registered trigger IDs."""
    return [t[0] for t in _TRIGGERS]


def get_trigger_alert(
    trigger_id: str,
    profile: Optional[CompanyProfile] = None,
) -> TriggerAlert | None:
    """Get a specific trigger alert by ID (for preview/documentation)."""
    if profile is None:
        profile = CompanyProfile(employee_count=0)
    for tid, _, alert_fn in _TRIGGERS:
        if tid == trigger_id:
            return alert_fn(profile)
    return None
