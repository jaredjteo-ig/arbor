import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../tokens/tokens.dart';

/// A floating action button for voice input that triggers haptic feedback
/// on press.
class VoiceInputButton extends StatelessWidget {
  const VoiceInputButton({
    super.key,
    required this.onPressed,
    this.isListening = false,
    this.tooltip = 'Voice input',
  });

  final VoidCallback onPressed;
  final bool isListening;
  final String tooltip;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 56,
      height: 56,
      child: FloatingActionButton(
        onPressed: () {
          HapticFeedback.mediumImpact();
          onPressed();
        },
        backgroundColor:
            isListening ? AppColors.riskRed : AppColors.primaryNavy,
        foregroundColor: AppColors.neutralWhite,
        tooltip: tooltip,
        child: Icon(
          isListening ? Icons.stop : Icons.mic,
          size: 28,
        ),
      ),
    );
  }
}
