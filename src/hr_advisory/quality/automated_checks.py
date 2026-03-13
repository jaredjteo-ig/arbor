"""Automated (deterministic) quality checks for HR advisory responses.

Pure Python, no LLM required. Provides partial scores for dimensions that
can be evaluated programmatically:

- Citation Quality: bracket-format citations present and traceable
- Risk Awareness: risk tier consistency (no contradictory language)
- Response Structure: presence of key sections (Summary, Legal basis, Actions)
- Disclaimer Presence: risk-appropriate disclaimer or framing text
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# Section heading patterns (case-insensitive)
# Match both markdown headings (## Summary) and bold-text headers (**Summary**)
_SUMMARY_PATTERNS = [
    re.compile(r"(?i)##?\s*summary"),
    re.compile(r"(?i)\*\*summary:?\s?\*\*"),
]
_LEGAL_PATTERNS = [
    re.compile(r"(?i)##?\s*what the law says"),
    re.compile(r"(?i)##?\s*legal basis"),
    re.compile(r"(?i)\*\*what the law says:?\s?\*\*"),
    re.compile(r"(?i)\*\*legal basis:?\s?\*\*"),
]
_ACTION_PATTERNS = [
    re.compile(r"(?i)##?\s*what you need to do"),
    re.compile(r"(?i)##?\s*action steps"),
    re.compile(r"(?i)\*\*what you need to do:?\s?\*\*"),
    re.compile(r"(?i)\*\*action steps:?\s?\*\*"),
    re.compile(r"(?i)\*\*next steps:?\s?\*\*"),
    re.compile(r"(?i)\*\*what to do now:?\s?\*\*"),
    re.compile(r"(?i)\*\*recommended actions:?\s?\*\*"),
]

# Risk tier inconsistency patterns
_AMBER_DISALLOWED = [
    re.compile(r"(?i)\bno action needed\b"),
    re.compile(r"(?i)\bnothing to worry about\b"),
]

_RED_REQUIRED = [
    re.compile(r"(?i)\bconsult\b"),
    re.compile(r"(?i)\bseek professional advice\b"),
]

_GREEN_DISALLOWED = [
    re.compile(r"(?i)\burgent\b"),
    re.compile(r"(?i)\bimmediate action required\b"),
]

# Disclaimer patterns
_STRONG_DISCLAIMER_PATTERNS = [
    re.compile(r"(?i)strongly recommend.{0,30}consult"),
    re.compile(r"(?i)significant legal or financial implications"),
    re.compile(r"(?i)recommend consulting an employment law"),
    re.compile(r"(?i)seek professional advice"),
    re.compile(r"(?i)consult.{0,30}(lawyer|legal|professional|specialist|advisor)"),
    re.compile(r"(?i)engage.{0,20}(lawyer|legal counsel|employment lawyer)"),
    re.compile(
        r"(?i)recommend.{0,30}(professional|legal|specialist).{0,20}(advice|guidance|counsel)"
    ),
    re.compile(r"(?i)professional.{0,20}(advice|guidance|help)"),
]
_GENERIC_DISCLAIMER_PATTERNS = [
    re.compile(r"(?i)\bnot legal advice\b"),
    re.compile(r"(?i)\bgeneral information only\b"),
    re.compile(r"(?i)\bnot a substitute for\b"),
    re.compile(r"(?i)\bgeneral guidance\b"),
    re.compile(r"(?i)\binformational purposes\b"),
    re.compile(r"(?i)\bdoes not constitute.{0,20}(legal|professional) advice\b"),
]
_AMBER_FRAMING_PATTERNS = [
    re.compile(r"(?i)based on current .{0,40} provisions"),
    re.compile(r"(?i)based on current .{0,40} rules"),
    re.compile(r"(?i)based on current .{0,40} guidelines"),
    re.compile(r"(?i)based on current .{0,40} requirements"),
    re.compile(r"(?i)based on current regulations"),
    re.compile(r"(?i)under the .{0,50}(Act|legislation|regulations)"),
    re.compile(r"(?i)as of .{0,20}\d{4}"),
    re.compile(r"(?i)under current.{0,30}(law|legislation|provisions|framework)"),
]

# Citation bracket pattern: [ID] or [Act s.X] etc.
_CITATION_BRACKET_PATTERN = re.compile(r"\[[\w\-]+(?:\s+s[\.\d]+)?\]")

# Parenthetical citation pattern: (EA s.10), (CPFA s.52), (EFMA s.22), etc.
_CITATION_PAREN_PATTERN = re.compile(
    r"\("
    r"(?:EA|CPFA|CPF Act|EFMA|WSHA|WSH Act|PDPA|IRAS|ITA|TGFEP|WFA|WFL|CDCSA)"
    r"\s+s[\.\d]+"
    r"[a-zA-Z]?"  # optional subsection letter, e.g., s.14A
    r"\)"
)


class AutomatedChecks:
    """Deterministic quality checks that do not require an LLM."""

    @staticmethod
    def check_citation_quality(
        response_text: str,
        cited_provisions: list[str],
    ) -> tuple[float, str]:
        """Score citation quality based on count and format.

        Returns:
            (score, explanation) where score is 1.0-5.0.

        Scoring:
            5 = 3+ citations
            4 = 2 citations
            3 = 1 citation
            1 = 0 citations
        """
        # Count citations from the cited_provisions list AND from text patterns
        provision_count = len(cited_provisions)

        # Count bracket-format citations in the response text: [EA-S10]
        bracket_citations = _CITATION_BRACKET_PATTERN.findall(response_text)
        bracket_count = len(bracket_citations)

        # Count parenthetical citations: (EA s.10), (CPFA s.52)
        paren_citations = _CITATION_PAREN_PATTERN.findall(response_text)
        paren_count = len(paren_citations)

        # Total text citations = bracket + parenthetical (deduplicated by count)
        text_citation_count = bracket_count + paren_count

        # Use the higher count (provisions list may be more authoritative,
        # but text citations show inline referencing)
        effective_count = max(provision_count, text_citation_count)

        if effective_count >= 3:
            return 5.0, f"{effective_count} citations found; good coverage."
        elif effective_count == 2:
            return 4.0, f"2 citations found; acceptable but could cite more."
        elif effective_count == 1:
            return 3.0, "1 citation found; minimal citation coverage."
        else:
            return 1.0, "0 citations found; no sources referenced."

    @staticmethod
    def check_risk_awareness(
        response_text: str,
        risk_tier: str,
    ) -> tuple[float, str]:
        """Score risk tier consistency between tier label and response language.

        Returns:
            (score, explanation) where score is 1.0-5.0.

        Checks:
            - amber must NOT say "no action needed" / "nothing to worry about"
            - red MUST contain "consult" or "seek professional advice"
            - green must NOT contain "urgent" / "immediate action required"

        Scoring:
            5 = all checks pass
            3 = one check fails
            1 = multiple checks fail
        """
        failures: list[str] = []

        if risk_tier == "amber":
            for pattern in _AMBER_DISALLOWED:
                if pattern.search(response_text):
                    failures.append(
                        f"Amber response contains disallowed language: '{pattern.pattern}'"
                    )

        elif risk_tier == "red":
            has_consult = any(p.search(response_text) for p in _RED_REQUIRED)
            if not has_consult:
                failures.append(
                    "Red response must contain 'consult' or 'seek professional advice' language"
                )

        elif risk_tier == "green":
            for pattern in _GREEN_DISALLOWED:
                if pattern.search(response_text):
                    failures.append(
                        f"Green response contains alarming language: '{pattern.pattern}'"
                    )

        if len(failures) == 0:
            return 5.0, "Risk tier language is consistent."
        elif len(failures) == 1:
            return 3.0, f"Risk inconsistency: {failures[0]}"
        else:
            joined = "; ".join(failures)
            return 1.0, f"Multiple risk inconsistencies: {joined}"

    @staticmethod
    def check_response_structure(
        response_text: str,
    ) -> tuple[float, str]:
        """Score response structure based on presence of key sections.

        Returns:
            (score, explanation) where score is 1.0-5.0.

        Expected sections:
            1. Summary
            2. "What the law says" or "Legal basis"
            3. "What you need to do" or "Action steps"

        Scoring:
            5 = all 3 sections present
            4 = 2 of 3 sections
            3 = 1 of 3 sections
            1 = none
        """
        sections_found = 0
        found_names: list[str] = []

        if any(p.search(response_text) for p in _SUMMARY_PATTERNS):
            sections_found += 1
            found_names.append("Summary")

        if any(p.search(response_text) for p in _LEGAL_PATTERNS):
            sections_found += 1
            found_names.append("Legal basis")

        if any(p.search(response_text) for p in _ACTION_PATTERNS):
            sections_found += 1
            found_names.append("Action steps")

        if sections_found == 3:
            return 5.0, "All key sections present: Summary, Legal basis, Action steps."
        elif sections_found == 2:
            missing = {"Summary", "Legal basis", "Action steps"} - set(found_names)
            return 4.0, f"2 of 3 sections present. Missing: {', '.join(missing)}."
        elif sections_found == 1:
            missing = {"Summary", "Legal basis", "Action steps"} - set(found_names)
            return 3.0, f"Only 1 section found ({found_names[0]}). Missing: {', '.join(missing)}."
        else:
            return 1.0, "No key sections found. Response lacks structured format."

    @staticmethod
    def check_disclaimer_presence(
        response_text: str,
        risk_tier: str,
    ) -> tuple[float, str]:
        """Score disclaimer presence and appropriateness for the risk tier.

        Returns:
            (score, explanation) where score is 1.0-5.0.

        Rules:
            - GREEN: no disclaimer required (always scores 5)
            - AMBER: domain framing text required (e.g., "Based on current EA provisions...")
            - RED: strong disclaimer with professional referral required

        Scoring:
            5 = appropriate disclaimer present
            3 = disclaimer present but not tier-appropriate (generic)
            1 = no disclaimer at all
        """
        has_strong = any(p.search(response_text) for p in _STRONG_DISCLAIMER_PATTERNS)
        has_generic = any(p.search(response_text) for p in _GENERIC_DISCLAIMER_PATTERNS)
        has_framing = any(p.search(response_text) for p in _AMBER_FRAMING_PATTERNS)

        if risk_tier == "green":
            # Green does not need a disclaimer
            return 5.0, "Green tier: no disclaimer required."

        elif risk_tier == "amber":
            if has_framing or has_strong:
                return 5.0, "Amber tier: appropriate framing text present."
            elif has_generic:
                return 3.0, "Amber tier: has generic disclaimer but missing domain framing."
            else:
                return 1.0, "Amber tier: no framing or disclaimer found."

        elif risk_tier == "red":
            if has_strong:
                return 5.0, "Red tier: strong disclaimer with professional referral present."
            elif has_generic or has_framing:
                return 3.0, "Red tier: has disclaimer but not strong enough for red tier."
            else:
                return 1.0, "Red tier: no disclaimer found. Professional referral required."

        # Unknown tier — log and score conservatively
        logger.warning("Unknown risk tier '%s' in disclaimer check", risk_tier)
        return 3.0, f"Unknown risk tier '{risk_tier}'; cannot assess disclaimer appropriateness."

    @staticmethod
    def run_all(
        response_text: str,
        risk_tier: str,
        cited_provisions: list[str],
    ) -> tuple[dict[str, float], dict[str, str]]:
        """Run all automated checks and return scores + explanations.

        Returns:
            (scores_dict, details_dict) where each dict is keyed by dimension name.
        """
        scores: dict[str, float] = {}
        details: dict[str, str] = {}

        cq_score, cq_detail = AutomatedChecks.check_citation_quality(
            response_text, cited_provisions
        )
        scores["citation_quality"] = cq_score
        details["citation_quality"] = cq_detail

        ra_score, ra_detail = AutomatedChecks.check_risk_awareness(response_text, risk_tier)
        scores["risk_awareness"] = ra_score
        details["risk_awareness"] = ra_detail

        rs_score, rs_detail = AutomatedChecks.check_response_structure(response_text)
        scores["response_structure"] = rs_score
        details["response_structure"] = rs_detail

        dp_score, dp_detail = AutomatedChecks.check_disclaimer_presence(response_text, risk_tier)
        scores["disclaimer_presence"] = dp_score
        details["disclaimer_presence"] = dp_detail

        return scores, details
