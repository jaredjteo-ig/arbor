import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../core/design/components/components.dart';
import '../../../core/design/tokens/tokens.dart';
import '../models/template_definition.dart';

/// Form screen that collects field values and generates a document
/// by calling the backend API.
class DocumentGenerateScreen extends StatefulWidget {
  const DocumentGenerateScreen({super.key, required this.templateId});

  final int templateId;

  @override
  State<DocumentGenerateScreen> createState() => _DocumentGenerateScreenState();
}

class _DocumentGenerateScreenState extends State<DocumentGenerateScreen> {
  late final TemplateDefinition? _template;
  final Map<String, TextEditingController> _controllers = {};
  String? _error;
  bool _generating = false;
  String? _generatedContent;
  String? _generatedTitle;

  @override
  void initState() {
    super.initState();
    _template = TemplateDefinition.fromId(widget.templateId);
    if (_template != null) {
      for (final f in [..._template.requiredFields, ..._template.optionalFields]) {
        _controllers[f] = TextEditingController();
      }
    }
  }

  @override
  void dispose() {
    for (final c in _controllers.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _generate() async {
    final template = _template;
    if (template == null) return;

    // Validate required fields
    final missing = template.requiredFields
        .where((f) => (_controllers[f]?.text.trim() ?? '').isEmpty)
        .toList();
    if (missing.isNotEmpty) {
      setState(() {
        _error =
            'Please fill in: ${missing.map((f) => f.replaceAll('_', ' ')).join(', ')}';
      });
      return;
    }

    setState(() {
      _error = null;
      _generating = true;
    });

    // Simulate API call — in production this would call documentsApi.generate()
    await Future<void>.delayed(const Duration(milliseconds: 500));

    // Build a simple preview by listing field values
    final fields = <String, String>{};
    for (final entry in _controllers.entries) {
      if (entry.value.text.trim().isNotEmpty) {
        fields[entry.key] = entry.value.text.trim();
      }
    }

    final preview = StringBuffer()
      ..writeln(template.name.toUpperCase())
      ..writeln()
      ..writeln('Generated with the following details:')
      ..writeln();
    for (final entry in fields.entries) {
      preview.writeln(
        '${entry.key.replaceAll('_', ' ').toUpperCase()}: ${entry.value}',
      );
    }
    preview
      ..writeln()
      ..writeln('---')
      ..writeln('This document was generated based on the ${template.name} template.')
      ..writeln(
        'Please review all details before use. Compliance notes:',
      );
    for (final note in template.complianceNotes) {
      preview.writeln('• $note');
    }

    setState(() {
      _generating = false;
      _generatedContent = preview.toString();
      _generatedTitle = template.name;
    });
  }

  void _copyToClipboard() {
    if (_generatedContent == null) return;
    Clipboard.setData(ClipboardData(text: _generatedContent!));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Copied to clipboard')),
    );
  }

  String _fieldLabel(String name) {
    return name
        .replaceAll('_', ' ')
        .split(' ')
        .map((w) => w.isEmpty ? w : '${w[0].toUpperCase()}${w.substring(1)}')
        .join(' ');
  }

  @override
  Widget build(BuildContext context) {
    final template = _template;

    if (template == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Generate')),
        body: const ErrorState(
          title: 'Template not found',
          description: 'The requested template could not be loaded.',
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(title: Text('Generate: ${template.name}')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.base),
        child: _generatedContent != null
            ? _buildResult(context)
            : _buildForm(context, template),
      ),
    );
  }

  Widget _buildForm(BuildContext context, TemplateDefinition template) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Compliance reminder
        if (template.complianceNotes.isNotEmpty)
          Container(
            margin: const EdgeInsets.only(bottom: AppSpacing.base),
            padding: const EdgeInsets.all(AppSpacing.md),
            decoration: BoxDecoration(
              color: AppColors.primaryNavy.withValues(alpha: 0.05),
              borderRadius: AppRadius.md,
            ),
            child: Row(
              children: [
                const Icon(Icons.shield_outlined,
                    size: 16, color: AppColors.primaryNavy),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: Text(
                    template.complianceNotes.first,
                    style: AppTypography.caption.copyWith(
                      color: AppColors.neutralGray600,
                    ),
                  ),
                ),
              ],
            ),
          ),

        // Error
        if (_error != null)
          Container(
            margin: const EdgeInsets.only(bottom: AppSpacing.base),
            padding: const EdgeInsets.all(AppSpacing.md),
            decoration: BoxDecoration(
              color: AppColors.riskRedBg,
              borderRadius: AppRadius.md,
              border: Border.all(color: AppColors.riskRedBorder),
            ),
            child: Text(
              _error!,
              style: AppTypography.bodySmall.copyWith(color: AppColors.riskRed),
            ),
          ),

        // Required fields
        Text(
          'Required Fields',
          style: AppTypography.bodyMedium.copyWith(
            color: AppColors.neutralGray900,
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        ...template.requiredFields.map(
          (f) => Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.md),
            child: AppInput(
              label: '${_fieldLabel(f)} *',
              controller: _controllers[f],
              hintText: 'Enter ${_fieldLabel(f).toLowerCase()}',
            ),
          ),
        ),

        // Optional fields
        if (template.optionalFields.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.sm),
          Text(
            'Optional Fields',
            style: AppTypography.bodyMedium.copyWith(
              color: AppColors.neutralGray600,
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          ...template.optionalFields.map(
            (f) => Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.md),
              child: AppInput(
                label: _fieldLabel(f),
                controller: _controllers[f],
                hintText: 'Enter ${_fieldLabel(f).toLowerCase()}',
              ),
            ),
          ),
        ],

        // Generate button
        const SizedBox(height: AppSpacing.md),
        SizedBox(
          width: double.infinity,
          child: AppButton(
            label: _generating ? 'Generating...' : 'Generate Document',
            icon: Icons.edit_document,
            onPressed: _generating ? null : _generate,
          ),
        ),

        const SizedBox(height: AppSpacing.s2xl),
      ],
    );
  }

  Widget _buildResult(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Title and actions
        Row(
          children: [
            Expanded(
              child: Text(
                _generatedTitle ?? 'Generated Document',
                style: AppTypography.title.copyWith(
                  color: AppColors.neutralGray900,
                ),
              ),
            ),
            IconButton(
              icon: const Icon(Icons.copy, size: 20),
              onPressed: _copyToClipboard,
              tooltip: 'Copy to clipboard',
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.base),

        // Content
        AppCard(
          variant: AppCardVariant.elevated,
          child: SelectableText(
            _generatedContent!,
            style: AppTypography.bodySmall.copyWith(
              fontFamily: 'monospace',
              color: AppColors.neutralGray700,
              height: 1.6,
            ),
          ),
        ),

        const SizedBox(height: AppSpacing.xl),

        // Actions
        Row(
          children: [
            Expanded(
              child: AppButton(
                label: 'Generate Another',
                variant: AppButtonVariant.outlined,
                onPressed: () => setState(() {
                  _generatedContent = null;
                  _generatedTitle = null;
                  _error = null;
                }),
              ),
            ),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: AppButton(
                label: 'Copy Document',
                icon: Icons.copy,
                onPressed: _copyToClipboard,
              ),
            ),
          ],
        ),

        const SizedBox(height: AppSpacing.s2xl),
      ],
    );
  }
}
