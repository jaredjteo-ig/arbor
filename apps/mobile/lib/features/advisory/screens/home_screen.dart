import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/design/components/components.dart';
import '../../../core/design/tokens/tokens.dart';
import '../../../core/providers/auth_providers.dart';

// ---------------------------------------------------------------------------
// Placeholder data (replaced by API in production)
// ---------------------------------------------------------------------------

class _MetricData {
  const _MetricData({
    required this.label,
    required this.value,
    required this.icon,
    this.subtext,
  });
  final String label;
  final String value;
  final IconData icon;
  final String? subtext;
}

class _RecentConversation {
  const _RecentConversation({
    required this.id,
    required this.topic,
    required this.date,
    this.riskTier,
  });
  final int id;
  final String topic;
  final String date;
  final RiskTier? riskTier;
}

class _ActionItem {
  const _ActionItem({
    required this.title,
    required this.tier,
    this.dueDate,
  });
  final String title;
  final RiskTier tier;
  final String? dueDate;
}

const _metrics = [
  _MetricData(
    label: 'Compliance Score',
    value: '78/100',
    icon: Icons.shield_outlined,
    subtext: '2 items need attention',
  ),
  _MetricData(
    label: 'Pending Actions',
    value: '3',
    icon: Icons.checklist,
    subtext: '1 high priority',
  ),
  _MetricData(
    label: 'Next Deadline',
    value: '31 Mar',
    icon: Icons.calendar_today,
    subtext: 'CPF submission',
  ),
];

const _conversations = [
  _RecentConversation(
    id: 1,
    topic: 'Can I terminate employee during probation without notice?',
    date: 'Today',
    riskTier: RiskTier.amber,
  ),
  _RecentConversation(
    id: 2,
    topic: 'CPF contribution rates for PR employee (2nd year)',
    date: 'Yesterday',
    riskTier: RiskTier.green,
  ),
  _RecentConversation(
    id: 3,
    topic: 'Foreign worker quota calculation after new hire',
    date: '11 Mar',
    riskTier: RiskTier.green,
  ),
];

const _actions = [
  _ActionItem(
    title: 'Update employment contracts with new KET requirements',
    tier: RiskTier.red,
    dueDate: '15 Mar 2026',
  ),
  _ActionItem(
    title: 'Review FWA policy against TG-FWAR guidelines',
    tier: RiskTier.amber,
  ),
  _ActionItem(
    title: 'Renew foreign worker medical insurance',
    tier: RiskTier.amber,
    dueDate: '31 Mar 2026',
  ),
];

