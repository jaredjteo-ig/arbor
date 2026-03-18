import 'package:flutter/material.dart';
import '../tokens/tokens.dart';

/// A placeholder shown when a view has no content to display.
///
/// Includes an icon, heading, description, and optional CTA action widget.
class EmptyState extends StatelessWidget {
  const EmptyState({
    super.key,
    required this.icon,
    required this.heading,
    required this.description,
    this.action,
  });

  final IconData icon;
  final String heading;
  final String description;

  /// Optional call-to-action widget (e.g. an [AppButton]).
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.s2xl),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 64,
              color: AppColors.neutralGray300,
            ),
            const SizedBox(height: AppSpacing.base),
            Text(
              heading,
              style: AppTypography.subtitle.copyWith(
                color: AppColors.neutralGray700,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppSpacing.sm),
            Text(
              description,
              style: AppTypography.body.copyWith(
                color: AppColors.neutralGray500,
              ),
              textAlign: TextAlign.center,
            ),
            if (action != null) ...[
              const SizedBox(height: AppSpacing.xl),
              action!,
            ],
          ],
        ),
      ),
    );
  }
}
