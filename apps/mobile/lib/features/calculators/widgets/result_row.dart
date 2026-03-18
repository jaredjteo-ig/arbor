import 'package:flutter/material.dart';

import '../../../core/design/tokens/tokens.dart';

/// A single label/value pair row used inside calculator results.
class ResultRow extends StatelessWidget {
  const ResultRow({
    super.key,
    required this.label,
    required this.value,
    this.isBold = false,
    this.valueColor,
  });

  final String label;
  final String value;

  /// Whether to render the value in bold (used for totals).
  final bool isBold;

  /// Optional override colour for the value text.
  final Color? valueColor;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(
            child: Text(
              label,
              style: AppTypography.bodySmall.copyWith(
                color: AppColors.neutralGray600,
              ),
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          Text(
            value,
            style: (isBold ? AppTypography.bodyBold : AppTypography.body)
                .copyWith(
              color: valueColor ?? AppColors.neutralGray900,
            ),
          ),
        ],
      ),
    );
  }
}

/// A thin divider matching the design system spacing.
class ResultDivider extends StatelessWidget {
  const ResultDivider({super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
      child: const Divider(
        height: 1,
        color: AppColors.neutralGray200,
      ),
    );
  }
}
