/// Models for the Search API domain.
library;

/// A single result from a semantic search.
class SemanticResult {
  const SemanticResult({
    required this.provisionId,
    required this.title,
    required this.content,
    required this.score,
    this.section,
    this.actName,
    this.domainName,
  });

  final int provisionId;
  final String title;
  final String content;
  final double score;
  final String? section;
  final String? actName;
  final String? domainName;

  factory SemanticResult.fromJson(Map<String, dynamic> json) {
    return SemanticResult(
      provisionId: json['provision_id'] as int,
      title: json['title'] as String,
      content: json['content'] as String,
      score: (json['score'] as num).toDouble(),
      section: json['section'] as String?,
      actName: json['act_name'] as String?,
      domainName: json['domain_name'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'provision_id': provisionId,
      'title': title,
      'content': content,
      'score': score,
      if (section != null) 'section': section,
      if (actName != null) 'act_name': actName,
      if (domainName != null) 'domain_name': domainName,
    };
  }
}

/// Response from a semantic search request.
class SemanticSearchResponse {
  const SemanticSearchResponse({
    required this.query,
    required this.results,
    required this.total,
  });

  final String query;
  final List<SemanticResult> results;
  final int total;

  factory SemanticSearchResponse.fromJson(Map<String, dynamic> json) {
    return SemanticSearchResponse(
      query: json['query'] as String,
      results: (json['results'] as List<dynamic>)
          .map((item) =>
              SemanticResult.fromJson(item as Map<String, dynamic>))
          .toList(),
      total: json['total'] as int,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'query': query,
      'results': results.map((r) => r.toJson()).toList(),
      'total': total,
    };
  }
}

/// A single result from a full-text search.
class FullTextResult {
  const FullTextResult({
    required this.provisionId,
    required this.title,
    required this.content,
    this.section,
    this.actName,
    this.domainName,
    this.authorityLevel,
    this.highlight,
  });

  final int provisionId;
  final String title;
  final String content;
  final String? section;
  final String? actName;
  final String? domainName;
  final String? authorityLevel;
  final String? highlight;

  factory FullTextResult.fromJson(Map<String, dynamic> json) {
    return FullTextResult(
      provisionId: json['provision_id'] as int,
      title: json['title'] as String,
      content: json['content'] as String,
      section: json['section'] as String?,
      actName: json['act_name'] as String?,
      domainName: json['domain_name'] as String?,
      authorityLevel: json['authority_level'] as String?,
      highlight: json['highlight'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'provision_id': provisionId,
      'title': title,
      'content': content,
      if (section != null) 'section': section,
      if (actName != null) 'act_name': actName,
      if (domainName != null) 'domain_name': domainName,
      if (authorityLevel != null) 'authority_level': authorityLevel,
      if (highlight != null) 'highlight': highlight,
    };
  }
}

/// Response from a full-text search request.
class FullTextSearchResponse {
  const FullTextSearchResponse({
    required this.query,
    required this.results,
    required this.total,
    required this.page,
    required this.pageSize,
  });

  final String query;
  final List<FullTextResult> results;
  final int total;
  final int page;
  final int pageSize;

  factory FullTextSearchResponse.fromJson(Map<String, dynamic> json) {
    return FullTextSearchResponse(
      query: json['query'] as String,
      results: (json['results'] as List<dynamic>)
          .map((item) =>
              FullTextResult.fromJson(item as Map<String, dynamic>))
          .toList(),
      total: json['total'] as int,
      page: json['page'] as int,
      pageSize: json['page_size'] as int,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'query': query,
      'results': results.map((r) => r.toJson()).toList(),
      'total': total,
      'page': page,
      'page_size': pageSize,
    };
  }
}
