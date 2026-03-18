/// Client-side cost-to-company calculation.
///
/// Combines CPF, levies, and other employer costs into a full breakdown.
class CostToCompanyCalculation {
  const CostToCompanyCalculation({
    required this.grossSalary,
    required this.citizenship,
    required this.age,
    required this.passType,
    required this.sector,
    required this.cpfEmployer,
    required this.cpfEmployee,
    required this.sdl,
    required this.fwLevy,
    required this.totalMonthlyCost,
    required this.totalAnnualCost,
    required this.employeeTakeHome,
  });

  final double grossSalary;
  final String citizenship;
  final int age;

  /// Pass type for foreign workers: 'EP', 'SP', 'WP', 'N/A'.
  final String passType;
  final String sector;

  final double cpfEmployer;
  final double cpfEmployee;

  /// Skills Development Levy (SDL): 0.25% of salary, min $2, max $11.25/month.
  final double sdl;

  /// Foreign worker levy (0 for locals).
  final double fwLevy;

  final double totalMonthlyCost;
  final double totalAnnualCost;
  final double employeeTakeHome;

  /// Calculate full cost-to-company breakdown.
  static CostToCompanyCalculation calculate({
    required double grossSalary,
    required String citizenship,
    required int age,
    required String passType,
    required String sector,
  }) {
    // CPF rates (simplified — see cpf_logic.dart for detailed version).
    double cpfEmployerRate = 0;
    double cpfEmployeeRate = 0;

    if (citizenship == 'SC' || citizenship == 'PR') {
      if (age <= 55) {
        cpfEmployerRate = 0.17;
        cpfEmployeeRate = 0.20;
      } else if (age <= 60) {
        cpfEmployerRate = 0.15;
        cpfEmployeeRate = 0.165;
      } else if (age <= 65) {
        cpfEmployerRate = 0.115;
        cpfEmployeeRate = 0.115;
      } else if (age <= 70) {
        cpfEmployerRate = 0.09;
        cpfEmployeeRate = 0.075;
      } else {
        cpfEmployerRate = 0.075;
        cpfEmployeeRate = 0.05;
      }
    }

    final double cpfEr = _round(grossSalary * cpfEmployerRate);
    final double cpfEe = _round(grossSalary * cpfEmployeeRate);

    // SDL: 0.25% of gross, min $2, max $11.25.
    double sdl = grossSalary * 0.0025;
    if (sdl < 2) sdl = 2;
    if (sdl > 11.25) sdl = 11.25;
    sdl = _round(sdl);

    // Foreign worker levy.
    double fwLevy = 0;
    if (citizenship != 'SC' && citizenship != 'PR') {
      fwLevy = _levyForPass(passType, sector);
    }

    final double totalMonthly = grossSalary + cpfEr + sdl + fwLevy;
    final double takeHome = grossSalary - cpfEe;

    return CostToCompanyCalculation(
      grossSalary: grossSalary,
      citizenship: citizenship,
      age: age,
      passType: passType,
      sector: sector,
      cpfEmployer: cpfEr,
      cpfEmployee: cpfEe,
      sdl: sdl,
      fwLevy: fwLevy,
      totalMonthlyCost: _round(totalMonthly),
      totalAnnualCost: _round(totalMonthly * 12),
      employeeTakeHome: _round(takeHome),
    );
  }

  /// Monthly levy per foreign worker by pass type and sector.
  static double _levyForPass(String passType, String sector) {
    if (passType == 'EP') return 0;
    if (passType == 'SP') return 450;
    if (passType == 'WP') {
      return switch (sector) {
        'Construction' => 550,
        'Marine' => 450,
        'Process' => 450,
        _ => 450,
      };
    }
    return 0;
  }

  static double _round(double value) {
    return (value * 100).roundToDouble() / 100;
  }
}
