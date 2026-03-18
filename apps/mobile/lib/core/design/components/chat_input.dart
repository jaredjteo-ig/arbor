import 'package:flutter/material.dart';
import '../tokens/tokens.dart';

/// A chat input bar with a text field, optional voice button, send button,
/// and suggestion chips.
class ChatInput extends StatefulWidget {
  const ChatInput({
    super.key,
    required this.onSend,
    this.onVoicePressed,
    this.suggestions,
    this.onSuggestionSelected,
    this.hintText = 'Ask a question...',
    this.enabled = true,
  });

  final ValueChanged<String> onSend;
  final VoidCallback? onVoicePressed;

  /// Optional suggestion chips displayed above the input row.
  final List<String>? suggestions;
  final ValueChanged<String>? onSuggestionSelected;
  final String hintText;
  final bool enabled;

  @override
  State<ChatInput> createState() => _ChatInputState();
}

class _ChatInputState extends State<ChatInput> {
  final _controller = TextEditingController();
  bool _hasText = false;

  @override
  void initState() {
    super.initState();
    _controller.addListener(_onTextChanged);
  }

  void _onTextChanged() {
    final hasText = _controller.text.trim().isNotEmpty;
    if (hasText != _hasText) {
      setState(() => _hasText = hasText);
    }
  }

  void _handleSend() {
    final text = _controller.text.trim();
    if (text.isEmpty) return;
    widget.onSend(text);
    _controller.clear();
  }

  @override
  void dispose() {
    _controller.removeListener(_onTextChanged);
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (widget.suggestions != null && widget.suggestions!.isNotEmpty)
          SizedBox(
            height: AppTouch.minTarget,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.base),
              itemCount: widget.suggestions!.length,
              separatorBuilder: (_, _) => const SizedBox(width: AppSpacing.sm),
              itemBuilder: (context, index) {
                final suggestion = widget.suggestions![index];
                return ActionChip(
                  label: Text(
                    suggestion,
                    style: AppTypography.bodySmall.copyWith(
                      color: AppColors.primaryNavy,
                    ),
                  ),
                  backgroundColor: AppColors.neutralGray100,
                  side: const BorderSide(color: AppColors.neutralGray200),
                  shape: RoundedRectangleBorder(borderRadius: AppRadius.full),
                  onPressed: () => widget.onSuggestionSelected?.call(suggestion),
                );
              },
            ),
          ),
        Padding(
          padding: const EdgeInsets.all(AppSpacing.sm),
          child: Row(
            children: [
              if (widget.onVoicePressed != null)
                IconButton(
                  onPressed: widget.enabled ? widget.onVoicePressed : null,
                  icon: const Icon(Icons.mic),
                  color: AppColors.primaryNavy,
                  constraints: const BoxConstraints(
                    minWidth: AppTouch.minTarget,
                    minHeight: AppTouch.minTarget,
                  ),
                  tooltip: 'Voice input',
                ),
              Expanded(
                child: TextField(
                  controller: _controller,
                  enabled: widget.enabled,
                  textInputAction: TextInputAction.send,
                  onSubmitted: (_) => _handleSend(),
                  autocorrect: true,
                  style: AppTypography.body.copyWith(
                    color: AppColors.neutralGray900,
                  ),
                  decoration: InputDecoration(
                    hintText: widget.hintText,
                    hintStyle: AppTypography.body.copyWith(
                      color: AppColors.neutralGray400,
                    ),
                    contentPadding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.base,
                      vertical: AppSpacing.md,
                    ),
                    isDense: true,
                  ),
                ),
              ),
              const SizedBox(width: AppSpacing.xs),
              IconButton(
                onPressed: (_hasText && widget.enabled) ? _handleSend : null,
                icon: const Icon(Icons.send),
                color: AppColors.primaryNavy,
                constraints: const BoxConstraints(
                  minWidth: AppTouch.minTarget,
                  minHeight: AppTouch.minTarget,
                ),
                tooltip: 'Send',
              ),
            ],
          ),
        ),
      ],
    );
  }
}
