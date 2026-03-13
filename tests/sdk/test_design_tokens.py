"""Verify design token generation and consistency."""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
TOKENS_PATH = PROJECT_ROOT / "design-tokens" / "tokens.json"
REACT_TOKENS = PROJECT_ROOT / "apps" / "web" / "src" / "lib" / "tokens.ts"
FLUTTER_TOKENS = (
    PROJECT_ROOT / "apps" / "mobile" / "lib" / "core" / "design" / "tokens" / "tokens.dart"
)


class TestTokensJson:
    """Verify the source-of-truth tokens.json is correct."""

    def test_tokens_file_exists(self):
        assert TOKENS_PATH.exists()

    def test_tokens_is_valid_json(self):
        tokens = json.loads(TOKENS_PATH.read_text())
        assert isinstance(tokens, dict)

    def test_primary_navy_color(self):
        tokens = json.loads(TOKENS_PATH.read_text())
        assert tokens["color"]["primary"]["navy"] == "#1E3A5F"

    def test_secondary_teal_color(self):
        tokens = json.loads(TOKENS_PATH.read_text())
        assert tokens["color"]["secondary"]["teal"] == "#0D6E4F"

    def test_risk_tier_colors_exist(self):
        tokens = json.loads(TOKENS_PATH.read_text())
        risk = tokens["color"]["risk"]
        assert "green" in risk
        assert "amber" in risk
        assert "red" in risk

    def test_authority_colors_exist(self):
        tokens = json.loads(TOKENS_PATH.read_text())
        auth = tokens["color"]["authority"]
        assert "statutory" in auth
        assert "guideline" in auth
        assert "best-practice" in auth

    def test_typography_scale_complete(self):
        tokens = json.loads(TOKENS_PATH.read_text())
        scale = tokens["typography"]["scale"]
        expected = [
            "overline", "caption", "body-small", "body", "body-medium",
            "body-bold", "subtitle", "title", "heading", "page-title",
        ]
        for name in expected:
            assert name in scale, f"Missing type scale: {name}"

    def test_body_minimum_16px(self):
        tokens = json.loads(TOKENS_PATH.read_text())
        assert tokens["typography"]["scale"]["body"]["size"] >= 16

    def test_text_size_multipliers(self):
        tokens = json.loads(TOKENS_PATH.read_text())
        m = tokens["typography"]["text-size-multiplier"]
        assert m["normal"] == 1.0
        assert m["large"] > 1.0
        assert m["extra-large"] > m["large"]

    def test_spacing_scale(self):
        tokens = json.loads(TOKENS_PATH.read_text())
        spacing = tokens["spacing"]["scale"]
        assert spacing["xs"] == 4
        assert spacing["base"] == 16

    def test_touch_target_minimum(self):
        tokens = json.loads(TOKENS_PATH.read_text())
        assert tokens["touch"]["min-target"] >= 48


class TestGeneratedFiles:
    """Verify generated React and Flutter token files exist and are consistent."""

    def test_react_tokens_exist(self):
        assert REACT_TOKENS.exists()

    def test_flutter_tokens_exist(self):
        assert FLUTTER_TOKENS.exists()

    def test_react_tokens_contain_primary_color(self):
        content = REACT_TOKENS.read_text()
        assert "#1E3A5F" in content

    def test_flutter_tokens_contain_primary_color(self):
        content = FLUTTER_TOKENS.read_text()
        assert "0xFF1E3A5F" in content

    def test_react_tokens_contain_risk_colors(self):
        content = REACT_TOKENS.read_text()
        assert "risk_green" in content
        assert "risk_amber" in content
        assert "risk_red" in content

    def test_flutter_tokens_contain_risk_colors(self):
        content = FLUTTER_TOKENS.read_text()
        assert "riskGreen" in content
        assert "riskAmber" in content
        assert "riskRed" in content

    def test_react_tokens_contain_text_size_multiplier(self):
        content = REACT_TOKENS.read_text()
        assert "textSizeMultiplier" in content
        assert "TextSizePreference" in content

    def test_flutter_tokens_contain_text_size_preference(self):
        content = FLUTTER_TOKENS.read_text()
        assert "TextSizePreference" in content
        assert "multiplier" in content


class TestI18nSetup:
    """Verify i18n infrastructure is in place."""

    def test_react_i18n_exists(self):
        en_file = PROJECT_ROOT / "apps" / "web" / "src" / "lib" / "i18n" / "en.json"
        assert en_file.exists()
        data = json.loads(en_file.read_text())
        assert "app" in data
        assert "nav" in data
        assert data["common"]["currency"] == "S$"

    def test_flutter_arb_exists(self):
        arb_file = PROJECT_ROOT / "apps" / "mobile" / "lib" / "l10n" / "app_en.arb"
        assert arb_file.exists()
        data = json.loads(arb_file.read_text())
        assert data["@@locale"] == "en"
        assert data["commonCurrency"] == "S$"

    def test_flutter_l10n_config_exists(self):
        l10n_yaml = PROJECT_ROOT / "apps" / "mobile" / "l10n.yaml"
        assert l10n_yaml.exists()
