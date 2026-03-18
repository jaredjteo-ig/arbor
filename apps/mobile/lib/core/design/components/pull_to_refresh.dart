import 'package:flutter/material.dart';
import '../tokens/tokens.dart';

/// A convenience wrapper around [RefreshIndicator] with design-system styling.
class PullToRefresh extends StatelessWidget {
  const PullToRefresh({
    super.key,
    required this.onRefresh,
    required this.child,
  });

  final Future<void> Function() onRefresh;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: onRefresh,
      color: AppColors.primaryNavy,
      backgroundColor: AppColors.surfaceCard,
      displacement: AppSpacing.s3xl,
      child: child,
    );
  }
}
