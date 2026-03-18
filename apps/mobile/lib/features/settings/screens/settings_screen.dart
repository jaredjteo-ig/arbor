import 'package:flutter/material.dart';

import '../../../core/design/tokens/tokens.dart';
import '../../../core/design/components/components.dart';

/// App settings: text size, notifications, data management.
class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  // Display preferences
  String _textSize = 'normal'; // normal, large, extraLarge

  // Notification preferences
  bool _emailAlerts = true;
  bool _pushNotifications = true;
  bool _inAppNotifications = true;
  String _alertFrequency = 'immediately'; // immediately, daily, weekly

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        padding: const EdgeInsets.all(AppSpacing.base),
        children: [
          // Display section
          AppCard(
            variant: AppCardVariant.standard,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.text_fields, size: 20, color: AppColors.primaryNavy),
                    const SizedBox(width: AppSpacing.sm),
                    Text(
                      'Display',
                      style: AppTypography.subtitle.copyWith(
                        color: AppColors.neutralGray900,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: AppSpacing.md),
                Text(
                  'Text Size',
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.neutralGray500,
                  ),
                ),
                const SizedBox(height: AppSpacing.sm),
                _TextSizeOption(
                  label: 'Normal',
                  example: 'Aa',
                  selected: _textSize == 'normal',
                  onTap: () => setState(() => _textSize = 'normal'),
                ),
                _TextSizeOption(
                  label: 'Large',
                  example: 'Aa',
                  fontSize: 18,
                  selected: _textSize == 'large',
                  onTap: () => setState(() => _textSize = 'large'),
                ),
                _TextSizeOption(
                  label: 'Extra Large',
                  example: 'Aa',
                  fontSize: 22,
                  selected: _textSize == 'extraLarge',
                  onTap: () => setState(() => _textSize = 'extraLarge'),
                ),
              ],
            ),
          ),

          const SizedBox(height: AppSpacing.md),

          // Notifications section
          AppCard(
            variant: AppCardVariant.standard,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.notifications_outlined, size: 20, color: AppColors.primaryNavy),
                    const SizedBox(width: AppSpacing.sm),
                    Text(
                      'Notifications',
                      style: AppTypography.subtitle.copyWith(
                        color: AppColors.neutralGray900,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: AppSpacing.md),
                SwitchListTile(
                  title: Text(
                    'Email Alerts',
                    style: AppTypography.body.copyWith(color: AppColors.neutralGray900),
                  ),
                  subtitle: Text(
                    'Receive regulatory change alerts via email',
                    style: AppTypography.caption.copyWith(color: AppColors.neutralGray500),
                  ),
                  value: _emailAlerts,
                  onChanged: (v) => setState(() => _emailAlerts = v),
                  activeThumbColor: AppColors.primaryNavy,
                  contentPadding: EdgeInsets.zero,
                ),
                SwitchListTile(
                  title: Text(
                    'Push Notifications',
                    style: AppTypography.body.copyWith(color: AppColors.neutralGray900),
                  ),
                  subtitle: Text(
                    'Get notified on your device',
                    style: AppTypography.caption.copyWith(color: AppColors.neutralGray500),
                  ),
                  value: _pushNotifications,
                  onChanged: (v) => setState(() => _pushNotifications = v),
                  activeThumbColor: AppColors.primaryNavy,
                  contentPadding: EdgeInsets.zero,
                ),
                SwitchListTile(
                  title: Text(
                    'In-App Notifications',
                    style: AppTypography.body.copyWith(color: AppColors.neutralGray900),
                  ),
                  subtitle: Text(
                    'Show notification badge in the app',
                    style: AppTypography.caption.copyWith(color: AppColors.neutralGray500),
                  ),
                  value: _inAppNotifications,
                  onChanged: (v) => setState(() => _inAppNotifications = v),
                  activeThumbColor: AppColors.primaryNavy,
                  contentPadding: EdgeInsets.zero,
                ),
                const Divider(),
                const SizedBox(height: AppSpacing.sm),
                Text(
                  'Alert Frequency',
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.neutralGray500,
                  ),
                ),
                const SizedBox(height: AppSpacing.sm),
                Wrap(
                  spacing: AppSpacing.sm,
                  children: [
                    ChoiceChip(
                      label: const Text('Immediately'),
                      selected: _alertFrequency == 'immediately',
                      onSelected: (_) =>
                          setState(() => _alertFrequency = 'immediately'),
                      selectedColor: AppColors.primaryNavy,
                      labelStyle: TextStyle(
                        color: _alertFrequency == 'immediately'
                            ? AppColors.neutralWhite
                            : AppColors.neutralGray600,
                        fontSize: 13,
                      ),
                      shape: RoundedRectangleBorder(borderRadius: AppRadius.full),
                    ),
                    ChoiceChip(
                      label: const Text('Daily Digest'),
                      selected: _alertFrequency == 'daily',
                      onSelected: (_) =>
                          setState(() => _alertFrequency = 'daily'),
                      selectedColor: AppColors.primaryNavy,
                      labelStyle: TextStyle(
                        color: _alertFrequency == 'daily'
                            ? AppColors.neutralWhite
                            : AppColors.neutralGray600,
                        fontSize: 13,
                      ),
                      shape: RoundedRectangleBorder(borderRadius: AppRadius.full),
                    ),
                    ChoiceChip(
                      label: const Text('Weekly'),
                      selected: _alertFrequency == 'weekly',
                      onSelected: (_) =>
                          setState(() => _alertFrequency = 'weekly'),
                      selectedColor: AppColors.primaryNavy,
                      labelStyle: TextStyle(
                        color: _alertFrequency == 'weekly'
                            ? AppColors.neutralWhite
                            : AppColors.neutralGray600,
                        fontSize: 13,
                      ),
                      shape: RoundedRectangleBorder(borderRadius: AppRadius.full),
                    ),
                  ],
                ),
              ],
            ),
          ),

          const SizedBox(height: AppSpacing.md),

          // Language section
          AppCard(
            variant: AppCardVariant.standard,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.language, size: 20, color: AppColors.primaryNavy),
                    const SizedBox(width: AppSpacing.sm),
                    Text(
                      'Language',
                      style: AppTypography.subtitle.copyWith(
                        color: AppColors.neutralGray900,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: AppSpacing.md),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.md,
                    vertical: AppSpacing.md,
                  ),
                  decoration: BoxDecoration(
                    color: AppColors.neutralGray50,
                    borderRadius: AppRadius.md,
                    border: Border.all(color: AppColors.primaryNavy),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.check_circle, size: 18, color: AppColors.primaryNavy),
                      const SizedBox(width: AppSpacing.sm),
                      Text(
                        'English',
                        style: AppTypography.bodyMedium.copyWith(
                          color: AppColors.neutralGray900,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: AppSpacing.sm),
                Text(
                  'More languages coming soon.',
                  style: AppTypography.caption.copyWith(
                    color: AppColors.neutralGray400,
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: AppSpacing.md),

          // Data & Privacy section
          AppCard(
            variant: AppCardVariant.standard,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.security, size: 20, color: AppColors.primaryNavy),
                    const SizedBox(width: AppSpacing.sm),
                    Text(
                      'Data & Privacy',
                      style: AppTypography.subtitle.copyWith(
                        color: AppColors.neutralGray900,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: AppSpacing.md),
                Text(
                  'Under the Personal Data Protection Act (PDPA), you have the right to access and manage your data.',
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.neutralGray600,
                  ),
                ),
                const SizedBox(height: AppSpacing.base),
                AppButton(
                  label: 'Export My Data',
                  variant: AppButtonVariant.outlined,
                  onPressed: () {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text(
                          'Your data export will be prepared and sent to your email.',
                        ),
                      ),
                    );
                  },
                ),
                const SizedBox(height: AppSpacing.md),
                AppButton(
                  label: 'Delete Account',
                  variant: AppButtonVariant.outlined,
                  onPressed: () => _showDeleteConfirmation(context),
                ),
              ],
            ),
          ),

          const SizedBox(height: AppSpacing.xl),
        ],
      ),
    );
  }

  void _showDeleteConfirmation(BuildContext context) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete Account'),
        content: const Text(
          'This will permanently delete your account and all associated data. '
          'This action cannot be undone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            style: TextButton.styleFrom(foregroundColor: AppColors.riskRed),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }
}

class _TextSizeOption extends StatelessWidget {
  const _TextSizeOption({
    required this.label,
    required this.example,
    this.fontSize = 14,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final String example;
  final double fontSize;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: AppRadius.md,
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: AppSpacing.md,
        ),
        margin: const EdgeInsets.only(bottom: AppSpacing.sm),
        decoration: BoxDecoration(
          borderRadius: AppRadius.md,
          border: Border.all(
            color: selected ? AppColors.primaryNavy : AppColors.neutralGray200,
            width: selected ? 2 : 1,
          ),
          color: selected ? AppColors.primaryNavy.withAlpha(13) : null,
        ),
        child: Row(
          children: [
            Icon(
              selected ? Icons.radio_button_checked : Icons.radio_button_off,
              size: 20,
              color: selected ? AppColors.primaryNavy : AppColors.neutralGray400,
            ),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Text(
                label,
                style: AppTypography.body.copyWith(
                  color: AppColors.neutralGray900,
                ),
              ),
            ),
            Text(
              example,
              style: TextStyle(
                fontSize: fontSize,
                fontWeight: FontWeight.w600,
                color: AppColors.neutralGray600,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
