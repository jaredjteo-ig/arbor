/// Models for the Knowledge Base API domain.
library;

/// A legislative act in the knowledge base.
class Act {
  const Act({
    required this.id,
    required this.name,
    required this.shortName,
    this.description,
    this.effectiveDate,
    this.provisionsCount,
  });

  final int id;
  final String name;
  final String shortName;
  final String? description;
  final String? effectiveDate;
  final int? provisionsCount;

  factory Act.fromJson(Map<String, dynamic> json) {
    return Act(
      id: json['id'] as int,
      name: json['name'] as String,
      shortName: json['short_name'] as String,
      description: json['description'] as String?,
      effectiveDate: json['effective_date'] as String?,
      provisionsCount: json['provisions_count'] as int?,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'id': id,
      'name': name,
      'short_name': shortName,
      if (description != null) 'description': description,
      if (effectiveDate != null) 'effective_date': effectiveDate,
      if (provisionsCount != null) 'provisions_count': provisionsCount,
    };
  }
}

/// A regulatory domain (e.g. "Employment", "CPF", "Workplace Safety").
class Domain {
  const Domain({
    required this.id,
    required this.name,
    this.description,
    this.actsCount,
  });

  final int id;
  final String name;
  final String? description;
  final int? actsCount;

  factory Domain.fromJson(Map<String, dynamic> json) {
    return Domain(
      id: json['id'] as int,
      name: json['name'] as String,
      description: json['description'] as String?,
      actsCount: json['acts_count'] as int?,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'id': id,
      'name': name,
      if (description != null) 'description': description,
      if (actsCount != null) 'acts_count': actsCount,
    };
  }
}

/// A specific legal provision within an act.
class Provision {
  const Provision({
    required this.id,
    required this.title,
    required this.content,
    required this.section,
    this.actId,
    this.actName,
    this.domainId,
    this.domainName,
    this.authorityLevel,
  });

  final int id;
  final String title;
  final String content;
  final String section;
  final int? actId;
  final String? actName;
  final int? domainId;
  final String? domainName;
  final String? authorityLevel;

  factory Provision.fromJson(Map<String, dynamic> json) {
    return Provision(
      id: json['id'] as int,
      title: json['title'] as String,
      content: json['content'] as String,
      section: json['section'] as String,
      actId: json['act_id'] as int?,
      actName: json['act_name'] as String?,
      domainId: json['domain_id'] as int?,
      domainName: json['domain_name'] as String?,
      authorityLevel: json['authority_level'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'id': id,
      'title': title,
      'content': content,
      'section': section,
      if (actId != null) 'act_id': actId,
      if (actName != null) 'act_name': actName,
      if (domainId != null) 'domain_id': domainId,
      if (domainName != null) 'domain_name': domainName,
      if (authorityLevel != null) 'authority_level': authorityLevel,
    };
  }
}

/// Result from a knowledge base query.
class KbQueryResult {
  const KbQueryResult({
    required this.query,
    required this.results,
    required this.total,
  });

  final String query;
  final List<Provision> results;
  final int total;

  factory KbQueryResult.fromJson(Map<String, dynamic> json) {
    return KbQueryResult(
      query: json['query'] as String,
      results: (json['results'] as List<dynamic>)
          .map((item) =>
              Provision.fromJson(item as Map<String, dynamic>))
          .toList(),
      total: json['total'] as int,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'query': query,
      'results': results.map((p) => p.toJson()).toList(),
      'total': total,
    };
  }
}
