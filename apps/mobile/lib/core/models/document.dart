/// Models for the Document API domain.
library;

/// A document template available for generation.
class Template {
  const Template({
    required this.id,
    required this.name,
    required this.description,
    required this.category,
    this.requiredFields,
  });

  final int id;
  final String name;
  final String description;
  final String category;
  final List<String>? requiredFields;

  factory Template.fromJson(Map<String, dynamic> json) {
    return Template(
      id: json['id'] as int,
      name: json['name'] as String,
      description: json['description'] as String,
      category: json['category'] as String,
      requiredFields: (json['required_fields'] as List<dynamic>?)
          ?.map((item) => item as String)
          .toList(),
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'id': id,
      'name': name,
      'description': description,
      'category': category,
      if (requiredFields != null) 'required_fields': requiredFields,
    };
  }
}

/// A document generated from a template for a specific company.
class GeneratedDocument {
  const GeneratedDocument({
    required this.id,
    required this.templateId,
    required this.companyId,
    required this.content,
    required this.generatedAt,
    this.title,
    this.downloadUrl,
  });

  final int id;
  final int templateId;
  final int companyId;
  final String content;
  final String generatedAt;
  final String? title;
  final String? downloadUrl;

  factory GeneratedDocument.fromJson(Map<String, dynamic> json) {
    return GeneratedDocument(
      id: json['id'] as int,
      templateId: json['template_id'] as int,
      companyId: json['company_id'] as int,
      content: json['content'] as String,
      generatedAt: json['generated_at'] as String,
      title: json['title'] as String?,
      downloadUrl: json['download_url'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return <String, dynamic>{
      'id': id,
      'template_id': templateId,
      'company_id': companyId,
      'content': content,
      'generated_at': generatedAt,
      if (title != null) 'title': title,
      if (downloadUrl != null) 'download_url': downloadUrl,
    };
  }
}
