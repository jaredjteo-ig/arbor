/// Client-side foreign worker quota and levy calculation.
///
/// Rates are simplified approximations based on MOM levy schedules.
class QuotaLevyCalculation {
  const QuotaLevyCalculation({
    required this.sector,
    required this.localCount,
    required this.wpCount,
    required this.spCount,
    required this.totalHeadcount,
    required this.foreignRatio,
    required this.drcLimit,
    required this.withinQuota,
    required this.estimatedMonthlyLevy,
    required this.levyBreakdown,
  });

  final String sector;
  final int localCount;
  final int wpCount;
  final int spCount;
  final int totalHeadcount;

  /// Current foreign worker ratio as a percentage.
  final double foreignRatio;

  /// Dependency Ratio Ceiling for the sector as a percentage.
  final double drcLimit;

  /// Whether the company is within quota.
  final bool withinQuota;

  /// Total estimated monthly levy for all foreign workers.
  final double estimatedMonthlyLevy;

  /// Per-category levy breakdown: {'WP Tier 1': amount, ...}.
  final Map<String, double> levyBreakdown;

  /// Calculate quota and levy.
  ///
  /// [sector] must be one of: 'Manufacturing', 'Services', 'Construction',
  /// 'Process', 'Marine'.
  static QuotaLevyCalculation calculate({
    required String sector,
    required int localCount,
    required int wpCount,
    required int spCount,
  }) {
    final total = localCount + wpCount + spCount;
    final foreignCount = wpCount + spCount;
    final ratio = total > 0 ? (foreignCount / total) * 100 : 0.0;
    final drc = _drcForSector(sector);
    final withinQuota = ratio <= drc;

    final wpLevy = _wpLevyRate(sector);
    final spLevy = _spLevyRate(sector);
    final wpTotal = wpCount * wpLevy;
    final spTotal = spCount * spLevy;

    return QuotaLevyCalculation(
      sector: sector,
      localCount: localCount,
      wpCount: wpCount,
      spCount: spCount,
      totalHeadcount: total,
      foreignRatio: _round(ratio),
      drcLimit: drc,
      withinQuota: withinQuota,
      estimatedMonthlyLevy: _round(wpTotal + spTotal),
      levyBreakdown: {
        'Work Permit levy ($wpCount workers)': _round(wpTotal),
        'S Pass levy ($spCount workers)': _round(spTotal),
      },
    );
  }

  /// Dependency Ratio Ceiling by sector (percentage).
  static double _drcForSector(String sector) {
    return switch (sector) {
      'Manufacturing' => 60.0,
      'Services' => 35.0,
      'Construction' => 87.5,
      'Process' => 87.5,
      'Marine' => 77.8,
      _ => 35.0,
    };
  }

  /// Monthly WP levy rate per worker by sector (Tier 1 basic).
  static double _wpLevyRate(String sector) {
    return switch (sector) {
      'Manufacturing' => 450.0,
      'Services' => 450.0,
      'Construction' => 550.0,
      'Process' => 450.0,
      'Marine' => 450.0,
      _ => 450.0,
    };
  }

  /// Monthly S Pass levy rate per worker by sector.
  static double _spLevyRate(String sector) {
    return switch (sector) {
      'Manufacturing' => 450.0,
      'Services' => 450.0,
      'Construction' => 450.0,
      'Process' => 450.0,
      'Marine' => 450.0,
      _ => 450.0,
    };
  }

  static double _round(double value) {
    return (value * 100).roundToDouble() / 100;
  }
}
