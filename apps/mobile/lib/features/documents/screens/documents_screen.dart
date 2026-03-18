import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/design/components/components.dart';
import '../../../core/design/tokens/tokens.dart';
import '../models/template_definition.dart';

/// Lists all available HR document templates with category filtering and search.
class DocumentsScreen extends StatefulWidget {
  const DocumentsScreen({super.key});

  @override
  State<DocumentsScreen> createState() => _DocumentsScreenState();
}

class _DocumentsScreenState extends State<DocumentsScreen> {
  String _activeCategory = 'All';
  String _searchQuery = '';
  final _searchController = TextEditingController();

  static const _categories = ['All', 'Contracts', 'Policies', 'Letters', 'Forms'];

  List<TemplateDefinition> get _filtered {
    var results = TemplateDefinition.all;
    if (_activeCategory != 'All') {
      results = results.where((t) => t.category == _activeCategory).toList();
    }
    if (_searchQuery.isNotEmpty) {
      final q = _searchQuery.toLowerCase();
      results = results
          .where((t) =>
              t.name.toLowerCase().contains(q) ||
              t.description.toLowerCase().contains(q))
          .toList();
    }
    return results;
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _filtered;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Document Templates'),
      ),
      body: Column(
        children: [
          // Search bar
          Padding(
            padding: const EdgeInsets.fromLTRB(
              AppSpacing.base, AppSpacing.sm, AppSpacing.base, AppSpacing.sm,
            ),
            child: TextField(
              controller: _searchController,
              onChanged: (v) => setState(() => _searchQuery = v),
              decoration: InputDecoration(
                hintText: 'Search templates...',
                hintStyle: AppTypography.bodySmall.copyWith(
                  color: AppColors.neutralGray400,
                ),
                prefixIcon: const Icon(Icons.search, size: 20),
                filled: true,
                fillColor: AppColors.neutralGray100,
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.md, vertical: AppSpacing.sm,
                ),
                border: OutlineInputBorder(
                  borderRadius: AppRadius.md,
                  borderSide: BorderSide.none,
                ),
              ),
              style: AppTypography.bodySmall,
            ),
          ),

          // Category chips
          SizedBox(
            height: 40,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.base),
              itemCount: _categories.length,
              separatorBuilder: (_, _) => const SizedBox(width: AppSpacing.sm),
              itemBuilder: (context, index) {
                final cat = _categories[index];
                final isActive = cat == _activeCategory;
                return ChoiceChip(
                  label: Text(cat),
                  selected: isActive,
                  onSelected: (_) => setState(() => _activeCategory = cat),
                  selectedColor: AppColors.primaryNavy,
                  labelStyle: AppTypography.caption.copyWith(
                    color: isActive ? AppColors.neutralWhite : AppColors.neutralGray600,
                    fontWeight: isActive ? FontWeight.w600 : FontWeight.w400,
                  ),
                  backgroundColor: AppColors.neutralGray100,
                  shape: RoundedRectangleBorder(borderRadius: AppRadius.full),
                  side: BorderSide.none,
                );
              },
            ),
          ),

          const SizedBox(height: AppSpacing.sm),

          // Count
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.base),
            child: Align(
              alignment: Alignment.centerLeft,
              child: Text(
                '${filtered.length} template${filtered.length != 1 ? 's' : ''}'
                '${_activeCategory != 'All' ? ' in $_activeCategory' : ''}',
                style: AppTypography.caption.copyWith(
                  color: AppColors.neutralGray500,
                ),
              ),
            ),
          ),

          const SizedBox(height: AppSpacing.sm),

          // Template list
          Expanded(
            child: filtered.isEmpty
                ? const EmptyState(
                    icon: Icons.description_outlined,
                    heading: 'No templates found',
                    description: 'Try adjusting your search or filters.',
                  )
                : ListView.separated(
                    padding: const EdgeInsets.fromLTRB(
                      AppSpacing.base, 0, AppSpacing.base, AppSpacing.s2xl,
                    ),
                    itemCount: filtered.length,
                    separatorBuilder: (_, _) =>
                        const SizedBox(height: AppSpacing.sm),
                    itemBuilder: (context, index) =>
                        _TemplateCard(template: filtered[index]),
                  ),
          ),
        ],
      ),
    );
  }
}

class _TemplateCard extends StatelessWidget {
  const _TemplateCard({required this.template});

  final TemplateDefinition template;

  IconData get _icon => switch (template.category) {
        'Contracts' => Icons.description,
        'Policies' => Icons.menu_book,
        'Letters' => Icons.mail_outline,
        'Forms' => Icons.assignment_outlined,
        _ => Icons.description_outlined,
      };

  @override
  Widget build(BuildContext context) {
    return AppCard(
      variant: AppCardVariant.standard,
      onTap: () => context.push('/documents/${template.id}/preview'),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Icon
          Container(
            padding: const EdgeInsets.all(AppSpacing.sm),
            decoration: BoxDecoration(
              color: AppColors.primaryNavy.withValues(alpha: 0.08),
              borderRadius: AppRadius.md,
            ),
            child: Icon(_icon, size: 24, color: AppColors.primaryNavy),
          ),
          const SizedBox(width: AppSpacing.md),

          // Content
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  template.name,
                  style: AppTypography.bodyMedium.copyWith(
                    color: AppColors.neutralGray900,
                  ),
                ),
                const SizedBox(height: 2),
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
                      '${template.provisionsCount} provisions',
                      style: AppTypography.caption.copyWith(
                        color: AppColors.neutralGray400,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: AppSpacing.xs),
                Text(
                  template.description,
                  style: AppTypography.caption.copyWith(
                    color: AppColors.neutralGray600,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                if (template.complianceNotes.isNotEmpty) ...[
                  const SizedBox(height: AppSpacing.sm),
                  Container(
                    padding: const EdgeInsets.all(AppSpacing.sm),
                    decoration: BoxDecoration(
                      color: AppColors.neutralGray50,
                      borderRadius: AppRadius.sm,
                    ),
                    child: Row(
                      children: [
                        const Icon(
                          Icons.shield_outlined,
                          size: 14,
                          color: AppColors.primaryNavy,
                        ),
                        const SizedBox(width: AppSpacing.xs),
                        Expanded(
                          child: Text(
                            template.complianceNotes.first,
                            style: AppTypography.caption.copyWith(
                              color: AppColors.neutralGray600,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),

          const SizedBox(width: AppSpacing.sm),
          const Icon(
            Icons.chevron_right,
            size: 20,
            color: AppColors.neutralGray400,
          ),
        ],
      ),
    );
  }
}
