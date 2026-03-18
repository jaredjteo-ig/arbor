/// Client-side notice period calculation based on Singapore Employment Act.
class NoticePeriodCalculation {
  const NoticePeriodCalculation({
    required this.yearsOfService,
    required this.monthlySalary,
    required this.contractualWeeks,
    required this.terminatedBy,
    required this.noticeWeeks,
    required this.salaryInLieu,
    required this.source,
  });

  final int yearsOfService;
  final double monthlySalary;

  /// Contractual notice period in weeks (0 means use statutory default).
  final int contractualWeeks;

  /// Who is terminating: 'Employer' or 'Employee'.
  final String terminatedBy;

  /// Required notice period in weeks.
  final int noticeWeeks;

  /// Salary in lieu of notice (if applicable).
  final double salaryInLieu;

  /// Whether the period is statutory or contractual.
  final String source;

  /// Calculate notice period and salary in lieu.
  static NoticePeriodCalculation calculate({
    required int yearsOfService,
    required double monthlySalary,
    required int contractualWeeks,
    required String terminatedBy,
  }) {
    // If contractual notice is specified, it overrides statutory minimum.
    final int statutory = _statutoryWeeks(yearsOfService);
    final bool useContractual = contractualWeeks > 0;
    final int weeks =
        useContractual ? contractualWeeks : statutory;
    final String source = useContractual ? 'Contractual' : 'Statutory (EA)';

    // Salary in lieu = weekly salary * notice weeks.
    final double weeklySalary = monthlySalary / 4.33;
    final double inLieu = _round(weeklySalary * weeks);

    return NoticePeriodCalculation(
      yearsOfService: yearsOfService,
      monthlySalary: monthlySalary,
      contractualWeeks: contractualWeeks,
      terminatedBy: terminatedBy,
      noticeWeeks: weeks,
      salaryInLieu: inLieu,
      source: source,
    );
  }

  /// Statutory notice period (Employment Act s10).
  static int _statutoryWeeks(int years) {
    if (years < 2) return 1;
    if (years < 5) return 2;
    return 4;
  }

  static double _round(double value) {
    return (value * 100).roundToDouble() / 100;
  }
}
