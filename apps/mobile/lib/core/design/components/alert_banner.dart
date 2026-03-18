import 'package:flutter/material.dart';
import '../tokens/tokens.dart';

/// Severity variants for [AlertBanner].
enum AlertBannerVariant { info, warning, error, success }

/// A full-width banner showing contextual information with an icon, title,
/// description, and optional dismiss button.
class AlertBanner extends StatelessWidget {
  const AlertBanner({
    super.key,
    required this.title,
    this.description,
    this.variant = AlertBannerVariant.info,
    this.onDismiss,
  });

  final String title;
  final String? description;
  final AlertBannerVariant variant;
  final VoidCallback? onDismiss;

  IconData get _icon {
    return switch (variant) {
      AlertBannerVariant.info => Icons.info_outline,
      AlertBannerVariant.warning => Icons.warning_amber_rounded,
      AlertBannerVariant.error => Icons.error_outline,
      AlertBannerVariant.success => Icons.check_circle_outline,
    };
  }

  Color get _iconColor {
    return switch (variant) {
      AlertBannerVariant.info => AppColors.semanticInfo,
      AlertBannerVariant.warning => AppColors.semanticWarning,
      AlertBannerVariant.error => AppColors.semanticError,
      AlertBannerVariant.success => AppColors.semanticSuccess,
    };
  }

  Color get _backgroundColor {
    return switch (variant) {
      AlertBannerVariant.info => AppColors.semanticInfoBg,
      AlertBannerVariant.warning => AppColors.semanticWarningBg,
      AlertBannerVariant.error => AppColors.semanticErrorBg,
      AlertBannerVariant.success => AppColors.semanticSuccessBg,
    };
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.base),
      decoration: BoxDecoration(
        color: _backgroundColor,
        borderRadius: AppRadius.md,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(_icon, color: _iconColor, size: 24),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: AppTypography.bodyBold.copyWith(
                    color: AppColors.neutralGray900,
                  ),
                ),
                if (description != null) ...[
                  const SizedBox(height: AppSpacing.xs),
                  Text(
                    description!,
                    style: AppTypography.bodySmall.copyWith(
                      color: AppColors.neutralGray700,
                    ),
                  ),
                ],
              ],
            ),
          ),
          if (onDismiss != null)
            IconButton(
              onPressed: onDismiss,
              icon: const Icon(Icons.close, size: 20),
              color: AppColors.neutralGray500,
              constraints: const BoxConstraints(
                minWidth: AppTouch.minTarget,
                minHeight: AppTouch.minTarget,
              ),
              tooltip: 'Dismiss',
            ),
        ],
      ),
    );
  }
}
