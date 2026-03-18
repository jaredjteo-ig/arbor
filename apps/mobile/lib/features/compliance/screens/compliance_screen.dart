import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../core/design/components/components.dart';
import '../../../core/design/tokens/tokens.dart';

// ── Data Models ─────────────────────────────────────────

@immutable
class _Finding {
  const _Finding({
    required this.domain,
    required this.issue,
    required this.severity,
    required this.recommendation,
    required this.provisionId,
    required this.deadline,
  });

  final String domain;
  final String issue;
  final String severity;
  final String recommendation;
  final String provisionId;
  final String deadline;
}

@immutable
class _InspectionItem {
  const _InspectionItem({
    required this.category,
    required this.item,
    required this.status,
    required this.provision,
  });

  final String category;
  final String item;
  final String status; // "pass" | "fail" | "unknown"
  final String provision;
}

@immutable
class _CheckResult {
  const _CheckResult({
    required this.score,
    required this.riskTier,
    required this.findings,
    required this.actionItems,
    required this.domainsChecked,
    required this.inspectionReadiness,
  });

  final int score;
  final String riskTier;
  final List<_Finding> findings;
  final List<String> actionItems;
  final List<String> domainsChecked;
  final List<_InspectionItem> inspectionReadiness;
}

// ── Checklist Item Definition ───────────────────────────

@immutable
class _CheckItem {
  const _CheckItem({
    required this.key,
    required this.label,
    required this.help,
  });

  final String key;
  final String label;
  final String help;
}

const List<_CheckItem> _checkItems = [
  _CheckItem(
    key: 'ket',
    label: 'KET issued to all employees',
    help: 'Key Employment Terms document per EA s95A',
  ),
  _CheckItem(
    key: 'contracts',
    label: 'Written employment contracts in place',
    help: 'For all employees',
  ),
  _CheckItem(
    key: 'payslips',
    label: 'Itemised payslip system operational',
    help: 'EA s88A requirement',
  ),
  _CheckItem(
    key: 'leave',
    label: 'Leave records maintained',
    help: 'EA Part XII compliance',
  ),
  _CheckItem(
    key: 'ot',
    label: 'Overtime records maintained',
    help: 'EA Part IV for eligible employees',
  ),
  _CheckItem(
    key: 'safety',
    label: 'Workplace safety policy in place',
    help: 'WSH Act requirement',
  ),
  _CheckItem(
    key: 'grievance',
    label: 'Grievance handling process established',
    help: 'TGFEP recommendation',
  ),
  _CheckItem(
    key: 'fwa',
    label: 'FWA policy implemented',
    help: 'TG-FWAR effective Dec 2024',
  ),
];

// ── Compliance Logic (client-side mirror of backend) ────

