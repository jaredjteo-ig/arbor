"""Pre-retrieval domain classifier for the Advisory engine.

Red-team finding O2 / X2 / C3 (workspaces/obayashi/04-validate/
13-redteam-comprehensive-2026-05-19.md): the flagship advisory
classified "How do I calculate CPF contributions?" as domain
`["general"]` because the engine has NO input-side domain
classifier — domains are derived purely from which `search_kb(domain=...)`
calls the LLM happened to emit. When the model answers from its
parametric memory (as it did for CPF), no `search_kb` runs, the
domain falls back to "general", and the response recites stale
training data (e.g. "OW ceiling scheduled to reach $8,000 by 2026"
when we're already in 2026 and the ceiling IS $8,000).

This module fixes that by adding a deterministic keyword/regex
detector that maps the user query to one or more domains BEFORE the
LLM turn. The caller can then pre-fetch KB content and inject it
into the conversation so the model always has grounded provisions
in context — never reasoning from parametric memory alone.

The classifier is intentionally simple and deterministic — keyword
matching gives transparent, debuggable behaviour, and the LLM still
chooses how to use the retrieved content. The classifier doesn't
replace the LLM's reasoning — it just guarantees that for known
domains, the LLM gets the relevant KB provisions in its context
from turn 1.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# Canonical domain enum used downstream by `_search_kb_with_fallback`.
# Mirrors the 6 regulatory domains the platform claims to cover.
DOMAIN_CPF = "cpf"
DOMAIN_EMPLOYMENT_ACT = "employment_act"
DOMAIN_EFMA = "efma"  # Foreign Manpower (passes, levies, quotas)
DOMAIN_WSH = "wsh"  # Workplace Safety & Health
DOMAIN_TAFEP = "tafep"  # Fair Employment / TAFEP / WFA
DOMAIN_TAX_IRAS = "tax_iras"  # IR8A, IR21, tax filing

ALL_DOMAINS = {
    DOMAIN_CPF,
    DOMAIN_EMPLOYMENT_ACT,
    DOMAIN_EFMA,
    DOMAIN_WSH,
    DOMAIN_TAFEP,
    DOMAIN_TAX_IRAS,
}


@dataclass(frozen=True)
class _DomainPattern:
    domain: str
    # Compiled OR-of-keywords; matched case-insensitively against the query.
    # Designed so each keyword is unambiguous (no overlap across domains).
    pattern: re.Pattern[str]


def _compile(domain: str, keywords: list[str]) -> _DomainPattern:
    # \b ensures whole-word match so "cpf" doesn't match "specific".
    # Multi-word phrases stay literal.
    escaped = [re.escape(kw) for kw in keywords]
    rx = re.compile(r"\b(?:" + "|".join(escaped) + r")\b", re.IGNORECASE)
    return _DomainPattern(domain=domain, pattern=rx)


_PATTERNS: list[_DomainPattern] = [
    _compile(
        DOMAIN_CPF,
        [
            "cpf",
            "ow ceiling",
            "ordinary wage",
            "ordinary wages",
            "aw ceiling",
            "additional wage",
            "additional wages",
            "employer contribution",
            "employer contributions",
            "employee contribution",
            "employee contributions",
            "ordinary account",
            "special account",
            "medisave",
            "retirement account",
            "sdl",
            "skills development levy",
            "shg",
            "self-help group",
        ],
    ),
    _compile(
        DOMAIN_EMPLOYMENT_ACT,
        [
            "employment act",
            "ea s",
            "ea part",
            "ket",
            "key employment terms",
            "itemised payslip",
            "itemized payslip",
            "payslip",
            "annual leave",
            "sick leave",
            "hospitalisation leave",
            "hospitalization leave",
            "maternity leave",
            "paternity leave",
            "childcare leave",
            "infant care leave",
            "notice period",
            "termination",
            "resignation",
            "wrongful dismissal",
            "overtime",
            "part iv",
            "salary in lieu",
            "retrenchment",
            "salary",
            "wages",
            "working hours",
        ],
    ),
    _compile(
        DOMAIN_EFMA,
        [
            "efma",
            "foreign manpower",
            "work pass",
            "work permit",
            "employment pass",
            "s pass",
            "s-pass",
            "fwl",
            "foreign worker levy",
            "levy",
            "quota",
            "dependency ratio",
            "tech.pass",
            "ep holder",
            "wp holder",
            "sp holder",
            "fdw",
            "domestic worker",
        ],
    ),
    _compile(
        DOMAIN_WSH,
        [
            "wsh",
            "workplace safety",
            "workplace health",
            "safety policy",
            "risk assessment",
            "occupational hazard",
            "occupational health",
            "incident reporting",
            "near-miss",
            "near miss",
            "safety officer",
            "wsho",
            "ptw",
            "permit to work",
            "wica",
            "work injury compensation",
        ],
    ),
    _compile(
        DOMAIN_TAFEP,
        [
            "tafep",
            "wfa",
            "workplace fairness act",
            "fair employment",
            "discrimination",
            "harassment",
            "grievance",
            "tgfep",
            "fair consideration",
            "fcf",
            "diversity",
            "inclusion",
            "flexible work arrangement",
            "tg-fwar",
            "flexi-work",
            "flexible work",
        ],
    ),
    _compile(
        DOMAIN_TAX_IRAS,
        [
            "iras",
            "ir8a",
            "ir21",
            "auto-inclusion",
            "ais",
            "income tax",
            "tax filing",
            "tax clearance",
            "tax return",
            "tax reference",
        ],
    ),
]


def classify_domains(query: str) -> list[str]:
    """Return the list of regulatory domains relevant to `query`.

    Multiple domains are returned when the query spans regulations
    (e.g., "What's the CPF treatment for a foreign worker on an S Pass?"
    → ["cpf", "efma"]). The list is deterministic and stable so callers
    can pre-fetch KB content per detected domain.

    Empty list means no domain match — caller should let the LLM use
    its general reasoning, but still call search_kb at least once for
    citation coverage (handled by the engine's force-search_kb policy).
    """
    if not query:
        return []
    detected: list[str] = []
    for dp in _PATTERNS:
        if dp.pattern.search(query):
            detected.append(dp.domain)
    return detected


def primary_domain(query: str) -> str | None:
    """Return the single best-fit domain, or None.

    Useful when only one domain is needed for retrieval. Picks the
    first detected domain in iteration order (which mirrors how the
    KB priorities are configured — CPF before EA, EA before EFMA,
    etc.). Most queries match a single domain anyway.
    """
    domains = classify_domains(query)
    return domains[0] if domains else None
