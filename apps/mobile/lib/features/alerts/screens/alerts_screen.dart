import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../core/design/components/components.dart';
import '../../../core/design/tokens/tokens.dart';

// ── Data Models ─────────────────────────────────────────

/// Severity levels for regulatory alerts.
enum AlertSeverity { critical, high, medium, low }

/// A single regulatory alert with metadata and action items.
@immutable
class RegulatoryAlert {
  const RegulatoryAlert({
    required this.id,
    required this.title,
    required this.description,
    required this.severity,
    required this.isRead,
    required this.domain,
    required this.createdAt,
    required this.impactSummary,
    required this.actions,
    required this.effectiveDate,
  });

  final String id;
  final String title;
  final String description;
  final AlertSeverity severity;
  final bool isRead;
  final String domain;
  final DateTime createdAt;
  final String impactSummary;
  final List<String> actions;
  final DateTime effectiveDate;
}

// ── Filter Enums ────────────────────────────────────────

enum _ViewFilter { all, affectingYou, upcoming }

enum _SeverityFilter { all, critical, high, medium, low }

// ── Demo Data ───────────────────────────────────────────

List<RegulatoryAlert> _buildDemoAlerts() {
  return [
    RegulatoryAlert(
      id: 'alert-001',
      title: 'Progressive Wage Model Extended to Food Services',
      description:
          'MOM has extended PWM coverage to the food services sector. '
          'All food services employers must meet new wage requirements '
          'by the effective date.',
      severity: AlertSeverity.critical,
      isRead: false,
      domain: 'Wages & PWM',
      createdAt: DateTime(2026, 2, 20),
      impactSummary:
          'If your company operates in food services, you must adjust '
          'wages to meet the new Progressive Wage Model minimums. '
          'Non-compliance may result in inability to renew work passes '
          'and potential MOM enforcement action.',
      actions: [
        'Review current wage structure against new PWM requirements',
        'Identify employees whose wages fall below the new minimums',
        'Prepare a wage adjustment plan and budget for affected roles',
        'Update employment contracts to reflect new wage levels',
        'Submit wage compliance declaration via MOM portal',
      ],
      effectiveDate: DateTime(2026, 3, 1),
    ),
    RegulatoryAlert(
      id: 'alert-002',
      title: 'Updated CPF Contribution Rates for 2026',
      description:
          'CPF Board has published revised contribution rates effective '
          '2026. Changes affect employer and employee rates for senior '
          'workers aged 55 and above.',
      severity: AlertSeverity.high,
      isRead: false,
      domain: 'CPF',
      createdAt: DateTime(2026, 2, 10),
      impactSummary:
          'Your payroll calculations must be updated to reflect the new '
          'CPF rates. Incorrect contributions can result in penalties '
          'and interest charges from CPFB.',
      actions: [
        'Download the updated CPF contribution rate table from CPFB',
        'Update payroll system with new employer and employee rates',
        'Run a test payroll cycle to verify correct deductions',
        'Notify affected employees about changes to their take-home pay',
      ],
      effectiveDate: DateTime(2026, 2, 15),
    ),
    RegulatoryAlert(
      id: 'alert-003',
      title: 'TG-FWAR Updated Flexible Work Arrangement Guidelines',
      description:
          'The Tripartite Guidelines on Flexible Work Arrangement '
          'Requests have been updated with new response timeframes '
          'and documentation requirements.',
      severity: AlertSeverity.medium,
      isRead: true,
      domain: 'Fair Employment',
      createdAt: DateTime(2026, 1, 15),
      impactSummary:
          'Your company must update its FWA request process to comply '
          'with the revised guidelines. Employers now have stricter '
          'response deadlines and must provide written reasons for '
          'rejecting FWA requests.',
      actions: [
        'Review the updated TG-FWAR guidelines document',
        'Update your company FWA policy to reflect new response timeframes',
        'Train managers on the revised process for handling FWA requests',
        'Update the FWA request form template',
      ],
      effectiveDate: DateTime(2026, 1, 20),
    ),
    RegulatoryAlert(
      id: 'alert-004',
      title: 'WICA Minimum Insurance Coverage Increase',
      description:
          'MOM has raised the minimum work injury compensation '
          'insurance coverage amounts. All employers must update '
          'their WICA policies.',
      severity: AlertSeverity.high,
      isRead: false,
      domain: 'Workplace Safety',
      createdAt: DateTime(2026, 3, 1),
      impactSummary:
          'Your existing WICA insurance policy may no longer meet the '
          'new minimum coverage requirements. Operating without '
          'adequate WICA coverage is a criminal offence with fines '
          'up to \$10,000 and/or 12 months imprisonment.',
      actions: [
        'Contact your WICA insurer to verify current coverage levels',
        'Request a policy upgrade if coverage falls below new minimums',
        'Obtain updated certificate of insurance',
        'File the updated insurance details with MOM',
      ],
      effectiveDate: DateTime(2026, 3, 10),
    ),
    RegulatoryAlert(
      id: 'alert-005',
      title: 'PDPA Breach Notification Deadline Shortened',
      description:
          'PDPC has reduced the mandatory data breach notification '
          'window. Organisations must now notify within a shorter '
          'timeframe of discovering a notifiable breach.',
      severity: AlertSeverity.critical,
      isRead: false,
      domain: 'Data Protection',
      createdAt: DateTime(2026, 2, 22),
      impactSummary:
          'Your data breach response plan must be updated immediately. '
          'The shortened notification window means your incident '
          'response team needs to act faster. Late notification can '
          'result in financial penalties up to \$1 million.',
      actions: [
        'Update your Data Breach Response Plan with the new timeline',
        'Retrain your incident response team on the shortened deadline',
        'Review and test your breach detection mechanisms',
        'Update contracts with data processors to reflect new requirements',
        'Conduct a tabletop exercise to verify response readiness',
      ],
      effectiveDate: DateTime(2026, 2, 28),
    ),
    RegulatoryAlert(
      id: 'alert-006',
      title: 'Foreign Worker Levy Rate Changes',
      description:
          'MOM has announced revised foreign worker levy rates for '
          'S Pass and Work Permit holders across multiple sectors.',
      severity: AlertSeverity.high,
      isRead: true,
      domain: 'Foreign Manpower',
      createdAt: DateTime(2026, 2, 25),
      impactSummary:
          'If your company employs foreign workers, your monthly levy '
          'costs will change. Budget adjustments may be needed. '
          'Failure to pay levies on time incurs a 2% monthly penalty.',
      actions: [
        'Review the updated levy rate schedule for your sector and tier',
        'Calculate the impact on monthly foreign worker costs',
        'Update your financial budget and forecasts',
        'Review workforce composition for levy optimisation opportunities',
      ],
      effectiveDate: DateTime(2026, 3, 5),
    ),
    RegulatoryAlert(
      id: 'alert-007',
      title: 'TAFEP Age Discrimination Guidelines Strengthened',
      description:
          'TAFEP has published strengthened guidelines on age '
          'discrimination in hiring and employment practices, '
          'with clearer enforcement standards.',
      severity: AlertSeverity.medium,
      isRead: true,
      domain: 'Fair Employment',
      createdAt: DateTime(2026, 1, 10),
      impactSummary:
          'Your hiring practices and job advertisements must comply '
          'with the strengthened age discrimination guidelines. '
          'Non-compliant employers risk TAFEP investigation and '
          'potential curtailment of work pass privileges.',
      actions: [
        'Audit all current job advertisements for age-related language',
        'Review interview and selection criteria for age bias',
        'Update HR policies to reflect the strengthened guidelines',
        'Brief hiring managers on compliant practices',
      ],
      effectiveDate: DateTime(2026, 1, 15),
    ),
    RegulatoryAlert(
      id: 'alert-008',
      title: 'Employment Act Late Salary Payment Penalty Increase',
      description:
          'Parliament has passed amendments increasing penalties for '
          'late salary payment under the Employment Act. Fines have '
          'been significantly raised.',
      severity: AlertSeverity.critical,
      isRead: false,
      domain: 'Employment Act',
      createdAt: DateTime(2026, 3, 2),
      impactSummary:
          'Late salary payments now carry substantially higher fines. '
          'Employers must ensure all salaries are paid within 7 days '
          'after the end of the salary period. Repeated offences can '
          'result in prosecution.',
      actions: [
        'Verify your payroll calendar meets the 7-day payment deadline',
        'Set up automated reminders for payroll processing cutoffs',
        'Review and optimise your payroll approval workflow',
        'Establish a contingency plan for payroll processing delays',
        'Brief management on the increased penalty framework',
      ],
      effectiveDate: DateTime(2026, 3, 8),
    ),
  ];
}

