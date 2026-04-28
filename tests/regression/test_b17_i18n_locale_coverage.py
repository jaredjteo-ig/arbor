"""Regression: B17 — minimum-viable i18n locale coverage.

Ensures every supported locale file defines the navbar keys that
NavigationSidebar and TopBar render. If a translator forgets a key,
the UI silently falls back to English — these assertions surface the
miss before it reaches production.

Run in isolation (test-once protocol):

    pytest tests/regression/test_b17_i18n_locale_coverage.py -v
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# Path to the i18n bundles inside the Next.js workspace.
I18N_DIR = (
    Path(__file__).resolve().parents[2]
    / "apps"
    / "web"
    / "src"
    / "lib"
    / "i18n"
)

SUPPORTED_LOCALES = ("en", "zh-CN", "ms-MY", "ta-SG")

# Keys that MUST exist in every locale because they are rendered by
# the dashboard navbar (NavigationSidebar + TopBar) on every page. If
# any of these is missing, the UI shows raw key strings to the user.
REQUIRED_NAVBAR_KEYS = (
    "nav.dashboard",
    "nav.advisory",
    "nav.compliance",
    "nav.calculators",
    "nav.documents",
    "nav.settings",
    "nav.help",
    "nav.my-dashboard",
    "nav.my-leave",
    "nav.my-payslips",
    "nav.my-claims",
    "topbar.search_placeholder",
    "topbar.my_profile",
    "topbar.settings",
    "topbar.log_out",
    "settings.language",
    "language.en",
    "language.zh-CN",
    "language.ms-MY",
    "language.ta-SG",
    "payslips.page_title",
    "payslips.empty_title",
    "payslips.net_pay",
)


def _load(locale: str) -> dict:
    path = I18N_DIR / f"{locale}.json"
    assert path.exists(), f"Missing locale bundle: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve(bundle: dict, dotted: str) -> object:
    """Walk a dotted key path through the JSON bundle."""
    node: object = bundle
    for segment in dotted.split("."):
        if not isinstance(node, dict) or segment not in node:
            return None
        node = node[segment]
    return node


@pytest.mark.regression
@pytest.mark.parametrize("locale", SUPPORTED_LOCALES)
def test_locale_file_exists_and_loads(locale: str) -> None:
    bundle = _load(locale)
    assert isinstance(bundle, dict)
    assert "nav" in bundle, f"{locale}.json missing top-level 'nav' namespace"


@pytest.mark.regression
@pytest.mark.parametrize("locale", SUPPORTED_LOCALES)
@pytest.mark.parametrize("key", REQUIRED_NAVBAR_KEYS)
def test_required_navbar_key_translated(locale: str, key: str) -> None:
    """Every locale MUST translate every navbar / topbar / settings key."""
    bundle = _load(locale)
    value = _resolve(bundle, key)
    assert value is not None, (
        f"Locale '{locale}' is missing key '{key}'. Add a translation "
        f"to apps/web/src/lib/i18n/{locale}.json."
    )
    assert isinstance(value, str), (
        f"Locale '{locale}' key '{key}' resolved to {type(value).__name__}, "
        f"expected str."
    )
    assert value.strip(), (
        f"Locale '{locale}' key '{key}' is an empty string."
    )


@pytest.mark.regression
def test_non_english_locales_actually_translate_navbar() -> None:
    """zh-CN / ms-MY / ta-SG must NOT just echo the English string for
    the most user-visible labels. Catches placeholder copy-paste."""
    en = _load("en")
    spot_check_keys = ("nav.dashboard", "nav.settings", "nav.my-payslips")
    for locale in ("zh-CN", "ms-MY", "ta-SG"):
        bundle = _load(locale)
        for key in spot_check_keys:
            en_value = _resolve(en, key)
            other_value = _resolve(bundle, key)
            assert other_value != en_value, (
                f"Locale '{locale}' key '{key}' is identical to English "
                f"({en_value!r}). Provide a real translation."
            )
