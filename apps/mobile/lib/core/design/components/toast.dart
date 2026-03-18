import 'package:flutter/material.dart';
import '../tokens/tokens.dart';

/// Convenience helper for showing themed snack bars via [ScaffoldMessenger].
///
/// Usage:
/// ```dart
/// AppToast.success(context, 'Record saved');
/// AppToast.error(context, 'Failed to load data');
/// ```
abstract final class AppToast {
  static void success(BuildContext context, String message) {
    _show(
      context,
      message: message,
      icon: Icons.check_circle_outline,
      backgroundColor: AppColors.semanticSuccessBg,
      foregroundColor: AppColors.semanticSuccess,
    );
  }

  static void error(BuildContext context, String message) {
    _show(
      context,
      message: message,
      icon: Icons.error_outline,
      backgroundColor: AppColors.semanticErrorBg,
      foregroundColor: AppColors.semanticError,
    );
  }

  static void warning(BuildContext context, String message) {
    _show(
      context,
      message: message,
      icon: Icons.warning_amber_rounded,
      backgroundColor: AppColors.semanticWarningBg,
      foregroundColor: AppColors.semanticWarning,
    );
  }

  static void info(BuildContext context, String message) {
    _show(
      context,
      message: message,
      icon: Icons.info_outline,
      backgroundColor: AppColors.semanticInfoBg,
      foregroundColor: AppColors.semanticInfo,
    );
  }

  static void _show(
    BuildContext context, {
    required String message,
    required IconData icon,
    required Color backgroundColor,
    required Color foregroundColor,
  }) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          behavior: SnackBarBehavior.floating,
          backgroundColor: backgroundColor,
          shape: RoundedRectangleBorder(borderRadius: AppRadius.md),
          content: Row(
            children: [
              Icon(icon, color: foregroundColor, size: 20),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Text(
                  message,
                  style: AppTypography.bodySmall.copyWith(
                    color: foregroundColor,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
          duration: const Duration(seconds: 4),
        ),
      );
  }
}