// ---------------------------------------------------------------------------
// Dashboard screen
// ---------------------------------------------------------------------------

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authStateProvider);
    final firstName = authState is AuthAuthenticated
        ? authState.user.name.split(' ').first
        : 'there';

    return Scaffold(
      appBar: AppBar(
        title: const Text('Dashboard'),
        actions: [
          IconButton(
            onPressed: () => context.push('/alerts'),
            icon: Badge(
              label: const Text('2'),
              child: const Icon(Icons.notifications_outlined),
            ),
            tooltip: 'Alerts',
          ),
        ],
      ),
      body: PullToRefresh(
        onRefresh: () async {
          // Refresh dashboard data
        },
        child: ListView(
          padding: const EdgeInsets.all(AppSpacing.base),
          children: [
            // Greeting
            Text(
              'Welcome back, $firstName',
              style: AppTypography.title.copyWith(
                color: AppColors.neutralGray900,
              ),
            ),
            const SizedBox(height: AppSpacing.xs),
            Text(
              "Here's your HR compliance overview",
              style: AppTypography.body.copyWith(
                color: AppColors.neutralGray500,
              ),
            ),
            const SizedBox(height: AppSpacing.base),

            // Regulatory alert
            AlertBanner(
              variant: AlertBannerVariant.warning,
              title: 'New KET Requirements Effective 1 April 2026',
              description:
                  'Employment contracts must include additional terms. Update your templates.',
              onDismiss: () {},
            ),
            const SizedBox(height: AppSpacing.base),

            // Metric cards
            SizedBox(
              height: 100,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: _metrics.length,
                separatorBuilder: (_, _) =>
                    const SizedBox(width: AppSpacing.md),
                itemBuilder: (context, index) {
                  final m = _metrics[index];
                  return SizedBox(
                    width: 160,
                    child: AppCard(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Row(
                            mainAxisAlignment:
                                MainAxisAlignment.spaceBetween,
                            children: [
                              Text(
                                m.label,
                                style: AppTypography.caption.copyWith(
                                  color: AppColors.neutralGray500,
                                ),
                              ),
                              Icon(m.icon,
                                  size: 18,
                                  color: AppColors.primaryNavy),
                            ],
                          ),
                          const SizedBox(height: AppSpacing.xs),
                          Text(
                            m.value,
                            style: AppTypography.heading.copyWith(
                              color: AppColors.neutralGray900,
                            ),
                          ),
                          if (m.subtext != null) ...[
                            const SizedBox(height: 2),
                            Text(
                              m.subtext!,
                              style: AppTypography.caption.copyWith(
                                color: AppColors.neutralGray400,
                                fontSize: 10,
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),
            const SizedBox(height: AppSpacing.xl),

            // Quick actions
            Text(
              'Quick Actions',
              style: AppTypography.subtitle.copyWith(
                color: AppColors.neutralGray900,
              ),
            ),
            const SizedBox(height: AppSpacing.md),
            _QuickActionsGrid(),
            const SizedBox(height: AppSpacing.xl),

            // Recent conversations
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Recent Conversations',
                  style: AppTypography.subtitle.copyWith(
                    color: AppColors.neutralGray900,
                  ),
                ),
                TextButton(
                  onPressed: () => context.push('/advisory'),
                  child: const Text('View all'),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.sm),
            for (final conv in _conversations) ...[
              _ConversationTile(conversation: conv),
              const SizedBox(height: AppSpacing.sm),
            ],
            const SizedBox(height: AppSpacing.base),

            // Pending actions
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Pending Actions',
                  style: AppTypography.subtitle.copyWith(
                    color: AppColors.neutralGray900,
                  ),
                ),
                TextButton(
                  onPressed: () => context.push('/compliance'),
                  child: const Text('View all'),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.sm),
            for (final action in _actions) ...[
              _ActionTile(action: action),
              const SizedBox(height: AppSpacing.sm),
            ],
            const SizedBox(height: AppSpacing.base),

            // Compliance check CTA
            AppButton(
              label: 'Run Compliance Check',
              onPressed: () => context.push('/compliance'),
              variant: AppButtonVariant.outlined,
              icon: Icons.verified_user,
              fullWidth: true,
            ),
            const SizedBox(height: AppSpacing.xl),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Quick actions grid
// ---------------------------------------------------------------------------

class _QuickActionsGrid extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final actions = [
      (
        label: 'Ask a question',
        icon: Icons.chat_bubble_outline,
        route: '/advisory',
        primary: true,
      ),
      (
        label: 'Calculate',
        icon: Icons.calculate_outlined,
        route: '/calculators',
        primary: false,
      ),
      (
        label: 'Documents',
        icon: Icons.description_outlined,
        route: '/documents',
        primary: false,
      ),
      (
        label: 'Compliance',
        icon: Icons.fact_check_outlined,
        route: '/compliance',
        primary: false,
      ),
    ];

    return GridView.count(
      crossAxisCount: 2,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: AppSpacing.md,
      crossAxisSpacing: AppSpacing.md,
      childAspectRatio: 2.2,
      children: actions.map((a) {
        return Material(
          color: a.primary
              ? AppColors.primaryNavy
              : AppColors.neutralGray100,
          borderRadius: AppRadius.md,
          child: InkWell(
            onTap: () => context.push(a.route),
            borderRadius: AppRadius.md,
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    a.icon,
                    size: 22,
                    color: a.primary
                        ? AppColors.neutralWhite
                        : AppColors.neutralGray700,
                  ),
                  const SizedBox(height: AppSpacing.xs),
                  Text(
                    a.label,
                    style: AppTypography.bodySmall.copyWith(
                      color: a.primary
                          ? AppColors.neutralWhite
                          : AppColors.neutralGray700,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      }).toList(),
    );
  }
}

// ---------------------------------------------------------------------------
// Recent conversation tile
// ---------------------------------------------------------------------------

class _ConversationTile extends StatelessWidget {
  const _ConversationTile({required this.conversation});
  final _RecentConversation conversation;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: () => context.push('/advisory'),
      borderRadius: AppRadius.md,
      child: Container(
        padding: const EdgeInsets.all(AppSpacing.md),
        decoration: BoxDecoration(
          color: AppColors.neutralWhite,
          borderRadius: AppRadius.md,
          border: Border.all(color: AppColors.neutralGray200),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    conversation.topic,
                    style: AppTypography.bodySmall.copyWith(
                      color: AppColors.neutralGray900,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                if (conversation.riskTier != null)
                  RiskTierBadge(tier: conversation.riskTier!),
              ],
            ),
            const SizedBox(height: AppSpacing.xs),
            Row(
              children: [
                Icon(Icons.access_time,
                    size: 12, color: AppColors.neutralGray400),
                const SizedBox(width: 4),
                Text(
                  conversation.date,
                  style: AppTypography.caption.copyWith(
                    color: AppColors.neutralGray400,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Action item tile
// ---------------------------------------------------------------------------

class _ActionTile extends StatelessWidget {
  const _ActionTile({required this.action});
  final _ActionItem action;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.neutralWhite,
        borderRadius: AppRadius.md,
        border: Border.all(color: AppColors.neutralGray200),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          RiskTierBadge(tier: action.tier),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  action.title,
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.neutralGray900,
                  ),
                ),
                if (action.dueDate != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    'Due: ${action.dueDate}',
                    style: AppTypography.caption.copyWith(
                      color: AppColors.neutralGray400,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}
