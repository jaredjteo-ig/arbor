import 'package:flutter/material.dart';

import '../../../core/design/components/components.dart';
import '../../../core/design/tokens/tokens.dart';

// ── Demo Data ────────────────────────────────────────────

/// Nationality breakdown entry for workforce composition.
@immutable
class _NationalityEntry {
  const _NationalityEntry({
    required this.label,
    required this.count,
    required this.color,
  });
  final String label;
  final int count;
  final Color color;
}

/// Pass type breakdown entry.
@immutable
class _PassTypeEntry {
  const _PassTypeEntry({
    required this.label,
    required this.count,
    required this.color,
  });
  final String label;
  final int count;
  final Color color;
}

/// Advisory usage top domain entry.
@immutable
class _TopDomain {
  const _TopDomain({required this.name, required this.queries});
  final String name;
  final int queries;
}

// Demo data
const _nationalityBreakdown = [
  _NationalityEntry(
    label: 'Citizen',
    count: 42,
    color: AppColors.primaryNavy,
  ),
  _NationalityEntry(
    label: 'PR',
    count: 18,
    color: AppColors.secondaryTeal,
  ),
  _NationalityEntry(
    label: 'Foreigner',
    count: 40,
    color: AppColors.riskAmber,
  ),
];

const _passTypeBreakdown = [
  _PassTypeEntry(label: 'EP', count: 15, color: AppColors.primaryNavy),
  _PassTypeEntry(label: 'S Pass', count: 12, color: AppColors.secondaryTeal),
  _PassTypeEntry(label: 'WP', count: 13, color: AppColors.riskAmber),
  _PassTypeEntry(label: 'N/A', count: 60, color: AppColors.neutralGray300),
];

const _topDomains = [
  _TopDomain(name: 'Employment Act', queries: 34),
  _TopDomain(name: 'CPF', queries: 28),
  _TopDomain(name: 'Foreign Manpower', queries: 19),
  _TopDomain(name: 'Leave & Benefits', queries: 14),
  _TopDomain(name: 'Workplace Safety', queries: 9),
];

// ── Main Screen ──────────────────────────────────────────

/// Analytics dashboard showing workforce composition, compliance score,
/// cost summary, and advisory usage metrics.
class AnalyticsScreen extends StatelessWidget {
  const AnalyticsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.surfaceBackground,
      appBar: AppBar(
        title: const Text('Analytics'),
        backgroundColor: AppColors.primaryNavy,
        foregroundColor: AppColors.neutralWhite,
        elevation: 0,
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(AppSpacing.base),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Section 1: Workforce Composition
              const _SectionHeader(
                icon: Icons.people_outlined,
                title: 'Workforce Composition',
              ),
              const SizedBox(height: AppSpacing.md),
              const _WorkforceCompositionCard(),
              const SizedBox(height: AppSpacing.xl),

              // Section 2: Compliance Score
              const _SectionHeader(
                icon: Icons.shield_outlined,
                title: 'Compliance Score',
              ),
              const SizedBox(height: AppSpacing.md),
              const _ComplianceScoreCard(),
              const SizedBox(height: AppSpacing.xl),

              // Section 3: Cost Summary
              const _SectionHeader(
                icon: Icons.payments_outlined,
                title: 'Cost Summary',
              ),
              const SizedBox(height: AppSpacing.md),
              const _CostSummaryCard(),
              const SizedBox(height: AppSpacing.xl),

              // Section 4: Advisory Usage
              const _SectionHeader(
                icon: Icons.forum_outlined,
                title: 'Advisory Usage',
              ),
              const SizedBox(height: AppSpacing.md),
              const _AdvisoryUsageCard(),
              const SizedBox(height: AppSpacing.xl),
            ],
          ),
        ),
      ),
    );
  }
}

// ── Section Header ───────────────────────────────────────

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({
    required this.icon,
    required this.title,
  });

  final IconData icon;
  final String title;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 22, color: AppColors.primaryNavy),
        const SizedBox(width: AppSpacing.sm),
        Text(
          title,
          style: AppTypography.subtitle.copyWith(
            color: AppColors.neutralGray900,
          ),
        ),
      ],
    );
  }
}

// ── Workforce Composition Card ───────────────────────────

class _WorkforceCompositionCard extends StatelessWidget {
  const _WorkforceCompositionCard();

