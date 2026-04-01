import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/design/components/components.dart';
import '../../../core/design/tokens/tokens.dart';
import '../../../core/providers/auth_providers.dart';

// ---------------------------------------------------------------------------
// Data class for company profile collected during onboarding
// ---------------------------------------------------------------------------

class OnboardingProfileData {
  String companyName;
  String sector;
  int totalHeadcount;
  int headcountLocal;
  int headcountPR;
  int headcountEP;
  int headcountSP;
  int headcountWP;
  int salaryRangeMin;
  int salaryRangeMax;

  OnboardingProfileData({
    this.companyName = '',
    this.sector = '',
    this.totalHeadcount = 0,
    this.headcountLocal = 0,
    this.headcountPR = 0,
    this.headcountEP = 0,
    this.headcountSP = 0,
    this.headcountWP = 0,
    this.salaryRangeMin = 0,
    this.salaryRangeMax = 0,
  });
}

// ---------------------------------------------------------------------------
// Main onboarding screen (4-step flow)
// ---------------------------------------------------------------------------

class OnboardingScreen extends ConsumerStatefulWidget {
  const OnboardingScreen({super.key});

  @override
  ConsumerState<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends ConsumerState<OnboardingScreen> {
  final _pageController = PageController();
  int _currentStep = 0;
  final _profile = OnboardingProfileData();

  static const _steps = ['Welcome', 'Company', 'Snapshot', 'Ask'];

  void _goToStep(int step) {
    setState(() => _currentStep = step);
    _pageController.animateToPage(
      step,
      duration: const Duration(milliseconds: 300),
      curve: Curves.easeInOut,
    );
  }

  void _next() => _goToStep(_currentStep + 1);
  void _back() => _goToStep(_currentStep - 1);

  void _completeOnboarding([String? question]) {
    ref.read(isOnboardedProvider.notifier).set(true);
    if (question != null && question.isNotEmpty) {
      context.go('/advisory');
    } else {
      context.go('/');
    }
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            // Step indicator
            Padding(
              padding: const EdgeInsets.fromLTRB(
                AppSpacing.base,
                AppSpacing.base,
                AppSpacing.base,
                AppSpacing.sm,
              ),
              child: StepIndicator(steps: _steps, currentStep: _currentStep),
            ),
            const Divider(height: 1),

            // Pages
            Expanded(
              child: PageView(
                controller: _pageController,
                physics: const NeverScrollableScrollPhysics(),
                children: [
                  _WelcomeStep(onNext: _next),
                  _CompanyProfileStep(
                    profile: _profile,
                    onNext: _next,
                    onBack: _back,
                  ),
                  _ComplianceSnapshotStep(
                    profile: _profile,
                    onNext: _next,
                    onBack: _back,
                  ),
                  _FirstQuestionStep(
                    profile: _profile,
                    onSubmit: (q) => _completeOnboarding(q),
                    onSkip: () => _completeOnboarding(),
                    onBack: _back,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Step 1: Welcome
// ---------------------------------------------------------------------------

class _WelcomeStep extends StatelessWidget {
  const _WelcomeStep({required this.onNext});
  final VoidCallback onNext;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.xl),
      child: Column(
        children: [
          const SizedBox(height: AppSpacing.s2xl),
          Container(
            width: 64,
            height: 64,
            decoration: const BoxDecoration(
              color: AppColors.primaryNavy,
              shape: BoxShape.circle,
            ),
            child: const Icon(
              Icons.business_outlined,
              size: 32,
              color: AppColors.neutralWhite,
            ),
          ),
          const SizedBox(height: AppSpacing.base),
          Text(
            'Welcome to Central',
            style: AppTypography.heading.copyWith(
              color: AppColors.neutralGray900,
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            'Your AI-powered HR advisory platform for Singapore SMEs.',
            textAlign: TextAlign.center,
            style: AppTypography.body.copyWith(
              color: AppColors.neutralGray600,
            ),
          ),
          const SizedBox(height: AppSpacing.s2xl),
          _FeatureCard(
            icon: Icons.shield_outlined,
            title: 'Compliance Guidance',
            description:
                'Get instant answers to HR questions with citations from Singapore employment law.',
          ),
          const SizedBox(height: AppSpacing.md),
          _FeatureCard(
            icon: Icons.calculate_outlined,
            title: 'Accurate Calculators',
            description:
                'Calculate CPF contributions, leave entitlements, and foreign worker quotas.',
          ),
          const SizedBox(height: AppSpacing.md),
          _FeatureCard(
            icon: Icons.description_outlined,
            title: 'Ready-Made Templates',
            description:
                'Download employment contracts, leave policies, and other HR documents.',
          ),
          const SizedBox(height: AppSpacing.md),
          _FeatureCard(
            icon: Icons.business_center_outlined,
            title: 'Company-Specific Advice',
            description:
                'Set up your company profile for tailored compliance recommendations.',
          ),
          const SizedBox(height: AppSpacing.s3xl),
          AppButton(
            label: 'Get Started',
            onPressed: onNext,
            fullWidth: true,
            size: AppButtonSize.large,
          ),
          const SizedBox(height: AppSpacing.xl),
        ],
      ),
    );
  }
}

class _FeatureCard extends StatelessWidget {
  const _FeatureCard({
    required this.icon,
    required this.title,
    required this.description,
  });

  final IconData icon;
  final String title;
  final String description;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: AppColors.primaryNavy.withValues(alpha: 0.1),
              borderRadius: AppRadius.sm,
            ),
            child: Icon(icon, size: 20, color: AppColors.primaryNavy),
          ),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: AppTypography.bodyMedium.copyWith(
                    color: AppColors.neutralGray900,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  description,
                  style: AppTypography.caption.copyWith(
                    color: AppColors.neutralGray500,
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
// Step 2: Company Profile
// ---------------------------------------------------------------------------

class _CompanyProfileStep extends StatefulWidget {
  const _CompanyProfileStep({
    required this.profile,
    required this.onNext,
    required this.onBack,
  });

  final OnboardingProfileData profile;
  final VoidCallback onNext;
  final VoidCallback onBack;

  @override
  State<_CompanyProfileStep> createState() => _CompanyProfileStepState();
}

class _CompanyProfileStepState extends State<_CompanyProfileStep> {
  late final TextEditingController _nameCtl;
  late final TextEditingController _headcountCtl;
  String? _selectedSector;
  bool _showWorkforce = false;
  bool _showSalary = false;

  // Workforce controllers
  late final TextEditingController _localCtl;
  late final TextEditingController _prCtl;
  late final TextEditingController _epCtl;
  late final TextEditingController _spCtl;
  late final TextEditingController _wpCtl;
  late final TextEditingController _salMinCtl;
  late final TextEditingController _salMaxCtl;

  static const _sectors = <String, String>{
    'services': 'Services (F&B, retail, hospitality)',
    'manufacturing': 'Manufacturing',
    'construction': 'Construction',
    'process': 'Process (chemicals, pharma)',
    'marine': 'Marine (shipyard, offshore)',
    'tech': 'Technology / IT',
    'finance': 'Financial Services',
    'healthcare': 'Healthcare',
    'education': 'Education',
    'other': 'Other',
  };

  @override
  void initState() {
    super.initState();
    final p = widget.profile;
    _nameCtl = TextEditingController(text: p.companyName);
    _headcountCtl = TextEditingController(
      text: p.totalHeadcount > 0 ? p.totalHeadcount.toString() : '',
    );
    _selectedSector = p.sector.isEmpty ? null : p.sector;
    _localCtl = TextEditingController(
      text: p.headcountLocal > 0 ? p.headcountLocal.toString() : '',
    );
    _prCtl = TextEditingController(
      text: p.headcountPR > 0 ? p.headcountPR.toString() : '',
    );
    _epCtl = TextEditingController(
      text: p.headcountEP > 0 ? p.headcountEP.toString() : '',
    );
    _spCtl = TextEditingController(
      text: p.headcountSP > 0 ? p.headcountSP.toString() : '',
    );
    _wpCtl = TextEditingController(
      text: p.headcountWP > 0 ? p.headcountWP.toString() : '',
    );
    _salMinCtl = TextEditingController(
      text: p.salaryRangeMin > 0 ? p.salaryRangeMin.toString() : '',
    );
    _salMaxCtl = TextEditingController(
      text: p.salaryRangeMax > 0 ? p.salaryRangeMax.toString() : '',
    );
  }

  @override
  void dispose() {
    _nameCtl.dispose();
    _headcountCtl.dispose();
    _localCtl.dispose();
    _prCtl.dispose();
    _epCtl.dispose();
    _spCtl.dispose();
    _wpCtl.dispose();
    _salMinCtl.dispose();
    _salMaxCtl.dispose();
    super.dispose();
  }

  bool get _canProceed =>
      _nameCtl.text.trim().isNotEmpty && _selectedSector != null;

  void _saveAndProceed() {
    final p = widget.profile;
    p.companyName = _nameCtl.text.trim();
    p.sector = _selectedSector ?? '';
    p.totalHeadcount = int.tryParse(_headcountCtl.text) ?? 0;
    p.headcountLocal = int.tryParse(_localCtl.text) ?? 0;
    p.headcountPR = int.tryParse(_prCtl.text) ?? 0;
    p.headcountEP = int.tryParse(_epCtl.text) ?? 0;
    p.headcountSP = int.tryParse(_spCtl.text) ?? 0;
    p.headcountWP = int.tryParse(_wpCtl.text) ?? 0;
    p.salaryRangeMin = int.tryParse(_salMinCtl.text) ?? 0;
    p.salaryRangeMax = int.tryParse(_salMaxCtl.text) ?? 0;
    widget.onNext();
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.xl),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Company Profile',
            style: AppTypography.title.copyWith(
              color: AppColors.neutralGray900,
            ),
          ),
          const SizedBox(height: AppSpacing.xs),
          Text(
            'Only company name and sector are required — fill in the rest later.',
            style: AppTypography.bodySmall.copyWith(
              color: AppColors.neutralGray500,
            ),
          ),
          const SizedBox(height: AppSpacing.xl),

          // Company name
          AppInput(
            label: 'Company Name',
            hintText: 'e.g. Acme Pte Ltd',
            controller: _nameCtl,
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: AppSpacing.base),

          // Sector
          AppInput(
            type: AppInputType.dropdown,
            label: 'Sector',
            dropdownValue: _selectedSector,
            dropdownItems: _sectors.entries
                .map(
                  (e) => DropdownMenuItem(value: e.key, child: Text(e.value)),
                )
                .toList(),
            onDropdownChanged: (v) => setState(() => _selectedSector = v),
            hintText: 'Select your sector',
          ),
          _WhyWeAsk(
            text:
                'Your sector determines foreign worker quota limits and levy rates.',
          ),
          const SizedBox(height: AppSpacing.base),

          // Total headcount
          AppInput(
            type: AppInputType.number,
            label: 'Total Employees',
            hintText: 'e.g. 25',
            controller: _headcountCtl,
          ),
          _WhyWeAsk(
            text: 'We use this to calculate your foreign worker quota headroom.',
          ),
          const SizedBox(height: AppSpacing.lg),

          // Workforce breakdown (collapsible)
          _CollapsibleSection(
            title: 'Workforce Breakdown (optional)',
            isExpanded: _showWorkforce,
            onToggle: () =>
                setState(() => _showWorkforce = !_showWorkforce),
            child: Column(
              children: [
                Row(
                  children: [
                    Expanded(
                      child: AppInput(
                        type: AppInputType.number,
                        label: 'Local (SC)',
                        controller: _localCtl,
                      ),
                    ),
                    const SizedBox(width: AppSpacing.md),
                    Expanded(
                      child: AppInput(
                        type: AppInputType.number,
                        label: 'PR',
                        controller: _prCtl,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: AppSpacing.md),
                Row(
                  children: [
                    Expanded(
                      child: AppInput(
                        type: AppInputType.number,
                        label: 'EP',
                        controller: _epCtl,
                      ),
                    ),
                    const SizedBox(width: AppSpacing.md),
                    Expanded(
                      child: AppInput(
                        type: AppInputType.number,
                        label: 'S Pass',
                        controller: _spCtl,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: AppSpacing.md),
                Row(
                  children: [
                    Expanded(
                      child: AppInput(
                        type: AppInputType.number,
                        label: 'WP',
                        controller: _wpCtl,
                      ),
                    ),
                    const Expanded(child: SizedBox()),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.md),

          // Salary range (collapsible)
          _CollapsibleSection(
            title: 'Salary Range (optional)',
            isExpanded: _showSalary,
            onToggle: () => setState(() => _showSalary = !_showSalary),
            child: Row(
              children: [
                Expanded(
                  child: AppInput(
                    type: AppInputType.number,
                    label: 'Minimum (\$)',
                    hintText: 'e.g. 2000',
                    controller: _salMinCtl,
                  ),
                ),
                const SizedBox(width: AppSpacing.md),
                Expanded(
                  child: AppInput(
                    type: AppInputType.number,
                    label: 'Maximum (\$)',
                    hintText: 'e.g. 8000',
                    controller: _salMaxCtl,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.s2xl),

          // Actions
          Row(
            children: [
              AppButton(
                label: 'Back',
                variant: AppButtonVariant.outlined,
                onPressed: widget.onBack,
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: AppButton(
                  label: 'Continue',
                  onPressed: _canProceed ? _saveAndProceed : null,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.xl),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Step 3: Compliance Snapshot
// ---------------------------------------------------------------------------

class _ComplianceSnapshotStep extends StatefulWidget {
  const _ComplianceSnapshotStep({
    required this.profile,
    required this.onNext,
    required this.onBack,
  });

  final OnboardingProfileData profile;
  final VoidCallback onNext;
  final VoidCallback onBack;

  @override
  State<_ComplianceSnapshotStep> createState() =>
      _ComplianceSnapshotStepState();
}

class _ComplianceSnapshotStepState extends State<_ComplianceSnapshotStep> {
  bool _loading = true;
  List<_ComplianceInsight> _insights = [];

  @override
  void initState() {
    super.initState();
    Future.delayed(const Duration(milliseconds: 1200), () {
      if (mounted) {
        setState(() {
          _insights = _generateInsights(widget.profile);
          _loading = false;
        });
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            LoadingState(),
            SizedBox(height: AppSpacing.base),
            Text('Analysing your company profile...'),
          ],
        ),
      );
    }

    final hasRed = _insights.any((i) => i.tier == RiskTier.red);
    final hasAmber = _insights.any((i) => i.tier == RiskTier.amber);
    final RiskTier overallTier = hasRed
        ? RiskTier.red
        : hasAmber
            ? RiskTier.amber
            : RiskTier.green;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.xl),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Compliance Snapshot',
            style: AppTypography.title.copyWith(
              color: AppColors.neutralGray900,
            ),
          ),
          const SizedBox(height: AppSpacing.xs),
          Text(
            'Quick overview based on your company profile.',
            style: AppTypography.bodySmall.copyWith(
              color: AppColors.neutralGray500,
            ),
          ),
          const SizedBox(height: AppSpacing.lg),

          // Overall gauge
          AppCard(
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Overall Compliance',
                        style: AppTypography.bodyMedium.copyWith(
                          color: AppColors.neutralGray700,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        hasRed
                            ? 'Action Required'
                            : hasAmber
                                ? 'Some Items Need Attention'
                                : 'Looking Good',
                        style: AppTypography.caption.copyWith(
                          color: AppColors.neutralGray500,
                        ),
                      ),
                    ],
                  ),
                ),
                RiskTierBadge(tier: overallTier),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.base),

          // Insight cards
          for (final insight in _insights) ...[
            _InsightCard(insight: insight),
            const SizedBox(height: AppSpacing.md),
          ],
          const SizedBox(height: AppSpacing.lg),

          // Actions
          Row(
            children: [
              AppButton(
                label: 'Back',
                variant: AppButtonVariant.outlined,
                onPressed: widget.onBack,
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: AppButton(
                  label: 'Ask Your First Question',
                  onPressed: widget.onNext,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.xl),
        ],
      ),
    );
  }
}

class _InsightCard extends StatelessWidget {
  const _InsightCard({required this.insight});
  final _ComplianceInsight insight;

  IconData get _icon => switch (insight.tier) {
        RiskTier.red => Icons.error_outline,
        RiskTier.amber => Icons.warning_amber_outlined,
        RiskTier.green => Icons.check_circle_outline,
      };

  Color get _iconColor => switch (insight.tier) {
        RiskTier.red => AppColors.riskRed,
        RiskTier.amber => AppColors.riskAmber,
        RiskTier.green => AppColors.riskGreen,
      };

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(_icon, size: 20, color: _iconColor),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        insight.title,
                        style: AppTypography.bodyMedium.copyWith(
                          color: AppColors.neutralGray900,
                        ),
                      ),
                    ),
                    RiskTierBadge(tier: insight.tier),
                  ],
                ),
                const SizedBox(height: AppSpacing.xs),
                Text(
                  insight.description,
                  style: AppTypography.caption.copyWith(
                    color: AppColors.neutralGray600,
                    height: 1.4,
                  ),
                ),
                const SizedBox(height: AppSpacing.xs),
                Text(
                  insight.category,
                  style: AppTypography.overline.copyWith(
                    color: AppColors.neutralGray400,
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
// Step 4: First Question
// ---------------------------------------------------------------------------

class _FirstQuestionStep extends StatefulWidget {
  const _FirstQuestionStep({
    required this.profile,
    required this.onSubmit,
    required this.onSkip,
    required this.onBack,
  });

  final OnboardingProfileData profile;
  final ValueChanged<String> onSubmit;
  final VoidCallback onSkip;
  final VoidCallback onBack;

  @override
  State<_FirstQuestionStep> createState() => _FirstQuestionStepState();
}

class _FirstQuestionStepState extends State<_FirstQuestionStep> {
  final _questionCtl = TextEditingController();

  static const _genericSuggestions = [
    'What are the minimum leave entitlements for my employees?',
    'How do I calculate CPF contributions?',
    'What notice period do I need to give for termination?',
    'What are the key employment terms I must provide?',
  ];

  static const _sectorSuggestions = <String, List<String>>{
    'services': [
      'What is the foreign worker quota limit for the services sector?',
      'How much levy do I pay for each S Pass and WP holder?',
    ],
    'manufacturing': [
      'What is the DRC limit for manufacturing?',
      'How do I manage overtime for production workers?',
    ],
    'construction': [
      'What is the DRC limit for construction?',
      'What bizSAFE level do I need?',
    ],
    'tech': [
      'Do I need to advertise on MyCareersFuture before hiring an EP holder?',
      'What are the COMPASS scoring criteria for EP applications?',
    ],
    'finance': [
      'What are the higher salary thresholds for financial services EP?',
      'How do I handle bonuses for CPF calculation?',
    ],
  };

  List<String> get _suggestions {
    final sector = _sectorSuggestions[widget.profile.sector] ?? [];
    return [...sector, ..._genericSuggestions].take(5).toList();
  }

  @override
  void dispose() {
    _questionCtl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.xl),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Ask Your First Question',
            style: AppTypography.title.copyWith(
              color: AppColors.neutralGray900,
            ),
          ),
          const SizedBox(height: AppSpacing.xs),
          Text(
            'Type any HR question in plain English (Singlish works too!), or pick a suggestion below.',
            style: AppTypography.bodySmall.copyWith(
              color: AppColors.neutralGray500,
            ),
          ),
          const SizedBox(height: AppSpacing.xl),

          // Question input
          Container(
            decoration: BoxDecoration(
              borderRadius: AppRadius.lg,
              border: Border.all(color: AppColors.neutralGray300),
            ),
            child: Column(
              children: [
                TextField(
                  controller: _questionCtl,
                  maxLines: 3,
                  autocorrect: false,
                  decoration: InputDecoration(
                    hintText:
                        'e.g. My staff resign already, need pay notice period or not?',
                    hintStyle: AppTypography.body.copyWith(
                      color: AppColors.neutralGray400,
                    ),
                    border: InputBorder.none,
                    contentPadding: const EdgeInsets.all(AppSpacing.base),
                  ),
                  onChanged: (_) => setState(() {}),
                ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(
                    AppSpacing.sm,
                    0,
                    AppSpacing.sm,
                    AppSpacing.sm,
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      VoiceInputButton(onPressed: () {}),
                      const SizedBox(width: AppSpacing.sm),
                      AppButton(
                        label: 'Send',
                        size: AppButtonSize.small,
                        icon: Icons.send,
                        onPressed: _questionCtl.text.trim().isNotEmpty
                            ? () =>
                                widget.onSubmit(_questionCtl.text.trim())
                            : null,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.xl),

          // Suggestions
          Text(
            'SUGGESTED QUESTIONS',
            style: AppTypography.overline.copyWith(
              color: AppColors.neutralGray500,
              letterSpacing: 1.2,
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          for (final suggestion in _suggestions) ...[
            _SuggestionTile(
              text: suggestion,
              onTap: () => widget.onSubmit(suggestion),
            ),
            const SizedBox(height: AppSpacing.sm),
          ],
          const SizedBox(height: AppSpacing.s2xl),

          // Actions
          Row(
            children: [
              AppButton(
                label: 'Back',
                variant: AppButtonVariant.outlined,
                onPressed: widget.onBack,
              ),
              const SizedBox(width: AppSpacing.md),
              Expanded(
                child: AppButton(
                  label: 'Skip — Go to Dashboard',
                  variant: AppButtonVariant.text,
                  onPressed: widget.onSkip,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.xl),
        ],
      ),
    );
  }
}

class _SuggestionTile extends StatelessWidget {
  const _SuggestionTile({required this.text, required this.onTap});
  final String text;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: () {
        HapticFeedback.lightImpact();
        onTap();
      },
      borderRadius: AppRadius.md,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.base,
          vertical: AppSpacing.md,
        ),
        decoration: BoxDecoration(
          borderRadius: AppRadius.md,
          border: Border.all(color: AppColors.neutralGray200),
        ),
        child: Row(
          children: [
            Expanded(
              child: Text(
                text,
                style: AppTypography.bodySmall.copyWith(
                  color: AppColors.neutralGray700,
                ),
              ),
            ),
            const SizedBox(width: AppSpacing.sm),
            const Icon(
              Icons.arrow_forward_ios,
              size: 14,
              color: AppColors.neutralGray400,
            ),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Shared widgets
// ---------------------------------------------------------------------------

class _WhyWeAsk extends StatefulWidget {
  const _WhyWeAsk({required this.text});
  final String text;

  @override
  State<_WhyWeAsk> createState() => _WhyWeAskState();
}

class _WhyWeAskState extends State<_WhyWeAsk> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () => setState(() => _expanded = !_expanded),
      child: Padding(
        padding: const EdgeInsets.only(top: AppSpacing.xs),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(
                  Icons.help_outline,
                  size: 14,
                  color: AppColors.primaryNavy,
                ),
                const SizedBox(width: 4),
                Text(
                  'Why do we ask this?',
                  style: AppTypography.caption.copyWith(
                    color: AppColors.primaryNavy,
                  ),
                ),
                Icon(
                  _expanded ? Icons.expand_less : Icons.expand_more,
                  size: 16,
                  color: AppColors.primaryNavy,
                ),
              ],
            ),
            if (_expanded)
              Padding(
                padding: const EdgeInsets.only(
                  top: AppSpacing.xs,
                  left: AppSpacing.lg,
                ),
                child: Text(
                  widget.text,
                  style: AppTypography.caption.copyWith(
                    color: AppColors.neutralGray500,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _CollapsibleSection extends StatelessWidget {
  const _CollapsibleSection({
    required this.title,
    required this.isExpanded,
    required this.onToggle,
    required this.child,
  });

  final String title;
  final bool isExpanded;
  final VoidCallback onToggle;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        GestureDetector(
          onTap: onToggle,
          child: Row(
            children: [
              Icon(
                isExpanded ? Icons.expand_less : Icons.expand_more,
                size: 20,
                color: AppColors.primaryNavy,
              ),
              const SizedBox(width: AppSpacing.xs),
              Text(
                title,
                style: AppTypography.bodyMedium.copyWith(
                  color: AppColors.primaryNavy,
                ),
              ),
            ],
          ),
        ),
        if (isExpanded)
          Padding(
            padding: const EdgeInsets.only(top: AppSpacing.md),
            child: AppCard(child: child),
          ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Compliance insight generation (deterministic, no LLM)
// ---------------------------------------------------------------------------

class _ComplianceInsight {
  final String title;
  final String description;
  final RiskTier tier;
  final String category;

  const _ComplianceInsight({
    required this.title,
    required this.description,
    required this.tier,
    required this.category,
  });
}

List<_ComplianceInsight> _generateInsights(OnboardingProfileData data) {
  final insights = <_ComplianceInsight>[];
  final totalForeign = data.headcountEP + data.headcountSP + data.headcountWP;
  final totalLocal = data.headcountLocal + data.headcountPR;

  // DRC check
  const drcLimits = {
    'services': 0.35,
    'manufacturing': 0.60,
    'construction': 0.875,
    'process': 0.60,
    'marine': 0.60,
  };
  final drc = drcLimits[data.sector];
  if (drc != null) {
    final total = totalLocal + totalForeign;
    final ratio = total > 0 ? totalForeign / total : 0.0;
    if (ratio > drc) {
      insights.add(_ComplianceInsight(
        title: 'Foreign Worker Quota Exceeded',
        description:
            'Your foreign worker ratio (${(ratio * 100).toStringAsFixed(0)}%) exceeds the ${data.sector} sector DRC limit of ${(drc * 100).toStringAsFixed(0)}%.',
        tier: RiskTier.red,
        category: 'Foreign Manpower',
      ));
    } else if (ratio > drc * 0.9) {
      insights.add(_ComplianceInsight(
        title: 'Approaching Foreign Worker Ceiling',
        description:
            'Your foreign worker ratio (${(ratio * 100).toStringAsFixed(0)}%) is close to the ${(drc * 100).toStringAsFixed(0)}% DRC limit.',
        tier: RiskTier.amber,
        category: 'Foreign Manpower',
      ));
    } else if (totalForeign > 0) {
      insights.add(_ComplianceInsight(
        title: 'Foreign Worker Quota Within Limits',
        description:
            'Your foreign worker ratio (${(ratio * 100).toStringAsFixed(0)}%) is within the ${(drc * 100).toStringAsFixed(0)}% DRC limit.',
        tier: RiskTier.green,
        category: 'Foreign Manpower',
      ));
    }
  }

  // CPF
  if (data.totalHeadcount > 0 || totalLocal > 0) {
    insights.add(_ComplianceInsight(
      title: 'CPF Contributions Required',
      description:
          'You must contribute CPF for all SC and PR employees. Use our CPF calculator to check exact amounts.',
      tier: RiskTier.green,
      category: 'CPF',
    ));
  }

  // EA coverage
  if (data.salaryRangeMin > 0 && data.salaryRangeMin <= 2600) {
    insights.add(_ComplianceInsight(
      title: 'Part IV Protections Apply',
      description:
          'Some employees earn \$2,600 or below — Part IV of the EA (hours, overtime, rest days) applies. Track overtime and pay at 1.5x.',
      tier: RiskTier.amber,
      category: 'Employment Act',
    ));
  } else {
    insights.add(_ComplianceInsight(
      title: 'Employment Act Applies',
      description:
          'All employees are covered by the Employment Act regardless of salary.',
      tier: RiskTier.green,
      category: 'Employment Act',
    ));
  }

  // TAFEP
  insights.add(_ComplianceInsight(
    title: 'Fair Consideration Framework',
    description:
        'Before hiring foreign workers on EP or S Pass, advertise on MyCareersFuture for 14 consecutive days.',
    tier: RiskTier.green,
    category: 'Fair Employment',
  ));

  // Levy
  if (data.headcountSP > 0 || data.headcountWP > 0) {
    final spLevy = data.headcountSP * 550;
    final wpLevy = data.headcountWP * 450;
    final totalLevy = spLevy + wpLevy;
    insights.add(_ComplianceInsight(
      title: 'Estimated Monthly Levy: \$${totalLevy.toString()}',
      description:
          '${data.headcountSP} S Pass (\$550/month) + ${data.headcountWP} WP (\$450/month). Use our quota calculator for exact figures.',
      tier: totalLevy > 5000 ? RiskTier.amber : RiskTier.green,
      category: 'Foreign Manpower',
    ));
  }

  return insights.take(5).toList();
}
