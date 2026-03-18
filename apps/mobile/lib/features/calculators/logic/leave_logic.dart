/// Client-side leave entitlement calculation based on Singapore Employment Act.
class LeaveCalculation {
  const LeaveCalculation({
    required this.yearsOfService,
    required this.employmentType,
    required this.annualLeave,
    required this.sickLeave,
    required this.hospitalisationLeave,
    required this.maternityLeave,
    required this.paternityLeave,
    required this.childcareLeave,
  });

  final int yearsOfService;
  final String employmentType;
  final int annualLeave;
  final int sickLeave;
  final int hospitalisationLeave;
  final int maternityLeave;
  final int paternityLeave;
  final int childcareLeave;

  /// Calculate leave entitlements.
  ///
  /// [employmentType] must be one of: 'Full-time', 'Part-time'.
  static LeaveCalculation calculate({
    required int yearsOfService,
    required String employmentType,
  }) {
    final years = yearsOfService.clamp(0, 99);
    final isPartTime = employmentType == 'Part-time';

    // Annual leave: 7 days for year 1, +1 per year up to 14 days.
    int annual = (7 + (years - 1).clamp(0, 7));
    if (years == 0) annual = 0;
    if (isPartTime) annual = (annual / 2).ceil();

    // Outpatient sick leave: 14 days (after 6 months).
    int sick = years >= 1 ? 14 : (years > 0 ? 5 : 0);
    if (isPartTime) sick = (sick / 2).ceil();

    // Hospitalisation leave: 60 days inclusive of sick leave.
    int hosp = years >= 1 ? 60 : (years > 0 ? 15 : 0);
    if (isPartTime) hosp = (hosp / 2).ceil();

    // Maternity: 16 weeks = 112 calendar days (statutory).
    const int maternity = 112;

    // Paternity: 4 weeks = 28 calendar days.
    const int paternity = 28;

    // Childcare leave: 6 days/year per parent (child under 7).
    int childcare = 6;
    if (isPartTime) childcare = 3;

    return LeaveCalculation(
      yearsOfService: years,
      employmentType: employmentType,
      annualLeave: annual,
      sickLeave: sick,
      hospitalisationLeave: hosp,
      maternityLeave: maternity,
      paternityLeave: paternity,
      childcareLeave: childcare,
    );
  }
}
