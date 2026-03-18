import 'package:dio/dio.dart';

import '../models/document.dart';
import '../network/api_client.dart';
import '../network/api_error.dart';

/// Repository for the Document API domain.
///
/// Provides typed access to document template listing, detail retrieval,
/// and document generation.
class DocumentRepository {
  const DocumentRepository({required ApiClient client})
      : _client = client;

  final ApiClient _client;

  /// Fetches all available document templates.
  Future<List<Template>> getTemplates() async {
    try {
      final response =
          await _client.dio.get<List<dynamic>>('/document/templates');
      return response.data!
          .map((item) =>
              Template.fromJson(item as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw ApiError.fromDioException(e);
    }
  }

  /// Fetches the detail of a single template by its ID.
  Future<Template> getTemplate(int templateId) async {
    try {
      final response =
          await _client.dio.get<Map<String, dynamic>>(
        '/document/templates/$templateId',
      );
      return Template.fromJson(response.data!);
    } on DioException catch (e) {
      throw ApiError.fromDioException(e);
    }
  }

  /// Generates a document from a template for a specific company.
  Future<GeneratedDocument> generate({
    required int templateId,
    required int companyId,
  }) async {
    try {
      final response =
          await _client.dio.post<Map<String, dynamic>>(
        '/document/generate',
        data: <String, dynamic>{
          'template_id': templateId,
          'company_id': companyId,
        },
      );
      return GeneratedDocument.fromJson(response.data!);
    } on DioException catch (e) {
      throw ApiError.fromDioException(e);
    }
  }
}