  @override
  Widget build(BuildContext context) {
    final totalEmployees = _nationalityBreakdown.fold<int>(
      0,
      (sum, e) => sum + e.count,
    );
    final totalByPass = _passTypeBreakdown.fold<int>(
      0,
      (sum, e) => sum + e.count,
    );

    return AppCard(
      variant: AppCardVariant.standard,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Headcount
          Row(
            crossAxisAlignment: CrossAxisAlignment.baseline,
            textBaseline: TextBaseline.alphabetic,
            children: [
              Text(
                '$totalEmployees',
                style: AppTypography.heading.copyWith(
                  color: AppColors.neutralGray900,
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
              Text(
                'Total Employees',
                style: AppTypography.bodySmall.copyWith(
                  color: AppColors.neutralGray500,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.lg),

          // Nationality breakdown
          Text(
            'By Nationality / Residency',
            style: AppTypography.caption.copyWith(
              color: AppColors.neutralGray500,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          _HorizontalPercentageBar(
            entries: _nationalityBreakdown
                .map((e) => _BarSegment(
                      label: e.label,
                      value: e.count,
                      color: e.color,
                    ))
                .toList(),
            total: totalEmployees,
          ),
          const SizedBox(height: AppSpacing.sm),
          _BarLegend(
            items: _nationalityBreakdown
                .map((e) => _LegendItem(
                      label: e.label,
                      value: e.count,
                      total: totalEmployees,
                      color: e.color,
                    ))
                .toList(),
          ),
          const SizedBox(height: AppSpacing.lg),

          // Pass type breakdown
          Text(
            'By Pass Type',
            style: AppTypography.caption.copyWith(
              color: AppColors.neutralGray500,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          _HorizontalPercentageBar(
            entries: _passTypeBreakdown
                .map((e) => _BarSegment(
                      label: e.label,
                      value: e.count,
                      color: e.color,
                    ))
                .toList(),
            total: totalByPass,
          ),
          const SizedBox(height: AppSpacing.sm),
          _BarLegend(
            items: _passTypeBreakdown
                .map((e) => _LegendItem(
                      label: e.label,
                      value: e.count,
                      total: totalByPass,
                      color: e.color,
                    ))
                .toList(),
          ),
        ],
      ),
    );
  }
}

// ── Horizontal Percentage Bar ────────────────────────────

@immutable
class _BarSegment {
  const _BarSegment({
    required this.label,
    required this.value,
    required this.color,
  });
  final String label;
  final int value;
  final Color color;
}

class _HorizontalPercentageBar extends StatelessWidget {
  const _HorizontalPercentageBar({
    required this.entries,
    required this.total,
  });

  final List<_BarSegment> entries;
  final int total;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: AppRadius.sm,
      child: SizedBox(
        height: 28,
        child: Row(
          children: entries.map((entry) {
            final fraction = total > 0 ? entry.value / total : 0.0;
            if (fraction <= 0) return const SizedBox.shrink();
            return Expanded(
              flex: entry.value,
              child: Container(
                color: entry.color,
                alignment: Alignment.center,
                child: fraction >= 0.08
                    ? Text(
                        '${(fraction * 100).round()}%',
                        style: AppTypography.caption.copyWith(
                          color: AppColors.neutralWhite,
                          fontWeight: FontWeight.w600,
                          fontSize: 11,
                        ),
                      )
                    : null,
              ),
            );
          }).toList(),
        ),
      ),
    );
  }
}

// ── Bar Legend ────────────────────────────────────────────

@immutable
class _LegendItem {
  const _LegendItem({
    required this.label,
    required this.value,
    required this.total,
    required this.color,
  });
  final String label;
  final int value;
  final int total;
  final Color color;
}

class _BarLegend extends StatelessWidget {
  const _BarLegend({required this.items});
  final List<_LegendItem> items;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: AppSpacing.base,
      runSpacing: AppSpacing.xs,
      children: items.map((item) {
        final pct = item.total > 0
            ? (item.value / item.total * 100).round()
            : 0;
        return Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 10,
              height: 10,
              decoration: BoxDecoration(
                color: item.color,
                borderRadius: AppRadius.sm,
              ),
            ),
            const SizedBox(width: AppSpacing.xs),
            Text(
              '${item.label} ${item.value} ($pct%)',
              style: AppTypography.caption.copyWith(
                color: AppColors.neutralGray600,
              ),
            ),
          ],
        );
      }).toList(),
    );
  }
}

// ── Compliance Score Card ────────────────────────────────

class _ComplianceScoreCard extends StatelessWidget {
  const _ComplianceScoreCard();

  // Demo data
  static const int _score = 78;
  static const RiskTier _tier = RiskTier.amber;
  static const String _trend = '+3';

  @override
  Widget build(BuildContext context) {
    return AppCard(
      variant: AppCardVariant.elevated,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Score
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Current Score',
                      style: AppTypography.caption.copyWith(
                        color: AppColors.neutralGray500,
                      ),
                    ),
                    const SizedBox(height: AppSpacing.xs),
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.baseline,
                      textBaseline: TextBaseline.alphabetic,
                      children: [
                        Text(
                          '$_score',
                          style: AppTypography.pageTitle.copyWith(
                            fontSize: 40,
                            color: AppColors.neutralGray900,
                          ),
                        ),
                        const SizedBox(width: AppSpacing.xs),
                        Text(
                          '/ 100',
                          style: AppTypography.subtitle.copyWith(
                            color: AppColors.neutralGray400,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),

              // Risk tier badge
              const RiskTierBadge(tier: _tier),
            ],
          ),
          const SizedBox(height: AppSpacing.md),

          // Trend indicator
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.sm,
              vertical: AppSpacing.xs,
            ),
            decoration: BoxDecoration(
              color: AppColors.riskGreenBg,
              borderRadius: AppRadius.sm,
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(
                  Icons.trending_up,
                  size: 16,
                  color: AppColors.riskGreen,
                ),
                const SizedBox(width: AppSpacing.xs),
                Text(
                  '$_trend pts from last month',
                  style: AppTypography.caption.copyWith(
                    color: AppColors.riskGreen,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.md),

          // Summary text
          Text(
            '2 findings need attention across 5 compliance domains.',
            style: AppTypography.bodySmall.copyWith(
              color: AppColors.neutralGray600,
            ),
          ),
        ],
      ),
    );
  }
}

