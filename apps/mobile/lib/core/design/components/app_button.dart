import 'package:flutter/material.dart';
import '../tokens/tokens.dart';

/// Variants available for [AppButton].
enum AppButtonVariant { primary, secondary, outlined, text, danger }

/// Sizes available for [AppButton].
enum AppButtonSize { small, medium, large }

/// A design-system button that supports multiple variants, sizes, and a
/// built-in loading state.
///
/// Touch targets are enforced at a minimum of [AppTouch.minTarget].
class AppButton extends StatelessWidget {
  const AppButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.variant = AppButtonVariant.primary,
    this.size = AppButtonSize.medium,
    this.isLoading = false,
    this.icon,
    this.fullWidth = false,
  });

  final String label;
  final VoidCallback? onPressed;
  final AppButtonVariant variant;
  final AppButtonSize size;
  final bool isLoading;
  final IconData? icon;
  final bool fullWidth;

  // -- Size-dependent metrics ------------------------------------------------

  double get _height {
    return switch (size) {
      AppButtonSize.small => AppTouch.minTarget,
      AppButtonSize.medium => 52,
      AppButtonSize.large => 60,
    };
  }

  EdgeInsets get _padding {
    return switch (size) {
      AppButtonSize.small =>
        const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.xs),
      AppButtonSize.medium =>
        const EdgeInsets.symmetric(horizontal: AppSpacing.base, vertical: AppSpacing.sm),
      AppButtonSize.large =>
        const EdgeInsets.symmetric(horizontal: AppSpacing.xl, vertical: AppSpacing.md),
    };
  }

  TextStyle get _textStyle {
    return switch (size) {
      AppButtonSize.small => AppTypography.bodySmall.copyWith(fontWeight: FontWeight.w600),
      AppButtonSize.medium => AppTypography.bodyMedium,
      AppButtonSize.large => AppTypography.bodyBold,
    };
  }

  double get _iconSize {
    return switch (size) {
      AppButtonSize.small => 18,
      AppButtonSize.medium => 20,
      AppButtonSize.large => 24,
    };
  }

  // -- Variant-dependent styling ---------------------------------------------

  Color _backgroundColor(ColorScheme scheme) {
    return switch (variant) {
      AppButtonVariant.primary => AppColors.primaryNavy,
      AppButtonVariant.secondary => AppColors.secondaryTeal,
      AppButtonVariant.outlined => Colors.transparent,
      AppButtonVariant.text => Colors.transparent,
      AppButtonVariant.danger => AppColors.riskRed,
    };
  }

  Color _foregroundColor(ColorScheme scheme) {
    return switch (variant) {
      AppButtonVariant.primary => AppColors.neutralWhite,
      AppButtonVariant.secondary => AppColors.neutralWhite,
      AppButtonVariant.outlined => AppColors.primaryNavy,
      AppButtonVariant.text => AppColors.primaryNavy,
      AppButtonVariant.danger => AppColors.neutralWhite,
    };
  }

  BorderSide? get _side {
    return switch (variant) {
      AppButtonVariant.outlined =>
        const BorderSide(color: AppColors.primaryNavy, width: 1.5),
      _ => BorderSide.none,
    };
  }

  double get _elevation {
    return switch (variant) {
      AppButtonVariant.text => 0,
      AppButtonVariant.outlined => 0,
      _ => 1,
    };
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final bg = _backgroundColor(scheme);
    final fg = _foregroundColor(scheme);

    final style = ButtonStyle(
      backgroundColor: WidgetStatePropertyAll<Color>(bg),
      foregroundColor: WidgetStatePropertyAll<Color>(fg),
      minimumSize: WidgetStatePropertyAll<Size>(
        Size(fullWidth ? double.infinity : AppTouch.minTarget, _height),
      ),
      padding: WidgetStatePropertyAll<EdgeInsets>(_padding),
      elevation: WidgetStatePropertyAll<double>(_elevation),
      shape: WidgetStatePropertyAll<RoundedRectangleBorder>(
        RoundedRectangleBorder(
          borderRadius: AppRadius.md,
          side: _side ?? BorderSide.none,
        ),
      ),
      textStyle: WidgetStatePropertyAll<TextStyle>(_textStyle.copyWith(color: fg)),
    );

    final Widget child;
    if (isLoading) {
      child = SizedBox(
        width: _iconSize,
        height: _iconSize,
        child: CircularProgressIndicator(
          strokeWidth: 2,
          valueColor: AlwaysStoppedAnimation<Color>(fg),
        ),
      );
    } else if (icon != null) {
      child = Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: _iconSize),
          const SizedBox(width: AppSpacing.sm),
          Text(label),
        ],
      );
    } else {
      child = Text(label);
    }

    return ElevatedButton(
      onPressed: isLoading ? null : onPressed,
      style: style,
      child: child,
    );
  }
}
