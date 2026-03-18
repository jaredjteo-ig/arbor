import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/design/components/components.dart';
import '../../../core/design/tokens/tokens.dart';

/// Wraps calculator results in an [AppCard] with source citations
/// and an "Ask about this" link.
class CalculatorResultCard extends StatelessWidget {
  const CalculatorResultCard({
    super.key,
    required this.title,
    required this.child,
    this.citations = const [],
  });

  final String title;
  final Widget child;

  /// Source citations to display below the results.
  final List<({String label, AuthorityLevel level})> citations;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      variant: AppCardVariant.flat,
      header: Text(
        title,
        style: AppTypography.subtitle.copyWith(
          color: AppColors.primaryNavy,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          child,
          if (citations.isNotEmpty) ...[
            const SizedBox(height: AppSpacing.base),
            Text(
              'Sources',
              style: AppTypography.caption.copyWith(
                color: AppColors.neutralGray500,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: AppSpacing.xs),
            Wrap(
              spacing: AppSpacing.sm,
              runSpacing: AppSpacing.sm,
              children: [
                for (final c in citations)
                  SourceCitation(
                    label: c.label,
                    authorityLevel: c.level,
                  ),
              ],
            ),
          ],
          const SizedBox(height: AppSpacing.md),
          InkWell(
            onTap: () => context.go('/advisory'),
            borderRadius: AppRadius.sm,
            child: Padding(
              padding: const EdgeInsets.symmetric(
                vertical: AppSpacing.xs,
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.chat_outlined,
                    size: 18,
                    color: AppColors.secondaryTeal,
                  ),
                  const SizedBox(width: AppSpacing.xs),
                  Text(
                    'Ask about this',
                    style: AppTypography.bodySmall.copyWith(
                      color: AppColors.secondaryTeal,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