// ── Severity Helpers ────────────────────────────────────

Color _severityColor(AlertSeverity severity) {
  return switch (severity) {
    AlertSeverity.critical => AppColors.riskRed,
    AlertSeverity.high => AppColors.riskAmber,
    AlertSeverity.medium => AppColors.primaryNavy,
    AlertSeverity.low => AppColors.neutralGray400,
  };
}

Color _severityBgColor(AlertSeverity severity) {
  return switch (severity) {
    AlertSeverity.critical => AppColors.riskRedBg,
    AlertSeverity.high => AppColors.riskAmberBg,
    AlertSeverity.medium => AppColors.semanticInfoBg,
    AlertSeverity.low => AppColors.neutralGray100,
  };
}

String _severityLabel(AlertSeverity severity) {
  return switch (severity) {
    AlertSeverity.critical => 'CRITICAL',
    AlertSeverity.high => 'HIGH',
    AlertSeverity.medium => 'MEDIUM',
    AlertSeverity.low => 'LOW',
  };
}

// ── Main Screen ─────────────────────────────────────────

/// Lists regulatory alerts, deadline reminders, and compliance notifications.
class AlertsScreen extends StatefulWidget {
  const AlertsScreen({super.key});

  @override
  State<AlertsScreen> createState() => _AlertsScreenState();
}

