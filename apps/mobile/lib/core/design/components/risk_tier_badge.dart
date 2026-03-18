import 'package:flutter/material.dart';
import '../tokens/tokens.dart';

/// Risk classification tiers.
enum RiskTier { green, amber, red }

/// A badge showing a risk tier with icon + text for accessibility.
///
/// Uses icon and text label (not colour alone) per WCAG guidelines.
class RiskTierBadge extends StatelessWidget {
  const RiskTierBadge({
    super.key,
    required this.tier,
    this.label,
  });

  final RiskTier tier;

  /// Override the default tier label (e.g. "Low Risk").
  final String? label;

  String get _defaultLabel {
    return switch (tier) {
      RiskTier.green => 'Low Risk',
      RiskTier.amber => 'Medium Risk',
      RiskTier.red => 'High Risk',
    };
  }

  IconData get _icon {
    return switch (tier) {
      RiskTier.green => Icons.check_circle,
      RiskTier.amber => Icons.warning,
      RiskTier.red => Icons.error,
    };
  }

  Color get _color {
    return switch (tier) {
      RiskTier.green => AppColors.riskGreen,
      RiskTier.amber => AppColors.riskAmber,
      RiskTier.red => AppColors.riskRed,
    };
  }

  Color get _bgColor {
    return switch (tier) {
      RiskTier.green => AppColors.riskGreenBg,
      RiskTier.amber => AppColors.riskAmberBg,
      RiskTier.red => AppColors.riskRedBg,
    };
  }

  Color get _borderColor {
    return switch (tier) {
      RiskTier.green => AppColors.riskGreenBorder,
      RiskTier.amber => AppColors.riskAmberBorder,
      RiskTier.red => AppColors.riskRedBorder,
    };
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minHeight: AppTouch.minTarget),
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.md,
        vertical: AppSpacing.xs,
      ),
      decoration: BoxDecoration(
        color: _bgColor,
        borderRadius: AppRadius.full,
        border: Border.all(color: _borderColor),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(_icon, size: 18, color: _color),
          const SizedBox(width: AppSpacing.xs),
          Text(
            label ?? _defaultLabel,
            style: AppTypography.bodySmall.copyWith(
              color: _color,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}
