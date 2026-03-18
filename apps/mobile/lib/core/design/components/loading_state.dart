import 'package:flutter/material.dart';
import '../tokens/tokens.dart';

/// Skeleton shape variants for [LoadingState].
enum LoadingVariant { card, list, chat }

/// A loading placeholder that shows animated shimmer skeletons matching
/// common layout shapes (card, list rows, chat bubbles).
class LoadingState extends StatefulWidget {
  const LoadingState({
    super.key,
    this.variant = LoadingVariant.card,
    this.itemCount = 3,
  });

  final LoadingVariant variant;
  final int itemCount;

  @override
  State<LoadingState> createState() => _LoadingStateState();
}

class _LoadingStateState extends State<LoadingState>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);
    _animation = Tween<double>(begin: 0.3, end: 0.7).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _animation,
      builder: (context, _) {
        return switch (widget.variant) {
          LoadingVariant.card => _buildCardSkeleton(),
          LoadingVariant.list => _buildListSkeleton(),
          LoadingVariant.chat => _buildChatSkeleton(),
        };
      },
    );
  }

  Widget _shimmerBox({
    double? width,
    double height = 16,
    BorderRadius? borderRadius,
  }) {
    return Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        color: AppColors.neutralGray200.withValues(alpha: _animation.value),
        borderRadius: borderRadius ?? AppRadius.sm,
      ),
    );
  }

  Widget _buildCardSkeleton() {
    return Column(
      children: List.generate(widget.itemCount, (index) {
        return Padding(
          padding: const EdgeInsets.only(bottom: AppSpacing.base),
          child: Container(
            padding: const EdgeInsets.all(AppSpacing.base),
            decoration: BoxDecoration(
              color: AppColors.surfaceCard,
              borderRadius: AppRadius.lg,
              border: Border.all(color: AppColors.neutralGray200),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _shimmerBox(width: 180, height: 20),
                const SizedBox(height: AppSpacing.md),
                _shimmerBox(height: 14),
                const SizedBox(height: AppSpacing.sm),
                _shimmerBox(width: 240, height: 14),
              ],
            ),
          ),
        );
      }),
    );
  }

  Widget _buildListSkeleton() {
    return Column(
      children: List.generate(widget.itemCount, (index) {
        return Padding(
          padding: const EdgeInsets.only(bottom: AppSpacing.sm),
          child: Row(
            children: [
              _shimmerBox(
                width: 40,
                height: 40,
                borderRadius: AppRadius.full,
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _shimmerBox(width: 160, height: 14),
                    const SizedBox(height: AppSpacing.xs),
                    _shimmerBox(height: 12),
                  ],
                ),
              ),
            ],
          ),
        );
      }),
    );
  }

  Widget _buildChatSkeleton() {
    return Column(
      children: List.generate(widget.itemCount, (index) {
        final isRight = index.isOdd;
        return Align(
          alignment: isRight ? Alignment.centerRight : Alignment.centerLeft,
          child: Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.md),
            child: Container(
              width: 220,
              padding: const EdgeInsets.all(AppSpacing.md),
              decoration: BoxDecoration(
                color: AppColors.neutralGray100,
                borderRadius: AppRadius.lg,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _shimmerBox(height: 14),
                  const SizedBox(height: AppSpacing.sm),
                  _shimmerBox(width: 140, height: 14),
                ],
              ),
            ),
          ),
        );
      }),
    );
  }
}