_CheckResult _runComplianceCheck({
  required Map<String, bool> inputs,
  required int companySize,
  required bool hasForeignWorkers,
}) {
  final findings = <_Finding>[];
  final actionItems = <String>[];

  if (inputs['ket'] != true) {
    findings.add(const _Finding(
      domain: 'Employment Act',
      issue: 'Key Employment Terms (KET) not issued to employees',
      severity: 'critical',
      recommendation:
          'Issue KET to all employees within 14 days of employment start. '
          'Fine up to \$5,000 per offence.',
      provisionId: 'EA-S95-KETs',
      deadline: 'Immediate',
    ));
    actionItems.add('Issue KET documents to all current employees');
  }

  if (inputs['contracts'] != true) {
    findings.add(const _Finding(
      domain: 'Employment Act',
      issue: 'No written employment contracts in place',
      severity: 'high',
      recommendation: 'Provide written contracts to all employees.',
      provisionId: 'EA-KET',
      deadline: 'Within 30 days',
    ));
    actionItems.add('Prepare and issue written employment contracts');
  }

  if (inputs['payslips'] != true) {
    findings.add(const _Finding(
      domain: 'Employment Act',
      issue: 'No itemised payslip system in place',
      severity: 'critical',
      recommendation:
          'Implement itemised payslips for every salary payment. '
          'Fine up to \$5,000 per offence (EA s88A).',
      provisionId: 'EA-S88A-payslip',
      deadline: 'Immediate',
    ));
    actionItems.add('Set up itemised payslip system');
  }

  if (inputs['leave'] != true) {
    findings.add(const _Finding(
      domain: 'Employment Act',
      issue: 'No leave records maintained',
      severity: 'high',
      recommendation:
          'Maintain accurate leave records for all employees.',
      provisionId: 'EA-PART-X-annual-leave',
      deadline: 'Within 14 days',
    ));
    actionItems.add('Set up leave tracking system');
  }

  if (inputs['ot'] != true) {
    findings.add(const _Finding(
      domain: 'Employment Act',
      issue: 'No overtime records maintained',
      severity: 'high',
      recommendation:
          'Maintain OT records for all Part IV eligible employees.',
      provisionId: 'EA-PART-IV-hours',
      deadline: 'Within 14 days',
    ));
    actionItems.add('Set up overtime tracking');
  }

  if (inputs['safety'] != true &&
      (hasForeignWorkers || companySize >= 10)) {
    findings.add(const _Finding(
      domain: 'Workplace Safety & Health',
      issue: 'No workplace safety and health policy',
      severity: 'high',
      recommendation: 'Develop and implement a WSH policy.',
      provisionId: 'WSHA-S12',
      deadline: 'Within 30 days',
    ));
    actionItems.add('Develop workplace safety policy');
  }

  if (inputs['grievance'] != true) {
    findings.add(const _Finding(
      domain: 'Fair Employment',
      issue: 'No formal grievance handling process',
      severity: 'medium',
      recommendation:
          'Establish a grievance handling process per TGFEP.',
      provisionId: 'TGFEP-GRIEVANCE',
      deadline: 'Within 60 days',
    ));
    actionItems.add('Establish grievance handling process');
  }

  if (inputs['fwa'] != true) {
    findings.add(const _Finding(
      domain: 'Fair Employment',
      issue: 'No FWA policy in place',
      severity: 'medium',
      recommendation:
          'Implement FWA policy per TG-FWAR guidelines (effective 1 Dec 2024).',
      provisionId: 'TGFWAR-request-process',
      deadline: 'Within 60 days',
    ));
    actionItems.add('Draft FWA policy');
  }

  // Score calculation
  const deductions = <String, int>{
    'critical': 20,
    'high': 10,
    'medium': 5,
    'low': 2,
  };

  var score = 100;
  for (final f in findings) {
    score -= deductions[f.severity] ?? 0;
  }
  score = math.max(0, score);

  final riskTier =
      score >= 80 ? 'green' : (score >= 50 ? 'amber' : 'red');

  final domainsChecked = <String>[
    'Employment Act',
    'CPF',
    'Workplace Safety & Health',
    'Fair Employment',
  ];
  if (hasForeignWorkers) {
    domainsChecked.add('Foreign Manpower');
  }

  // MOM inspection readiness
  final inspectionReadiness = <_InspectionItem>[
    _InspectionItem(
      category: 'Employment Records',
      item: 'KET issued to all employees',
      status: inputs['ket'] == true ? 'pass' : 'fail',
      provision: 'EA s95A',
    ),
    _InspectionItem(
      category: 'Employment Records',
      item: 'Written contracts available',
      status: inputs['contracts'] == true ? 'pass' : 'fail',
      provision: 'EA',
    ),
    _InspectionItem(
      category: 'Salary Records',
      item: 'Itemised payslips issued',
      status: inputs['payslips'] == true ? 'pass' : 'fail',
      provision: 'EA s88A',
    ),
    _InspectionItem(
      category: 'Leave & Hours',
      item: 'Leave records maintained',
      status: inputs['leave'] == true ? 'pass' : 'fail',
      provision: 'EA Part XII',
    ),
    _InspectionItem(
      category: 'Leave & Hours',
      item: 'Overtime records maintained',
      status: inputs['ot'] == true ? 'pass' : 'fail',
      provision: 'EA Part IV',
    ),
    _InspectionItem(
      category: 'Safety',
      item: 'WSH policy in place',
      status: inputs['safety'] == true
          ? 'pass'
          : (companySize >= 10 ? 'fail' : 'unknown'),
      provision: 'WSH Act',
    ),
    _InspectionItem(
      category: 'Fair Employment',
      item: 'Grievance process',
      status: inputs['grievance'] == true ? 'pass' : 'unknown',
      provision: 'TGFEP',
    ),
    _InspectionItem(
      category: 'Fair Employment',
      item: 'FWA policy',
      status: inputs['fwa'] == true ? 'pass' : 'unknown',
      provision: 'TG-FWAR',
    ),
  ];

  return _CheckResult(
    score: score,
    riskTier: riskTier,
    findings: findings,
    actionItems: actionItems,
    domainsChecked: domainsChecked,
    inspectionReadiness: inspectionReadiness,
  );
}

