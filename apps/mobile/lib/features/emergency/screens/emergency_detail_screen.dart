import 'package:flutter/material.dart';

import '../../../core/design/components/components.dart';
import '../../../core/design/tokens/tokens.dart';
import 'emergency_screen.dart';

// ---------------------------------------------------------------------------
// Emergency Detail Screen
// ---------------------------------------------------------------------------

class EmergencyDetailScreen extends StatefulWidget {
  const EmergencyDetailScreen({super.key, required this.topicId});

  final String topicId;

  @override
  State<EmergencyDetailScreen> createState() => _EmergencyDetailScreenState();
}

class _EmergencyDetailScreenState extends State<EmergencyDetailScreen> {
  late final EmergencyTopic? _topic;
  late final List<bool> _documentChecked;

  @override
  void initState() {
    super.initState();
    _topic = findEmergencyTopic(widget.topicId);
    _documentChecked = _topic != null
        ? List<bool>.filled(_topic.documentsNeeded.length, false)
        : [];
  }

  @override
  Widget build(BuildContext context) {
    final topic = _topic;

    if (topic == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Not Found')),
        body: const Center(
          child: ErrorState(
            title: 'Emergency topic not found',
            description: 'The requested emergency guide could not be loaded.',
          ),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(title: Text(topic.title)),
      body: ListView(
        padding: const EdgeInsets.all(AppSpacing.base),
        children: [
          // Red header card
          _HeaderCard(topic: topic),
          const SizedBox(height: AppSpacing.lg),

          // Section 1: Immediate Obligations
          _ImmediateObligationsSection(steps: topic.immediateObligations),
          const SizedBox(height: AppSpacing.base),

          // Section 2: Documents checklist
          _DocumentsSection(
            documents: topic.documentsNeeded,
            checked: _documentChecked,
            onToggle: (index) {
              setState(() {
                _documentChecked[index] = !_documentChecked[index];
              });
            },
          ),
          const SizedBox(height: AppSpacing.base),

          // Section 3: Step-by-step process
          _ProcessStepsSection(steps: topic.processSteps),
          const SizedBox(height: AppSpacing.base),

          // Section 4: When to get help
          _WhenToGetHelpSection(items: topic.whenToGetHelp),
          const SizedBox(height: AppSpacing.xl),

          // Footer: Key provisions
          _KeyProvisionsFooter(provisions: topic.keyProvisions),
          const SizedBox(height: AppSpacing.base),

          // Connect to specialist button
          AppButton(
            label: 'Connect to Employment Law Specialist',
            onPressed: () {
              // Specialist connection flow
            },
            variant: AppButtonVariant.primary,
            icon: Icons.phone,
            fullWidth: true,
          ),
          const SizedBox(height: AppSpacing.xl),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Header card — red accent with icon and description
// ---------------------------------------------------------------------------

class _HeaderCard extends StatelessWidget {
  const _HeaderCard({required this.topic});

  final EmergencyTopic topic;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.lg),
      decoration: BoxDecoration(
        color: AppColors.riskRedBg,
        borderRadius: AppRadius.lg,
        border: Border.all(color: AppColors.riskRedBorder),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              color: AppColors.neutralWhite,
              borderRadius: AppRadius.md,
              border: Border.all(color: AppColors.riskRedBorder),
            ),
            child: Icon(
              topic.icon,
              color: AppColors.riskRed,
              size: 28,
            ),
          ),
          const SizedBox(width: AppSpacing.base),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  topic.title,
                  style: AppTypography.subtitle.copyWith(
                    color: AppColors.riskRed,
                  ),
                ),
                const SizedBox(height: AppSpacing.xs),
                Text(
                  topic.description,
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.neutralGray700,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Section 1: Immediate Obligations
// ---------------------------------------------------------------------------

class _ImmediateObligationsSection extends StatelessWidget {
  const _ImmediateObligationsSection({required this.steps});

  final List<EmergencyStep> steps;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      variant: AppCardVariant.flat,
      padding: EdgeInsets.zero,
      header: Row(
        children: [
          const Icon(Icons.priority_high, color: AppColors.riskRed, size: 22),
          const SizedBox(width: AppSpacing.sm),
          Text(
            'Your Immediate Obligations',
            style: AppTypography.subtitle.copyWith(
              color: AppColors.neutralGray900,
            ),
          ),
        ],
      ),
      child: Column(
        children: steps.map((step) {
          return Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.md),
            child: _ObligationStepTile(step: step),
          );
        }).toList(),
      ),
    );
  }
}

class _ObligationStepTile extends StatelessWidget {
  const _ObligationStepTile({required this.step});

