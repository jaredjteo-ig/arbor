import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../../core/design/tokens/tokens.dart';

/// The "More" tab screen that provides navigation to secondary features:
/// Compliance, Alerts, Profile, Settings, and Help.
class MoreScreen extends StatelessWidget {
  const MoreScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('More')),
      body: ListView(
        padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
        children: [
          _MoreTile(
            icon: Icons.verified_user_outlined,
            label: 'Compliance',
            onTap: () => context.go('/compliance'),
          ),
          _MoreTile(
            icon: Icons.warning_amber_outlined,
            label: 'Emergency',
            onTap: () => context.go('/emergency'),
          ),
          _MoreTile(
            icon: Icons.people_outlined,
            label: 'Clients',
            onTap: () => context.go('/clients'),
          ),
          _MoreTile(
            icon: Icons.bar_chart_outlined,
            label: 'Analytics',
            onTap: () => context.go('/analytics'),
          ),
          _MoreTile(
            icon: Icons.notifications_outlined,
            label: 'Alerts',
            onTap: () => context.go('/alerts'),
          ),
          _MoreTile(
            icon: Icons.business_outlined,
            label: 'Company Profile',
            onTap: () => context.go('/profile'),
          ),
          const Divider(height: 1),
          _MoreTile(
            icon: Icons.settings_outlined,
            label: 'Settings',
            onTap: () => context.go('/settings'),
          ),
          _MoreTile(
            icon: Icons.help_outline,
            label: 'Help',
            onTap: () => context.go('/help'),
          ),
        ],
      ),
    );
  }
}

class _MoreTile extends StatelessWidget {
  const _MoreTile({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(icon, color: AppColors.primaryNavy),
      title: Text(label, style: AppTypography.body),
      trailing: const Icon(
        Icons.chevron_right,
        color: AppColors.neutralGray400,
      ),
      minTileHeight: AppTouch.minTarget,
      onTap: onTap,
    );
  }
}
