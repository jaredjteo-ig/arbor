import 'package:flutter/material.dart';
import '../tokens/tokens.dart';

/// A horizontal step indicator that marks completed, current, and upcoming
/// steps.
class StepIndicator extends StatelessWidget {
  const StepIndicator({
    super.key,
    required this.steps,
    required this.currentStep,
  });

  /// Labels for each step.
  final List<String> steps;

  /// Zero-based index of the current (active) step.
  final int currentStep;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        return Row(
          children: [
            for (int i = 0; i < steps.length; i++) ...[
              _StepDot(
                label: steps[i],
                index: i,
                isCompleted: i < currentStep,
                isCurrent: i == currentStep,
              ),
              if (i < steps.length - 1)
                Expanded(
                  child: Container(
                    height: 2,
                    color: i < currentStep
                        ? AppColors.primaryNavy
                        : AppColors.neutralGray300,
                  ),
                ),
            ],
          ],
        );
      },
    );
  }
}

class _StepDot extends StatelessWidget {
  const _StepDot({
    required this.label,
    required this.index,
    required this.isCompleted,
    required this.isCurrent,
  });

  final String label;
  final int index;
  final bool isCompleted;
  final bool isCurrent;

  @override
  Widget build(BuildContext context) {
    final Color circleColor;
    final Widget circleContent;

    if (isCompleted) {
      circleColor = AppColors.primaryNavy;
      circleContent = const Icon(
        Icons.check,
        size: 16,
        color: AppColors.neutralWhite,
      );
    } else if (isCurrent) {
      circleColor = AppColors.primaryNavy;
      circleContent = Text(
        '${index + 1}',
        style: AppTypography.caption.copyWith(
          color: AppColors.neutralWhite,
          fontWeight: FontWeight.w700,
        ),
      );
    } else {
      circleColor = AppColors.neutralGray300;
      circleContent = Text(
        '${index + 1}',
        style: AppTypography.caption.copyWith(
          color: AppColors.neutralGray600,
          fontWeight: FontWeight.w600,
        ),
      );
    }

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 28,
          height: 28,
          decoration: BoxDecoration(
            color: circleColor,
            shape: BoxShape.circle,
          ),
          alignment: Alignment.center,
          child: circleContent,
        ),
        const SizedBox(height: AppSpacing.xs),
        Text(
          label,
          style: AppTypography.caption.copyWith(
            color: (isCompleted || isCurrent)
                ? AppColors.primaryNavy
                : AppColors.neutralGray500,
            fontWeight: isCurrent ? FontWeight.w600 : FontWeight.w400,
          ),
          textAlign: TextAlign.center,
        ),
      ],
    );
  }
}
