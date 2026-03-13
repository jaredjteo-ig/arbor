"""Generate React CSS variables and Flutter Dart constants from tokens.json.

Usage: python design-tokens/generate.py
"""

import json
from pathlib import Path

TOKENS_PATH = Path(__file__).parent / "tokens.json"
REACT_OUTPUT = Path(__file__).parent.parent / "apps" / "web" / "src" / "lib" / "tokens.ts"
FLUTTER_OUTPUT = (
    Path(__file__).parent.parent
    / "apps"
    / "mobile"
    / "lib"
    / "core"
    / "design"
    / "tokens"
    / "tokens.dart"
)


def load_tokens() -> dict:
    return json.loads(TOKENS_PATH.read_text())


def generate_react(tokens: dict) -> str:
    lines = [
        "// AUTO-GENERATED from design-tokens/tokens.json — do not edit manually.",
        "// Run: python design-tokens/generate.py",
        "",
        "// ── Colors ──────────────────────────────────────────────",
        "export const colors = {",
    ]

    for group_name, group in tokens["color"].items():
        for key, value in group.items():
            var_name = f"{group_name}_{key}".replace("-", "_").replace(" ", "_")
            lines.append(f'  {var_name}: "{value}",')

    lines.append("} as const;")
    lines.append("")

    # Typography
    lines.append("// ── Typography ───────────────────────────────────────────")
    lines.append(f'export const fontFamily = {json.dumps(tokens["typography"]["font-family"])};')
    lines.append("")
    lines.append("export const typeScale = {")
    for name, props in tokens["typography"]["scale"].items():
        dart_name = name.replace("-", "_")
        lines.append(f"  {dart_name}: {{")
        for prop, val in props.items():
            prop_name = prop.replace("-", "_")
            if isinstance(val, str):
                lines.append(f'    {prop_name}: "{val}",')
            else:
                lines.append(f"    {prop_name}: {val},")
        lines.append("  },")
    lines.append("} as const;")
    lines.append("")

    # Text size multipliers
    lines.append("export const textSizeMultiplier = {")
    for name, val in tokens["typography"]["text-size-multiplier"].items():
        dart_name = name.replace("-", "_")
        lines.append(f"  {dart_name}: {val},")
    lines.append("} as const;")
    lines.append("")
    lines.append("export type TextSizePreference = keyof typeof textSizeMultiplier;")
    lines.append("")

    # Spacing
    lines.append("// ── Spacing ─────────────────────────────────────────────")
    lines.append("export const spacing = {")
    for name, val in tokens["spacing"]["scale"].items():
        ts_name = name.replace("-", "_")
        # Quote keys that start with a digit
        if ts_name[0].isdigit():
            lines.append(f'  "{ts_name}": {val},')
        else:
            lines.append(f"  {ts_name}: {val},")
    lines.append("} as const;")
    lines.append("")

    # Radius
    lines.append("// ── Border Radius ───────────────────────────────────────")
    lines.append("export const radius = {")
    for name, val in tokens["radius"].items():
        lines.append(f"  {name}: {val},")
    lines.append("} as const;")
    lines.append("")

    # Shadows
    lines.append("// ── Shadows ─────────────────────────────────────────────")
    lines.append("export const shadow = {")
    for name, val in tokens["shadow"].items():
        lines.append(f'  {name}: "{val}",')
    lines.append("} as const;")
    lines.append("")

    # Touch targets
    lines.append("// ── Touch Targets ───────────────────────────────────────")
    lines.append(f'export const minTouchTarget = {tokens["touch"]["min-target"]};')
    lines.append("")

    return "\n".join(lines)


def _hex_to_flutter(hex_color: str) -> str:
    """Convert #RRGGBB to 0xFFRRGGBB for Flutter Color constructor."""
    h = hex_color.lstrip("#")
    return f"0xFF{h.upper()}"


