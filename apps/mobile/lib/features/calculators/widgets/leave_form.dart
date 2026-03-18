import 'package:flutter/material.dart';

import '../../../core/design/components/components.dart';
import '../../../core/design/tokens/tokens.dart';
import '../logic/leave_logic.dart';
import 'calculator_result_card.dart';
import 'result_row.dart';

/// Leave entitlement calculator form.
class LeaveForm extends StatefulWidget {
  const LeaveForm({super.key});

  @override
  State<LeaveForm> createState() => _LeaveFormState();
}

class _LeaveFormState extends State<LeaveForm> {
  final _yearsCtrl = TextEditingController(text: '3');
  String _employmentType = 'Full-time';
  LeaveCalculation? _result;

  void _calculate() {
    setState(() {
      _result = LeaveCalculation.calculate(
        yearsOfService: int.tryParse(_yearsCtrl.text) ?? 0,
        employmentType: _employmentType,
      );
    });
  }

  @override
  void dispose() {
    _yearsCtrl.dispose();
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
          type: AppInputType.dropdown,
          label: 'Employment Type',
          dropdownValue: _employmentType,
          dropdownItems: const [
            DropdownMenuItem(value: 'Full-time', child: Text('Full-time')),
            DropdownMenuItem(value: 'Part-time', child: Text('Part-time')),
          ],
          onDropdownChanged: (v) =>
              setState(() => _employmentType = v ?? 'Full-time'),
        ),
        const SizedBox(height: AppSpacing.xl),
        AppButton(
          label: 'Calculate Leave',
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

  Widget _buildResults(LeaveCalculation r) {
    return CalculatorResultCard(
      title: 'Leave Entitlements',
      citations: const [
        (
          label: 'Employment Act (Part XII)',
          level: AuthorityLevel.statutory
        ),
        (
          label: "Child Development Co-Savings Act",
          level: AuthorityLevel.statutory
        ),
      ],
      child: Column(
        children: [
          ResultRow(
            label: 'Annual Leave',
            value: '${r.annualLeave} days',
            isBold: true,
            valueColor: AppColors.primaryNavy,
          ),
          const ResultDivider(),
          ResultRow(
            label: 'Outpatient Sick Leave',
            value: '${r.sickLeave} days',
          ),
          ResultRow(
            label: 'Hospitalisation Leave',
            value: '${r.hospitalisationLeave} days',
          ),
          const ResultDivider(),
          ResultRow(
            label: 'Maternity Leave',
            value: '${r.maternityLeave} days',
          ),
          ResultRow(
            label: 'Paternity Leave',
            value: '${r.paternityLeave} days',
          ),
          ResultRow(
            label: 'Childcare Leave',
            value: '${r.childcareLeave} days/year',
          ),
        ],
      ),
    );
  }
}