// ── Main Screen ─────────────────────────────────────────

/// Client-side compliance health check screen that evaluates a company's
/// posture against Singapore employment regulations.
class ComplianceScreen extends StatefulWidget {
  const ComplianceScreen({super.key});

  @override
  State<ComplianceScreen> createState() => _ComplianceScreenState();
}

class _ComplianceScreenState extends State<ComplianceScreen> {
  // Form state
  final _employeeController = TextEditingController(text: '10');
  bool _hasForeignWorkers = false;
  late Map<String, bool> _checkValues;

  // Results state
  _CheckResult? _result;

  @override
  void initState() {
    super.initState();
    _checkValues = {
      for (final item in _checkItems) item.key: false,
    };
  }

  @override
  void dispose() {
    _employeeController.dispose();
    super.dispose();
  }

  void _runCheck() {
    final companySize =
        int.tryParse(_employeeController.text) ?? 10;
    setState(() {
      _result = _runComplianceCheck(
        inputs: _checkValues,
        companySize: companySize,
        hasForeignWorkers: _hasForeignWorkers,
      );
    });
  }

  void _reset() {
    setState(() {
      _result = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.surfaceBackground,
      appBar: AppBar(
        title: const Text('Compliance Health Check'),
        backgroundColor: AppColors.primaryNavy,
        foregroundColor: AppColors.neutralWhite,
        elevation: 0,
      ),
      body: SafeArea(
        child: _result == null
            ? _ChecklistForm(
                employeeController: _employeeController,
                hasForeignWorkers: _hasForeignWorkers,
                checkValues: _checkValues,
                onForeignWorkersChanged: (value) {
                  setState(() => _hasForeignWorkers = value);
                },
                onCheckChanged: (key, value) {
                  setState(() => _checkValues[key] = value);
                },
                onRunCheck: _runCheck,
              )
            : _ResultsView(
                result: _result!,
                onReset: _reset,
              ),
      ),
    );
  }
}

// ── Checklist Form ──────────────────────────────────────

class _ChecklistForm extends StatelessWidget {
  const _ChecklistForm({
    required this.employeeController,
    required this.hasForeignWorkers,
    required this.checkValues,
    required this.onForeignWorkersChanged,
    required this.onCheckChanged,
    required this.onRunCheck,
  });

