/// Models for the Calculator API domain.
library;

/// CPF contribution breakdown result.
class CpfResult {
  const CpfResult({
    required this.grossSalary,
    required this.employeeAge,
    required this.citizenshipStatus,
    required this.employeeContribution,
    required this.employerContribution,
    required this.totalContribution,
    required this.employeeRate,
    required this.employerRate,
    required this.ordinaryAccount,
    required this.specialAccount,
    required this.medisaveAccount,
    required this.takeHomePay,
  });

  final double grossSalary;
  final int employeeAge;
  final String citizenshipStatus;
  final double employeeContribution;
  final double employerContribution;
  final double totalContribution;
  final double employeeRate;
  final double employerRate;
  final double ordinaryAccount;
  final double specialAccount;
  final double medisaveAccount;
  final double takeHomePay;

  factory CpfResult.fromJson(Map<String, dynamic> json) {
    return CpfResult(
      grossSalary: (json['gross_salary'] as num).toDouble(),
      employeeAge: json['employee_age'] as int,
      citizenshipStatus: json['citizenship_status'] as String,
      employeeContribution:
          (json['employee_contribution'] as num).toDouble(),
      employerContribution:
          (json['employer_contribution'] as num).toDouble(),
      totalContribution:
          (json['total_contribution'] as num).toDouble(),
      employeeRate: (json['employee_rate'] as num).toDouble(),
      employerRate: (json['employer_rate'] as num).toDouble(),
      ordinaryAccount: (json['ordinary_account'] as num).toDouble(),
      specialAccount: (json['special_account'] as num).toDouble(),
      medisaveAccount: (json['medisave_account'] as num).toDouble(),
      takeHomePay: (json['take_home_pay'] as num).toDouble(),
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'gross_salary': grossSalary,
      'employee_age': employeeAge,
      'citizenship_status': citizenshipStatus,
      'employee_contribution': employeeContribution,
      'employer_contribution': employerContribution,
      'total_contribution': totalContribution,
      'employee_rate': employeeRate,
      'employer_rate': employerRate,
      'ordinary_account': ordinaryAccount,
      'special_account': specialAccount,
      'medisave_account': medisaveAccount,
      'take_home_pay': takeHomePay,
    };
  }
}

/// Leave entitlement calculation result.
class LeaveResult {
  const LeaveResult({
    required this.yearsOfService,
    required this.employmentType,
    required this.annualLeave,
    required this.sickLeave,
    required this.hospitalizationLeave,
    required this.maternityLeave,
    required this.paternityLeave,
    required this.childcareleave,
  });

  final int yearsOfService;
  final String employmentType;
  final int annualLeave;
  final int sickLeave;
  final int hospitalizationLeave;
  final int maternityLeave;
  final int paternityLeave;
  final int childcareleave;

  factory LeaveResult.fromJson(Map<String, dynamic> json) {
    return LeaveResult(
      yearsOfService: json['years_of_service'] as int,
      employmentType: json['employment_type'] as String,
      annualLeave: json['annual_leave'] as int,
      sickLeave: json['sick_leave'] as int,
      hospitalizationLeave: json['hospitalization_leave'] as int,
      maternityLeave: json['maternity_leave'] as int,
      paternityLeave: json['paternity_leave'] as int,
      childcareleave: json['childcare_leave'] as int,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'years_of_service': yearsOfService,
      'employment_type': employmentType,
      'annual_leave': annualLeave,
      'sick_leave': sickLeave,
      'hospitalization_leave': hospitalizationLeave,
      'maternity_leave': maternityLeave,
      'paternity_leave': paternityLeave,
      'childcare_leave': childcareleave,
    };
  }
}

/// Salary breakdown result.
class SalaryResult {
  const SalaryResult({
    required this.grossSalary,
    required this.cpfEmployee,
    required this.cpfEmployer,
    required this.netSalary,
    required this.totalEmployerCost,
  });

  final double grossSalary;
  final double cpfEmployee;
  final double cpfEmployer;
  final double netSalary;
  final double totalEmployerCost;

  factory SalaryResult.fromJson(Map<String, dynamic> json) {
    return SalaryResult(
      grossSalary: (json['gross_salary'] as num).toDouble(),
      cpfEmployee: (json['cpf_employee'] as num).toDouble(),
      cpfEmployer: (json['cpf_employer'] as num).toDouble(),
      netSalary: (json['net_salary'] as num).toDouble(),
      totalEmployerCost:
          (json['total_employer_cost'] as num).toDouble(),
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'gross_salary': grossSalary,
      'cpf_employee': cpfEmployee,
      'cpf_employer': cpfEmployer,
      'net_salary': netSalary,
      'total_employer_cost': totalEmployerCost,
    };
  }
}
