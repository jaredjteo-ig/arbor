import 'package:flutter/material.dart';

import '../../../core/design/components/components.dart';
import '../../../core/design/tokens/tokens.dart';
import '../models/calculator_definition.dart';
import '../widgets/cost_to_company_form.dart';
import '../widgets/cpf_form.dart';
import '../widgets/leave_form.dart';
import '../widgets/notice_period_form.dart';
import '../widgets/overtime_form.dart';
import '../widgets/quota_levy_form.dart';
import '../widgets/retrenchment_form.dart';

/// Detail screen that renders the correct calculator form based on the
/// [calculatorType] route parameter.
class CalculatorDetailScreen extends StatelessWidget {
  const CalculatorDetailScreen({super.key, required this.calculatorType});

  /// The type slug from the route, e.g. "cpf", "leave", "overtime".
  final String calculatorType;

  @override
  Widget build(BuildContext context) {
    final definition = CalculatorDefinition.fromSlug(calculatorType);

    if (definition == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Calculator')),
        body: const EmptyState(
          icon: Icons.error_outline,
          heading: 'Unknown Calculator',
          description: 'This calculator type was not found.',
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(definition.name),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.base),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header description.
            Text(
              definition.description,
              style: AppTypography.body.copyWith(
                color: AppColors.neutralGray600,
              ),
            ),
            const SizedBox(height: AppSpacing.xl),
            // Calculator form for this type.
            _formForType(definition.type),
            // Bottom padding for scroll safety.
            const SizedBox(height: AppSpacing.s3xl),
          ],
        ),
      ),
    );
  }

  /// Returns the appropriate form widget for the calculator type.
  Widget _formForType(CalculatorType type) {
    return switch (type) {
      CalculatorType.cpf => const CpfForm(),
      CalculatorType.quotaLevy => const QuotaLevyForm(),
      CalculatorType.leave => const LeaveForm(),
      CalculatorType.noticePeriod => const NoticePeriodForm(),
      CalculatorType.overtime => const OvertimeForm(),
      CalculatorType.retrenchment => const RetrenchmentForm(),
      CalculatorType.costToCompany => const CostToCompanyForm(),
    };
  }
}
