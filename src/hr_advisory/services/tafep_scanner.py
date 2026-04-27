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

import json
import logging
import os
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


# ---------------------------------------------------------------------------
# T-R053: Optional AI second-pass scan for subtler discrimination phrases.
# ---------------------------------------------------------------------------


_AI_SYSTEM_PROMPT = (
    "You are a Singapore employment-law fair-hiring reviewer. The user will "
    "give you a job advertisement. Identify any phrases that may breach the "
    "TAFEP Tripartite Guidelines on Fair Employment Practices (age, gender, "
    "race, language, nationality, marital/family status, religion). Return "
    "STRICT JSON of the form: "
    '{"findings": [{"matched_text": str, "category": str, "suggestion": str}]}.'
    " Use one of these category values: age, gender, race, race_language, "
    "nationality, marital, family, religion, other. If nothing is found, "
    'return {"findings": []}. Do NOT include any prose outside the JSON.'
)


def _resolve_llm_config() -> tuple[str, str, str] | None:
    """Pick an available LLM (OpenAI first, then Gemini) using only env vars.

    Returns ``(provider, api_key, model)`` or None if no provider is configured.
    Model name is pulled from env per the env-models rule — never hardcoded.
    """
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    gemini_key = os.environ.get("GEMINI_API_KEY", "") or os.environ.get(
        "GOOGLE_API_KEY", ""
    )
    prod_model = os.environ.get("OPENAI_PROD_MODEL", "")
    default_model = os.environ.get("DEFAULT_LLM_MODEL", "")

    if openai_key:
        model = prod_model or default_model
        if not model:
            return None
        return "openai", openai_key, model
    if gemini_key:
        # Gemini SDK reads its own model env var for safety.
        model = os.environ.get("GEMINI_MODEL", "") or default_model
        if not model:
            return None
        return "gemini", gemini_key, model
    return None


def scan_with_ai(text: str) -> dict:
    """Second-pass discrimination scan via LLM (opt-in).

    Returns a dict with key ``findings`` (a list of {matched_text, category,
    suggestion} dicts) on success, or ``{"findings": [], "ai_unavailable":
    True, "reason": "..."}`` on any failure (fail-open).

    Never raises. Reads the API key and model name from environment per the
    project's env-models rule.
    """
    if not text or not text.strip():
        return {"findings": []}

    config = _resolve_llm_config()
    if config is None:
        return {
            "findings": [],
            "ai_unavailable": True,
            "reason": "No LLM API key configured.",
        }

    provider, api_key, model = config

    try:
        if provider == "openai":
            try:
                from openai import OpenAI  # type: ignore
            except ImportError:
                return {
                    "findings": [],
                    "ai_unavailable": True,
                    "reason": "openai SDK not installed.",
                }
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": _AI_SYSTEM_PROMPT},
                    {"role": "user", "content": text[:8000]},
                ],
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content or "{}"
        else:  # gemini
            try:
                import google.generativeai as genai  # type: ignore
            except ImportError:
                return {
                    "findings": [],
                    "ai_unavailable": True,
                    "reason": "google-generativeai SDK not installed.",
                }
            genai.configure(api_key=api_key)
            gemini_model = genai.GenerativeModel(model)
            prompt = f"{_AI_SYSTEM_PROMPT}\n\nAdvertisement:\n{text[:8000]}"
            result = gemini_model.generate_content(prompt)
            raw = (getattr(result, "text", None) or "").strip()
            # Strip code fences if the model wrapped its response.
            if raw.startswith("```"):
                raw = re.sub(r"^```[a-zA-Z]*\n|```$", "", raw).strip()

        parsed = json.loads(raw or "{}")
        findings_raw = parsed.get("findings", [])
        if not isinstance(findings_raw, list):
            findings_raw = []
        # Normalize each finding to the same shape as the rule scanner.
        cleaned: list[dict] = []
        for f in findings_raw:
            if not isinstance(f, dict):
                continue
            cleaned.append({
                "matched_text": str(f.get("matched_text", ""))[:500],
                "category": str(f.get("category", "other"))[:50],
                "suggestion": str(f.get("suggestion", ""))[:500],
                "source": "ai",
            })
        logger.info("TAFEP AI scan returned %d finding(s)", len(cleaned))
        return {"findings": cleaned}
    except Exception as exc:
        logger.warning("TAFEP AI scan failed: %s", exc)
        return {
            "findings": [],
            "ai_unavailable": True,
            "reason": "LLM call failed.",
        }