// ── Cost Summary Card ────────────────────────────────────

class _CostSummaryCard extends StatelessWidget {
  const _CostSummaryCard();

  @override
  Widget build(BuildContext context) {
    return AppCard(
      variant: AppCardVariant.standard,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Monthly Breakdown',
            style: AppTypography.caption.copyWith(
              color: AppColors.neutralGray500,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          const _CostRow(
            label: 'CPF Contributions (Employer)',
            value: '\$28,560',
            icon: Icons.account_balance_outlined,
          ),
          const Divider(height: AppSpacing.lg),
          const _CostRow(
            label: 'Foreign Worker Levy',
            value: '\$11,400',
            icon: Icons.receipt_long_outlined,
          ),
          const Divider(height: AppSpacing.lg),
          const _CostRow(
            label: 'Skills Development Levy',
            value: '\$250',
            icon: Icons.school_outlined,
          ),
          const SizedBox(height: AppSpacing.md),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(AppSpacing.md),
            decoration: BoxDecoration(
              color: AppColors.neutralGray100,
              borderRadius: AppRadius.md,
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Total Monthly Cost',
                  style: AppTypography.bodyMedium.copyWith(
                    color: AppColors.neutralGray900,
                  ),
                ),
                Text(
                  '\$40,210',
                  style: AppTypography.title.copyWith(
                    color: AppColors.primaryNavy,
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

class _CostRow extends StatelessWidget {
  const _CostRow({
    required this.label,
    required this.value,
    required this.icon,
  });

  final String label;
  final String value;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 20, color: AppColors.neutralGray400),
        const SizedBox(width: AppSpacing.md),
        Expanded(
          child: Text(
            label,
            style: AppTypography.bodySmall.copyWith(
              color: AppColors.neutralGray700,
            ),
          ),
        ),
        Text(
          value,
          style: AppTypography.bodyMedium.copyWith(
            color: AppColors.neutralGray900,
          ),
        ),
      ],
    );
  }
}

// ── Advisory Usage Card ──────────────────────────────────

class _AdvisoryUsageCard extends StatelessWidget {
  const _AdvisoryUsageCard();

  // Demo data
  static const int _queriesThisMonth = 104;
  static const double _positiveFeedbackPct = 92.0;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      variant: AppCardVariant.standard,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Stat row
          Row(
            children: [
              Expanded(
                child: _StatTile(
                  label: 'Queries This Month',
                  value: '$_queriesThisMonth',
                  icon: Icons.chat_outlined,
                ),
              ),
              Container(
                width: 1,
                height: 48,
                color: AppColors.neutralGray200,
              ),
              Expanded(
                child: _StatTile(
                  label: 'Positive Feedback',
                  value: '${_positiveFeedbackPct.round()}%',
                  icon: Icons.thumb_up_outlined,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.lg),

          // Top domains
          Text(
            'Top Domains',
            style: AppTypography.caption.copyWith(
              color: AppColors.neutralGray500,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          ..._topDomains.map((domain) {
            final maxQueries = _topDomains.first.queries;
            return Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.sm),
              child: _DomainRow(
                name: domain.name,
                queries: domain.queries,
                maxQueries: maxQueries,
              ),
            );
          }),
        ],
      ),
    );
  }
}

class _StatTile extends StatelessWidget {
  const _StatTile({
    required this.label,
    required this.value,
    required this.icon,
  });

  final String label;
  final String value;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
      child: Column(
        children: [
          Icon(icon, size: 20, color: AppColors.primaryNavy),
          const SizedBox(height: AppSpacing.xs),
          Text(
            value,
            style: AppTypography.title.copyWith(
              color: AppColors.neutralGray900,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            label,
            style: AppTypography.caption.copyWith(
              color: AppColors.neutralGray500,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}

class _DomainRow extends StatelessWidget {
  const _DomainRow({
    required this.name,
    required this.queries,
    required this.maxQueries,
  });

  final String name;
  final int queries;
  final int maxQueries;

  @override
  Widget build(BuildContext context) {
    final fraction = maxQueries > 0 ? queries / maxQueries : 0.0;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              name,
              style: AppTypography.bodySmall.copyWith(
                color: AppColors.neutralGray700,
              ),
            ),
            Text(
              '$queries',
              style: AppTypography.bodySmall.copyWith(
                color: AppColors.neutralGray900,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.xs),
        ClipRRect(
          borderRadius: AppRadius.sm,
          child: LinearProgressIndicator(
            value: fraction,
            backgroundColor: AppColors.neutralGray100,
            valueColor:
                const AlwaysStoppedAnimation<Color>(AppColors.primaryNavy),
            minHeight: 6,
          ),
        ),
      ],
    );
  }
}
