import 'package:flutter/material.dart';

/// Identifies each calculator available in the hub.
enum CalculatorType {
  cpf,
  quotaLevy,
  leave,
  noticePeriod,
  overtime,
  retrenchment,
  costToCompany,
}

/// Metadata for a single calculator card in the hub.
class CalculatorDefinition {
  const CalculatorDefinition({
    required this.type,
    required this.name,
    required this.description,
    required this.icon,
    required this.routeSlug,
  });

  final CalculatorType type;
  final String name;
  final String description;
  final IconData icon;

  /// The URL path segment used in `/calculators/:type`.
  final String routeSlug;

  /// All available calculators in display order.
  static const List<CalculatorDefinition> all = [
    CalculatorDefinition(
      type: CalculatorType.cpf,
      name: 'CPF Calculator',
      description:
          'Calculate employer and employee CPF contributions by age and status.',
      icon: Icons.account_balance,
      routeSlug: 'cpf',
    ),
    CalculatorDefinition(
      type: CalculatorType.quotaLevy,
      name: 'Quota & Levy',
      description:
          'Check foreign worker quota ratios and estimate monthly levies.',
      icon: Icons.groups,
      routeSlug: 'quota-levy',
    ),
    CalculatorDefinition(
      type: CalculatorType.leave,
      name: 'Leave Entitlement',
      description:
          'Find statutory leave entitlements based on years of service.',
      icon: Icons.event_available,
      routeSlug: 'leave',
    ),
    CalculatorDefinition(
      type: CalculatorType.noticePeriod,
      name: 'Notice Period',
      description:
          'Determine notice period and salary in lieu of notice.',
      icon: Icons.schedule,
      routeSlug: 'notice-period',
    ),
    CalculatorDefinition(
      type: CalculatorType.overtime,
      name: 'Overtime Pay',
      description:
          'Check OT eligibility and calculate overtime pay rates.',
      icon: Icons.access_time_filled,
      routeSlug: 'overtime',
    ),
    CalculatorDefinition(
      type: CalculatorType.retrenchment,
      name: 'Retrenchment Benefit',
      description:
          'Estimate retrenchment benefits based on market norms.',
      icon: Icons.work_off,
      routeSlug: 'retrenchment',
    ),
    CalculatorDefinition(
      type: CalculatorType.costToCompany,
      name: 'Cost-to-Company',
      description:
          'See the full employment cost breakdown including levies and CPF.',
      icon: Icons.receipt_long,
      routeSlug: 'cost-to-company',
    ),
  ];

  /// Look up a definition by its route slug. Returns null if not found.
  static CalculatorDefinition? fromSlug(String slug) {
    for (final def in all) {
      if (def.routeSlug == slug) return def;
    }
    return null;
  }
}
