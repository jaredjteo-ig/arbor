import 'package:flutter/material.dart';

import '../../../core/design/components/components.dart';
import '../../../core/design/tokens/tokens.dart';
import '../logic/cpf_logic.dart';
import 'calculator_result_card.dart';
import 'result_row.dart';

/// CPF contribution calculator form.
class CpfForm extends StatefulWidget {
  const CpfForm({super.key});

  @override
  State<CpfForm> createState() => _CpfFormState();
}

class _CpfFormState extends State<CpfForm> {
  final _salaryCtrl = TextEditingController(text: '5000');
  final _ageCtrl = TextEditingController(text: '30');
  String _citizenship = 'SC';
  String _prYear = '2';
  CpfCalculation? _result;

  void _calculate() {
    final salary = double.tryParse(_salaryCtrl.text) ?? 0;
    final age = int.tryParse(_ageCtrl.text) ?? 30;
    setState(() {
      _result = CpfCalculation.calculate(
        salary: salary,
        age: age,
        citizenship: _citizenship,
        prYear: int.tryParse(_prYear) ?? 2,
      );
    });
  }

  @override
  void dispose() {
    _salaryCtrl.dispose();
    _ageCtrl.dispose();
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
        AppInput(
          type: AppInputType.number,
          label: 'Age',
          controller: _ageCtrl,
        ),
        const SizedBox(height: AppSpacing.base),
        AppInput(
          type: AppInputType.dropdown,
          label: 'Citizenship Status',
          dropdownValue: _citizenship,
          dropdownItems: const [
            DropdownMenuItem(value: 'SC', child: Text('Singapore Citizen')),
            DropdownMenuItem(value: 'PR', child: Text('Permanent Resident')),
            DropdownMenuItem(value: 'EP', child: Text('Employment Pass')),
          ],
          onDropdownChanged: (v) => setState(() => _citizenship = v ?? 'SC'),
        ),
        if (_citizenship == 'PR') ...[
          const SizedBox(height: AppSpacing.base),
          AppInput(
            type: AppInputType.dropdown,
            label: 'PR Graduated Year',
            dropdownValue: _prYear,
            dropdownItems: const [
              DropdownMenuItem(value: '1', child: Text('Year 1 (lower rates)')),
              DropdownMenuItem(value: '2', child: Text('Year 2+ (full rates)')),
            ],
            onDropdownChanged: (v) => setState(() => _prYear = v ?? '2'),
          ),
        ],
        const SizedBox(height: AppSpacing.xl),
        AppButton(
          label: 'Calculate CPF',
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

  Widget _buildResults(CpfCalculation r) {
    return CalculatorResultCard(
      title: 'CPF Contribution Breakdown',
      citations: const [
        (label: 'CPF Act (Cap 36)', level: AuthorityLevel.statutory),
        (label: 'CPF Contribution Rates 2025', level: AuthorityLevel.statutory),
      ],
      child: Column(
        children: [
          ResultRow(label: 'Gross Salary', value: '\$${r.grossSalary.toStringAsFixed(2)}'),
          ResultRow(label: 'Employee Rate', value: '${r.employeeRate.toStringAsFixed(1)}%'),
          ResultRow(label: 'Employer Rate', value: '${r.employerRate.toStringAsFixed(1)}%'),
          const ResultDivider(),
          ResultRow(label: 'Employee Contribution', value: '\$${r.employeeContribution.toStringAsFixed(2)}'),
          ResultRow(label: 'Employer Contribution', value: '\$${r.employerContribution.toStringAsFixed(2)}'),
          ResultRow(
            label: 'Total CPF',
            value: '\$${r.totalContribution.toStringAsFixed(2)}',
            isBold: true,
            valueColor: AppColors.primaryNavy,
          ),
          const ResultDivider(),
          ResultRow(
            label: 'Take-Home Pay',
            value: '\$${r.takeHomePay.toStringAsFixed(2)}',
            isBold: true,
            valueColor: AppColors.secondaryTeal,
          ),
        ],
      ),
    );
  }
}