  final TextEditingController employeeController;
  final bool hasForeignWorkers;
  final Map<String, bool> checkValues;
  final ValueChanged<bool> onForeignWorkersChanged;
  final void Function(String key, bool value) onCheckChanged;
  final VoidCallback onRunCheck;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(AppSpacing.base),
      children: [
        // Header
        Row(
          children: [
            const Icon(
              Icons.shield_outlined,
              color: AppColors.primaryNavy,
              size: 28,
            ),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Compliance Health Check',
                    style: AppTypography.title.copyWith(
                      color: AppColors.neutralGray900,
                    ),
                  ),
                  const SizedBox(height: AppSpacing.xs),
                  Text(
                    'Verify your compliance posture across Singapore '
                    'employment regulations.',
                    style: AppTypography.bodySmall.copyWith(
                      color: AppColors.neutralGray500,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),

        const SizedBox(height: AppSpacing.xl),

        // Company profile
        AppCard(
          variant: AppCardVariant.standard,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Company Profile',
                style: AppTypography.subtitle.copyWith(
                  color: AppColors.neutralGray900,
                ),
              ),
              const SizedBox(height: AppSpacing.base),
              Text(
                'Number of employees',
                style: AppTypography.bodySmall.copyWith(
                  color: AppColors.neutralGray700,
                  fontWeight: FontWeight.w500,
                ),
              ),
              const SizedBox(height: AppSpacing.sm),
              TextField(
                controller: employeeController,
                keyboardType: TextInputType.number,
                inputFormatters: [
                  FilteringTextInputFormatter.digitsOnly,
                ],
                decoration: InputDecoration(
                  hintText: 'e.g. 10',
                  hintStyle: AppTypography.bodySmall.copyWith(
                    color: AppColors.neutralGray400,
                  ),
                  filled: true,
                  fillColor: AppColors.surfaceInput,
                  contentPadding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.md,
                    vertical: AppSpacing.md,
                  ),
                  border: OutlineInputBorder(
                    borderRadius: AppRadius.md,
                    borderSide: const BorderSide(
                      color: AppColors.neutralGray300,
                    ),
                  ),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: AppRadius.md,
                    borderSide: const BorderSide(
                      color: AppColors.neutralGray300,
                    ),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: AppRadius.md,
                    borderSide: const BorderSide(
                      color: AppColors.primaryNavy,
                      width: 2,
                    ),
                  ),
                ),
                style: AppTypography.bodySmall.copyWith(
                  color: AppColors.neutralGray900,
                ),
              ),
              const SizedBox(height: AppSpacing.base),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: Text(
                  'Company employs foreign workers',
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.neutralGray700,
                  ),
                ),
                value: hasForeignWorkers,
                onChanged: (value) => onForeignWorkersChanged(value),
                activeTrackColor: AppColors.primaryNavy,
              ),
            ],
          ),
        ),

        const SizedBox(height: AppSpacing.base),

        // Compliance checklist
        AppCard(
          variant: AppCardVariant.standard,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Compliance Checklist',
                style: AppTypography.subtitle.copyWith(
                  color: AppColors.neutralGray900,
                ),
              ),
              const SizedBox(height: AppSpacing.xs),
              Text(
                'Check each item that your company currently has in place.',
                style: AppTypography.caption.copyWith(
                  color: AppColors.neutralGray500,
                ),
              ),
              const SizedBox(height: AppSpacing.sm),
              ..._checkItems.map((item) => CheckboxListTile(
                    contentPadding: EdgeInsets.zero,
                    controlAffinity: ListTileControlAffinity.leading,
                    activeColor: AppColors.primaryNavy,
                    value: checkValues[item.key] ?? false,
                    onChanged: (value) =>
                        onCheckChanged(item.key, value ?? false),
                    title: Text(
                      item.label,
                      style: AppTypography.bodySmall.copyWith(
                        color: AppColors.neutralGray900,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    subtitle: Text(
                      item.help,
                      style: AppTypography.caption.copyWith(
                        color: AppColors.neutralGray500,
                      ),
                    ),
                  )),
            ],
          ),
        ),

        const SizedBox(height: AppSpacing.xl),

        // Run button
        AppButton(
          label: 'Run Compliance Check',
          onPressed: onRunCheck,
          icon: Icons.play_arrow_rounded,
          fullWidth: true,
        ),

        const SizedBox(height: AppSpacing.xl),
      ],
    );
  }
}

// ── Results View ────────────────────────────────────────

class _ResultsView extends StatelessWidget {
  const _ResultsView({
    required this.result,
    required this.onReset,
  });

  final _CheckResult result;
  final VoidCallback onReset;

  RiskTier get _riskTier {
    return switch (result.riskTier) {
      'green' => RiskTier.green,
      'amber' => RiskTier.amber,
      _ => RiskTier.red,
    };
  }

