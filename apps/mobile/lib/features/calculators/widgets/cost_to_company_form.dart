import 'package:flutter/material.dart';

import '../../../core/design/components/components.dart';
import '../../../core/design/tokens/tokens.dart';
import '../logic/cost_to_company_logic.dart';
import 'calculator_result_card.dart';
import 'result_row.dart';

/// Cost-to-company calculator form.
class CostToCompanyForm extends StatefulWidget {
  const CostToCompanyForm({super.key});

  @override
  State<CostToCompanyForm> createState() => _CostToCompanyFormState();
}

class _CostToCompanyFormState extends State<CostToCompanyForm> {
  final _salaryCtrl = TextEditingController(text: '5000');
  final _ageCtrl = TextEditingController(text: '30');
  String _citizenship = 'SC';
  String _passType = 'EP';
  String _sector = 'Services';
  CostToCompanyCalculation? _result;

  void _calculate() {
    setState(() {
      _result = CostToCompanyCalculation.calculate(
        grossSalary: double.tryParse(_salaryCtrl.text) ?? 0,
        citizenship: _citizenship,
        age: int.tryParse(_ageCtrl.text) ?? 30,
        passType: _passType,
        sector: _sector,
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
    final isForeign = _citizenship != 'SC' && _citizenship != 'PR';

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
          type: AppInputType.dropdown,
          label: 'Citizenship Status',
          dropdownValue: _citizenship,
          dropdownItems: const [
            DropdownMenuItem(value: 'SC', child: Text('Singapore Citizen')),
            DropdownMenuItem(value: 'PR', child: Text('Permanent Resident')),
            DropdownMenuItem(value: 'Foreign', child: Text('Foreign Worker')),
          ],
          onDropdownChanged: (v) {
            setState(() {
              _citizenship = v ?? 'SC';
              if (_citizenship == 'SC' || _citizenship == 'PR') {
                _passType = 'N/A';
              } else {
                _passType = 'EP';
              }
            });
          },
        ),
        const SizedBox(height: AppSpacing.base),
        AppInput(
          type: AppInputType.number,
          label: 'Age',
          controller: _ageCtrl,
        ),
        if (isForeign) ...[
          const SizedBox(height: AppSpacing.base),
          AppInput(
            type: AppInputType.dropdown,
            label: 'Pass Type',
            dropdownValue: _passType,
            dropdownItems: const [
              DropdownMenuItem(value: 'EP', child: Text('Employment Pass')),
              DropdownMenuItem(value: 'SP', child: Text('S Pass')),
              DropdownMenuItem(value: 'WP', child: Text('Work Permit')),
            ],
            onDropdownChanged: (v) =>
                setState(() => _passType = v ?? 'EP'),
          ),
        ],
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
          onDropdownChanged: (v) =>
              setState(() => _sector = v ?? 'Services'),
        ),
        const SizedBox(height: AppSpacing.xl),
        AppButton(
          label: 'Calculate Total Cost',
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

  Widget _buildResults(CostToCompanyCalculation r) {
    return CalculatorResultCard(
      title: 'Cost-to-Company Breakdown',
      citations: const [
        (label: 'CPF Act (Cap 36)', level: AuthorityLevel.statutory),
        (label: 'Skills Development Levy Act', level: AuthorityLevel.statutory),
        (label: 'Employment of Foreign Manpower Act', level: AuthorityLevel.statutory),
      ],
      child: Column(
        children: [
          ResultRow(
            label: 'Gross Salary',
            value: '\$${r.grossSalary.toStringAsFixed(2)}',
          ),
          const ResultDivider(),
          ResultRow(
            label: 'CPF (Employer)',
            value: '\$${r.cpfEmployer.toStringAsFixed(2)}',
          ),
          ResultRow(
            label: 'CPF (Employee)',
            value: '\$${r.cpfEmployee.toStringAsFixed(2)}',
          ),
          ResultRow(
            label: 'SDL',
            value: '\$${r.sdl.toStringAsFixed(2)}',
          ),
          if (r.fwLevy > 0)
            ResultRow(
              label: 'FW Levy (${r.passType})',
              value: '\$${r.fwLevy.toStringAsFixed(2)}',
            ),
          const ResultDivider(),
          ResultRow(
            label: 'Total Monthly Cost',
            value: '\$${r.totalMonthlyCost.toStringAsFixed(2)}',
            isBold: true,
            valueColor: AppColors.primaryNavy,
          ),
          ResultRow(
            label: 'Total Annual Cost',
            value: '\$${r.totalAnnualCost.toStringAsFixed(2)}',
            isBold: true,
            valueColor: AppColors.primaryNavy,
          ),
          const ResultDivider(),
          ResultRow(
            label: 'Employee Take-Home',
            value: '\$${r.employeeTakeHome.toStringAsFixed(2)}',
            isBold: true,
            valueColor: AppColors.secondaryTeal,
          ),
        ],
      ),
    );
  }
}
