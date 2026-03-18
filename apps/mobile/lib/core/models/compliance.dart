/// Models for the Compliance API domain.
library;

/// A single compliance finding within a check result.
class ComplianceFinding {
  const ComplianceFinding({
    required this.domain,
    required this.requirement,
    required this.status,
    required this.severity,
    this.recommendation,
    this.provisionId,
  });

  final String domain;
  final String requirement;
  final String status;
  final String severity;
  final String? recommendation;
  final int? provisionId;

  factory ComplianceFinding.fromJson(Map<String, dynamic> json) {
    return ComplianceFinding(
      domain: json['domain'] as String,
      requirement: json['requirement'] as String,
      status: json['status'] as String,
      severity: json['severity'] as String,
      recommendation: json['recommendation'] as String?,
      provisionId: json['provision_id'] as int?,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'domain': domain,
      'requirement': requirement,
      'status': status,
      'severity': severity,
      if (recommendation != null) 'recommendation': recommendation,
      if (provisionId != null) 'provision_id': provisionId,
    };
  }
}

/// Result from a compliance check.
class ComplianceResult {
  const ComplianceResult({
    required this.companyId,
    required this.overallScore,
    required this.findings,
    required this.checkedAt,
    this.domains,
  });

  final int companyId;
  final double overallScore;
  final List<ComplianceFinding> findings;
  final String checkedAt;
  final List<String>? domains;

  factory ComplianceResult.fromJson(Map<String, dynamic> json) {
    return ComplianceResult(
      companyId: json['company_id'] as int,
      overallScore: (json['overall_score'] as num).toDouble(),
      findings: (json['findings'] as List<dynamic>)
          .map((item) =>
              ComplianceFinding.fromJson(item as Map<String, dynamic>))
          .toList(),
      checkedAt: json['checked_at'] as String,
      domains: (json['domains'] as List<dynamic>?)
          ?.map((item) => item as String)
          .toList(),
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'company_id': companyId,
      'overall_score': overallScore,
      'findings': findings.map((f) => f.toJson()).toList(),
      'checked_at': checkedAt,
      if (domains != null) 'domains': domains,
    };
  }
}

/// Status response for an ongoing or completed compliance assessment.
class ComplianceStatus {
  const ComplianceStatus({
    required this.companyId,
    required this.status,
    required this.lastCheckedAt,
    this.overallScore,
    this.findingsCount,
  });

  final int companyId;
  final String status;
  final String lastCheckedAt;
  final double? overallScore;
  final int? findingsCount;

  factory ComplianceStatus.fromJson(Map<String, dynamic> json) {
    return ComplianceStatus(
      companyId: json['company_id'] as int,
      status: json['status'] as String,
      lastCheckedAt: json['last_checked_at'] as String,
      overallScore: json['overall_score'] != null
          ? (json['overall_score'] as num).toDouble()
          : null,
      findingsCount: json['findings_count'] as int?,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'company_id': companyId,
      'status': status,
      'last_checked_at': lastCheckedAt,
      if (overallScore != null) 'overall_score': overallScore,
      if (findingsCount != null) 'findings_count': findingsCount,
    };
  }
}

/// A single gap identified in a gap analysis.
class ComplianceGap {
  const ComplianceGap({
    required this.domain,
    required this.gap,
    required this.priority,
    required this.recommendation,
    this.estimatedEffort,
  });

  final String domain;
  final String gap;
  final String priority;
  final String recommendation;
  final String? estimatedEffort;

  factory ComplianceGap.fromJson(Map<String, dynamic> json) {
    return ComplianceGap(
      domain: json['domain'] as String,
      gap: json['gap'] as String,
      priority: json['priority'] as String,
      recommendation: json['recommendation'] as String,
      estimatedEffort: json['estimated_effort'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'domain': domain,
      'gap': gap,
      'priority': priority,
      'recommendation': recommendation,
      if (estimatedEffort != null) 'estimated_effort': estimatedEffort,
    };
  }
}

/// Result of a gap analysis for a company.
class GapAnalysisResult {
  const GapAnalysisResult({
    required this.companyId,
    required this.gaps,
    required this.analyzedAt,
    required this.totalGaps,
  });

  final int companyId;
  final List<ComplianceGap> gaps;
  final String analyzedAt;
  final int totalGaps;

  factory GapAnalysisResult.fromJson(Map<String, dynamic> json) {
    return GapAnalysisResult(
      companyId: json['company_id'] as int,
      gaps: (json['gaps'] as List<dynamic>)
          .map((item) =>
              ComplianceGap.fromJson(item as Map<String, dynamic>))
          .toList(),
      analyzedAt: json['analyzed_at'] as String,
      totalGaps: json['total_gaps'] as int,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'company_id': companyId,
      'gaps': gaps.map((g) => g.toJson()).toList(),
      'analyzed_at': analyzedAt,
      'total_gaps': totalGaps,
    };
  }
}
