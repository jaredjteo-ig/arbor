import 'package:flutter/material.dart';

import '../../../core/design/components/components.dart';
import '../../../core/design/tokens/tokens.dart';
import '../logic/quota_levy_logic.dart';
import 'calculator_result_card.dart';
import 'result_row.dart';

/// Quota and Levy calculator form.
class QuotaLevyForm extends StatefulWidget {
  const QuotaLevyForm({super.key});

  @override
  State<QuotaLevyForm> createState() => _QuotaLevyFormState();
}

class _QuotaLevyFormState extends State<QuotaLevyForm> {
  String _sector = 'Services';
  final _localCtrl = TextEditingController(text: '10');
  final _wpCtrl = TextEditingController(text: '3');
  final _spCtrl = TextEditingController(text: '2');
  QuotaLevyCalculation? _result;

  void _calculate() {
    setState(() {
      _result = QuotaLevyCalculation.calculate(
        sector: _sector,
        localCount: int.tryParse(_localCtrl.text) ?? 0,
        wpCount: int.tryParse(_wpCtrl.text) ?? 0,
        spCount: int.tryParse(_spCtrl.text) ?? 0,
      );
    });
  }

  @override
  void dispose() {
    _localCtrl.dispose();
    _wpCtrl.dispose();
    _spCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        AppInput(
          type: AppInputType.dropdown,
          label: 'Sector',
          dropdownValue: _sector,
          dropdownItems: const [
            DropdownMenuItem(value: 'Manufacturing', child: Text('Manufacturing')),
            DropdownMenuItem(value: 'Services', child: Text('Services')),
            DropdownMenuItem(value: 'Construction', child: Text('Construction')),
            DropdownMenuItem(value: 'Process', child: Text('Process')),
            DropdownMenuItem(value: 'Marine', child: Text('Marine')),
          ],
          onDropdownChanged: (v) => setState(() => _sector = v ?? 'Services'),
        ),
        const SizedBox(height: AppSpacing.base),
        AppInput(
          type: AppInputType.number,
          label: 'Local Workers',
          controller: _localCtrl,
          prefixIcon: const Icon(Icons.person),
        ),
        const SizedBox(height: AppSpacing.base),
        AppInput(
          type: AppInputType.number,
          label: 'Work Permit Holders',
          controller: _wpCtrl,
          prefixIcon: const Icon(Icons.badge),
        ),
        const SizedBox(height: AppSpacing.base),
        AppInput(
          type: AppInputType.number,
          label: 'S Pass Holders',
          controller: _spCtrl,
          prefixIcon: const Icon(Icons.badge_outlined),
        ),
        const SizedBox(height: AppSpacing.xl),
        AppButton(
          label: 'Check Quota & Levy',
          onPressed: _calculate,
          fullWidth: true,
          icon: Icons.calculate,
        ),
        if (_result != null) ...[
          const SizedBox(height: AppSpacing.xl),
          _buildResults(_result!),
        ],
      ],
    );
  }

  Widget _buildResults(QuotaLevyCalculation r) {
    return CalculatorResultCard(
      title: 'Quota & Levy Results',
      citations: const [
        (label: 'Employment of Foreign Manpower Act', level: AuthorityLevel.statutory),
        (label: 'MOM Levy Schedule 2025', level: AuthorityLevel.statutory),
      ],
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ResultRow(label: 'Total Headcount', value: '${r.totalHeadcount}'),
          ResultRow(label: 'Foreign Worker Ratio', value: '${r.foreignRatio.toStringAsFixed(1)}%'),
          ResultRow(label: 'DRC Limit (${ r.sector})', value: '${r.drcLimit.toStringAsFixed(1)}%'),
          const ResultDivider(),
          RiskTierBadge(
            tier: r.withinQuota ? RiskTier.green : RiskTier.red,
            label: r.withinQuota ? 'Within Quota' : 'Exceeds Quota',
          ),
          const SizedBox(height: AppSpacing.md),
          const ResultDivider(),
          for (final entry in r.levyBreakdown.entries)
            ResultRow(label: entry.key, value: '\$${entry.value.toStringAsFixed(2)}'),
          const ResultDivider(),
          ResultRow(
            label: 'Total Monthly Levy',
            value: '\$${r.estimatedMonthlyLevy.toStringAsFixed(2)}',
            isBold: true,
            valueColor: AppColors.primaryNavy,
          ),
        ],
      ),
    );
  }
}
