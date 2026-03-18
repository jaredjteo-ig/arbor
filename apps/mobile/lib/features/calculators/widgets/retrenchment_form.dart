import 'package:flutter/material.dart';

import '../../../core/design/components/components.dart';
import '../../../core/design/tokens/tokens.dart';
import '../logic/retrenchment_logic.dart';
import 'calculator_result_card.dart';
import 'result_row.dart';

/// Retrenchment benefit estimator form.
class RetrenchmentForm extends StatefulWidget {
  const RetrenchmentForm({super.key});

  @override
  State<RetrenchmentForm> createState() => _RetrenchmentFormState();
}

class _RetrenchmentFormState extends State<RetrenchmentForm> {
  final _yearsCtrl = TextEditingController(text: '5');
  final _salaryCtrl = TextEditingController(text: '5000');
  String _sector = 'Services';
  RetrenchmentCalculation? _result;

  void _calculate() {
    setState(() {
      _result = RetrenchmentCalculation.calculate(
        yearsOfService: int.tryParse(_yearsCtrl.text) ?? 0,
        monthlySalary: double.tryParse(_salaryCtrl.text) ?? 0,
        sector: _sector,
      );
    });
  }

  @override
  void dispose() {
    _yearsCtrl.dispose();
    _salaryCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        AppInput(
          type: AppInputType.number,
          label: 'Years of Service',
          controller: _yearsCtrl,
          prefixIcon: const Icon(Icons.work_history),
        ),
        const SizedBox(height: AppSpacing.base),
        AppInput(
          type: AppInputType.number,
          label: 'Monthly Salary (SGD)',
          controller: _salaryCtrl,
          prefixIcon: const Icon(Icons.attach_money),
        ),
        const SizedBox(height: AppSpacing.base),
        AppInput(
          type: AppInputType.dropdown,
          label: 'Sector',
          dropdownValue: _sector,
          dropdownItems: const [
            DropdownMenuItem(value: 'Manufacturing', child: Text('Manufacturing')),
            DropdownMenuItem(value: 'Services', child: Text('Services')),
            DropdownMenuItem(value: 'Construction', child: Text('Construction')),
            DropdownMenuItem(value: 'Technology', child: Text('Technology')),
            DropdownMenuItem(value: 'Finance', child: Text('Finance')),
          ],
          onDropdownChanged: (v) => setState(() => _sector = v ?? 'Services'),
        ),
        const SizedBox(height: AppSpacing.xl),
        AppButton(
          label: 'Estimate Benefits',
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

  Widget _buildResults(RetrenchmentCalculation r) {
    return CalculatorResultCard(
      title: 'Retrenchment Benefit Estimate',
      citations: const [
        (
          label: 'Tripartite Advisory on Managing Excess Manpower',
          level: AuthorityLevel.guideline,
        ),
        (
          label: 'MOM Retrenchment Guide',
          level: AuthorityLevel.guideline,
        ),
      ],
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          RiskTierBadge(
            tier: RiskTier.amber,
            label: 'Market Norm (Not Statutory)',
          ),
          const SizedBox(height: AppSpacing.md),
          ResultRow(label: 'Market Range', value: r.weeksPerYear),
          const ResultDivider(),
          ResultRow(label: 'Low Estimate', value: '\$${r.lowEstimate.toStringAsFixed(2)}'),
          ResultRow(
            label: 'Mid Estimate',
            value: '\$${r.midEstimate.toStringAsFixed(2)}',
            isBold: true,
            valueColor: AppColors.primaryNavy,
          ),
          ResultRow(label: 'High Estimate', value: '\$${r.highEstimate.toStringAsFixed(2)}'),
        ],
      ),
    );
  }
}
