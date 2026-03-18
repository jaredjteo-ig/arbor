import 'package:flutter/material.dart';

import '../../../core/design/components/components.dart';

/// Detail screen for a specific compliance category.
class ComplianceCategoryScreen extends StatelessWidget {
  const ComplianceCategoryScreen({super.key, required this.category});

  /// The category slug from the route, e.g. "employment-act", "cpf", "tafep".
  final String category;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(_title)),
      body: EmptyState(
        icon: Icons.verified_user_outlined,
        heading: _title,
        description:
            'Detailed compliance checks for this category will appear here.',
      ),
    );
  }

  String get _title {
    if (category.isEmpty) return 'Compliance';
    // Convert slug to title case, e.g. "employment-act" → "Employment Act".
    return category
        .split('-')
        .map(
          (word) =>
              word.isEmpty
                  ? ''
                  : '${word[0].toUpperCase()}${word.substring(1)}',
        )
        .join(' ');
  }
}
