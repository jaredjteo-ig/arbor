/// Client-side retrenchment benefit estimation based on market norms.
///
/// Singapore does not have a statutory minimum retrenchment benefit.
/// The market norm is typically 2 weeks to 1 month per year of service.
class RetrenchmentCalculation {
  const RetrenchmentCalculation({
    required this.yearsOfService,
    required this.monthlySalary,
    required this.sector,
    required this.lowEstimate,
    required this.midEstimate,
    required this.highEstimate,
    required this.weeksPerYear,
  });

  final int yearsOfService;
  final double monthlySalary;
  final String sector;

  /// Low end of the market norm estimate.
  final double lowEstimate;

  /// Mid-range estimate.
  final double midEstimate;

  /// High end estimate.
  final double highEstimate;

  /// Description of weeks-per-year used.
  final String weeksPerYear;

  /// Calculate retrenchment benefit estimates.
  static RetrenchmentCalculation calculate({
    required int yearsOfService,
    required double monthlySalary,
    required String sector,
  }) {
    final double weeklySalary = monthlySalary / 4.33;

    // Market norm ranges (weeks per year of service).
    // These vary by sector — MNCs and unionised sectors tend higher.
    final (double low, double mid, double high) = _ratesForSector(sector);

    final double lowEst =
        _round(weeklySalary * low * yearsOfService);
    final double midEst =
        _round(weeklySalary * mid * yearsOfService);
    final double highEst =
        _round(weeklySalary * high * yearsOfService);

    return RetrenchmentCalculation(
      yearsOfService: yearsOfService,
      monthlySalary: monthlySalary,
      sector: sector,
      lowEstimate: lowEst,
      midEstimate: midEst,
      highEstimate: highEst,
      weeksPerYear:
          '${low.toStringAsFixed(1)} - ${high.toStringAsFixed(1)} weeks/year',
    );
  }

  /// (low, mid, high) weeks per year of service by sector.
  static (double, double, double) _ratesForSector(String sector) {
    return switch (sector) {
      'Manufacturing' => (2.0, 3.0, 4.0),
      'Services' => (2.0, 2.5, 4.0),
      'Construction' => (2.0, 2.5, 3.0),
      'Technology' => (2.0, 3.0, 4.33),
      'Finance' => (2.0, 3.0, 4.33),
      _ => (2.0, 2.5, 4.0),
    };
  }

  static double _round(double value) {
    return (value * 100).roundToDouble() / 100;
  }
}