  final EmergencyStep step;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Step number circle
        Container(
          width: 28,
          height: 28,
          decoration: const BoxDecoration(
            color: AppColors.riskRed,
            shape: BoxShape.circle,
          ),
          alignment: Alignment.center,
          child: Text(
            '${step.stepNumber}',
            style: AppTypography.bodySmall.copyWith(
              color: AppColors.neutralWhite,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
        const SizedBox(width: AppSpacing.md),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Action text
              Text(
                step.action,
                style: AppTypography.bodyMedium.copyWith(
                  color: AppColors.neutralGray900,
                ),
              ),
              const SizedBox(height: AppSpacing.xs),

              // Deadline badge
              RiskTierBadge(
                tier: RiskTier.red,
                label: step.deadline,
              ),
              const SizedBox(height: AppSpacing.xs),

              // Detail text
              Text(
                step.detail,
                style: AppTypography.bodySmall.copyWith(
                  color: AppColors.neutralGray500,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Section 2: Documents checklist
// ---------------------------------------------------------------------------

class _DocumentsSection extends StatelessWidget {
  const _DocumentsSection({
    required this.documents,
    required this.checked,
    required this.onToggle,
  });

  final List<String> documents;
  final List<bool> checked;
  final ValueChanged<int> onToggle;

  @override
  Widget build(BuildContext context) {
    final checkedCount = checked.where((v) => v).length;

    return AppCard(
      variant: AppCardVariant.flat,
      padding: EdgeInsets.zero,
      header: Row(
        children: [
          const Icon(Icons.folder_open, color: AppColors.primaryNavy, size: 22),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Text(
              'Documents You Need to Gather',
              style: AppTypography.subtitle.copyWith(
                color: AppColors.neutralGray900,
              ),
            ),
          ),
          Text(
            '$checkedCount/${documents.length}',
            style: AppTypography.caption.copyWith(
              color: checkedCount == documents.length
                  ? AppColors.riskGreen
                  : AppColors.neutralGray400,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
      child: Column(
        children: List.generate(documents.length, (index) {
          return CheckboxListTile(
            value: checked[index],
            onChanged: (_) => onToggle(index),
            title: Text(
              documents[index],
              style: AppTypography.bodySmall.copyWith(
                color: checked[index]
                    ? AppColors.neutralGray400
                    : AppColors.neutralGray800,
                decoration:
                    checked[index] ? TextDecoration.lineThrough : null,
              ),
            ),
            activeColor: AppColors.riskGreen,
            controlAffinity: ListTileControlAffinity.leading,
            contentPadding: EdgeInsets.zero,
            dense: true,
            visualDensity: VisualDensity.compact,
          );
        }),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Section 3: Step-by-step process (timeline stepper)
// ---------------------------------------------------------------------------

class _ProcessStepsSection extends StatelessWidget {
  const _ProcessStepsSection({required this.steps});

  final List<EmergencyStep> steps;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      variant: AppCardVariant.flat,
      padding: EdgeInsets.zero,
      header: Row(
        children: [
          const Icon(Icons.timeline, color: AppColors.primaryNavy, size: 22),
          const SizedBox(width: AppSpacing.sm),
          Text(
            'Step-by-Step Process',
            style: AppTypography.subtitle.copyWith(
              color: AppColors.neutralGray900,
            ),
          ),
        ],
      ),
      child: Column(
        children: List.generate(steps.length, (index) {
          final step = steps[index];
          final isLast = index == steps.length - 1;
          return _TimelineStep(step: step, isLast: isLast);
        }),
      ),
    );
  }
}

class _TimelineStep extends StatelessWidget {
  const _TimelineStep({required this.step, required this.isLast});

  final EmergencyStep step;
  final bool isLast;

  @override
  Widget build(BuildContext context) {
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Timeline column: circle + vertical line
          SizedBox(
            width: 28,
            child: Column(
              children: [
                // Step circle
                Container(
                  width: 28,
                  height: 28,
                  decoration: BoxDecoration(
                    color: AppColors.primaryNavy,
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: AppColors.primaryNavy,
                      width: 2,
                    ),
                  ),
                  alignment: Alignment.center,
                  child: Text(
                    '${step.stepNumber}',
                    style: AppTypography.caption.copyWith(
                      color: AppColors.neutralWhite,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                // Vertical line
                if (!isLast)
                  Expanded(
                    child: Container(
                      width: 2,
                      color: AppColors.neutralGray200,
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(width: AppSpacing.md),

          // Step content
          Expanded(
            child: Padding(
              padding: EdgeInsets.only(
                bottom: isLast ? 0 : AppSpacing.base,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    step.action,
                    style: AppTypography.bodyMedium.copyWith(
                      color: AppColors.neutralGray900,
                    ),
                  ),
                  const SizedBox(height: AppSpacing.xs),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.sm,
                      vertical: 2,
                    ),
                    decoration: BoxDecoration(
                      color: AppColors.neutralGray100,
                      borderRadius: AppRadius.sm,
                    ),
                    child: Text(
                      step.deadline,
                      style: AppTypography.caption.copyWith(
                        color: AppColors.neutralGray600,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  const SizedBox(height: AppSpacing.xs),
                  Text(
                    step.detail,
                    style: AppTypography.bodySmall.copyWith(
                      color: AppColors.neutralGray500,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Section 4: When to get professional help
// ---------------------------------------------------------------------------

class _WhenToGetHelpSection extends StatelessWidget {
  const _WhenToGetHelpSection({required this.items});

  final List<String> items;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      variant: AppCardVariant.flat,
      padding: EdgeInsets.zero,
      header: Row(
        children: [
          const Icon(
            Icons.warning_amber_rounded,
            color: AppColors.riskAmber,
            size: 22,
          ),
          const SizedBox(width: AppSpacing.sm),
          Text(
            'When to Get Professional Help',
            style: AppTypography.subtitle.copyWith(
              color: AppColors.neutralGray900,
            ),
          ),
        ],
      ),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(AppSpacing.md),
        decoration: BoxDecoration(
          color: AppColors.riskAmberBg,
          borderRadius: AppRadius.md,
          border: Border.all(color: AppColors.riskAmberBorder),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: items.map((item) {
            return Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.sm),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Padding(
                    padding: EdgeInsets.only(top: 2),
                    child: Icon(
                      Icons.warning,
                      color: AppColors.riskAmber,
                      size: 18,
                    ),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: Text(
                      item,
                      style: AppTypography.bodySmall.copyWith(
                        color: AppColors.neutralGray800,
                      ),
                    ),
                  ),
                ],
              ),
            );
          }).toList(),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Footer: Key provisions + specialist button
// ---------------------------------------------------------------------------

class _KeyProvisionsFooter extends StatelessWidget {
  const _KeyProvisionsFooter({required this.provisions});

  final List<String> provisions;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Key Provisions',
          style: AppTypography.caption.copyWith(
            color: AppColors.neutralGray500,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.5,
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        Wrap(
          spacing: AppSpacing.sm,
          runSpacing: AppSpacing.sm,
          children: provisions.map((provision) {
            return SourceCitation(
              label: provision,
              authorityLevel: AuthorityLevel.statutory,
            );
          }).toList(),
        ),
      ],
    );
  }
}
