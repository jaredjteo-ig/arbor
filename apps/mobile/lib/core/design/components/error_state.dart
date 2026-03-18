import 'package:flutter/material.dart';
import '../tokens/tokens.dart';

/// Error categories for [ErrorState].
enum ErrorVariant { network, server, unavailable }

/// A full-page error placeholder with variant-specific icons, messaging,
/// and a retry button.
class ErrorState extends StatelessWidget {
  const ErrorState({
    super.key,
    this.variant = ErrorVariant.server,
    this.title,
    this.description,
    this.onRetry,
    this.retryLabel = 'Try again',
  });

  final ErrorVariant variant;
  final String? title;
  final String? description;
  final VoidCallback? onRetry;
  final String retryLabel;

  IconData get _icon {
    return switch (variant) {
      ErrorVariant.network => Icons.wifi_off,
      ErrorVariant.server => Icons.cloud_off,
      ErrorVariant.unavailable => Icons.block,
    };
  }

  String get _defaultTitle {
    return switch (variant) {
      ErrorVariant.network => 'No connection',
      ErrorVariant.server => 'Something went wrong',
      ErrorVariant.unavailable => 'Service unavailable',
    };
  }

  String get _defaultDescription {
    return switch (variant) {
      ErrorVariant.network =>
        'Please check your internet connection and try again.',
      ErrorVariant.server =>
        'We encountered an unexpected error. Please try again later.',
      ErrorVariant.unavailable =>
        'This service is temporarily unavailable. Please try again later.',
    };
  }

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.s2xl),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              _icon,
              size: 64,
              color: AppColors.neutralGray400,
            ),
            const SizedBox(height: AppSpacing.base),
            Text(
              title ?? _defaultTitle,
              style: AppTypography.subtitle.copyWith(
                color: AppColors.neutralGray700,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppSpacing.sm),
            Text(
              description ?? _defaultDescription,
              style: AppTypography.body.copyWith(
                color: AppColors.neutralGray500,
              ),
              textAlign: TextAlign.center,
            ),
            if (onRetry != null) ...[
              const SizedBox(height: AppSpacing.xl),
              OutlinedButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh, size: 20),
                label: Text(retryLabel),
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppColors.primaryNavy,
                  minimumSize: const Size(
                    AppTouch.minTarget,
                    AppTouch.minTarget,
                  ),
                  side: const BorderSide(color: AppColors.primaryNavy),
                  shape: RoundedRectangleBorder(borderRadius: AppRadius.md),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
