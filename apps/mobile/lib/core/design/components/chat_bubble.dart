import 'package:flutter/material.dart';
import '../tokens/tokens.dart';

/// Whether the bubble is from the user or the system/AI.
enum ChatBubbleVariant { user, system }

/// The risk tier that determines the left border color on system bubbles.
enum ChatBubbleRiskTier { green, amber, red }

/// A chat message bubble with user (right-aligned) and system (left-aligned)
/// variants.
///
/// System bubbles support an optional [riskTier] left border and a [sources]
/// widget slot for citations.
class ChatBubble extends StatelessWidget {
  const ChatBubble({
    super.key,
    required this.message,
    this.variant = ChatBubbleVariant.system,
    this.timestamp,
    this.riskTier,
    this.sources,
  });

  final String message;
  final ChatBubbleVariant variant;
  final String? timestamp;
  final ChatBubbleRiskTier? riskTier;

  /// Optional widget (e.g. a row of [SourceCitation] chips) shown below the
  /// message text in system bubbles.
  final Widget? sources;

  bool get _isUser => variant == ChatBubbleVariant.user;

  Color get _backgroundColor {
    return _isUser ? AppColors.primaryNavy : AppColors.neutralGray100;
  }

  Color get _textColor {
    return _isUser ? AppColors.neutralWhite : AppColors.neutralGray900;
  }

  Color? get _riskBorderColor {
    if (_isUser || riskTier == null) return null;
    return switch (riskTier!) {
      ChatBubbleRiskTier.green => AppColors.riskGreen,
      ChatBubbleRiskTier.amber => AppColors.riskAmber,
      ChatBubbleRiskTier.red => AppColors.riskRed,
    };
  }

  @override
  Widget build(BuildContext context) {
    final borderColor = _riskBorderColor;

    final decoration = BoxDecoration(
      color: _backgroundColor,
      borderRadius: _isUser
          ? const BorderRadius.only(
              topLeft: Radius.circular(16),
              topRight: Radius.circular(16),
              bottomLeft: Radius.circular(16),
              bottomRight: Radius.circular(4),
            )
          : const BorderRadius.only(
              topLeft: Radius.circular(4),
              topRight: Radius.circular(16),
              bottomLeft: Radius.circular(16),
              bottomRight: Radius.circular(16),
            ),
      border: borderColor != null
          ? Border(left: BorderSide(color: borderColor, width: 4))
          : null,
    );

    return Align(
      alignment: _isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.sizeOf(context).width * 0.8,
        ),
        child: Container(
          decoration: decoration,
          padding: const EdgeInsets.all(AppSpacing.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                message,
                style: AppTypography.body.copyWith(color: _textColor),
              ),
              if (sources != null) ...[
                const SizedBox(height: AppSpacing.sm),
                sources!,
              ],
              if (timestamp != null) ...[
                const SizedBox(height: AppSpacing.xs),
                Text(
                  timestamp!,
                  style: AppTypography.caption.copyWith(
                    color: _isUser
                        ? AppColors.neutralWhite.withValues(alpha: 0.7)
                        : AppColors.neutralGray400,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