class _AlertsScreenState extends State<AlertsScreen> {
  late List<RegulatoryAlert> _alerts;
  _ViewFilter _viewFilter = _ViewFilter.all;
  _SeverityFilter _severityFilter = _SeverityFilter.all;
  final Set<String> _expandedIds = {};

  @override
  void initState() {
    super.initState();
    _alerts = _buildDemoAlerts();
  }

  int get _unreadCount => _alerts.where((a) => !a.isRead).length;

  List<RegulatoryAlert> get _filteredAlerts {
    var filtered = List<RegulatoryAlert>.from(_alerts);

    // Apply view filter
    final now = DateTime(2026, 3, 12);
    switch (_viewFilter) {
      case _ViewFilter.all:
        break;
      case _ViewFilter.affectingYou:
        // Simulates alerts relevant to the user's company profile
        filtered = filtered
            .where((a) =>
                a.severity == AlertSeverity.critical ||
                a.severity == AlertSeverity.high)
            .toList();
      case _ViewFilter.upcoming:
        filtered =
            filtered.where((a) => a.effectiveDate.isAfter(now)).toList();
    }

    // Apply severity filter
    switch (_severityFilter) {
      case _SeverityFilter.all:
        break;
      case _SeverityFilter.critical:
        filtered = filtered
            .where((a) => a.severity == AlertSeverity.critical)
            .toList();
      case _SeverityFilter.high:
        filtered = filtered
            .where((a) => a.severity == AlertSeverity.high)
            .toList();
      case _SeverityFilter.medium:
        filtered = filtered
            .where((a) => a.severity == AlertSeverity.medium)
            .toList();
      case _SeverityFilter.low:
        filtered = filtered
            .where((a) => a.severity == AlertSeverity.low)
            .toList();
    }

    // Sort: unread first, then by severity, then by date descending
    filtered.sort((a, b) {
      // Unread first
      if (a.isRead != b.isRead) return a.isRead ? 1 : -1;
      // Then by severity weight
      final severityOrder = {
        AlertSeverity.critical: 0,
        AlertSeverity.high: 1,
        AlertSeverity.medium: 2,
        AlertSeverity.low: 3,
      };
      final sevComp =
          severityOrder[a.severity]!.compareTo(severityOrder[b.severity]!);
      if (sevComp != 0) return sevComp;
      // Then by creation date, newest first
      return b.createdAt.compareTo(a.createdAt);
    });

    return filtered;
  }

