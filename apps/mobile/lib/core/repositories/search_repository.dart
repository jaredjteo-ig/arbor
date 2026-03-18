import 'package:dio/dio.dart';

import '../models/search.dart';
import '../network/api_client.dart';
import '../network/api_error.dart';

/// Repository for the Search API domain.
///
/// Provides typed access to semantic and full-text search
/// across the legal provision database.
class SearchRepository {
  const SearchRepository({required ApiClient client})
      : _client = client;

  final ApiClient _client;

  /// Performs a semantic (vector) search for provisions matching the
  /// given [query].
  ///
  /// [topK] controls the maximum number of results (server default
  /// applies if omitted). [threshold] sets the minimum similarity
  /// score.
  Future<SemanticSearchResponse> semanticSearch({
    required String query,
    int? topK,
    int? domainId,
    double? threshold,
  }) async {
    try {
      final response =
          await _client.dio.post<Map<String, dynamic>>(
        '/search/semantic',
        data: <String, dynamic>{
          'query': query,
          'top_k': ?topK,
          'domain_id': ?domainId,
          'threshold': ?threshold,
        },
      );
      return SemanticSearchResponse.fromJson(response.data!);
    } on DioException catch (e) {
      throw ApiError.fromDioException(e);
    }
  }

  /// Performs a full-text search across provisions with optional
  /// filtering and pagination.
  Future<FullTextSearchResponse> fullTextSearch({
    required String query,
    int? domainId,
    int? actId,
    String? authorityLevel,
    int? page,
    int? pageSize,
  }) async {
    try {
      final response =
          await _client.dio.post<Map<String, dynamic>>(
        '/search/fulltext',
        data: <String, dynamic>{
          'query': query,
          'domain_id': ?domainId,
          'act_id': ?actId,
          'authority_level': ?authorityLevel,
          'page': ?page,
          'page_size': ?pageSize,
        },
      );
      return FullTextSearchResponse.fromJson(response.data!);
    } on DioException catch (e) {
      throw ApiError.fromDioException(e);
    }
  }
}
