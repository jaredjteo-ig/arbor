import 'package:dio/dio.dart';

import '../models/advisory.dart';
import '../network/api_client.dart';
import '../network/api_error.dart';
import '../network/sse_client.dart';

/// Repository for the Advisory API domain.
///
/// Provides typed access to advisory queries, streaming responses,
/// and conversation history.
class AdvisoryRepository {
  const AdvisoryRepository({
    required ApiClient client,
    required SSEClient sseClient,
  })  : _client = client,
        _sseClient = sseClient;

  final ApiClient _client;
  final SSEClient _sseClient;

  /// Sends a query to the advisory engine and returns the full response.
  Future<AdvisoryResponse> query({
    required String query,
    int? companyId,
    int? conversationId,
  }) async {
    try {
      final response =
          await _client.dio.post<Map<String, dynamic>>(
        '/advisory/query',
        data: <String, dynamic>{
          'query': query,
          'company_id': ?companyId,
          'conversation_id': ?conversationId,
        },
      );
      return AdvisoryResponse.fromJson(response.data!);
    } on DioException catch (e) {
      throw ApiError.fromDioException(e);
    }
  }

  /// Sends a query to the advisory engine and returns a stream of SSE
  /// events for real-time token-by-token display.
  ///
  /// Events are: `start`, `token`, `complete`.
  Stream<SSEEvent> streamQuery({
    required String query,
    int? companyId,
    int? conversationId,
  }) {
    return _sseClient.stream(
      '/advisory/stream',
      <String, dynamic>{
        'query': query,
        'company_id': ?companyId,
        'conversation_id': ?conversationId,
      },
    );
  }

  /// Fetches the full conversation history for the given conversation.
  Future<AdvisoryHistory> getHistory(int conversationId) async {
    try {
      final response =
          await _client.dio.get<Map<String, dynamic>>(
        '/advisory/history/$conversationId',
      );
      return AdvisoryHistory.fromJson(response.data!);
    } on DioException catch (e) {
      throw ApiError.fromDioException(e);
    }
  }
}
