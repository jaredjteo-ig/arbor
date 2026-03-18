import 'package:dio/dio.dart';

import '../models/knowledge_base.dart';
import '../network/api_client.dart';
import '../network/api_error.dart';

/// Repository for the Knowledge Base API domain.
///
/// Provides typed access to acts, domains, provisions, and
/// knowledge-base query functionality.
class KbRepository {
  const KbRepository({required ApiClient client}) : _client = client;

  final ApiClient _client;

  /// Fetches all legislative acts in the knowledge base.
  Future<List<Act>> getActs() async {
    try {
      final response =
          await _client.dio.get<List<dynamic>>('/kb/acts');
      return response.data!
          .map((item) => Act.fromJson(item as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw ApiError.fromDioException(e);
    }
  }

  /// Fetches all regulatory domains in the knowledge base.
  Future<List<Domain>> getDomains() async {
    try {
      final response =
          await _client.dio.get<List<dynamic>>('/kb/domains');
      return response.data!
          .map(
              (item) => Domain.fromJson(item as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw ApiError.fromDioException(e);
    }
  }

  /// Fetches the detail of a specific provision by ID.
  Future<Provision> getProvision(int provisionId) async {
    try {
      final response =
          await _client.dio.get<Map<String, dynamic>>(
        '/kb/provisions/$provisionId',
      );
      return Provision.fromJson(response.data!);
    } on DioException catch (e) {
      throw ApiError.fromDioException(e);
    }
  }

  /// Queries the knowledge base using natural language.
  ///
  /// Optionally filters results to a specific [domainId].
  Future<KbQueryResult> query({
    required String query,
    int? domainId,
  }) async {
    try {
      final response =
          await _client.dio.post<Map<String, dynamic>>(
        '/kb/query',
        data: <String, dynamic>{
          'query': query,
          'domain_id': ?domainId,
        },
      );
      return KbQueryResult.fromJson(response.data!);
    } on DioException catch (e) {
      throw ApiError.fromDioException(e);
    }
  }
}
