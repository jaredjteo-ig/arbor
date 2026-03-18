// AUTO-GENERATED from design-tokens/tokens.json — do not edit manually.
// Run: python design-tokens/generate.py

// ── Colors ──────────────────────────────────────────────
export const colors = {
  primary_navy: "#1E3A5F",
  primary_navy_light: "#2A4F7F",
  primary_navy_dark: "#152B47",
  secondary_teal: "#0D6E4F",
  secondary_teal_light: "#11946A",
  secondary_teal_dark: "#0A5A40",
  neutral_white: "#FFFFFF",
  neutral_gray_50: "#F8FAFC",
  neutral_gray_100: "#F1F5F9",
  neutral_gray_200: "#E2E8F0",
  neutral_gray_300: "#CBD5E1",
  neutral_gray_400: "#94A3B8",
  neutral_gray_500: "#64748B",
  neutral_gray_600: "#475569",
  neutral_gray_700: "#334155",
  neutral_gray_800: "#1E293B",
  neutral_gray_900: "#0F172A",
  neutral_black: "#000000",
  risk_green: "#16A34A",
  risk_green_bg: "#F0FDF4",
  risk_green_border: "#BBF7D0",
  risk_amber: "#D97706",
  risk_amber_bg: "#FFFBEB",
  risk_amber_border: "#FDE68A",
  risk_red: "#DC2626",
  risk_red_bg: "#FEF2F2",
  risk_red_border: "#FECACA",
  semantic_info: "#2563EB",
  semantic_info_bg: "#EFF6FF",
  semantic_success: "#16A34A",
  semantic_success_bg: "#F0FDF4",
  semantic_warning: "#D97706",
  semantic_warning_bg: "#FFFBEB",
  semantic_error: "#DC2626",
  semantic_error_bg: "#FEF2F2",
  authority_statutory: "#2563EB",
  authority_statutory_bg: "#EFF6FF",
  authority_guideline: "#D97706",
  authority_guideline_bg: "#FFFBEB",
  authority_best_practice: "#16A34A",
  authority_best_practice_bg: "#F0FDF4",
  surface_background: "#F8FAFC",
  surface_card: "#FFFFFF",
  surface_sidebar: "#1E3A5F",
  surface_sidebar_hover: "#2A4F7F",
  surface_input: "#FFFFFF",
  surface_input_border: "#CBD5E1",
  surface_input_focus: "#1E3A5F",
} as const;

// ── Typography ───────────────────────────────────────────
export const fontFamily = "'Source Sans 3', 'Source Sans Pro', system-ui, -apple-system, sans-serif";

export const typeScale = {
  overline: {
    size: 11,
    weight: 600,
    line_height: 1.5,
    letter_spacing: 1.0,
    transform: "uppercase",
  },
  caption: {
    size: 12,
    weight: 400,
    line_height: 1.5,
  },
  body_small: {
    size: 14,
    weight: 400,
    line_height: 1.6,
  },
  body: {
    size: 16,
    weight: 400,
    line_height: 1.6,
  },
  body_medium: {
    size: 16,
    weight: 500,
    line_height: 1.6,
  },
  body_bold: {
    size: 16,
    weight: 600,
    line_height: 1.6,
  },
  subtitle: {
    size: 18,
    weight: 600,
    line_height: 1.4,
  },
  title: {
    size: 20,
    weight: 700,
    line_height: 1.3,
  },
  heading: {
    size: 24,
    weight: 700,
    line_height: 1.3,
  },
  page_title: {
    size: 28,
    weight: 700,
    line_height: 1.2,
  },
} as const;

export const textSizeMultiplier = {
  normal: 1.0,
  large: 1.15,
  extra_large: 1.3,
} as const;

export type TextSizePreference = keyof typeof textSizeMultiplier;

// ── Spacing ─────────────────────────────────────────────
export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  base: 16,
  lg: 20,
  xl: 24,
  "2xl": 32,
  "3xl": 48,
} as const;

// ── Border Radius ───────────────────────────────────────
export const radius = {
  sm: 6,
  md: 8,
  lg: 12,
  xl: 16,
  full: 9999,
} as const;

// ── Shadows ─────────────────────────────────────────────
export const shadow = {
  card: "0 1px 3px rgba(0, 0, 0, 0.08), 0 1px 2px rgba(0, 0, 0, 0.06)",
  raised: "0 4px 6px rgba(0, 0, 0, 0.07), 0 2px 4px rgba(0, 0, 0, 0.06)",
  modal: "0 20px 25px rgba(0, 0, 0, 0.1), 0 8px 10px rgba(0, 0, 0, 0.04)",
} as const;

// ── Touch Targets ───────────────────────────────────────
export const minTouchTarget = 48;
