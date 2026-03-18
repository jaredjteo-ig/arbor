import 'package:flutter/material.dart';
import '../tokens/tokens.dart';

/// The authority level of a cited source.
enum AuthorityLevel {
  /// Statutory / legal requirement (blue).
  statutory,

  /// Tripartite or industry guideline (amber).
  guideline,

  /// Recommended best practice (green).
  bestPractice,
}

/// A chip-like citation badge that shows the authority level of a source
/// reference.
class SourceCitation extends StatelessWidget {
  const SourceCitation({
    super.key,
    required this.label,
    this.authorityLevel = AuthorityLevel.bestPractice,
    this.onTap,
  });

  final String label;
  final AuthorityLevel authorityLevel;
  final VoidCallback? onTap;

  Color get _borderColor {
    return switch (authorityLevel) {
      AuthorityLevel.statutory => AppColors.authorityStatutory,
      AuthorityLevel.guideline => AppColors.authorityGuideline,
      AuthorityLevel.bestPractice => AppColors.authorityBestPractice,
    };
  }

  Color get _backgroundColor {
    return switch (authorityLevel) {
      AuthorityLevel.statutory => AppColors.authorityStatutoryBg,
      AuthorityLevel.guideline => AppColors.authorityGuidelineBg,
      AuthorityLevel.bestPractice => AppColors.authorityBestPracticeBg,
    };
  }

  Color get _textColor {
    return switch (authorityLevel) {
      AuthorityLevel.statutory => AppColors.authorityStatutory,
      AuthorityLevel.guideline => AppColors.authorityGuideline,
      AuthorityLevel.bestPractice => AppColors.authorityBestPractice,
    };
  }

  @override
  Widget build(BuildContext context) {
    final chip = Container(
      constraints: const BoxConstraints(minHeight: AppTouch.minTarget),
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.md,
        vertical: AppSpacing.xs,
      ),
      decoration: BoxDecoration(
        color: _backgroundColor,
        borderRadius: AppRadius.full,
        border: Border.all(color: _borderColor, width: 1.5),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.description_outlined, size: 16, color: _textColor),
          const SizedBox(width: AppSpacing.xs),
          Flexible(
            child: Text(
              label,
              style: AppTypography.caption.copyWith(
                color: _textColor,
                fontWeight: FontWeight.w600,
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );

    if (onTap != null) {
      return GestureDetector(onTap: onTap, child: chip);
    }

    return chip;
  }
}
