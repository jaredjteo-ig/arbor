"""Singlish and Singapore English natural language handling.

Provides:
- Common Singlish HR phrase patterns with standard English mappings
- Suggested question examples in natural Singapore English
- Query normalization hints for LLM system prompts
"""

from __future__ import annotations

# ── Singlish HR phrase mappings ──────────────────────────────
# These help LLMs understand common Singlish HR queries.
# Format: (pattern, standard_meaning, example_context)

SINGLISH_HR_PHRASES: list[tuple[str, str, str]] = [
    (
        "resign already",
        "has already resigned",
        "My staff resign already = My employee has already submitted their resignation",
    ),
    (
        "need pay or not",
        "is it required to pay",
        "Need pay notice period or not? = Is notice period payment required?",
    ),
    (
        "can forfeit",
        "is it allowed to forfeit / can we withhold",
        "Can forfeit MC if never take? = Can unused medical leave be forfeited?",
    ),
    (
        "never take",
        "did not use / unused",
        "MC never take = unused medical leave",
    ),
    (
        "how to calculate",
        "how do I calculate / what is the formula for",
        "How to calculate OT for part-timer? = What is the overtime rate for part-time employees?",
    ),
    (
        "got include",
        "does it include / is it included",
        "Got include CPF or not? = Does this include CPF contributions?",
    ),
    (
        "confirm plus chop",
        "definitely / confirmed",
        "Confirm plus chop must pay? = Is this definitely required by law?",
    ),
    (
        "kena",
        "got affected by / received / subjected to",
        "Kena MOM inspection = Received an MOM inspection",
    ),
    (
        "cannot anyhow",
        "cannot simply / must follow proper procedure",
        "Cannot anyhow fire = Cannot terminate without proper process",
    ),
    (
        "last time",
        "previously / in the past",
        "Last time the rule different = The regulation was previously different",
    ),
    (
        "still can",
        "is it still possible to / can we still",
        "Still can claim or not? = Is it still possible to make a claim?",
    ),
    (
        "bo bian",
        "no choice / unavoidable",
        "Bo bian must pay = No choice, payment is mandatory",
    ),
    (
        "abit sian",
        "somewhat tedious / troublesome",
        "Process abit sian = The process is somewhat tedious",
    ),
    (
        "paiseh",
        "embarrassing / awkward / sorry",
        "Paiseh to ask = Sorry to ask / embarrassing question",
    ),
    (
        "jialat",
        "serious / troublesome / dire",
        "Jialat, MOM coming = Serious situation, MOM is conducting an inspection",
    ),
    (
        "buay tahan",
        "cannot tolerate / at breaking point",
        "Staff buay tahan already = Employee is at breaking point",
    ),
]

# ── Suggested questions in Singlish ──────────────────────────
# These appear as example queries to show users the system understands their language.

SINGLISH_SUGGESTED_QUESTIONS: list[str] = [
    "My staff resign already, need pay notice period or not?",
    "Can forfeit MC if worker never take?",
    "How to calculate OT for part-timer?",
    "Got include CPF for bonus or not?",
    "Kena TADM claim, how ah?",
    "New staff from Malaysia, what permit need?",
    "Can deduct salary for damage or not?",
    "How many days annual leave for new staff?",
    "MOM inspection coming, what need prepare?",
    "Staff pregnant, can terminate or not?",
]

# ── LLM system prompt additions ──────────────────────────────

SINGLISH_SYSTEM_PROMPT = """
## Singapore English (Singlish) Understanding

You are serving users in Singapore. Many will write in Singlish — a creole
combining English with Mandarin, Malay, and Tamil influences. You MUST:

1. **Understand Singlish input naturally** — do not ask users to rephrase
2. **Respond in clear standard English** — while being warm and accessible
3. **Handle code-switching** — users may mix English with Chinese/Malay terms

Common Singlish patterns in HR contexts:
- "or not" at end = yes/no question ("Need pay or not?" = "Is payment required?")
- "already" = completed action ("resign already" = "has resigned")
- "how ah" = seeking advice ("How ah?" = "What should I do?")
- "can" at start = permission question ("Can fire or not?" = "Is termination allowed?")
- "kena" = passive/affected ("kena fine" = "was fined")
- "never" = did not ("never pay" = "did not pay")
- Absence of articles ("the", "a") is normal
- Simplified verb tenses are common

Do NOT:
- Correct users' Singlish
- Ask them to rephrase in "proper English"
- Respond in Singlish (keep responses professional but warm)
"""


def get_singlish_context() -> str:
    """Return the Singlish system prompt addition for LLM context."""
    return SINGLISH_SYSTEM_PROMPT


def get_suggested_questions() -> list[str]:
    """Return suggested questions in natural Singapore English."""
    return SINGLISH_SUGGESTED_QUESTIONS
