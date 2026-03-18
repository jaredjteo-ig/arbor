import 'package:flutter/material.dart';

import '../../../core/design/tokens/tokens.dart';
import '../../../core/design/components/components.dart';

/// Company profile screen with section-based editing.
class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  // Editing state per section
  String? _editingSection;

  // Demo company data
  final String _name = 'Horizon Tech Pte Ltd';
  final String _uen = '202301234A';
  final String _industry = 'Technology';
  final String _incDate = '15 Jan 2023';
  final int _employeeCount = 45;
  final bool _hasForeignWorkers = true;
  final String _email = 'hr@horizontech.sg';
  final String _phone = '+65 6123 4567';
  final String _address = '1 Raffles Place, #20-01, Singapore 048616';

  // Completeness calculation
  int get _completeness {
    int filled = 0;
    int total = 9;
    if (_name.isNotEmpty) filled++;
    if (_uen.isNotEmpty) filled++;
    if (_industry.isNotEmpty) filled++;
    if (_incDate.isNotEmpty) filled++;
    if (_employeeCount > 0) filled++;
    filled++; // foreign workers always has a value
    if (_email.isNotEmpty) filled++;
    if (_phone.isNotEmpty) filled++;
    if (_address.isNotEmpty) filled++;
    return ((filled / total) * 100).round();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Company Profile')),
      body: ListView(
        padding: const EdgeInsets.all(AppSpacing.base),
        children: [
          // Completeness indicator
          AppCard(
            variant: AppCardVariant.elevated,
            child: Row(
              children: [
                SizedBox(
                  width: 56,
                  height: 56,
                  child: Stack(
                    alignment: Alignment.center,
                    children: [
                      CircularProgressIndicator(
                        value: _completeness / 100,
                        backgroundColor: AppColors.neutralGray200,
                        color: _completeness == 100
                            ? AppColors.riskGreen
                            : AppColors.primaryNavy,
                        strokeWidth: 5,
                      ),
                      Text(
                        '$_completeness%',
                        style: AppTypography.bodyMedium.copyWith(
                          color: AppColors.neutralGray900,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: AppSpacing.base),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Profile Completeness',
                        style: AppTypography.subtitle.copyWith(
                          color: AppColors.neutralGray900,
                        ),
                      ),
                      const SizedBox(height: AppSpacing.xs),
                      Text(
                        _completeness == 100
                            ? 'All sections are complete.'
                            : 'Complete your profile for accurate compliance checks.',
                        style: AppTypography.bodySmall.copyWith(
                          color: AppColors.neutralGray500,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: AppSpacing.base),

          // Company Details section
          _buildSection(
            sectionId: 'details',
            title: 'Company Details',
            icon: Icons.business,
            fields: [
              _FieldRow('Company Name', _name),
              _FieldRow('UEN', _uen),
              _FieldRow('Industry', _industry),
              _FieldRow('Incorporation Date', _incDate),
            ],
          ),

          const SizedBox(height: AppSpacing.md),

          // Workforce section
          _buildSection(
            sectionId: 'workforce',
            title: 'Workforce',
            icon: Icons.people,
            fields: [
              _FieldRow('Employee Count', '$_employeeCount'),
              _FieldRow(
                'Foreign Workers',
                _hasForeignWorkers ? 'Yes' : 'No',
              ),
            ],
          ),

          const SizedBox(height: AppSpacing.md),

          // Contact section
          _buildSection(
            sectionId: 'contact',
            title: 'Contact Information',
            icon: Icons.contact_mail,
            fields: [
              _FieldRow('Email', _email),
              _FieldRow('Phone', _phone),
              _FieldRow('Address', _address),
            ],
          ),

          const SizedBox(height: AppSpacing.base),

          // Profile change history
          AppCard(
            variant: AppCardVariant.flat,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Recent Changes',
                  style: AppTypography.subtitle.copyWith(
                    color: AppColors.neutralGray900,
                  ),
                ),
                const SizedBox(height: AppSpacing.md),
                _ChangeRow('Employee count updated', '45 → 45', '12 Mar 2026'),
                _ChangeRow('Profile created', '—', '15 Jan 2023'),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSection({
    required String sectionId,
    required String title,
    required IconData icon,
    required List<_FieldRow> fields,
  }) {
    final isEditing = _editingSection == sectionId;
    return AppCard(
      variant: AppCardVariant.standard,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 20, color: AppColors.primaryNavy),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Text(
                  title,
                  style: AppTypography.subtitle.copyWith(
                    color: AppColors.neutralGray900,
                  ),
                ),
              ),
              if (!isEditing)
                TextButton.icon(
                  onPressed: () => setState(() => _editingSection = sectionId),
                  icon: const Icon(Icons.edit, size: 16),
                  label: const Text('Edit'),
                  style: TextButton.styleFrom(
                    foregroundColor: AppColors.primaryNavy,
                    textStyle: AppTypography.bodySmall,
                  ),
                )
              else
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextButton(
                      onPressed: () =>
                          setState(() => _editingSection = null),
                      child: const Text('Cancel'),
                    ),
                    const SizedBox(width: AppSpacing.sm),
                    TextButton(
                      onPressed: () {
                        setState(() => _editingSection = null);
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text('Section saved'),
                            duration: Duration(seconds: 2),
                          ),
                        );
                      },
                      style: TextButton.styleFrom(
                        foregroundColor: AppColors.riskGreen,
                      ),
                      child: const Text('Save'),
                    ),
                  ],
                ),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          ...fields.map(
            (f) => Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.md),
              child: isEditing
                  ? TextField(
                      controller: TextEditingController(text: f.value),
                      decoration: InputDecoration(
                        labelText: f.label,
                        border:
                            OutlineInputBorder(borderRadius: AppRadius.md),
                        isDense: true,
                      ),
                    )
                  : Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        SizedBox(
                          width: 120,
                          child: Text(
                            f.label,
                            style: AppTypography.bodySmall.copyWith(
                              color: AppColors.neutralGray500,
                            ),
                          ),
                        ),
                        Expanded(
                          child: Text(
                            f.value,
                            style: AppTypography.body.copyWith(
                              color: AppColors.neutralGray900,
                            ),
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

class _FieldRow {
  final String label;
  final String value;
  const _FieldRow(this.label, this.value);
}

class _ChangeRow extends StatelessWidget {
  const _ChangeRow(this.action, this.detail, this.date);

  final String action;
  final String detail;
  final String date;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Row(
        children: [
          const Icon(Icons.history, size: 16, color: AppColors.neutralGray400),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Text(
              action,
              style: AppTypography.bodySmall.copyWith(
                color: AppColors.neutralGray700,
              ),
            ),
          ),
          Text(
            date,
            style: AppTypography.caption.copyWith(
              color: AppColors.neutralGray400,
            ),
          ),
        ],
      ),
    );
  }
}
