// AUTO-GENERATED from design-tokens/tokens.json — do not edit manually.
// Run: python design-tokens/generate.py

import 'package:flutter/material.dart';

// ── Colors ──────────────────────────────────────────────
abstract final class AppColors {
  static const Color primaryNavy = Color(0xFF1E3A5F);
  static const Color primaryNavyLight = Color(0xFF2A4F7F);
  static const Color primaryNavyDark = Color(0xFF152B47);
  static const Color secondaryTeal = Color(0xFF0D6E4F);
  static const Color secondaryTealLight = Color(0xFF11946A);
  static const Color secondaryTealDark = Color(0xFF0A5A40);
  static const Color neutralWhite = Color(0xFFFFFFFF);
  static const Color neutralGray50 = Color(0xFFF8FAFC);
  static const Color neutralGray100 = Color(0xFFF1F5F9);
  static const Color neutralGray200 = Color(0xFFE2E8F0);
  static const Color neutralGray300 = Color(0xFFCBD5E1);
  static const Color neutralGray400 = Color(0xFF94A3B8);
  static const Color neutralGray500 = Color(0xFF64748B);
  static const Color neutralGray600 = Color(0xFF475569);
  static const Color neutralGray700 = Color(0xFF334155);
  static const Color neutralGray800 = Color(0xFF1E293B);
  static const Color neutralGray900 = Color(0xFF0F172A);
  static const Color neutralBlack = Color(0xFF000000);
  static const Color riskGreen = Color(0xFF16A34A);
  static const Color riskGreenBg = Color(0xFFF0FDF4);
  static const Color riskGreenBorder = Color(0xFFBBF7D0);
  static const Color riskAmber = Color(0xFFD97706);
  static const Color riskAmberBg = Color(0xFFFFFBEB);
  static const Color riskAmberBorder = Color(0xFFFDE68A);
  static const Color riskRed = Color(0xFFDC2626);
  static const Color riskRedBg = Color(0xFFFEF2F2);
  static const Color riskRedBorder = Color(0xFFFECACA);
  static const Color semanticInfo = Color(0xFF2563EB);
  static const Color semanticInfoBg = Color(0xFFEFF6FF);
  static const Color semanticSuccess = Color(0xFF16A34A);
  static const Color semanticSuccessBg = Color(0xFFF0FDF4);
  static const Color semanticWarning = Color(0xFFD97706);
  static const Color semanticWarningBg = Color(0xFFFFFBEB);
  static const Color semanticError = Color(0xFFDC2626);
  static const Color semanticErrorBg = Color(0xFFFEF2F2);
  static const Color authorityStatutory = Color(0xFF2563EB);
  static const Color authorityStatutoryBg = Color(0xFFEFF6FF);
  static const Color authorityGuideline = Color(0xFFD97706);
  static const Color authorityGuidelineBg = Color(0xFFFFFBEB);
  static const Color authorityBestPractice = Color(0xFF16A34A);
  static const Color authorityBestPracticeBg = Color(0xFFF0FDF4);
  static const Color surfaceBackground = Color(0xFFF8FAFC);
  static const Color surfaceCard = Color(0xFFFFFFFF);
  static const Color surfaceSidebar = Color(0xFF1E3A5F);
  static const Color surfaceSidebarHover = Color(0xFF2A4F7F);
  static const Color surfaceInput = Color(0xFFFFFFFF);
  static const Color surfaceInputBorder = Color(0xFFCBD5E1);
  static const Color surfaceInputFocus = Color(0xFF1E3A5F);
}

// ── Typography ───────────────────────────────────────────
abstract final class AppTypography {
  static const String fontFamily = 'Source Sans 3';

  static const TextStyle overline = TextStyle(
    fontFamily: fontFamily,
    fontSize: 11.0,
    fontWeight: FontWeight.w600,
    height: 1.5,
    letterSpacing: 1.0,
  );

  static const TextStyle caption = TextStyle(
    fontFamily: fontFamily,
    fontSize: 12.0,
    fontWeight: FontWeight.w400,
    height: 1.5,
  );

  static const TextStyle bodySmall = TextStyle(
    fontFamily: fontFamily,
    fontSize: 14.0,
    fontWeight: FontWeight.w400,
    height: 1.6,
  );

  static const TextStyle body = TextStyle(
    fontFamily: fontFamily,
    fontSize: 16.0,
    fontWeight: FontWeight.w400,
    height: 1.6,
  );

  static const TextStyle bodyMedium = TextStyle(
    fontFamily: fontFamily,
    fontSize: 16.0,
    fontWeight: FontWeight.w500,
    height: 1.6,
  );

  static const TextStyle bodyBold = TextStyle(
    fontFamily: fontFamily,
    fontSize: 16.0,
    fontWeight: FontWeight.w600,
    height: 1.6,
  );

  static const TextStyle subtitle = TextStyle(
    fontFamily: fontFamily,
    fontSize: 18.0,
    fontWeight: FontWeight.w600,
    height: 1.4,
  );

  static const TextStyle title = TextStyle(
    fontFamily: fontFamily,
    fontSize: 20.0,
    fontWeight: FontWeight.w700,
    height: 1.3,
  );

  static const TextStyle heading = TextStyle(
    fontFamily: fontFamily,
    fontSize: 24.0,
    fontWeight: FontWeight.w700,
    height: 1.3,
  );

  static const TextStyle pageTitle = TextStyle(
    fontFamily: fontFamily,
    fontSize: 28.0,
    fontWeight: FontWeight.w700,
    height: 1.2,
  );

}

enum TextSizePreference {
  normal(1.0),
  large(1.15),
  extraLarge(1.3),
  ;
  const TextSizePreference(this.multiplier);
  final double multiplier;
}

// ── Spacing ─────────────────────────────────────────────
abstract final class AppSpacing {
  static const double xs = 4.0;
  static const double sm = 8.0;
  static const double md = 12.0;
  static const double base = 16.0;
  static const double lg = 20.0;
  static const double xl = 24.0;
  static const double s2xl = 32.0;
  static const double s3xl = 48.0;
}

// ── Border Radius ───────────────────────────────────────
abstract final class AppRadius {
  static const BorderRadius sm = BorderRadius.all(Radius.circular(6.0));
  static const BorderRadius md = BorderRadius.all(Radius.circular(8.0));
  static const BorderRadius lg = BorderRadius.all(Radius.circular(12.0));
  static const BorderRadius xl = BorderRadius.all(Radius.circular(16.0));
  static const BorderRadius full = BorderRadius.all(Radius.circular(9999.0));
}

// ── Touch Targets ───────────────────────────────────────
abstract final class AppTouch {
  static const double minTarget = 48.0;
}
