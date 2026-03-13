"""Sector-Specific Playbooks (T051).

Pre-configured advisory packages for major Singapore SME sectors,
each containing:
- Sector-specific regulatory provisions and applicability rules
- Common compliance challenges for the sector
- Suggested questions in natural Singapore English
- Sector-relevant calculator configurations

Supported sectors: F&B, Construction, Technology, Professional Services,
Manufacturing, Retail.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Sector(str, Enum):
    """Supported SME sectors."""

    FNB = "fnb"
    CONSTRUCTION = "construction"
    TECHNOLOGY = "technology"
    PROFESSIONAL_SERVICES = "professional_services"
    MANUFACTURING = "manufacturing"
    RETAIL = "retail"


@dataclass(frozen=True)
class ComplianceChallenge:
    """A common compliance challenge for a sector."""

    title: str
    description: str
    risk_tier: str  # green, amber, red
    relevant_provisions: list[str]


@dataclass(frozen=True)
class SectorPlaybook:
    """Complete advisory package for a sector."""

    sector: Sector
    display_name: str
    description: str
    key_regulations: list[str]
    applicable_provisions: list[str]
    common_challenges: list[ComplianceChallenge]
    suggested_questions: list[str]
    calculator_focus: list[str]  # which calculators are most relevant
    drc_category: str  # Dependency Ratio Ceiling category if applicable
    pwm_applicable: bool  # Progressive Wage Model applicability


# ── Sector playbook definitions ──────────────────────────────

PLAYBOOKS: dict[Sector, SectorPlaybook] = {
    Sector.FNB: SectorPlaybook(
        sector=Sector.FNB,
        display_name="Food & Beverage",
        description="Restaurants, cafes, catering, food manufacturing",
        key_regulations=[
            "Employment Act — Part IV (hours, overtime, rest days)",
            "EFMA — Work permit conditions, Services DRC",
            "PWM — Cleaning staff (if applicable)",
            "WSH Act — Kitchen safety, food hygiene",
            "CPF Act — Contributions for all local employees",
        ],
        applicable_provisions=[
            "EA-PART-IV-hours",
            "EA-S88A-payslip",
            "EA-S95-KETs",
            "EFMA-conditions",
            "CPFA-S52",
            "WSH-incident-reporting",
            "WICA-employer-obligations",
        ],
        common_challenges=[
            ComplianceChallenge(
                title="Foreign worker quota management",
                description=(
                    "Services sector DRC is 35% for S Pass and 8% for work permit. "
                    "High turnover makes quota tracking critical."
                ),
                risk_tier="amber",
                relevant_provisions=["EFMA-conditions"],
            ),
            ComplianceChallenge(
                title="Split shift and overtime calculation",
                description=(
                    "F&B commonly uses split shifts. Overtime for Part IV employees "
                    "must be calculated at 1.5x for work beyond 8 hours/day or 44 hours/week."
                ),
                risk_tier="amber",
                relevant_provisions=["EA-PART-IV-hours"],
            ),
            ComplianceChallenge(
                title="Public holiday pay for hourly workers",
                description=(
                    "Employees who work on a public holiday are entitled to an extra "
                    "day's pay. Part-time employees get pro-rated PH pay."
                ),
                risk_tier="green",
                relevant_provisions=["EA-PART-X-annual-leave"],
            ),
            ComplianceChallenge(
                title="Kitchen workplace injuries",
                description=(
                    "Burns, cuts, and slips are common. Must report to MOM within "
                    "10 days if medical leave exceeds 3 days. WICA coverage required."
                ),
                risk_tier="red",
                relevant_provisions=["WSH-incident-reporting", "WICA-employer-obligations"],
            ),
        ],
        suggested_questions=[
            "How do I calculate overtime for my kitchen staff who work split shifts?",
            "What's the foreign worker quota for my restaurant?",
            "My staff got burned at work — what do I need to report?",
            "Do I need to pay my part-time server for public holidays?",
            "How much levy do I pay for my work permit holders?",
        ],
        calculator_focus=["cpf", "quota_levy", "leave"],
        drc_category="services",
        pwm_applicable=False,  # unless cleaning staff
    ),
    Sector.CONSTRUCTION: SectorPlaybook(
        sector=Sector.CONSTRUCTION,
        display_name="Construction",
        description="Building, civil engineering, renovation contractors",
        key_regulations=[
            "EFMA — Work permit conditions, Construction DRC",
            "WSH Act — Safety requirements, BCA regulations",
            "WICA — Mandatory insurance for all employees",
            "Employment Act — Hours, overtime, dormitory obligations",
            "CPF Act — Contributions for local workers",
        ],
        applicable_provisions=[
            "EA-PART-IV-hours",
            "EA-S88A-payslip",
            "EA-S95-KETs",
            "EFMA-conditions",
            "WSHA-S12",
            "WSH-incident-reporting",
            "WICA-employer-obligations",
            "CPFA-S52",
        ],
        common_challenges=[
            ComplianceChallenge(
                title="Higher foreign worker levy tiers",
                description=(
                    "Construction levies are higher than services. Skilled workers "
                    "pay lower levy than unskilled. Must track skill certification."
                ),
                risk_tier="amber",
                relevant_provisions=["EFMA-conditions"],
            ),
            ComplianceChallenge(
                title="Mandatory safety training",
                description=(
                    "All construction workers must complete Safety Orientation "
                    "Course (SOC). Site supervisors need additional WSQ certifications."
                ),
                risk_tier="red",
                relevant_provisions=["WSHA-S12"],
            ),
            ComplianceChallenge(
                title="Workplace injury reporting",
                description=(
                    "Construction has the highest workplace injury rate. Strict "
                    "MOM reporting within 10 days. Stop-work orders for serious breaches."
                ),
                risk_tier="red",
                relevant_provisions=["WSH-incident-reporting", "WICA-employer-obligations"],
            ),
            ComplianceChallenge(
                title="Dormitory obligations",
                description=(
                    "Employers housing foreign workers must meet MOM dormitory "
                    "standards including space, hygiene, and recreational facilities."
                ),
                risk_tier="amber",
                relevant_provisions=["EFMA-conditions"],
            ),
        ],
        suggested_questions=[
            "What safety courses must my construction workers complete?",
            "How much levy do I pay for skilled vs unskilled foreign workers?",
            "A worker fell at the site — what are my reporting obligations?",
            "What are the dormitory requirements for my foreign workers?",
            "What's the DRC quota for construction companies?",
        ],
        calculator_focus=["cpf", "quota_levy"],
        drc_category="construction",
        pwm_applicable=False,
    ),
    Sector.TECHNOLOGY: SectorPlaybook(
        sector=Sector.TECHNOLOGY,
        display_name="Technology",
        description="Software, IT services, digital platforms, tech startups",
        key_regulations=[
            "EFMA — EP/COMPASS framework for foreign tech talent",
            "PDPA — Data protection obligations",
            "Employment Act — Flexible work, stock options",
            "CPF Act — Contributions, stock option tax treatment",
            "TGFEP — Fair employment for diverse workforce",
        ],
        applicable_provisions=[
            "EA-S88A-payslip",
            "EA-S95-KETs",
            "EFMA-conditions",
            "PDPA-obligations",
            "TGFEP-fair-employment",
            "CPFA-S52",
        ],
        common_challenges=[
            ComplianceChallenge(
                title="COMPASS framework for EP applications",
                description=(
                    "Employment Pass applications now assessed under COMPASS "
                    "with points for salary, qualifications, diversity, and skills bonus."
                ),
                risk_tier="amber",
                relevant_provisions=["EFMA-conditions"],
            ),
            ComplianceChallenge(
                title="Stock option tax treatment",
                description=(
                    "Employee stock options are taxable as employment income on "
                    "exercise. Must track grant date, vesting, and exercise for "
                    "IRAS reporting. CPF not payable on stock option gains."
                ),
                risk_tier="amber",
                relevant_provisions=["CPFA-S52"],
            ),
            ComplianceChallenge(
                title="PDPA compliance for data roles",
                description=(
                    "Tech companies handling personal data must appoint a DPO, "
                    "implement data protection policies, and comply with PDPA "
                    "notification and consent requirements."
                ),
                risk_tier="amber",
                relevant_provisions=["PDPA-obligations"],
            ),
            ComplianceChallenge(
                title="Flexible work arrangement norms",
                description=(
                    "Tripartite Guidelines on Flexible Work Arrangements require "
                    "employers to fairly consider FWA requests. Tech companies "
                    "often have remote-first policies that exceed requirements."
                ),
                risk_tier="green",
                relevant_provisions=["TGFEP-fair-employment"],
            ),
        ],
        suggested_questions=[
            "What's the COMPASS score needed for my developer's EP application?",
            "How do I handle stock option taxation for my engineers?",
            "Do I need a Data Protection Officer for my startup?",
            "Can I reject an employee's request to work from home?",
            "What's the Fair Consideration Framework requirement for tech roles?",
        ],
        calculator_focus=["cpf"],
        drc_category="services",
        pwm_applicable=False,
    ),
    Sector.PROFESSIONAL_SERVICES: SectorPlaybook(
        sector=Sector.PROFESSIONAL_SERVICES,
        display_name="Professional Services",
        description="Consulting, legal, accounting, engineering firms",
        key_regulations=[
            "EFMA — EP salary thresholds, FCF compliance",
            "Employment Act — Non-compete clauses, notice periods",
            "TGFEP — Fair employment, advertising requirements",
            "CPF Act — Contributions for higher-income employees",
            "PDPA — Client data handling",
        ],
        applicable_provisions=[
            "EA-S10-notice",
            "EA-S88A-payslip",
            "EA-S95-KETs",
            "EFMA-conditions",
            "TGFEP-fair-employment",
            "CPFA-S52",
            "PDPA-obligations",
        ],
        common_challenges=[
            ComplianceChallenge(
                title="EP salary threshold compliance",
                description=(
                    "Minimum qualifying salary for EP is $5,000 (higher for "
                    "financial services at $5,500). Must be reviewed when "
                    "thresholds change annually."
                ),
                risk_tier="amber",
                relevant_provisions=["EFMA-conditions"],
            ),
            ComplianceChallenge(
                title="Non-compete and restraint of trade",
                description=(
                    "Non-compete clauses must be reasonable in scope, duration, "
                    "and geography. Singapore courts apply strict reasonableness test."
                ),
                risk_tier="amber",
                relevant_provisions=["EA-S10-notice"],
            ),
            ComplianceChallenge(
                title="MyCareersFuture advertising obligation",
                description=(
                    "Must advertise on MyCareersFuture for 14 days before "
                    "applying for EP (Fair Consideration Framework). Exemptions "
                    "for short-term and intra-corporate transfers."
                ),
                risk_tier="amber",
                relevant_provisions=["TGFEP-fair-employment", "EFMA-conditions"],
            ),
            ComplianceChallenge(
                title="CPF for high-income employees",
                description=(
                    "CPF Ordinary Wage ceiling is $8,000/month. Additional Wage "
                    "ceiling applies. Must calculate correctly for professionals "
                    "with bonus structures."
                ),
                risk_tier="green",
                relevant_provisions=["CPFA-S52"],
            ),
        ],
        suggested_questions=[
            "What's the minimum salary for an EP for my consulting firm?",
            "Is my non-compete clause enforceable in Singapore?",
            "Do I need to advertise on MyCareersFuture before hiring a foreigner?",
            "How do I calculate CPF for employees earning above the OW ceiling?",
            "Can I hire a foreign intern for my accounting firm?",
        ],
        calculator_focus=["cpf", "quota_levy"],
        drc_category="services",
        pwm_applicable=False,
    ),
    Sector.MANUFACTURING: SectorPlaybook(
        sector=Sector.MANUFACTURING,
        display_name="Manufacturing",
        description="Electronics, precision engineering, chemicals, food manufacturing",
        key_regulations=[
            "WSH Act — Factory safety, noise exposure, chemical handling",
            "Employment Act — Shift work, Part IV hours",
            "EFMA — Manufacturing DRC, work permit conditions",
            "WICA — Workplace injury compensation",
            "CPF Act — Contributions for shift workers",
        ],
        applicable_provisions=[
            "EA-PART-IV-hours",
            "EA-S88A-payslip",
            "EA-S95-KETs",
            "EFMA-conditions",
            "WSHA-S12",
            "WSH-incident-reporting",
            "WICA-employer-obligations",
            "CPFA-S52",
        ],
        common_challenges=[
            ComplianceChallenge(
                title="Shift work overtime calculation",
                description=(
                    "Manufacturing commonly uses 3-shift rotations. Must track "
                    "44-hour weekly limit across irregular shift patterns. "
                    "Overtime at 1.5x for Part IV employees."
                ),
                risk_tier="amber",
                relevant_provisions=["EA-PART-IV-hours"],
            ),
            ComplianceChallenge(
                title="Noise exposure and safety monitoring",
                description=(
                    "Must conduct noise monitoring if workers are exposed to "
                    "85dB+ for 8 hours. Annual audiometric testing required. "
                    "PPE provision mandatory."
                ),
                risk_tier="red",
                relevant_provisions=["WSHA-S12", "WSH-incident-reporting"],
            ),
            ComplianceChallenge(
                title="Chemical handling compliance",
                description=(
                    "Hazardous chemicals must be stored, handled, and disposed "
                    "per WSH regulations. Safety Data Sheets must be accessible. "
                    "Workers need chemical safety training."
                ),
                risk_tier="red",
                relevant_provisions=["WSHA-S12"],
            ),
            ComplianceChallenge(
                title="Manufacturing DRC management",
                description=(
                    "Manufacturing sector has its own DRC limits. Must manage "
                    "quota across different worker categories and skill levels."
                ),
                risk_tier="amber",
                relevant_provisions=["EFMA-conditions"],
            ),
        ],
        suggested_questions=[
            "How do I calculate overtime for workers on rotating 3-shift schedule?",
            "What noise monitoring do I need for my factory floor?",
            "What's the foreign worker quota for manufacturing?",
            "A worker was exposed to chemicals — what are my obligations?",
            "Do I need a WSH Officer for my factory?",
        ],
        calculator_focus=["cpf", "quota_levy", "leave"],
        drc_category="manufacturing",
        pwm_applicable=False,
    ),
    Sector.RETAIL: SectorPlaybook(
        sector=Sector.RETAIL,
        display_name="Retail",
        description="Shops, supermarkets, department stores, e-commerce with physical presence",
        key_regulations=[
            "Employment Act — Part-time work, PH pay, shift scheduling",
            "EFMA — Services DRC, work permit conditions",
            "CPF Act — Part-time CPF calculations",
            "PWM — Applicable for some retail cleaning roles",
            "TGFEP — Fair employment in hiring",
        ],
        applicable_provisions=[
            "EA-PART-IV-hours",
            "EA-PART-X-annual-leave",
            "EA-S88A-payslip",
            "EA-S95-KETs",
            "EFMA-conditions",
            "TGFEP-fair-employment",
            "CPFA-S52",
        ],
        common_challenges=[
            ComplianceChallenge(
                title="Part-time employee management",
                description=(
                    "Part-time employees (work <35 hrs/week) get pro-rated "
                    "leave, PH pay, and sick leave. CPF contributions based on "
                    "actual wages with no pro-ration of rates."
                ),
                risk_tier="green",
                relevant_provisions=["EA-PART-IV-hours", "EA-PART-X-annual-leave"],
            ),
            ComplianceChallenge(
                title="Public holiday working arrangements",
                description=(
                    "Retail often requires PH work. Employees working on PH "
                    "entitled to extra day's pay or substituted day off. "
                    "Must be agreed in advance."
                ),
                risk_tier="green",
                relevant_provisions=["EA-PART-X-annual-leave"],
            ),
            ComplianceChallenge(
                title="Weekend and evening shift scheduling",
                description=(
                    "Employees must have 1 rest day per week (unpaid for Part IV). "
                    "Work on rest day attracts premium pay. Retail scheduling "
                    "must comply with Part IV limits."
                ),
                risk_tier="amber",
                relevant_provisions=["EA-PART-IV-hours"],
            ),
            ComplianceChallenge(
                title="PWM for cleaning staff",
                description=(
                    "If retail employs in-house cleaners, Progressive Wage Model "
                    "minimum wages apply. Must meet annual wage increments."
                ),
                risk_tier="amber",
                relevant_provisions=["EA-PART-IV-hours"],
            ),
        ],
        suggested_questions=[
            "How do I calculate leave for my part-time retail staff?",
            "My shop is open on public holidays — how do I pay my workers?",
            "What's the minimum rest day requirement for my sales staff?",
            "Does PWM apply to cleaners in my shop?",
            "How much CPF do I pay for a part-time cashier?",
        ],
        calculator_focus=["cpf", "leave", "quota_levy"],
        drc_category="services",
        pwm_applicable=True,
    ),
}


# ── Public API ───────────────────────────────────────────────


def get_playbook(sector: Sector) -> SectorPlaybook:
    """Get the playbook for a sector."""
    return PLAYBOOKS[sector]


def get_all_playbooks() -> list[SectorPlaybook]:
    """Get all sector playbooks."""
    return list(PLAYBOOKS.values())


def get_sector_challenges(sector: Sector) -> list[ComplianceChallenge]:
    """Get compliance challenges for a sector."""
    return list(PLAYBOOKS[sector].common_challenges)


def get_sector_questions(sector: Sector) -> list[str]:
    """Get suggested questions for a sector."""
    return list(PLAYBOOKS[sector].suggested_questions)


def get_applicable_provisions(sector: Sector) -> list[str]:
    """Get provision IDs applicable to a sector."""
    return list(PLAYBOOKS[sector].applicable_provisions)


def match_sector(sector_name: str) -> Sector | None:
    """Match a free-text sector name to a Sector enum.

    Handles common variations like 'F&B', 'food', 'tech', etc.
    """
    normalised = sector_name.lower().strip()
    mapping: dict[str, Sector] = {
        "fnb": Sector.FNB,
        "f&b": Sector.FNB,
        "food": Sector.FNB,
        "food and beverage": Sector.FNB,
        "food & beverage": Sector.FNB,
        "restaurant": Sector.FNB,
        "cafe": Sector.FNB,
        "catering": Sector.FNB,
        "construction": Sector.CONSTRUCTION,
        "building": Sector.CONSTRUCTION,
        "renovation": Sector.CONSTRUCTION,
        "contractor": Sector.CONSTRUCTION,
        "technology": Sector.TECHNOLOGY,
        "tech": Sector.TECHNOLOGY,
        "it": Sector.TECHNOLOGY,
        "software": Sector.TECHNOLOGY,
        "startup": Sector.TECHNOLOGY,
        "professional services": Sector.PROFESSIONAL_SERVICES,
        "consulting": Sector.PROFESSIONAL_SERVICES,
        "legal": Sector.PROFESSIONAL_SERVICES,
        "accounting": Sector.PROFESSIONAL_SERVICES,
        "engineering": Sector.PROFESSIONAL_SERVICES,
        "manufacturing": Sector.MANUFACTURING,
        "factory": Sector.MANUFACTURING,
        "electronics": Sector.MANUFACTURING,
        "retail": Sector.RETAIL,
        "shop": Sector.RETAIL,
        "store": Sector.RETAIL,
        "supermarket": Sector.RETAIL,
    }
    return mapping.get(normalised)
