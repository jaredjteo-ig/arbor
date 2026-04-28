"""T223: Chat-style company onboarding state machine tests.

Tests the deterministic helpers that drive POST /shadow/onboarding/chat:

- _chat_onboarding_match_sector  -- maps free text to canonical sector keys
- _chat_onboarding_match_headcount -- maps free text/numbers to range buckets
- _chat_onboarding_match_yes_no -- yes/no parsing tolerant of common variants
- _chat_onboarding_prompt -- step-aware Arbor-prefixed prompts

These functions are LLM-free, so we can test them directly without any
mocking of model providers or HTTP clients.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

# Prevent Kaizen / shadow runtime imports — we only need the pure helpers.
_kaizen_mods = [
    "kaizen",
    "kaizen.core",
    "kaizen.core.base_agent",
    "kaizen.memory",
    "kaizen.config",
    "kaizen.config.providers",
    "kaizen.signatures",
    "kaizen.core.workflow_generator",
    "kaizen.nodes",
    "kaizen.nodes.ai",
    "kaizen.nodes.ai.llm_agent",
]
for _m in _kaizen_mods:
    if _m not in sys.modules:
        sys.modules[_m] = MagicMock()

from hr_advisory.api.routers.shadow import (  # noqa: E402
    _CHAT_ONBOARDING_HEADCOUNT_RANGES,
    _CHAT_ONBOARDING_SECTOR_KEYS,
    _CHAT_ONBOARDING_STEPS,
    _chat_onboarding_match_headcount,
    _chat_onboarding_match_sector,
    _chat_onboarding_match_yes_no,
    _chat_onboarding_prompt,
)


# =========================================================================
# Sector matching
# =========================================================================


class TestSectorMatching:
    """Free-text sector input -> canonical sector key."""

    @pytest.mark.parametrize(
        "answer,expected",
        [
            ("technology", "technology"),
            ("Technology", "technology"),
            ("  Tech  ", "technology"),
            ("IT", "technology"),
            ("Information Technology", "technology"),
            ("fnb", "fnb"),
            ("F&B", "fnb"),
            ("food", "fnb"),
            ("Food and Beverage", "fnb"),
            ("retail", "retail"),
            ("ecommerce", "retail"),
            ("E-commerce", "retail"),
            ("manufacturing", "manufacturing"),
            ("construction", "construction"),
            ("services", "services"),
            ("Professional Services", "services"),
            ("consulting", "services"),
            ("healthcare", "healthcare"),
            ("Health", "healthcare"),
            ("education", "education"),
            ("logistics", "logistics"),
            ("transport", "logistics"),
            ("other", "other"),
        ],
    )
    def test_canonical_and_alias_inputs_match(self, answer: str, expected: str) -> None:
        assert _chat_onboarding_match_sector(answer) == expected

    def test_unrecognised_sector_returns_none(self) -> None:
        assert _chat_onboarding_match_sector("something completely random") is None

    def test_empty_input_returns_none(self) -> None:
        assert _chat_onboarding_match_sector("") is None
        assert _chat_onboarding_match_sector("   ") is None

    def test_substring_fallback(self) -> None:
        # "We are in the technology sector" should match technology.
        assert _chat_onboarding_match_sector("We are in the technology sector") == "technology"

    def test_all_canonical_keys_round_trip(self) -> None:
        """Every canonical sector key must map back to itself."""
        for key in _CHAT_ONBOARDING_SECTOR_KEYS:
            assert _chat_onboarding_match_sector(key) == key


# =========================================================================
# Headcount matching
# =========================================================================


class TestHeadcountMatching:
    """Free-text headcount -> canonical range string."""

    @pytest.mark.parametrize(
        "answer,expected",
        [
            ("1-5", "1-5"),
            ("6-25", "6-25"),
            ("26-50", "26-50"),
            ("51-100", "51-100"),
            ("101-200", "101-200"),
            ("3", "1-5"),
            ("10", "6-25"),
            ("about 30 people", "26-50"),
            ("75", "51-100"),
            ("150", "101-200"),
            ("we have 500 staff", "101-200"),
            ("  1 ", "1-5"),
        ],
    )
    def test_valid_inputs(self, answer: str, expected: str) -> None:
        assert _chat_onboarding_match_headcount(answer) == expected

    def test_zero_headcount_returns_none(self) -> None:
        # 0 is below the lowest bucket and not >200 -> no match.
        assert _chat_onboarding_match_headcount("0") is None

    def test_unrecognised_returns_none(self) -> None:
        assert _chat_onboarding_match_headcount("a lot") is None
        assert _chat_onboarding_match_headcount("") is None

    def test_all_canonical_ranges_round_trip(self) -> None:
        for range_str, _lo, _hi in _CHAT_ONBOARDING_HEADCOUNT_RANGES:
            assert _chat_onboarding_match_headcount(range_str) == range_str


# =========================================================================
# Yes/No matching
# =========================================================================


class TestYesNoMatching:
    """Loose yes/no parsing for confirm + foreign_workers steps."""

    @pytest.mark.parametrize(
        "answer", ["yes", "Yes", "YES", "y", "yeah", "yep", "true", "1", "ok", "okay", "confirm"]
    )
    def test_positive(self, answer: str) -> None:
        assert _chat_onboarding_match_yes_no(answer) is True

    @pytest.mark.parametrize(
        "answer", ["no", "No", "NO", "n", "nope", "false", "0", "none", "cancel"]
    )
    def test_negative(self, answer: str) -> None:
        assert _chat_onboarding_match_yes_no(answer) is False

    @pytest.mark.parametrize("answer", ["maybe", "I don't know", "", "  ", "?"])
    def test_ambiguous_returns_none(self, answer: str) -> None:
        assert _chat_onboarding_match_yes_no(answer) is None

    def test_yes_prefix_phrase(self) -> None:
        assert _chat_onboarding_match_yes_no("Yes please go ahead") is True

    def test_no_prefix_phrase(self) -> None:
        assert _chat_onboarding_match_yes_no("No, let's start over") is False


# =========================================================================
# Prompt generation
# =========================================================================


class TestPromptGeneration:
    """All prompts must be Arbor-prefixed and step-appropriate."""

    def test_name_prompt_is_arbor_prefixed(self) -> None:
        prompt = _chat_onboarding_prompt("name", {})
        assert prompt.startswith("Arbor: ")
        assert "company" in prompt.lower()

    def test_sector_prompt_uses_collected_name(self) -> None:
        prompt = _chat_onboarding_prompt("sector", {"name": "Acme Pte Ltd"})
        assert prompt.startswith("Arbor: ")
        assert "Acme Pte Ltd" in prompt
        assert "industry" in prompt.lower()

    def test_headcount_prompt_lists_ranges(self) -> None:
        prompt = _chat_onboarding_prompt("headcount", {})
        assert prompt.startswith("Arbor: ")
        for range_str, _lo, _hi in _CHAT_ONBOARDING_HEADCOUNT_RANGES:
            assert range_str in prompt

    def test_foreign_workers_prompt(self) -> None:
        prompt = _chat_onboarding_prompt("foreign_workers", {})
        assert prompt.startswith("Arbor: ")
        assert "foreign" in prompt.lower()
        assert "yes" in prompt.lower()
        assert "no" in prompt.lower()

    def test_confirm_prompt_summarises_collected_fields(self) -> None:
        fields = {
            "name": "Bright Sparks Pte Ltd",
            "sector": "technology",
            "headcount": "26-50",
            "foreign_workers": True,
        }
        prompt = _chat_onboarding_prompt("confirm", fields)
        assert prompt.startswith("Arbor: ")
        assert "Bright Sparks Pte Ltd" in prompt
        assert "Technology & IT" in prompt  # human label, not the key
        assert "26-50" in prompt
        assert "yes" in prompt  # foreign_workers True -> yes

    def test_confirm_prompt_renders_no_for_false_foreign_workers(self) -> None:
        prompt = _chat_onboarding_prompt(
            "confirm",
            {
                "name": "Local Co",
                "sector": "fnb",
                "headcount": "1-5",
                "foreign_workers": False,
            },
        )
        assert "Foreign workers: no" in prompt

    def test_unknown_step_returns_completion_message(self) -> None:
        prompt = _chat_onboarding_prompt("unknown-step", {})
        assert prompt.startswith("Arbor: ")


# =========================================================================
# State-machine integrity
# =========================================================================


class TestStateMachineIntegrity:
    """The set of valid steps must be stable; tests guard against accidental drift."""

    def test_steps_contain_expected_states(self) -> None:
        assert _CHAT_ONBOARDING_STEPS == (
            "name",
            "sector",
            "headcount",
            "foreign_workers",
            "confirm",
        )

    def test_every_step_has_a_prompt(self) -> None:
        for step in _CHAT_ONBOARDING_STEPS:
            prompt = _chat_onboarding_prompt(step, {"name": "Acme", "sector": "technology"})
            assert prompt.startswith("Arbor: ")
            assert len(prompt) > len("Arbor: ")
