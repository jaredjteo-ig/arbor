import 'package:flutter/material.dart';
import '../tokens/tokens.dart';

/// Visual elevation variants for [AppCard].
enum AppCardVariant {
  /// Default card with subtle shadow (elevation 1).
  standard,

  /// Prominent card with deeper shadow (elevation 4).
  elevated,

  /// No shadow, border-only appearance (elevation 0).
  flat,
}

/// A design-system card with header/footer slots and configurable elevation.
class AppCard extends StatelessWidget {
  const AppCard({
    super.key,
    required this.child,
    this.variant = AppCardVariant.standard,
    this.header,
    this.footer,
    this.padding,
    this.onTap,
  });

  final Widget child;
  final AppCardVariant variant;
  final Widget? header;
  final Widget? footer;
  final EdgeInsetsGeometry? padding;
  final VoidCallback? onTap;

  double get _elevation {
    return switch (variant) {
      AppCardVariant.standard => 1,
      AppCardVariant.elevated => 4,
      AppCardVariant.flat => 0,
    };
  }

  @override
  Widget build(BuildContext context) {
    final cardShape = RoundedRectangleBorder(
      borderRadius: AppRadius.lg,
      side: variant == AppCardVariant.flat
          ? const BorderSide(color: AppColors.neutralGray200)
          : BorderSide.none,
    );

    Widget content = Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (header != null)
          Padding(
            padding: const EdgeInsets.fromLTRB(
              AppSpacing.base,
              AppSpacing.base,
              AppSpacing.base,
              0,
            ),
            child: header,
          ),
        Padding(
          padding: padding ?? const EdgeInsets.all(AppSpacing.base),
          child: child,
        ),
        if (footer != null)
          Padding(
            padding: const EdgeInsets.fromLTRB(
              AppSpacing.base,
              0,
              AppSpacing.base,
              AppSpacing.base,
            ),
            child: footer,
          ),
      ],
    );

    if (onTap != null) {
      content = InkWell(
        onTap: onTap,
        borderRadius: AppRadius.lg,
        child: content,
      );
    }

    return Card(
      elevation: _elevation,
      color: AppColors.surfaceCard,
      shape: cardShape,
      clipBehavior: Clip.antiAlias,
      child: content,
    );
  }
}
