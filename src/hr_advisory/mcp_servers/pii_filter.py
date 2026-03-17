"""PII stripping layer for LLM-bound data.

Strips employee PII before data reaches the LLM in shadow agent queries.
Replaces real names, NRICs, salaries, and bank accounts with anonymized
tokens. Restores original values in the response.

T210: PDPA PII Stripping Layer (Red Team C5)
"""

from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# SG-specific PII patterns
_NRIC_PATTERN = re.compile(r"\b[STFGM]\d{7}[A-Z]\b", re.IGNORECASE)
_PHONE_SG_PATTERN = re.compile(r"\+65\s?\d{4}\s?\d{4}|\b[689]\d{7}\b")
_POSTAL_CODE_PATTERN = re.compile(r"\b\d{6}\b")
_BANK_ACCOUNT_PATTERN = re.compile(r"\b\d{3}-?\d{5,6}-?\d{1,4}\b")
_EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
_SALARY_PATTERN = re.compile(r"\$\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\b\d{4,6}(?:\.\d{2})?\b")


class PIIFilter:
    """Strips and restores PII for LLM-safe processing.

    Usage::

        pii = PIIFilter()
        cleaned, token_map = pii.strip("John Tan (S1234567A) earns $5,000")
        # cleaned: "[PERSON_1] ([NRIC_1]) earns [AMOUNT_1]"

        # After LLM processes the cleaned text:
        response = "[PERSON_1] is entitled to 14 days annual leave."
        restored = pii.restore(response, token_map)
        # restored: "John Tan is entitled to 14 days annual leave."
    """

    def strip(
        self,
        text: str,
        strip_names: Optional[list[str]] = None,
    ) -> tuple[str, dict[str, str]]:
        """Strip PII from text, returning cleaned text and token map.

        Args:
            text: Input text potentially containing PII.
            strip_names: Optional list of known employee names to strip.

        Returns:
            Tuple of (cleaned_text, token_map) where token_map maps
            tokens back to original values.
        """
        token_map: dict[str, str] = {}
        result = text
        counters: dict[str, int] = {}

        def _next_token(category: str) -> str:
            counters[category] = counters.get(category, 0) + 1
            return f"[{category}_{counters[category]}]"

        # Strip NRICs (most sensitive — always strip)
        for match in _NRIC_PATTERN.finditer(result):
            token = _next_token("NRIC")
            token_map[token] = match.group()
        result = _NRIC_PATTERN.sub(lambda m: _next_token("NRIC"), text)
        # Reset counter for consistent replacement
        counters.clear()
        token_map.clear()

        # Two-pass: first collect all matches, then replace
        replacements: list[tuple[int, int, str, str]] = []  # (start, end, token, original)

        for match in _NRIC_PATTERN.finditer(text):
            token = _next_token("NRIC")
            replacements.append((match.start(), match.end(), token, match.group()))

        for match in _PHONE_SG_PATTERN.finditer(text):
            token = _next_token("PHONE")
            replacements.append((match.start(), match.end(), token, match.group()))

        for match in _EMAIL_PATTERN.finditer(text):
            token = _next_token("EMAIL")
            replacements.append((match.start(), match.end(), token, match.group()))

        for match in _BANK_ACCOUNT_PATTERN.finditer(text):
            token = _next_token("BANK_ACCT")
            replacements.append((match.start(), match.end(), token, match.group()))

        # Strip salary/dollar amounts (e.g., $5,000 or $12,345.67)
        for match in _SALARY_PATTERN.finditer(text):
            value = match.group()
            # Only strip amounts that look like salaries (4+ digits or dollar-prefixed)
            if value.startswith("$") or (
                value.replace(",", "").replace(".", "").isdigit()
                and len(value.replace(",", "").split(".")[0]) >= 4
            ):
                token = _next_token("AMOUNT")
                replacements.append((match.start(), match.end(), token, value))

        # Strip known employee names if provided
        if strip_names:
            for name in strip_names:
                if name in text:
                    token = _next_token("PERSON")
                    idx = text.find(name)
                    replacements.append((idx, idx + len(name), token, name))

        # Sort replacements by position (reverse) to preserve indices
        replacements.sort(key=lambda r: r[0], reverse=True)

        result = text
        for start, end, token, original in replacements:
            token_map[token] = original
            result = result[:start] + token + result[end:]

        if token_map:
            logger.debug("Stripped %d PII tokens from text", len(token_map))

        return result, token_map

    def restore(self, text: str, token_map: dict[str, str]) -> str:
        """Restore PII tokens in LLM response back to original values.

        Args:
            text: LLM response containing PII tokens.
            token_map: Map from tokens to original values (from strip()).

        Returns:
            Text with tokens replaced by original PII values.
        """
        result = text
        for token, original in token_map.items():
            result = result.replace(token, original)
        return result

    def has_pii(self, text: str) -> bool:
        """Quick check if text likely contains SG PII patterns."""
        return bool(_NRIC_PATTERN.search(text) or _BANK_ACCOUNT_PATTERN.search(text))


# Convenience singleton
_filter: Optional[PIIFilter] = None


def get_pii_filter() -> PIIFilter:
    """Get or create the global PII filter."""
    global _filter
    if _filter is None:
        _filter = PIIFilter()
    return _filter
