import 'package:flutter/material.dart';

import '../../../core/design/components/components.dart';
import '../../../core/design/tokens/tokens.dart';
import '../logic/overtime_logic.dart';
import 'calculator_result_card.dart';
import 'result_row.dart';

/// Overtime pay calculator form.
class OvertimeForm extends StatefulWidget {
  const OvertimeForm({super.key});

  @override
  State<OvertimeForm> createState() => _OvertimeFormState();
}

class _OvertimeFormState extends State<OvertimeForm> {
  final _salaryCtrl = TextEditingController(text: '3000');
  final _hoursCtrl = TextEditingController(text: '10');
  bool _isWorkman = true;
  String _dayType = 'Normal';
  OvertimeCalculation? _result;

  void _calculate() {
    setState(() {
      _result = OvertimeCalculation.calculate(
        monthlySalary: double.tryParse(_salaryCtrl.text) ?? 0,
        isWorkman: _isWorkman,
        otHours: double.tryParse(_hoursCtrl.text) ?? 0,
        dayType: _dayType,
      );
    });
  }

  @override
  void dispose() {
    _salaryCtrl.dispose();
    _hoursCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        AppInput(
          type: AppInputType.number,
          label: 'Monthly Salary (SGD)',
          controller: _salaryCtrl,
          prefixIcon: const Icon(Icons.attach_money),
        ),
        const SizedBox(height: AppSpacing.base),
        SwitchListTile(
          title: Text(
            'Is Workman?',
            style: AppTypography.body.copyWith(color: AppColors.neutralGray900),
          ),
          subtitle: Text(
            'Manual labour, machine operators, transport workers, etc.',
            style: AppTypography.caption.copyWith(
              color: AppColors.neutralGray500,
            ),
          ),
          value: _isWorkman,
          onChanged: (v) => setState(() => _isWorkman = v),
          activeThumbColor: AppColors.primaryNavy,
          contentPadding: EdgeInsets.zero,
        ),
        const SizedBox(height: AppSpacing.base),
        AppInput(
          type: AppInputType.number,
          label: 'Overtime Hours',
          controller: _hoursCtrl,
          prefixIcon: const Icon(Icons.access_time),
        ),
        const SizedBox(height: AppSpacing.base),
        AppInput(
          type: AppInputType.dropdown,
          label: 'Day Type',
          dropdownValue: _dayType,
          dropdownItems: const [
            DropdownMenuItem(value: 'Normal', child: Text('Normal Work Day')),
            DropdownMenuItem(value: 'Rest day', child: Text('Rest Day')),
            DropdownMenuItem(
              value: 'Public holiday',
              child: Text('Public Holiday'),
            ),
          ],
          onDropdownChanged: (v) =>
              setState(() => _dayType = v ?? 'Normal'),
        ),
        const SizedBox(height: AppSpacing.xl),
        AppButton(
          label: 'Calculate OT Pay',
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

  Widget _buildResults(OvertimeCalculation r) {
    return CalculatorResultCard(
      title: 'Overtime Pay',
      citations: const [
        (label: 'Employment Act Part IV', level: AuthorityLevel.statutory),
      ],
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          RiskTierBadge(
            tier: r.isEligible ? RiskTier.green : RiskTier.red,
            label: r.isEligible ? 'OT Eligible' : 'Not Eligible',
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            r.eligibilityReason,
            style: AppTypography.caption.copyWith(
              color: AppColors.neutralGray600,
            ),
          ),
          const ResultDivider(),
          ResultRow(
            label: 'Hourly Rate',
            value: '\$${r.hourlyRate.toStringAsFixed(2)}',
          ),
          ResultRow(
            label: 'OT Multiplier',
            value: '${r.otMultiplier}x',
          ),
          ResultRow(
            label: 'OT Hours',
            value: '${r.otHours}',
          ),
          const ResultDivider(),
          ResultRow(
            label: 'Total OT Pay',
            value: r.isEligible
                ? '\$${r.otPay.toStringAsFixed(2)}'
                : 'N/A',
            isBold: true,
            valueColor: r.isEligible
                ? AppColors.secondaryTeal
                : AppColors.neutralGray400,
          ),
        ],
      ),
    );
  }
}