  Color get _tierColor {
    return switch (result.riskTier) {
      'green' => AppColors.riskGreen,
      'amber' => AppColors.riskAmber,
      _ => AppColors.riskRed,
    };
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: NestedScrollView(
        headerSliverBuilder: (context, innerBoxIsScrolled) {
          return [
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.all(AppSpacing.base),
                child: Column(
                  children: [
                    // Score card
                    _ScoreCard(
                      score: result.score,
                      riskTier: _riskTier,
                      tierColor: _tierColor,
                      findingsCount: result.findings.length,
                      domainsCount: result.domainsChecked.length,
                    ),
                    const SizedBox(height: AppSpacing.base),
                  ],
                ),
              ),
            ),
            SliverPersistentHeader(
              pinned: true,
              delegate: _TabBarDelegate(
                tabBar: TabBar(
                  labelColor: AppColors.primaryNavy,
                  unselectedLabelColor: AppColors.neutralGray500,
                  indicatorColor: AppColors.primaryNavy,
                  labelStyle: AppTypography.bodySmall.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                  unselectedLabelStyle: AppTypography.bodySmall,
                  tabs: [
                    Tab(
                      text: 'Findings (${result.findings.length})',
                    ),
                    const Tab(text: 'MOM Inspection'),
                  ],
                ),
              ),
            ),
          ];
        },
        body: TabBarView(
          children: [
            _FindingsTab(
              findings: result.findings,
              actionItems: result.actionItems,
            ),
            _InspectionTab(
              items: result.inspectionReadiness,
            ),
          ],
        ),
      ),
    );
  }
}

// ── Score Card ───────────────────────────────────────────

class _ScoreCard extends StatelessWidget {
  const _ScoreCard({
    required this.score,
    required this.riskTier,
    required this.tierColor,
    required this.findingsCount,
    required this.domainsCount,
  });

  final int score;
  final RiskTier riskTier;
  final Color tierColor;
  final int findingsCount;
  final int domainsCount;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      variant: AppCardVariant.elevated,
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Compliance Score',
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.neutralGray500,
                  ),
                ),
                const SizedBox(height: AppSpacing.sm),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.baseline,
                  textBaseline: TextBaseline.alphabetic,
                  children: [
                    Text(
                      '$score',
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
                const SizedBox(height: AppSpacing.sm),
                RiskTierBadge(tier: riskTier),
                const SizedBox(height: AppSpacing.sm),
                Text(
                  '$findingsCount finding${findingsCount != 1 ? 's' : ''} '
                  'across $domainsCount domains',
                  style: AppTypography.caption.copyWith(
                    color: AppColors.neutralGray500,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: AppSpacing.base),
          _CircularScoreIndicator(
            score: score,
            color: tierColor,
          ),
        ],
      ),
    );
  }
}

// ── Circular Score Indicator ────────────────────────────

class _CircularScoreIndicator extends StatelessWidget {
  const _CircularScoreIndicator({
    required this.score,
    required this.color,
  });

  final int score;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 80,
      height: 80,
      child: CustomPaint(
        painter: _ScoreRingPainter(
          progress: score / 100,
          color: color,
        ),
        child: Center(
          child: Text(
            '$score%',
            style: AppTypography.title.copyWith(
              color: AppColors.neutralGray900,
            ),
          ),
        ),
      ),
    );
  }
}

class _ScoreRingPainter extends CustomPainter {
  _ScoreRingPainter({
    required this.progress,
    required this.color,
  });

  final double progress;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2 - 4;

    // Background track
    final trackPaint = Paint()
      ..color = AppColors.neutralGray200
      ..style = PaintingStyle.stroke
      ..strokeWidth = 6
      ..strokeCap = StrokeCap.round;

    canvas.drawCircle(center, radius, trackPaint);

    // Progress arc
    final progressPaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 6
      ..strokeCap = StrokeCap.round;

    const startAngle = -math.pi / 2;
    final sweepAngle = 2 * math.pi * progress;

    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      startAngle,
      sweepAngle,
      false,
      progressPaint,
    );
  }

  @override
  bool shouldRepaint(_ScoreRingPainter oldDelegate) {
    return oldDelegate.progress != progress || oldDelegate.color != color;
  }
}

// ── Tab Bar Delegate ────────────────────────────────────

class _TabBarDelegate extends SliverPersistentHeaderDelegate {
  const _TabBarDelegate({required this.tabBar});

  final TabBar tabBar;

  @override
  double get minExtent => tabBar.preferredSize.height;

  @override
  double get maxExtent => tabBar.preferredSize.height;

  @override
  Widget build(
    BuildContext context,
    double shrinkOffset,
    bool overlapsContent,
  ) {
    return Container(
      color: AppColors.surfaceBackground,
      child: tabBar,
    );
  }

  @override
  bool shouldRebuild(_TabBarDelegate oldDelegate) => false;
}

// ── Findings Tab ────────────────────────────────────────

