"""Deterministic regulatory change classifier.

Classifies detected changes from all monitoring sources (SSO RSS,
MOM sitemap, web change detection, Telegram) into actionable
categories: relevance, affected domains, urgency, and generates
plain-language summaries.

Uses deterministic keyword matching — no LLM dependency. This
ensures classification is fast, free, and deterministic.

T220: Regulatory Change Classifier (R06)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class Urgency(str, Enum):
    CRITICAL = "critical"  # Immediate action required (e.g., rate change effective now)
    HIGH = "high"  # Action within 1 week (e.g., new amendment gazetted)
    MEDIUM = "medium"  # Action within 1 month (e.g., upcoming regulatory change)
    LOW = "low"  # Informational (e.g., consultation paper, press release)


class Domain(str, Enum):
    PAYROLL = "payroll"
    CPF = "cpf"
    LEAVE = "leave"
    TAX = "tax"
    FOREIGN_WORKERS = "foreign_workers"
    WORKPLACE_SAFETY = "workplace_safety"
    FAIR_EMPLOYMENT = "fair_employment"
    RETIREMENT = "retirement"
    SKILLS_TRAINING = "skills_training"
    GENERAL_EMPLOYMENT = "general_employment"


@dataclass
class ClassificationInput:
    """Input to the classifier from any monitoring source."""

    title: str
    url: str
    source: str  # "sso_rss", "mom_sitemap", "change_detection", "telegram"
    description: str = ""
    diff_text: str = ""
    published_date: Optional[datetime] = None


@dataclass
class ClassificationResult:
    """Result of classifying a regulatory change."""

    is_relevant: bool
    confidence: float  # 0.0 to 1.0
    domains: list[Domain]
    urgency: Urgency
    summary: str
    action_items: list[str]
    affected_modules: list[str]  # AITE module names
    source: str
    title: str
    url: str
    classified_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "is_relevant": self.is_relevant,
            "confidence": round(self.confidence, 2),
            "domains": [d.value for d in self.domains],
            "urgency": self.urgency.value,
            "summary": self.summary,
            "action_items": self.action_items,
            "affected_modules": self.affected_modules,
            "source": self.source,
            "title": self.title,
            "url": self.url,
            "classified_at": self.classified_at.isoformat(),
        }


# ── Keyword-to-domain mapping ────────────────────────────────

# Each entry: (pattern, domain, weight).
# Pattern is a regex applied case-insensitively.
# Weight contributes to relevance confidence score.
_DOMAIN_RULES: list[tuple[str, Domain, float]] = [
    # CPF
    (r"\bcpf\b", Domain.CPF, 0.4),
    (r"central provident fund", Domain.CPF, 0.5),
    (r"ordinary account", Domain.CPF, 0.3),
    (r"special account", Domain.CPF, 0.3),
    (r"retirement account", Domain.CPF, 0.3),
    (r"medisave", Domain.CPF, 0.3),
    (r"cpf contribution", Domain.CPF, 0.5),
    (r"cpf rate", Domain.CPF, 0.5),
    (r"ordinary wage ceiling", Domain.CPF, 0.5),
    (r"additional wage ceiling", Domain.CPF, 0.5),
    # Payroll
    (r"\bpayroll\b", Domain.PAYROLL, 0.4),
    (r"\bsalary\b", Domain.PAYROLL, 0.3),
    (r"\bwages?\b", Domain.PAYROLL, 0.3),
    (r"minimum wage", Domain.PAYROLL, 0.4),
    (r"progressive wage", Domain.PAYROLL, 0.5),
    (r"overtime pay", Domain.PAYROLL, 0.4),
    (r"\bsdl\b", Domain.PAYROLL, 0.3),
    (r"skills development levy", Domain.PAYROLL, 0.4),
    (r"foreign worker levy", Domain.PAYROLL, 0.4),
    (r"\bfwl\b", Domain.PAYROLL, 0.3),
    (r"\bgiro\b", Domain.PAYROLL, 0.2),
    # Tax
    (r"\biras\b", Domain.TAX, 0.4),
    (r"\bir8a\b", Domain.TAX, 0.5),
    (r"\bir21\b", Domain.TAX, 0.5),
    (r"\bir8s\b", Domain.TAX, 0.5),
    (r"income tax", Domain.TAX, 0.4),
    (r"tax deduction", Domain.TAX, 0.3),
    (r"tax relief", Domain.TAX, 0.3),
    (r"year of assessment", Domain.TAX, 0.3),
    (r"auto.?inclusion", Domain.TAX, 0.4),
    # Leave
    (r"annual leave", Domain.LEAVE, 0.4),
    (r"sick leave", Domain.LEAVE, 0.4),
    (r"medical leave", Domain.LEAVE, 0.4),
    (r"maternity leave", Domain.LEAVE, 0.5),
    (r"paternity leave", Domain.LEAVE, 0.5),
    (r"childcare leave", Domain.LEAVE, 0.5),
    (r"shared parental leave", Domain.LEAVE, 0.5),
    (r"unpaid infant care", Domain.LEAVE, 0.4),
    (r"public holiday", Domain.LEAVE, 0.3),
    (r"rest day", Domain.LEAVE, 0.3),
    # Foreign workers
    (r"foreign manpower", Domain.FOREIGN_WORKERS, 0.5),
    (r"\befma\b", Domain.FOREIGN_WORKERS, 0.5),
    (r"work permit", Domain.FOREIGN_WORKERS, 0.4),
    (r"\bs pass\b", Domain.FOREIGN_WORKERS, 0.4),
    (r"employment pass", Domain.FOREIGN_WORKERS, 0.4),
    (r"dependant.?s? pass", Domain.FOREIGN_WORKERS, 0.3),
    (r"foreign worker", Domain.FOREIGN_WORKERS, 0.4),
    (r"migrant worker", Domain.FOREIGN_WORKERS, 0.4),
    (r"man-year entitlement", Domain.FOREIGN_WORKERS, 0.4),
    (r"quota", Domain.FOREIGN_WORKERS, 0.2),
    (r"levy tier", Domain.FOREIGN_WORKERS, 0.3),
    # Workplace safety
    (r"\bwsha\b", Domain.WORKPLACE_SAFETY, 0.5),
    (r"workplace safety", Domain.WORKPLACE_SAFETY, 0.5),
    (r"work injury", Domain.WORKPLACE_SAFETY, 0.4),
    (r"\bwica\b", Domain.WORKPLACE_SAFETY, 0.5),
    (r"occupational health", Domain.WORKPLACE_SAFETY, 0.4),
    (r"work accident", Domain.WORKPLACE_SAFETY, 0.4),
    # Fair employment
    (r"\btafep\b", Domain.FAIR_EMPLOYMENT, 0.5),
    (r"fair employment", Domain.FAIR_EMPLOYMENT, 0.5),
    (r"workplace fairness", Domain.FAIR_EMPLOYMENT, 0.5),
    (r"discrimination", Domain.FAIR_EMPLOYMENT, 0.3),
    (r"tripartite guidelines", Domain.FAIR_EMPLOYMENT, 0.4),
    (r"tripartite standard", Domain.FAIR_EMPLOYMENT, 0.3),
    # Retirement
    (r"\brra\b", Domain.RETIREMENT, 0.4),
    (r"retirement age", Domain.RETIREMENT, 0.5),
    (r"re-?employment age", Domain.RETIREMENT, 0.5),
    (r"retirement and re-?employment", Domain.RETIREMENT, 0.5),
    (r"senior worker", Domain.RETIREMENT, 0.3),
    # Skills/Training
    (r"skillsfuture", Domain.SKILLS_TRAINING, 0.5),
    (r"\bssg\b", Domain.SKILLS_TRAINING, 0.3),
    (r"skills development", Domain.SKILLS_TRAINING, 0.3),
    (r"training grant", Domain.SKILLS_TRAINING, 0.3),
    (r"absentee payroll", Domain.SKILLS_TRAINING, 0.4),
    # General employment
    (r"employment act", Domain.GENERAL_EMPLOYMENT, 0.5),
    (r"employment claims", Domain.GENERAL_EMPLOYMENT, 0.4),
    (r"\beca\b", Domain.GENERAL_EMPLOYMENT, 0.3),
    (r"retrenchment", Domain.GENERAL_EMPLOYMENT, 0.4),
    (r"termination of employment", Domain.GENERAL_EMPLOYMENT, 0.4),
    (r"notice period", Domain.GENERAL_EMPLOYMENT, 0.3),
    (r"probation", Domain.GENERAL_EMPLOYMENT, 0.2),
    (r"employment contract", Domain.GENERAL_EMPLOYMENT, 0.3),
]

# ── Urgency signal rules ─────────────────────────────────────

_URGENCY_SIGNALS: list[tuple[str, Urgency, float]] = [
    # Critical: immediate effect
    (r"effective immediately", Urgency.CRITICAL, 0.9),
    (r"with immediate effect", Urgency.CRITICAL, 0.9),
    (r"effective from \d{1,2}\s\w+\s\d{4}", Urgency.HIGH, 0.6),
    (r"gazetted", Urgency.HIGH, 0.7),
    (r"passed in parliament", Urgency.HIGH, 0.7),
    (r"enacted", Urgency.HIGH, 0.6),
    (r"amendment bill", Urgency.HIGH, 0.5),
    (r"rate change", Urgency.HIGH, 0.6),
    (r"rate increase", Urgency.HIGH, 0.7),
    (r"new rate", Urgency.HIGH, 0.6),
    (r"ceiling.*increase", Urgency.HIGH, 0.7),
    # Medium: upcoming
    (r"consultation paper", Urgency.LOW, 0.3),
    (r"proposed amendment", Urgency.MEDIUM, 0.5),
    (r"public consultation", Urgency.LOW, 0.3),
    (r"feedback invited", Urgency.LOW, 0.3),
    (r"will take effect", Urgency.MEDIUM, 0.5),
    (r"upcoming changes", Urgency.MEDIUM, 0.5),
    # Low: informational
    (r"press release", Urgency.LOW, 0.2),
    (r"media statement", Urgency.LOW, 0.2),
    (r"clarification", Urgency.LOW, 0.3),
    (r"faq", Urgency.LOW, 0.2),
    (r"infographic", Urgency.LOW, 0.1),
]

# ── Domain to AITE module mapping ────────────────────────────

_DOMAIN_MODULE_MAP: dict[Domain, list[str]] = {
    Domain.CPF: ["payroll_calculator", "cpf_engine", "statutory_files"],
    Domain.PAYROLL: ["payroll_calculator", "payslip_generator"],
    Domain.TAX: ["statutory_files", "ir8a_generator", "ir21_generator"],
    Domain.LEAVE: ["leave_engine", "leave_calendar", "payroll_calculator"],
    Domain.FOREIGN_WORKERS: ["foreign_worker_compliance", "payroll_calculator"],
    Domain.WORKPLACE_SAFETY: ["compliance_checker"],
    Domain.FAIR_EMPLOYMENT: ["compliance_checker", "advisory_engine"],
    Domain.RETIREMENT: ["payroll_calculator", "cpf_engine", "advisory_engine"],
    Domain.SKILLS_TRAINING: ["advisory_engine"],
    Domain.GENERAL_EMPLOYMENT: ["advisory_engine", "compliance_checker", "kb"],
}


class RegulatoryChangeClassifier:
    """Deterministic classifier for regulatory changes.

    Takes raw change data from monitoring sources and classifies it
    into: relevance (yes/no), affected HR domains, urgency level,
    and generates a plain-language summary with action items.

    All classification is keyword-based. No LLM calls.

    Usage::

        classifier = RegulatoryChangeClassifier()
        result = classifier.classify(ClassificationInput(
            title="CPF OW ceiling increase to $8,500",
            url="https://cpf.gov.sg/...",
            source="change_detection",
        ))
        print(result.urgency)  # Urgency.HIGH
        print(result.domains)  # [Domain.CPF, Domain.PAYROLL]
    """

    def __init__(
        self,
        relevance_threshold: float = 0.2,
        domain_rules: Optional[list] = None,
        urgency_signals: Optional[list] = None,
    ):
        self._relevance_threshold = relevance_threshold
        self._domain_rules = domain_rules or _DOMAIN_RULES
        self._urgency_signals = urgency_signals or _URGENCY_SIGNALS
        self._classifications: list[ClassificationResult] = []

    def classify(self, input_data: ClassificationInput) -> ClassificationResult:
        """Classify a regulatory change and return a structured result."""
        # Combine all text fields for analysis
        combined_text = " ".join(
            filter(
                None,
                [
                    input_data.title,
                    input_data.description,
                    input_data.diff_text,
                ],
            )
        )

        # Step 1: Find matching domains and compute relevance score
        domain_scores = self._score_domains(combined_text)
        domains = [d for d, score in domain_scores.items() if score > 0]
        max_score = max(domain_scores.values()) if domain_scores else 0.0

        # Total relevance confidence: sum of all domain scores, capped at 1.0
        total_score = min(1.0, sum(domain_scores.values()))
        is_relevant = total_score >= self._relevance_threshold and len(domains) > 0

        # Step 2: Determine urgency
        urgency = self._determine_urgency(combined_text)

        # Step 3: Determine affected AITE modules
        affected_modules = self._get_affected_modules(domains)

        # Step 4: Generate summary
        summary = self._generate_summary(input_data, domains, urgency)

        # Step 5: Generate action items
        action_items = self._generate_action_items(domains, urgency)

        result = ClassificationResult(
            is_relevant=is_relevant,
            confidence=total_score,
            domains=domains,
            urgency=urgency,
            summary=summary,
            action_items=action_items,
            affected_modules=affected_modules,
            source=input_data.source,
            title=input_data.title,
            url=input_data.url,
        )

        self._classifications.append(result)
        return result

    def _score_domains(self, text: str) -> dict[Domain, float]:
        """Score each domain based on keyword matches in the text."""
        scores: dict[Domain, float] = {}

        for pattern, domain, weight in self._domain_rules:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                current = scores.get(domain, 0.0)
                # Diminishing returns for multiple matches of the same pattern
                contribution = weight * min(len(matches), 3) / max(len(matches), 1)
                scores[domain] = min(1.0, current + contribution)

        return scores

    def _determine_urgency(self, text: str) -> Urgency:
        """Determine the urgency level based on signal keywords."""
        best_urgency = Urgency.LOW
        best_weight = 0.0

        for pattern, urgency, weight in self._urgency_signals:
            if re.search(pattern, text, re.IGNORECASE):
                if weight > best_weight:
                    best_urgency = urgency
                    best_weight = weight

        return best_urgency

    @staticmethod
    def _get_affected_modules(domains: list[Domain]) -> list[str]:
        """Map domains to affected AITE modules."""
        modules: set[str] = set()
        for domain in domains:
            module_list = _DOMAIN_MODULE_MAP.get(domain, [])
            modules.update(module_list)
        return sorted(modules)

    @staticmethod
    def _generate_summary(
        input_data: ClassificationInput,
        domains: list[Domain],
        urgency: Urgency,
    ) -> str:
        """Generate a plain-language summary of the regulatory change."""
        if not domains:
            return (
                f"A change was detected from {input_data.source}: "
                f'"{input_data.title}". '
                f"This does not appear to directly affect HR/employment operations."
            )

        domain_names = [d.value.replace("_", " ").title() for d in domains]
        domain_str = ", ".join(domain_names[:-1])
        if len(domain_names) > 1:
            domain_str += f" and {domain_names[-1]}"
        else:
            domain_str = domain_names[0]

        urgency_phrases = {
            Urgency.CRITICAL: "requires immediate attention",
            Urgency.HIGH: "requires action within the next week",
            Urgency.MEDIUM: "should be reviewed within the next month",
            Urgency.LOW: "is informational and may require future action",
        }

        source_names = {
            "sso_rss": "Singapore Statutes Online",
            "mom_sitemap": "Ministry of Manpower website",
            "change_detection": "a monitored government page",
            "telegram": "a government Telegram channel",
        }
        source_name = source_names.get(input_data.source, input_data.source)

        return (
            f'A regulatory change detected from {source_name}: "{input_data.title}". '
            f"This affects {domain_str} and {urgency_phrases[urgency]}."
        )

    @staticmethod
    def _generate_action_items(
        domains: list[Domain],
        urgency: Urgency,
    ) -> list[str]:
        """Generate specific action items based on domains and urgency."""
        items: list[str] = []

        if urgency in (Urgency.CRITICAL, Urgency.HIGH):
            items.append("Review the regulatory change details at the source URL")

        for domain in domains:
            if domain == Domain.CPF:
                items.append(
                    "Verify CPF contribution rates in payroll calculator match latest rates"
                )
                items.append("Check if CPF OW/AW ceilings have changed")
            elif domain == Domain.PAYROLL:
                items.append("Review payroll calculation parameters for updates")
            elif domain == Domain.TAX:
                items.append("Check if tax filing templates or deadlines are affected")
            elif domain == Domain.LEAVE:
                items.append("Review leave entitlement calculations for compliance")
                items.append("Update public holiday calendar if applicable")
            elif domain == Domain.FOREIGN_WORKERS:
                items.append("Review foreign worker levy rates and quota limits")
                items.append("Check work pass eligibility criteria for changes")
            elif domain == Domain.WORKPLACE_SAFETY:
                items.append("Review workplace safety compliance checklist")
            elif domain == Domain.FAIR_EMPLOYMENT:
                items.append("Review fair employment practice guidelines for updates")
            elif domain == Domain.RETIREMENT:
                items.append("Check retirement and re-employment age thresholds")
            elif domain == Domain.SKILLS_TRAINING:
                items.append("Review SkillsFuture grant eligibility and course listings")

        if urgency in (Urgency.CRITICAL, Urgency.HIGH):
            items.append("Create a regulatory update record for admin review")

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_items: list[str] = []
        for item in items:
            if item not in seen:
                seen.add(item)
                unique_items.append(item)

        return unique_items

    def get_recent_classifications(self, limit: int = 50) -> list[dict]:
        """Return recent classification results."""
        sorted_results = sorted(
            self._classifications,
            key=lambda c: c.classified_at,
            reverse=True,
        )
        return [r.to_dict() for r in sorted_results[:limit]]

    def get_classification_stats(self) -> dict:
        """Return statistics about classification activity."""
        total = len(self._classifications)
        relevant = sum(1 for c in self._classifications if c.is_relevant)
        by_urgency: dict[str, int] = {}
        by_domain: dict[str, int] = {}

        for c in self._classifications:
            by_urgency[c.urgency.value] = by_urgency.get(c.urgency.value, 0) + 1
            for d in c.domains:
                by_domain[d.value] = by_domain.get(d.value, 0) + 1

        return {
            "total_classified": total,
            "relevant": relevant,
            "irrelevant": total - relevant,
            "by_urgency": by_urgency,
            "by_domain": by_domain,
        }
