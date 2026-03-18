import 'package:flutter/material.dart';
import '../tokens/tokens.dart';

/// A reusable bottom-sheet wrapper with a drag handle and consistent styling.
///
/// Usage:
/// ```dart
/// showModalBottomSheet(
///   context: context,
///   builder: (_) => BottomSheetWrapper(child: MyContent()),
/// );
/// ```
class BottomSheetWrapper extends StatelessWidget {
  const BottomSheetWrapper({
    super.key,
    required this.child,
    this.title,
    this.padding,
  });

  final Widget child;
  final String? title;
  final EdgeInsetsGeometry? padding;

  /// Convenience method to open this bottom sheet via [showModalBottomSheet].
  static Future<T?> show<T>({
    required BuildContext context,
    required Widget child,
    String? title,
    bool isScrollControlled = true,
    bool isDismissible = true,
  }) {
    return showModalBottomSheet<T>(
      context: context,
      isScrollControlled: isScrollControlled,
      isDismissible: isDismissible,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (_) => BottomSheetWrapper(title: title, child: child),
    );
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: padding ?? const EdgeInsets.all(AppSpacing.base),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Drag handle
            Center(
              child: Container(
                width: 40,
                height: 4,
                margin: const EdgeInsets.only(bottom: AppSpacing.md),
                decoration: BoxDecoration(
                  color: AppColors.neutralGray300,
                  borderRadius: AppRadius.full,
                ),
              ),
            ),
            if (title != null) ...[
              Text(
                title!,
                style: AppTypography.subtitle.copyWith(
                  color: AppColors.neutralGray900,
                ),
              ),
              const SizedBox(height: AppSpacing.base),
            ],
            child,
          ],
        ),
      ),
    );
  }
}