  void _toggleExpanded(String id) {
    setState(() {
      if (_expandedIds.contains(id)) {
        _expandedIds.remove(id);
      } else {
        _expandedIds.add(id);
      }
    });
  }

  void _markAsRead(String id) {
    setState(() {
      final index = _alerts.indexWhere((a) => a.id == id);
      if (index != -1) {
        final alert = _alerts[index];
        _alerts[index] = RegulatoryAlert(
          id: alert.id,
          title: alert.title,
          description: alert.description,
          severity: alert.severity,
          isRead: true,
          domain: alert.domain,
          createdAt: alert.createdAt,
          impactSummary: alert.impactSummary,
          actions: alert.actions,
          effectiveDate: alert.effectiveDate,
        );
      }
    });
  }

  void _dismissAlert(String id) {
    setState(() {
      _alerts.removeWhere((a) => a.id == id);
      _expandedIds.remove(id);
    });
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _filteredAlerts;

    return Scaffold(
      backgroundColor: AppColors.surfaceBackground,
      appBar: AppBar(
        title: const Text('Regulatory Alerts'),
        backgroundColor: AppColors.primaryNavy,
        foregroundColor: AppColors.neutralWhite,
        elevation: 0,
        actions: [
          if (_unreadCount > 0)
            Padding(
              padding: const EdgeInsets.only(right: AppSpacing.base),
              child: Center(
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.sm,
                    vertical: AppSpacing.xs,
                  ),
                  decoration: BoxDecoration(
                    color: AppColors.riskRed,
                    borderRadius: AppRadius.full,
                  ),
                  child: Text(
                    '$_unreadCount',
                    style: AppTypography.caption.copyWith(
                      color: AppColors.neutralWhite,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Filter section
            _FilterSection(
              viewFilter: _viewFilter,
              severityFilter: _severityFilter,
              onViewFilterChanged: (filter) {
                setState(() => _viewFilter = filter);
              },
              onSeverityFilterChanged: (filter) {
                setState(() => _severityFilter = filter);
              },
            ),

            // Unread count banner
            if (_unreadCount > 0)
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.base,
                ),
                child: AlertBanner(
                  title: '$_unreadCount unread alert'
                      '${_unreadCount != 1 ? 's' : ''} '
                      'requiring your attention',
                  variant: _alerts.any((a) =>
                          !a.isRead &&
                          a.severity == AlertSeverity.critical)
                      ? AlertBannerVariant.error
                      : AlertBannerVariant.warning,
                ),
              ),

            const SizedBox(height: AppSpacing.sm),

            // Alert list
            Expanded(
              child: filtered.isEmpty
                  ? const EmptyState(
                      icon: Icons.notifications_outlined,
                      heading: 'No matching alerts',
                      description:
                          'Try adjusting the filters to see more alerts.',
                    )
                  : ListView.builder(
                      padding: const EdgeInsets.symmetric(
                        horizontal: AppSpacing.base,
                      ),
                      itemCount: filtered.length,
                      itemBuilder: (context, index) {
                        final alert = filtered[index];
                        return Padding(
                          padding: const EdgeInsets.only(
                            bottom: AppSpacing.md,
                          ),
                          child: _AlertCard(
                            alert: alert,
                            isExpanded: _expandedIds.contains(alert.id),
                            onTap: () => _toggleExpanded(alert.id),
                            onMarkAsRead: () => _markAsRead(alert.id),
                            onDismiss: () => _dismissAlert(alert.id),
                          ),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Filter Section ──────────────────────────────────────

class _FilterSection extends StatelessWidget {
  const _FilterSection({
    required this.viewFilter,
    required this.severityFilter,
    required this.onViewFilterChanged,
    required this.onSeverityFilterChanged,
  });

  final _ViewFilter viewFilter;
  final _SeverityFilter severityFilter;
  final ValueChanged<_ViewFilter> onViewFilterChanged;
  final ValueChanged<_SeverityFilter> onSeverityFilterChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppColors.surfaceCard,
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.base,
        AppSpacing.md,
        AppSpacing.base,
        AppSpacing.sm,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // View filter chips
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                _buildViewChip('All', _ViewFilter.all),
                const SizedBox(width: AppSpacing.sm),
                _buildViewChip('Affecting You', _ViewFilter.affectingYou),
                const SizedBox(width: AppSpacing.sm),
                _buildViewChip('Upcoming', _ViewFilter.upcoming),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          // Severity filter chips
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                _buildSeverityChip('All', _SeverityFilter.all),
                const SizedBox(width: AppSpacing.sm),
                _buildSeverityChip('Critical', _SeverityFilter.critical),
                const SizedBox(width: AppSpacing.sm),
                _buildSeverityChip('High', _SeverityFilter.high),
                const SizedBox(width: AppSpacing.sm),
                _buildSeverityChip('Medium', _SeverityFilter.medium),
                const SizedBox(width: AppSpacing.sm),
                _buildSeverityChip('Low', _SeverityFilter.low),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildViewChip(String label, _ViewFilter filter) {
    final isSelected = viewFilter == filter;
    return ChoiceChip(
      label: Text(
        label,
        style: AppTypography.caption.copyWith(
          color: isSelected ? AppColors.neutralWhite : AppColors.neutralGray700,
          fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
        ),
      ),
      selected: isSelected,
      onSelected: (_) => onViewFilterChanged(filter),
      selectedColor: AppColors.primaryNavy,
      backgroundColor: AppColors.neutralGray100,
      side: BorderSide.none,
      shape: RoundedRectangleBorder(borderRadius: AppRadius.full),
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm),
    );
  }

  Widget _buildSeverityChip(String label, _SeverityFilter filter) {
    final isSelected = severityFilter == filter;
    return ChoiceChip(
      label: Text(
        label,
        style: AppTypography.caption.copyWith(
          color: isSelected ? AppColors.neutralWhite : AppColors.neutralGray700,
          fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
        ),
      ),
      selected: isSelected,
      onSelected: (_) => onSeverityFilterChanged(filter),
      selectedColor: AppColors.primaryNavy,
      backgroundColor: AppColors.neutralGray100,
      side: BorderSide.none,
      shape: RoundedRectangleBorder(borderRadius: AppRadius.full),
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm),
    );
  }
}

// ── Alert Card ──────────────────────────────────────────

class _AlertCard extends StatelessWidget {
  const _AlertCard({
    required this.alert,
    required this.isExpanded,
    required this.onTap,
    required this.onMarkAsRead,
    required this.onDismiss,
  });

  final RegulatoryAlert alert;
  final bool isExpanded;
  final VoidCallback onTap;
  final VoidCallback onMarkAsRead;
  final VoidCallback onDismiss;

  @override
  Widget build(BuildContext context) {
    final severityColor = _severityColor(alert.severity);
    final dateFormat = DateFormat('d MMM yyyy');

    return AppCard(
      variant: AppCardVariant.standard,
      padding: EdgeInsets.zero,
      onTap: onTap,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Main content with colored left border
          Container(
            decoration: BoxDecoration(
              border: Border(
                left: BorderSide(
                  color: severityColor,
                  width: 4,
                ),
              ),
            ),
            padding: const EdgeInsets.all(AppSpacing.base),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Top row: unread dot + severity badge + date
                Row(
                  children: [
                    // Unread indicator
                    if (!alert.isRead)
                      Container(
                        width: 10,
                        height: 10,
                        margin: const EdgeInsets.only(right: AppSpacing.sm),
                        decoration: const BoxDecoration(
                          color: AppColors.semanticInfo,
                          shape: BoxShape.circle,
                        ),
                      ),

                    // Severity badge
                    _SeverityBadge(severity: alert.severity),

                    const Spacer(),

                    // Date
                    Text(
                      dateFormat.format(alert.createdAt),
                      style: AppTypography.caption.copyWith(
                        color: AppColors.neutralGray400,
                      ),
                    ),
                  ],
                ),

                const SizedBox(height: AppSpacing.md),

                // Title
                Text(
                  alert.title,
                  style: AppTypography.bodyMedium.copyWith(
                    color: AppColors.neutralGray900,
                  ),
                ),

                const SizedBox(height: AppSpacing.xs),

                // Description
                Text(
                  alert.description,
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.neutralGray600,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),

                const SizedBox(height: AppSpacing.md),

                // Domain tag and effective date
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: AppSpacing.sm,
                        vertical: AppSpacing.xs,
                      ),
                      decoration: BoxDecoration(
                        color: AppColors.neutralGray100,
                        borderRadius: AppRadius.sm,
                      ),
                      child: Text(
                        alert.domain,
                        style: AppTypography.caption.copyWith(
                          color: AppColors.neutralGray600,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                    const SizedBox(width: AppSpacing.sm),
                    Icon(
                      Icons.calendar_today_outlined,
                      size: 14,
                      color: AppColors.neutralGray400,
                    ),
                    const SizedBox(width: AppSpacing.xs),
                    Text(
                      'Effective ${dateFormat.format(alert.effectiveDate)}',
                      style: AppTypography.caption.copyWith(
                        color: AppColors.neutralGray400,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),

          // Expanded detail section
          if (isExpanded) _AlertDetail(
            alert: alert,
            onMarkAsRead: onMarkAsRead,
            onDismiss: onDismiss,
          ),
        ],
      ),
    );
  }
}

// ── Severity Badge ──────────────────────────────────────

class _SeverityBadge extends StatelessWidget {
  const _SeverityBadge({required this.severity});

  final AlertSeverity severity;

  @override
  Widget build(BuildContext context) {
    final color = _severityColor(severity);
    final bgColor = _severityBgColor(severity);
    final label = _severityLabel(severity);

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.sm,
        vertical: AppSpacing.xs,
      ),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: AppRadius.sm,
      ),
      child: Text(
        label,
        style: AppTypography.caption.copyWith(
          color: color,
          fontWeight: FontWeight.w700,
          fontSize: 11,
        ),
      ),
    );
  }
}

// ── Alert Detail (Expanded) ─────────────────────────────

class _AlertDetail extends StatelessWidget {
  const _AlertDetail({
    required this.alert,
    required this.onMarkAsRead,
    required this.onDismiss,
  });

  final RegulatoryAlert alert;
  final VoidCallback onMarkAsRead;
  final VoidCallback onDismiss;

  @override
  Widget build(BuildContext context) {
    final dateFormat = DateFormat('d MMM yyyy');

    return Container(
      decoration: const BoxDecoration(
        border: Border(
          top: BorderSide(color: AppColors.neutralGray200),
        ),
      ),
      padding: const EdgeInsets.all(AppSpacing.base),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Impact section
          Row(
            children: [
              const Icon(
                Icons.business_outlined,
                size: 18,
                color: AppColors.primaryNavy,
              ),
              const SizedBox(width: AppSpacing.sm),
              Text(
                'How this affects your company',
                style: AppTypography.bodyMedium.copyWith(
                  color: AppColors.primaryNavy,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            alert.impactSummary,
            style: AppTypography.bodySmall.copyWith(
              color: AppColors.neutralGray700,
            ),
          ),

          const SizedBox(height: AppSpacing.lg),

          // Action items
          Row(
            children: [
              const Icon(
                Icons.checklist_outlined,
                size: 18,
                color: AppColors.primaryNavy,
              ),
              const SizedBox(width: AppSpacing.sm),
              Text(
                'What you need to do',
                style: AppTypography.bodyMedium.copyWith(
                  color: AppColors.primaryNavy,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          ...List.generate(alert.actions.length, (index) {
            return Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.sm),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 24,
                    height: 24,
                    decoration: BoxDecoration(
                      color: AppColors.primaryNavy,
                      borderRadius: AppRadius.full,
                    ),
                    alignment: Alignment.center,
                    child: Text(
                      '${index + 1}',
                      style: AppTypography.caption.copyWith(
                        color: AppColors.neutralWhite,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  const SizedBox(width: AppSpacing.md),
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.only(top: 2),
                      child: Text(
                        alert.actions[index],
                        style: AppTypography.bodySmall.copyWith(
                          color: AppColors.neutralGray700,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            );
          }),

          const SizedBox(height: AppSpacing.md),

          // Effective date highlight
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(AppSpacing.md),
            decoration: BoxDecoration(
              color: AppColors.semanticInfoBg,
              borderRadius: AppRadius.md,
            ),
            child: Row(
              children: [
                const Icon(
                  Icons.event_outlined,
                  size: 18,
                  color: AppColors.semanticInfo,
                ),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: Text(
                    'Effective date: '
                    '${dateFormat.format(alert.effectiveDate)}',
                    style: AppTypography.bodySmall.copyWith(
                      color: AppColors.semanticInfo,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: AppSpacing.lg),

          // CTA buttons
          Row(
            children: [
              Expanded(
                child: AppButton(
                  label: 'Ask About This',
                  onPressed: () {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content:
                            Text('Opening advisory chat for this alert...'),
                      ),
                    );
                  },
                  variant: AppButtonVariant.primary,
                  icon: Icons.chat_outlined,
                  size: AppButtonSize.small,
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: AppButton(
                  label: 'Generate Policy',
                  onPressed: () {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('Generating updated policy draft...'),
                      ),
                    );
                  },
                  variant: AppButtonVariant.outlined,
                  icon: Icons.description_outlined,
                  size: AppButtonSize.small,
                ),
              ),
            ],
          ),

          const SizedBox(height: AppSpacing.md),

          // Text action buttons
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              if (!alert.isRead)
                TextButton.icon(
                  onPressed: onMarkAsRead,
                  icon: const Icon(
                    Icons.check_circle_outline,
                    size: 18,
                  ),
                  label: Text(
                    'Mark as Read',
                    style: AppTypography.bodySmall.copyWith(
                      color: AppColors.primaryNavy,
                    ),
                  ),
                  style: TextButton.styleFrom(
                    foregroundColor: AppColors.primaryNavy,
                  ),
                ),
              if (!alert.isRead)
                const SizedBox(width: AppSpacing.base),
              TextButton.icon(
                onPressed: onDismiss,
                icon: const Icon(
                  Icons.close,
                  size: 18,
                ),
                label: Text(
                  'Dismiss',
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.neutralGray500,
                  ),
                ),
                style: TextButton.styleFrom(
                  foregroundColor: AppColors.neutralGray500,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
