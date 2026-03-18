import 'package:flutter/material.dart';

import '../../../core/design/components/components.dart';
import '../../../core/design/tokens/tokens.dart';
import '../logic/notice_period_logic.dart';
import 'calculator_result_card.dart';
import 'result_row.dart';

/// Notice period calculator form.
class NoticePeriodForm extends StatefulWidget {
  const NoticePeriodForm({super.key});

  @override
  State<NoticePeriodForm> createState() => _NoticePeriodFormState();
}

class _NoticePeriodFormState extends State<NoticePeriodForm> {
  final _yearsCtrl = TextEditingController(text: '3');
  final _salaryCtrl = TextEditingController(text: '5000');
  final _contractualCtrl = TextEditingController(text: '0');
  String _terminatedBy = 'Employer';
  NoticePeriodCalculation? _result;

  void _calculate() {
    setState(() {
      _result = NoticePeriodCalculation.calculate(
        yearsOfService: int.tryParse(_yearsCtrl.text) ?? 0,
        monthlySalary: double.tryParse(_salaryCtrl.text) ?? 0,
        contractualWeeks: int.tryParse(_contractualCtrl.text) ?? 0,
        terminatedBy: _terminatedBy,
      );
    });
  }

  @override
  void dispose() {
    _yearsCtrl.dispose();
    _salaryCtrl.dispose();
    _contractualCtrl.dispose();
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
          type: AppInputType.number,
          label: 'Contractual Notice (weeks, 0 = statutory)',
          controller: _contractualCtrl,
          helperText: 'Leave as 0 to use statutory default',
        ),
        const SizedBox(height: AppSpacing.base),
        AppInput(
          type: AppInputType.dropdown,
          label: 'Terminated By',
          dropdownValue: _terminatedBy,
          dropdownItems: const [
            DropdownMenuItem(value: 'Employer', child: Text('Employer')),
            DropdownMenuItem(value: 'Employee', child: Text('Employee')),
          ],
          onDropdownChanged: (v) =>
              setState(() => _terminatedBy = v ?? 'Employer'),
        ),
        const SizedBox(height: AppSpacing.xl),
        AppButton(
          label: 'Calculate Notice',
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

  Widget _buildResults(NoticePeriodCalculation r) {
    return CalculatorResultCard(
      title: 'Notice Period',
      citations: const [
        (label: 'Employment Act s10-11', level: AuthorityLevel.statutory),
      ],
      child: Column(
        children: [
          ResultRow(label: 'Basis', value: r.source),
          ResultRow(label: 'Terminated By', value: r.terminatedBy),
          const ResultDivider(),
          ResultRow(
            label: 'Notice Period',
            value: '${r.noticeWeeks} week${r.noticeWeeks == 1 ? '' : 's'}',
            isBold: true,
            valueColor: AppColors.primaryNavy,
          ),
          ResultRow(
            label: 'Salary in Lieu',
            value: '\$${r.salaryInLieu.toStringAsFixed(2)}',
            isBold: true,
            valueColor: AppColors.secondaryTeal,
          ),
        ],
      ),
    );
  }
}
