import 'package:flutter/material.dart';

import '../../../core/design/components/components.dart';

/// Help and support screen with FAQs, contact information, and guides.
class HelpScreen extends StatelessWidget {
  const HelpScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Help')),
      body: const EmptyState(
        icon: Icons.help_outline,
        heading: 'Help & Support',
        description:
            'FAQs, user guides, and contact information will appear here.',
      ),
    );
  }
}
