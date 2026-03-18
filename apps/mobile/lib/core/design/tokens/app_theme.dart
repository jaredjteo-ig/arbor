import 'package:flutter/material.dart';
import 'tokens.dart';

ThemeData buildAppTheme({TextSizePreference textSize = TextSizePreference.normal}) {
  final m = textSize.multiplier;

  return ThemeData(
    useMaterial3: true,
    fontFamily: AppTypography.fontFamily,
    colorScheme: const ColorScheme(
      brightness: Brightness.light,
      primary: AppColors.primaryNavy,
      onPrimary: AppColors.neutralWhite,
      secondary: AppColors.secondaryTeal,
      onSecondary: AppColors.neutralWhite,
      error: AppColors.riskRed,
      onError: AppColors.neutralWhite,
      surface: AppColors.surfaceCard,
      onSurface: AppColors.neutralGray900,
    ),
    scaffoldBackgroundColor: AppColors.surfaceBackground,
    appBarTheme: AppBarTheme(
      backgroundColor: AppColors.primaryNavy,
      foregroundColor: AppColors.neutralWhite,
      elevation: 0,
      titleTextStyle: AppTypography.subtitle.copyWith(
        color: AppColors.neutralWhite,
        fontSize: AppTypography.subtitle.fontSize! * m,
      ),
    ),
    textTheme: TextTheme(
      displayLarge: AppTypography.pageTitle.copyWith(fontSize: AppTypography.pageTitle.fontSize! * m),
      displayMedium: AppTypography.heading.copyWith(fontSize: AppTypography.heading.fontSize! * m),
      displaySmall: AppTypography.title.copyWith(fontSize: AppTypography.title.fontSize! * m),
      headlineMedium: AppTypography.subtitle.copyWith(fontSize: AppTypography.subtitle.fontSize! * m),
      titleLarge: AppTypography.subtitle.copyWith(fontSize: AppTypography.subtitle.fontSize! * m),
      titleMedium: AppTypography.bodyBold.copyWith(fontSize: AppTypography.bodyBold.fontSize! * m),
      bodyLarge: AppTypography.body.copyWith(fontSize: AppTypography.body.fontSize! * m),
      bodyMedium: AppTypography.bodySmall.copyWith(fontSize: AppTypography.bodySmall.fontSize! * m),
      bodySmall: AppTypography.caption.copyWith(fontSize: AppTypography.caption.fontSize! * m),
      labelLarge: AppTypography.bodyMedium.copyWith(fontSize: AppTypography.bodyMedium.fontSize! * m),
      labelSmall: AppTypography.overline.copyWith(fontSize: AppTypography.overline.fontSize! * m),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.primaryNavy,
        foregroundColor: AppColors.neutralWhite,
        minimumSize: const Size(AppTouch.minTarget, AppTouch.minTarget),
        shape: RoundedRectangleBorder(borderRadius: AppRadius.md),
        textStyle: AppTypography.bodyMedium.copyWith(fontSize: AppTypography.bodyMedium.fontSize! * m),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.primaryNavy,
        minimumSize: const Size(AppTouch.minTarget, AppTouch.minTarget),
        shape: RoundedRectangleBorder(borderRadius: AppRadius.md),
        side: const BorderSide(color: AppColors.primaryNavy),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: AppColors.surfaceInput,
      border: OutlineInputBorder(
        borderRadius: AppRadius.md,
        borderSide: const BorderSide(color: AppColors.surfaceInputBorder),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: AppRadius.md,
        borderSide: const BorderSide(color: AppColors.surfaceInputBorder),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: AppRadius.md,
        borderSide: const BorderSide(color: AppColors.surfaceInputFocus, width: 2),
      ),
      contentPadding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.base,
        vertical: AppSpacing.md,
      ),
    ),
    cardTheme: CardThemeData(
      color: AppColors.surfaceCard,
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: AppRadius.lg),
    ),
    bottomNavigationBarTheme: const BottomNavigationBarThemeData(
      backgroundColor: AppColors.neutralWhite,
      selectedItemColor: AppColors.primaryNavy,
      unselectedItemColor: AppColors.neutralGray400,
    ),
  );
}