class _FindingsTab extends StatelessWidget {
  const _FindingsTab({
    required this.findings,
    required this.actionItems,
  });

  final List<_Finding> findings;
  final List<String> actionItems;

  @override
  Widget build(BuildContext context) {
    if (findings.isEmpty) {
      return const Center(
        child: EmptyState(
          icon: Icons.check_circle_outline,
          heading: 'All Clear',
          description:
              'No compliance issues found. Your company meets all checked requirements.',
        ),
      );
    }

    return ListView(
      padding: const EdgeInsets.all(AppSpacing.base),
      children: [
        // Group findings by severity
        for (final severity in const ['critical', 'high', 'medium', 'low'])
          ..._buildSeverityGroup(severity),

        // Action items
        if (actionItems.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.base),
          _ActionItemsCard(actionItems: actionItems),
        ],

        // Reset button
        const SizedBox(height: AppSpacing.xl),
        _buildResetButton(context),
        const SizedBox(height: AppSpacing.xl),
      ],
    );
  }

  List<Widget> _buildSeverityGroup(String severity) {
    final items =
        findings.where((f) => f.severity == severity).toList();
    if (items.isEmpty) return const [];

    return [
      Padding(
        padding: const EdgeInsets.only(
          top: AppSpacing.base,
          bottom: AppSpacing.sm,
        ),
        child: Text(
          '${severity.toUpperCase()} (${items.length})',
          style: AppTypography.overline.copyWith(
            color: _severityColor(severity),
          ),
        ),
      ),
      ...items.map((f) => Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.sm),
            child: _FindingCard(finding: f),
          )),
    ];
  }

  Widget _buildResetButton(BuildContext context) {
    // Walk up the tree to find the _ComplianceScreenState for reset
    final state =
        context.findAncestorStateOfType<_ComplianceScreenState>();
    return AppButton(
      label: 'Run Another Check',
      onPressed: state?._reset,
      variant: AppButtonVariant.outlined,
      icon: Icons.refresh_rounded,
      fullWidth: true,
    );
  }
}

// ── Finding Card ────────────────────────────────────────

Color _severityColor(String severity) {
  return switch (severity) {
    'critical' => AppColors.riskRed,
    'high' => AppColors.riskAmber,
    'medium' => AppColors.primaryNavy,
    _ => AppColors.neutralGray400,
  };
}

Color _severityBgColor(String severity) {
  return switch (severity) {
    'critical' => AppColors.riskRedBg,
    'high' => AppColors.riskAmberBg,
    'medium' => AppColors.semanticInfoBg,
    _ => AppColors.neutralGray100,
  };
}

class _FindingCard extends StatelessWidget {
  const _FindingCard({required this.finding});

  final _Finding finding;

