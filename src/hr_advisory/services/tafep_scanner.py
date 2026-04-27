"""TAFEP fair recruitment language scanner.

Checks job descriptions for language that may violate TAFEP's
Tripartite Guidelines on Fair Employment Practices (TGFEP).

Singapore employers must ensure job advertisements do not contain
discriminatory requirements based on age, gender, race, religion,
nationality, marital status, or family responsibilities unless
there is a genuine occupational qualification.

Reference: https://www.tal.sg/tafep/employment-practices/recruitment
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

DISCRIMINATORY_PATTERNS: list[tuple[str, str, str]] = [
    # Age-related
    (
        r"\byoung\b",
        "age",
        "Consider removing age-related language. Use 'motivated' or 'energetic' instead.",
    ),
    (
        r"\bfresh grad(?:uate)?s? only\b",
        "age",
        "This excludes experienced candidates. Consider 'open to fresh graduates' instead.",
    ),
    (
        r"\bbelow \d+ years?\b",
        "age",
        "Age requirements may violate TAFEP guidelines unless there is a legal basis.",
    ),
    (
        r"\babove \d+ years?\b",
        "age",
        "Age requirements may violate TAFEP guidelines unless there is a legal basis.",
    ),
    (
        r"\bage \d+",
        "age",
        "Specifying age requirements may violate TAFEP guidelines.",
    ),
    # Gender-related
    (
        r"\b(?:female|male) (?:only|preferred|candidates?)\b",
        "gender",
        "Gender-specific requirements violate TAFEP guidelines unless there is a genuine occupational qualification.",
    ),
    (
        r"\bpreferably (?:female|male)\b",
        "gender",
        "Gender preferences violate TAFEP guidelines.",
    ),
    (
        r"\b(?:female|male) \w+[ -]\w+ candidates?\b",
        "gender",
        "Gender-specific requirements violate TAFEP guidelines unless there is a genuine occupational qualification.",
    ),
    # Race/language (without business justification)
    (
        r"\bchinese[- ]speaking\b",
        "race_language",
        "Language requirements need business justification under TAFEP. Add the reason if applicable.",
    ),
    (
        r"\bmandarin[- ]speaking\b",
        "race_language",
        "Language requirements need business justification under TAFEP. Add the reason if applicable.",
    ),
    (
        r"\bmalay[- ]speaking\b",
        "race_language",
        "Language requirements need business justification under TAFEP. Add the reason if applicable.",
    ),
    (
        r"\btamil[- ]speaking\b",
        "race_language",
        "Language requirements need business justification under TAFEP. Add the reason if applicable.",
    ),
    (
        r"\b(?:chinese|malay|indian|eurasian) (?:only|preferred)\b",
        "race",
        "Race-based requirements violate TAFEP guidelines.",
    ),
    # Nationality
    (
        r"\bsingaporeans? only\b",
        "nationality",
        "Nationality restrictions may need FCF justification. Consider 'Singaporeans/PRs preferred' with business rationale.",
    ),
    (
        r"\bpr only\b",
        "nationality",
        "Restricting to PRs only may need justification.",
    ),
    # Marital/family status
    (
        r"\bsingle (?:only|preferred)\b",
        "marital",
        "Marital status requirements violate TAFEP guidelines.",
    ),
    (
        r"\bno children\b",
        "family",
        "Family status requirements violate TAFEP guidelines.",
    ),
    (
        r"\bunmarried\b",
        "marital",
        "Marital status requirements violate TAFEP guidelines.",
    ),
    # Religion
    (
        r"\b(?:muslim|christian|buddhist|hindu|catholic) (?:only|preferred)\b",
        "religion",
        "Religious requirements violate TAFEP guidelines unless there is a genuine occupational qualification.",
    ),
]


def scan_job_description(text: str) -> list[dict]:
    """Scan a job description for potentially discriminatory language.

    Returns a list of findings, each with:
      - matched_text: the matched text from the description
      - category: age/gender/race_language/race/nationality/marital/family/religion
      - suggestion: recommended action to fix the language
      - position: character position in the (lowered) text
    """
    if not text:
        return []

    findings: list[dict] = []
    text_lower = text.lower()

    for pattern, category, suggestion in DISCRIMINATORY_PATTERNS:
        for match in re.finditer(pattern, text_lower):
            findings.append({
                "matched_text": match.group(),
                "category": category,
                "suggestion": suggestion,
                "position": match.start(),
            })

    if findings:
        logger.info(
            "TAFEP scan found %d potential issue(s) across categories: %s",
            len(findings),
            ", ".join(sorted({f["category"] for f in findings})),
        )

    return findings