def generate_flutter(tokens: dict) -> str:
    lines = [
        "// AUTO-GENERATED from design-tokens/tokens.json — do not edit manually.",
        "// Run: python design-tokens/generate.py",
        "",
        "import 'package:flutter/material.dart';",
        "",
        "// ── Colors ──────────────────────────────────────────────",
        "abstract final class AppColors {",
    ]

    for group_name, group in tokens["color"].items():
        for key, value in group.items():
            var_name = _dart_var_name(f"{group_name}_{key}")
            if value.startswith("#"):
                lines.append(f"  static const Color {var_name} = Color({_hex_to_flutter(value)});")
            else:
                # Non-hex values (like rgba shadows) — skip for colors
                pass

    lines.append("}")
    lines.append("")

    # Typography
    lines.append("// ── Typography ───────────────────────────────────────────")
    font_family = tokens["typography"]["font-family"].split(",")[0].strip().strip("'\"")
    lines.append("abstract final class AppTypography {")
    lines.append(f"  static const String fontFamily = '{font_family}';")
    lines.append("")

    for name, props in tokens["typography"]["scale"].items():
        dart_name = _dart_var_name(name)
        size = props["size"]
        weight = props["weight"]
        lh = props["line-height"]
        fw = _flutter_font_weight(weight)
        lines.append(f"  static const TextStyle {dart_name} = TextStyle(")
        lines.append(f"    fontFamily: fontFamily,")
        lines.append(f"    fontSize: {float(size)},")
        lines.append(f"    fontWeight: {fw},")
        lines.append(f"    height: {float(lh)},")
        if "letter-spacing" in props:
            lines.append(f"    letterSpacing: {float(props['letter-spacing'])},")
        lines.append("  );")
        lines.append("")

    lines.append("}")
    lines.append("")

    # Text size multiplier
    lines.append("enum TextSizePreference {")
    for name, val in tokens["typography"]["text-size-multiplier"].items():
        dart_name = _dart_var_name(name)
        lines.append(f"  {dart_name}({float(val)}),")
    lines.append("  ;")
    lines.append("  const TextSizePreference(this.multiplier);")
    lines.append("  final double multiplier;")
    lines.append("}")
    lines.append("")

    # Spacing
    lines.append("// ── Spacing ─────────────────────────────────────────────")
    lines.append("abstract final class AppSpacing {")
    for name, val in tokens["spacing"]["scale"].items():
        dart_name = _dart_var_name(name)
        lines.append(f"  static const double {dart_name} = {float(val)};")
    lines.append("}")
    lines.append("")

    # Radius
    lines.append("// ── Border Radius ───────────────────────────────────────")
    lines.append("abstract final class AppRadius {")
    for name, val in tokens["radius"].items():
        dart_name = _dart_var_name(name)
        lines.append(
            f"  static const BorderRadius {dart_name} = BorderRadius.all(Radius.circular({float(val)}));"
        )
    lines.append("}")
    lines.append("")

    # Touch targets
    lines.append("// ── Touch Targets ───────────────────────────────────────")
    lines.append(f"abstract final class AppTouch {{")
    lines.append(f'  static const double minTarget = {float(tokens["touch"]["min-target"])};')
    lines.append("}")
    lines.append("")

    return "\n".join(lines)


def _dart_var_name(name: str) -> str:
    """Convert kebab-case to camelCase. Prefix digit-starting names."""
    parts = name.replace("-", "_").split("_")
    result = parts[0] + "".join(p.capitalize() for p in parts[1:])
    # Dart identifiers can't start with digits
    if result[0].isdigit():
        result = "s" + result  # e.g. 2xl -> s2xl
    return result


def _flutter_font_weight(weight: int) -> str:
    weight_map = {
        100: "FontWeight.w100",
        200: "FontWeight.w200",
        300: "FontWeight.w300",
        400: "FontWeight.w400",
        500: "FontWeight.w500",
        600: "FontWeight.w600",
        700: "FontWeight.w700",
        800: "FontWeight.w800",
        900: "FontWeight.w900",
    }
    return weight_map.get(weight, "FontWeight.w400")


def main():
    tokens = load_tokens()

    # Generate React tokens
    react_code = generate_react(tokens)
    REACT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    REACT_OUTPUT.write_text(react_code)
    print(f"React tokens → {REACT_OUTPUT}")

    # Generate Flutter tokens
    flutter_code = generate_flutter(tokens)
    FLUTTER_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    FLUTTER_OUTPUT.write_text(flutter_code)
    print(f"Flutter tokens → {FLUTTER_OUTPUT}")


if __name__ == "__main__":
    main()
