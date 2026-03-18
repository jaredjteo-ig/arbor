import 'package:flutter/material.dart';
import '../tokens/tokens.dart';

/// Callback shape for feedback submission.
typedef FeedbackCallback = void Function(bool isPositive, String? text);

/// Thumbs-up / thumbs-down feedback widget.
///
/// Selecting thumbs-down expands a text field for the user to explain
/// what was wrong.
class FeedbackButtons extends StatefulWidget {
  const FeedbackButtons({
    super.key,
    required this.onFeedback,
    this.promptText = 'Was this helpful?',
  });

  final FeedbackCallback onFeedback;
  final String promptText;

  @override
  State<FeedbackButtons> createState() => _FeedbackButtonsState();
}

class _FeedbackButtonsState extends State<FeedbackButtons> {
  bool? _rating; // null = no selection, true = positive, false = negative
  bool _submitted = false;
  final _textController = TextEditingController();

  void _select(bool isPositive) {
    if (_submitted) return;
    setState(() => _rating = isPositive);
    if (isPositive) {
      _submit();
    }
  }

  void _submit() {
    setState(() => _submitted = true);
    widget.onFeedback(
      _rating!,
      _rating == false ? _textController.text : null,
    );
  }

  @override
  void dispose() {
    _textController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_submitted) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
        child: Text(
          'Thank you for your feedback',
          style: AppTypography.bodySmall.copyWith(
            color: AppColors.neutralGray500,
          ),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              widget.promptText,
              style: AppTypography.bodySmall.copyWith(
                color: AppColors.neutralGray600,
              ),
            ),
            const SizedBox(width: AppSpacing.md),
            IconButton(
              onPressed: () => _select(true),
              icon: Icon(
                _rating == true ? Icons.thumb_up : Icons.thumb_up_outlined,
              ),
              color: _rating == true
                  ? AppColors.semanticSuccess
                  : AppColors.neutralGray500,
              constraints: const BoxConstraints(
                minWidth: AppTouch.minTarget,
                minHeight: AppTouch.minTarget,
              ),
              tooltip: 'Yes',
            ),
            IconButton(
              onPressed: () => _select(false),
              icon: Icon(
                _rating == false
                    ? Icons.thumb_down
                    : Icons.thumb_down_outlined,
              ),
              color: _rating == false
                  ? AppColors.semanticError
                  : AppColors.neutralGray500,
              constraints: const BoxConstraints(
                minWidth: AppTouch.minTarget,
                minHeight: AppTouch.minTarget,
              ),
              tooltip: 'No',
            ),
          ],
        ),
        if (_rating == false) ...[
          const SizedBox(height: AppSpacing.sm),
          TextField(
            controller: _textController,
            maxLines: 3,
            style: AppTypography.bodySmall.copyWith(
              color: AppColors.neutralGray900,
            ),
            decoration: InputDecoration(
              hintText: 'What was wrong?',
              hintStyle: AppTypography.bodySmall.copyWith(
                color: AppColors.neutralGray400,
              ),
              contentPadding: const EdgeInsets.all(AppSpacing.md),
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(
              onPressed: _submit,
              style: TextButton.styleFrom(
                foregroundColor: AppColors.primaryNavy,
                minimumSize: const Size(
                  AppTouch.minTarget,
                  AppTouch.minTarget,
                ),
              ),
              child: const Text('Submit'),
            ),
          ),
        ],
      ],
    );
  }
}
