/// Models for the Profile (Company) API domain.
library;

/// Full company profile.
class CompanyProfile {
  const CompanyProfile({
    required this.id,
    required this.name,
    required this.uen,
    required this.industry,
    required this.employeeCount,
    this.address,
    this.contactEmail,
    this.contactPhone,
    this.incorporationDate,
    this.description,
  });

  final int id;
  final String name;
  final String uen;
  final String industry;
  final int employeeCount;
  final String? address;
  final String? contactEmail;
  final String? contactPhone;
  final String? incorporationDate;
  final String? description;

  factory CompanyProfile.fromJson(Map<String, dynamic> json) {
    return CompanyProfile(
      id: json['id'] as int,
      name: json['name'] as String,
      uen: json['uen'] as String,
      industry: json['industry'] as String,
      employeeCount: json['employee_count'] as int,
      address: json['address'] as String?,
      contactEmail: json['contact_email'] as String?,
      contactPhone: json['contact_phone'] as String?,
      incorporationDate: json['incorporation_date'] as String?,
      description: json['description'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'id': id,
      'name': name,
      'uen': uen,
      'industry': industry,
      'employee_count': employeeCount,
      if (address != null) 'address': address,
      if (contactEmail != null) 'contact_email': contactEmail,
      if (contactPhone != null) 'contact_phone': contactPhone,
      if (incorporationDate != null)
        'incorporation_date': incorporationDate,
      if (description != null) 'description': description,
    };
  }
}

/// Workforce composition breakdown for a company.
class WorkforceComposition {
  const WorkforceComposition({
    required this.companyId,
    required this.totalEmployees,
    required this.breakdown,
  });

  final int companyId;
  final int totalEmployees;
  final List<WorkforceCategory> breakdown;

  factory WorkforceComposition.fromJson(Map<String, dynamic> json) {
    return WorkforceComposition(
      companyId: json['company_id'] as int,
      totalEmployees: json['total_employees'] as int,
      breakdown: (json['breakdown'] as List<dynamic>)
          .map((item) =>
              WorkforceCategory.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'company_id': companyId,
      'total_employees': totalEmployees,
      'breakdown': breakdown.map((c) => c.toJson()).toList(),
    };
  }
}

/// A single category within the workforce breakdown.
class WorkforceCategory {
  const WorkforceCategory({
    required this.category,
    required this.count,
    required this.percentage,
  });

  final String category;
  final int count;
  final double percentage;

  factory WorkforceCategory.fromJson(Map<String, dynamic> json) {
    return WorkforceCategory(
      category: json['category'] as String,
      count: json['count'] as int,
      percentage: (json['percentage'] as num).toDouble(),
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'category': category,
      'count': count,
      'percentage': percentage,
    };
  }
}
