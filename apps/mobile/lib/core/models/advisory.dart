/// Models for the Advisory API domain.
library;

/// A single provision cited in an advisory response.
class ProvisionCitation {
  const ProvisionCitation({
    required this.provisionId,
    required this.title,
    required this.summary,
    this.actName,
    this.section,
  });

  final int provisionId;
  final String title;
  final String summary;
  final String? actName;
  final String? section;

  factory ProvisionCitation.fromJson(Map<String, dynamic> json) {
    return ProvisionCitation(
      provisionId: json['provision_id'] as int,
      title: json['title'] as String,
      summary: json['summary'] as String,
      actName: json['act_name'] as String?,
      section: json['section'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'provision_id': provisionId,
      'title': title,
      'summary': summary,
      if (actName != null) 'act_name': actName,
      if (section != null) 'section': section,
    };
  }
}

/// Response from the advisory query endpoint.
class AdvisoryResponse {
  const AdvisoryResponse({
    required this.query,
    required this.response,
    required this.provisionsCited,
    required this.riskTier,
    required this.confidenceScore,
    required this.conversationId,
    required this.timestamp,
    this.companyId,
  });

  final String query;
  final String response;
  final List<ProvisionCitation> provisionsCited;
  final String riskTier;
  final double confidenceScore;
  final int conversationId;
  final String timestamp;
  final int? companyId;

  factory AdvisoryResponse.fromJson(Map<String, dynamic> json) {
    return AdvisoryResponse(
      query: json['query'] as String,
      response: json['response'] as String,
      provisionsCited: (json['provisions_cited'] as List<dynamic>)
          .map((item) =>
              ProvisionCitation.fromJson(item as Map<String, dynamic>))
          .toList(),
      riskTier: json['risk_tier'] as String,
      confidenceScore: (json['confidence_score'] as num).toDouble(),
      conversationId: json['conversation_id'] as int,
      timestamp: json['timestamp'] as String,
      companyId: json['company_id'] as int?,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'query': query,
      'response': response,
      'provisions_cited':
          provisionsCited.map((c) => c.toJson()).toList(),
      'risk_tier': riskTier,
      'confidence_score': confidenceScore,
      'conversation_id': conversationId,
      'timestamp': timestamp,
      if (companyId != null) 'company_id': companyId,
    };
  }
}

/// A single message within a conversation history.
class AdvisoryMessage {
  const AdvisoryMessage({
    required this.role,
    required this.content,
    required this.timestamp,
    this.provisionsCited,
    this.riskTier,
    this.confidenceScore,
  });

  final String role;
  final String content;
  final String timestamp;
  final List<ProvisionCitation>? provisionsCited;
  final String? riskTier;
  final double? confidenceScore;

  factory AdvisoryMessage.fromJson(Map<String, dynamic> json) {
    return AdvisoryMessage(
      role: json['role'] as String,
      content: json['content'] as String,
      timestamp: json['timestamp'] as String,
      provisionsCited: json['provisions_cited'] != null
          ? (json['provisions_cited'] as List<dynamic>)
              .map((item) => ProvisionCitation.fromJson(
                  item as Map<String, dynamic>))
              .toList()
          : null,
      riskTier: json['risk_tier'] as String?,
      confidenceScore: json['confidence_score'] != null
          ? (json['confidence_score'] as num).toDouble()
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'role': role,
      'content': content,
      'timestamp': timestamp,
      if (provisionsCited != null)
        'provisions_cited':
            provisionsCited!.map((c) => c.toJson()).toList(),
      if (riskTier != null) 'risk_tier': riskTier,
      if (confidenceScore != null) 'confidence_score': confidenceScore,
    };
  }
}

/// Full conversation history for an advisory session.
class AdvisoryHistory {
  const AdvisoryHistory({
    required this.conversationId,
    required this.messages,
    required this.total,
  });

  final int conversationId;
  final List<AdvisoryMessage> messages;
  final int total;

  factory AdvisoryHistory.fromJson(Map<String, dynamic> json) {
    return AdvisoryHistory(
      conversationId: json['conversation_id'] as int,
      messages: (json['messages'] as List<dynamic>)
          .map((item) =>
              AdvisoryMessage.fromJson(item as Map<String, dynamic>))
          .toList(),
      total: json['total'] as int,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'conversation_id': conversationId,
      'messages': messages.map((m) => m.toJson()).toList(),
      'total': total,
    };
  }
}
