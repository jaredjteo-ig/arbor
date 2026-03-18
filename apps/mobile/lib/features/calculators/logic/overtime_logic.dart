/// Client-side overtime pay calculation based on Singapore Employment Act.
class OvertimeCalculation {
  const OvertimeCalculation({
    required this.monthlySalary,
    required this.isWorkman,
    required this.otHours,
    required this.dayType,
    required this.isEligible,
    required this.eligibilityReason,
    required this.hourlyRate,
    required this.otMultiplier,
    required this.otPay,
  });

  final double monthlySalary;
  final bool isWorkman;
  final double otHours;

  /// Day type: 'Normal', 'Rest day', 'Public holiday'.
  final String dayType;

  /// Whether the employee is eligible for OT under the EA.
  final bool isEligible;

  /// Explanation of eligibility determination.
  final String eligibilityReason;

  /// Base hourly rate used for calculation.
  final double hourlyRate;

  /// OT multiplier applied (e.g. 1.5x, 2.0x).
  final double otMultiplier;

  /// Total overtime pay amount.
  final double otPay;

  /// Calculate overtime pay.
  ///
  /// [dayType] must be one of: 'Normal', 'Rest day', 'Public holiday'.
  static OvertimeCalculation calculate({
    required double monthlySalary,
    required bool isWorkman,
    required double otHours,
    required String dayType,
  }) {
    // Eligibility check.
    // Workmen: salary up to SGD 4,500 are covered by Part IV of the EA.
    // Non-workmen: salary up to SGD 2,600 are covered.
    final double cap = isWorkman ? 4500.0 : 2600.0;
    final bool eligible = monthlySalary <= cap;

    String reason;
    if (eligible) {
      reason = isWorkman
          ? 'Eligible: Workman earning \$${monthlySalary.toStringAsFixed(0)} '
              '(cap: \$${cap.toStringAsFixed(0)})'
          : 'Eligible: Non-workman earning \$${monthlySalary.toStringAsFixed(0)} '
              '(cap: \$${cap.toStringAsFixed(0)})';
    } else {
      reason = isWorkman
          ? 'Not eligible: Workman salary exceeds \$${cap.toStringAsFixed(0)} cap'
          : 'Not eligible: Non-workman salary exceeds \$${cap.toStringAsFixed(0)} cap';
    }

    // For salary-capped calculation, use capped salary for OT rate.
    final double effectiveSalary =
        eligible ? monthlySalary : monthlySalary;

    // Hourly rate = monthly salary / (26 days * 8 hours).
    final double hourlyRate = _round(effectiveSalary / (26 * 8));

    // Multiplier by day type.
    final double multiplier = switch (dayType) {
      'Normal' => 1.5,
      'Rest day' => 2.0,
      'Public holiday' => 2.0,
      _ => 1.5,
    };

    final double pay =
        eligible ? _round(hourlyRate * multiplier * otHours) : 0;

    return OvertimeCalculation(
      monthlySalary: monthlySalary,
      isWorkman: isWorkman,
      otHours: otHours,
      dayType: dayType,
      isEligible: eligible,
      eligibilityReason: reason,
      hourlyRate: hourlyRate,
      otMultiplier: multiplier,
      otPay: pay,
    );
  }

  static double _round(double value) {
    return (value * 100).roundToDouble() / 100;
  }
}
