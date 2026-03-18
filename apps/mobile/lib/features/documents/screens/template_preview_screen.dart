import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/design/components/components.dart';
import '../../../core/design/tokens/tokens.dart';
import '../models/template_definition.dart';

/// Shows template details: description, compliance notes, required fields,
/// and a "Generate" button to fill in fields and produce the document.
class TemplatePreviewScreen extends StatelessWidget {
  const TemplatePreviewScreen({super.key, required this.templateId});

  final int templateId;

  @override
  Widget build(BuildContext context) {
    final template = TemplateDefinition.fromId(templateId);

    if (template == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Template')),
        body: const ErrorState(
          title: 'Template not found',
          description: 'The requested template could not be loaded.',
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(title: Text(template.name)),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.base),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Description
            AppCard(
              variant: AppCardVariant.standard,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: AppSpacing.sm, vertical: 2,
                        ),
                        decoration: BoxDecoration(
                          color: AppColors.neutralGray100,
                          borderRadius: AppRadius.full,
                        ),
                        child: Text(
                          template.category,
                          style: AppTypography.caption.copyWith(
                            color: AppColors.neutralGray500,
                          ),
                        ),
                      ),
                      const SizedBox(width: AppSpacing.sm),
                      Text(
                        '${template.provisionsCount} provisions linked',
                        style: AppTypography.caption.copyWith(
                          color: AppColors.neutralGray400,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  Text(
                    template.description,
                    style: AppTypography.body.copyWith(
                      color: AppColors.neutralGray700,
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: AppSpacing.base),

            // Compliance notes
            if (template.complianceNotes.isNotEmpty) ...[
              AppCard(
                variant: AppCardVariant.standard,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(
                          Icons.shield_outlined,
                          size: 18,
                          color: AppColors.primaryNavy,
                        ),
                        const SizedBox(width: AppSpacing.sm),
                        Text(
                          'Compliance Notes',
                          style: AppTypography.bodyMedium.copyWith(
                            color: AppColors.neutralGray900,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    ...template.complianceNotes.map(
                      (note) => Padding(
                        padding: const EdgeInsets.only(bottom: AppSpacing.xs),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Container(
                              margin: const EdgeInsets.only(top: 6),
                              width: 6,
                              height: 6,
                              decoration: const BoxDecoration(
                                color: AppColors.primaryNavy,
                                shape: BoxShape.circle,
                              ),
                            ),
                            const SizedBox(width: AppSpacing.sm),
                            Expanded(
                              child: Text(
                                note,
                                style: AppTypography.bodySmall.copyWith(
                                  color: AppColors.neutralGray600,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: AppSpacing.base),
            ],

            // Required fields
            AppCard(
              variant: AppCardVariant.standard,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Required Fields (${template.requiredFields.length})',
                    style: AppTypography.bodyMedium.copyWith(
                      color: AppColors.neutralGray900,
                    ),
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  Wrap(
                    spacing: AppSpacing.sm,
                    runSpacing: AppSpacing.xs,
                    children: template.requiredFields
                        .map((f) => Chip(
                              label: Text(
                                f.replaceAll('_', ' '),
                                style: AppTypography.caption,
                              ),
                              materialTapTargetSize:
                                  MaterialTapTargetSize.shrinkWrap,
                              visualDensity: VisualDensity.compact,
                            ))
                        .toList(),
                  ),
                ],
              ),
            ),

            if (template.optionalFields.isNotEmpty) ...[
              const SizedBox(height: AppSpacing.md),
              AppCard(
                variant: AppCardVariant.flat,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Optional Fields (${template.optionalFields.length})',
                      style: AppTypography.bodyMedium.copyWith(
                        color: AppColors.neutralGray600,
                      ),
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    Wrap(
                      spacing: AppSpacing.sm,
                      runSpacing: AppSpacing.xs,
                      children: template.optionalFields
                          .map((f) => Chip(
                                label: Text(
                                  f.replaceAll('_', ' '),
                                  style: AppTypography.caption.copyWith(
                                    color: AppColors.neutralGray500,
                                  ),
                                ),
                                materialTapTargetSize:
                                    MaterialTapTargetSize.shrinkWrap,
                                visualDensity: VisualDensity.compact,
                              ))
                          .toList(),
                    ),
                  ],
                ),
              ),
            ],

            const SizedBox(height: AppSpacing.xl),

            // Generate button
            SizedBox(
              width: double.infinity,
              child: AppButton(
                label: 'Generate Document',
                icon: Icons.edit_document,
                onPressed: () => context.push(
                  '/documents/$templateId/generate',
                ),
              ),
            ),

            const SizedBox(height: AppSpacing.s2xl),
          ],
        ),
      ),
    );
  }
}
