import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/design/components/components.dart';
import '../../../core/design/tokens/tokens.dart';
import '../models/calculator_definition.dart';

/// Lists all available HR calculators as tappable cards.
class CalculatorsScreen extends StatelessWidget {
  const CalculatorsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('HR Calculators')),
      body: ListView.builder(
        padding: const EdgeInsets.all(AppSpacing.base),
        itemCount: CalculatorDefinition.all.length + 1,
        itemBuilder: (context, index) {
          if (index == 0) {
            return Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.base),
              child: Text(
                'Deterministic calculations based on current Singapore '
                'employment regulations.',
                style: AppTypography.body.copyWith(
                  color: AppColors.neutralGray600,
                ),
              ),
            );
          }
          final calc = CalculatorDefinition.all[index - 1];
          return Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.md),
            child: _CalculatorCard(definition: calc),
          );
        },
      ),
    );
  }
}

/// A single calculator card in the hub list.
class _CalculatorCard extends StatelessWidget {
  const _CalculatorCard({required this.definition});

  final CalculatorDefinition definition;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      variant: AppCardVariant.standard,
      onTap: () => context.push('/calculators/${definition.routeSlug}'),
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.base,
        vertical: AppSpacing.md,
      ),
      child: Row(
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              color: AppColors.primaryNavy.withValues(alpha: 0.08),
              borderRadius: AppRadius.md,
            ),
            child: Icon(
              definition.icon,
              color: AppColors.primaryNavy,
              size: 24,
            ),
          ),
          const SizedBox(width: AppSpacing.base),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  definition.name,
                  style: AppTypography.bodyBold.copyWith(
                    color: AppColors.neutralGray900,
                  ),
                ),
                const SizedBox(height: AppSpacing.xs),
                Text(
                  definition.description,
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.neutralGray500,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          const Icon(
            Icons.chevron_right,
            color: AppColors.neutralGray400,
          ),
        ],
      ),
    );
  }
}