  @override
  Widget build(BuildContext context) {
    final color = _severityColor(finding.severity);
    final bgColor = _severityBgColor(finding.severity);

    return AppCard(
      variant: AppCardVariant.standard,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Severity badge
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.sm,
                  vertical: AppSpacing.xs,
                ),
                decoration: BoxDecoration(
                  color: bgColor,
                  borderRadius: AppRadius.sm,
                ),
                child: Text(
                  finding.severity.toUpperCase(),
                  style: AppTypography.caption.copyWith(
                    color: color,
                    fontWeight: FontWeight.w700,
                    fontSize: 11,
                  ),
                ),
              ),
              const SizedBox(width: AppSpacing.md),
              // Issue title
              Expanded(
                child: Text(
                  finding.issue,
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.neutralGray900,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          // Recommendation
          Text(
            finding.recommendation,
            style: AppTypography.caption.copyWith(
              color: AppColors.neutralGray600,
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          // Metadata row
          Wrap(
            spacing: AppSpacing.sm,
            runSpacing: AppSpacing.sm,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Text(
                finding.domain,
                style: AppTypography.caption.copyWith(
                  color: AppColors.neutralGray400,
                ),
              ),
              Container(
                width: 3,
                height: 3,
                decoration: const BoxDecoration(
                  color: AppColors.neutralGray300,
                  shape: BoxShape.circle,
                ),
              ),
              Text(
                'Deadline: ${finding.deadline}',
                style: AppTypography.caption.copyWith(
                  color: AppColors.neutralGray400,
                ),
              ),
              SourceCitation(
                label: finding.provisionId,
                authorityLevel: AuthorityLevel.statutory,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// ── Action Items Card ───────────────────────────────────

class _ActionItemsCard extends StatefulWidget {
  const _ActionItemsCard({required this.actionItems});

  final List<String> actionItems;

  @override
  State<_ActionItemsCard> createState() => _ActionItemsCardState();
}

class _ActionItemsCardState extends State<_ActionItemsCard> {
  late List<bool> _checked;

  @override
  void initState() {
    super.initState();
    _checked = List.filled(widget.actionItems.length, false);
  }

  @override
  Widget build(BuildContext context) {
    return AppCard(
      variant: AppCardVariant.standard,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Action Items',
            style: AppTypography.subtitle.copyWith(
              color: AppColors.neutralGray900,
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          ...List.generate(widget.actionItems.length, (i) {
            return CheckboxListTile(
              contentPadding: EdgeInsets.zero,
              controlAffinity: ListTileControlAffinity.leading,
              activeColor: AppColors.secondaryTeal,
              value: _checked[i],
              onChanged: (value) {
                setState(() => _checked[i] = value ?? false);
              },
              title: Text(
                widget.actionItems[i],
                style: AppTypography.bodySmall.copyWith(
                  color: _checked[i]
                      ? AppColors.neutralGray400
                      : AppColors.neutralGray700,
                  decoration: _checked[i]
                      ? TextDecoration.lineThrough
                      : TextDecoration.none,
                ),
              ),
            );
          }),
        ],
      ),
    );
  }
}

// ── Inspection Tab ──────────────────────────────────────

class _InspectionTab extends StatelessWidget {
  const _InspectionTab({required this.items});

  final List<_InspectionItem> items;

  static const _categories = [
    'Employment Records',
    'Salary Records',
    'Leave & Hours',
    'Safety',
    'Fair Employment',
  ];

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(AppSpacing.base),
      children: [
        for (final category in _categories) ...[
          ..._buildCategory(category),
        ],
        // Reset button
        const SizedBox(height: AppSpacing.xl),
        _buildResetButton(context),
        const SizedBox(height: AppSpacing.xl),
      ],
    );
  }

  List<Widget> _buildCategory(String category) {
    final categoryItems =
        items.where((i) => i.category == category).toList();
    if (categoryItems.isEmpty) return const [];

    return [
      Padding(
        padding: const EdgeInsets.only(bottom: AppSpacing.sm),
        child: AppCard(
          variant: AppCardVariant.standard,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                category,
                style: AppTypography.subtitle.copyWith(
                  color: AppColors.neutralGray900,
                ),
              ),
              const SizedBox(height: AppSpacing.md),
              ...categoryItems.map((item) => _InspectionRow(item: item)),
            ],
          ),
        ),
      ),
    ];
  }

  Widget _buildResetButton(BuildContext context) {
    final state =
        context.findAncestorStateOfType<_ComplianceScreenState>();
    return AppButton(
      label: 'Run Another Check',
      onPressed: state?._reset,
      variant: AppButtonVariant.outlined,
      icon: Icons.refresh_rounded,
      fullWidth: true,
    );
  }
}

// ── Inspection Row ──────────────────────────────────────

class _InspectionRow extends StatelessWidget {
  const _InspectionRow({required this.item});

  final _InspectionItem item;

  IconData get _icon {
    return switch (item.status) {
      'pass' => Icons.check_circle,
      'fail' => Icons.cancel,
      _ => Icons.help_outline,
    };
  }

  Color get _iconColor {
    return switch (item.status) {
      'pass' => AppColors.riskGreen,
      'fail' => AppColors.riskRed,
      _ => AppColors.neutralGray400,
    };
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
      child: Row(
        children: [
          Icon(_icon, size: 20, color: _iconColor),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: Text(
              item.item,
              style: AppTypography.bodySmall.copyWith(
                color: AppColors.neutralGray700,
              ),
            ),
          ),
          Text(
            item.provision,
            style: AppTypography.caption.copyWith(
              color: AppColors.neutralGray400,
            ),
          ),
        ],
      ),
    );
  }
}
