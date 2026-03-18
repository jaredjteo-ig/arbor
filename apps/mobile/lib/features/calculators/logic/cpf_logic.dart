/// Client-side CPF contribution calculation based on Singapore CPF rates.
///
/// Rates are simplified approximations for the 2025 schedule.
/// Actual rates vary by exact wage band — this covers the common case
/// for monthly wages above SGD 750.
class CpfCalculation {
  const CpfCalculation({
    required this.grossSalary,
    required this.age,
    required this.citizenship,
    required this.prYear,
    required this.employeeRate,
    required this.employerRate,
    required this.employeeContribution,
    required this.employerContribution,
    required this.totalContribution,
    required this.takeHomePay,
  });

  final double grossSalary;
  final int age;
  final String citizenship;
  final int prYear;
  final double employeeRate;
  final double employerRate;
  final double employeeContribution;
  final double employerContribution;
  final double totalContribution;
  final double takeHomePay;

  /// Calculate CPF contributions.
  ///
  /// [citizenship] must be one of: 'SC', 'PR', 'EP'.
  /// [prYear] is the PR graduation year (1 or 2); ignored for SC/EP.
  static CpfCalculation calculate({
    required double salary,
    required int age,
    required String citizenship,
    int prYear = 2,
  }) {
    if (citizenship == 'EP') {
      return CpfCalculation(
        grossSalary: salary,
        age: age,
        citizenship: citizenship,
        prYear: prYear,
        employeeRate: 0,
        employerRate: 0,
        employeeContribution: 0,
        employerContribution: 0,
        totalContribution: 0,
        takeHomePay: salary,
      );
    }

    final rates = _getRates(age, citizenship, prYear);
    final employeeContrib = _round(salary * rates.$1);
    final employerContrib = _round(salary * rates.$2);

    return CpfCalculation(
      grossSalary: salary,
      age: age,
      citizenship: citizenship,
      prYear: prYear,
      employeeRate: rates.$1 * 100,
      employerRate: rates.$2 * 100,
      employeeContribution: employeeContrib,
      employerContribution: employerContrib,
      totalContribution: employeeContrib + employerContrib,
      takeHomePay: salary - employeeContrib,
    );
  }

  /// Returns (employeeRate, employerRate) as decimals.
  static (double, double) _getRates(
    int age,
    String citizenship,
    int prYear,
  ) {
    // PR Year 1 graduated rates (lower).
    if (citizenship == 'PR' && prYear == 1) {
      if (age <= 55) return (0.05, 0.04);
      if (age <= 60) return (0.05, 0.04);
      if (age <= 65) return (0.05, 0.035);
      if (age <= 70) return (0.05, 0.03);
      return (0.05, 0.025);
    }

    // SC and PR Year 2+ use full rates.
    if (age <= 55) return (0.20, 0.17);
    if (age <= 60) return (0.165, 0.15);
    if (age <= 65) return (0.115, 0.115);
    if (age <= 70) return (0.075, 0.09);
    return (0.05, 0.075);
  }

  static double _round(double value) {
    return (value * 100).roundToDouble() / 100;
  }
}
