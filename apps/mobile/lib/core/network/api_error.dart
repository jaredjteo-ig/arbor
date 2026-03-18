import 'package:dio/dio.dart';

/// Structured error type for all API failures.
///
/// Wraps Dio exceptions and backend error responses into a consistent
/// format that the UI layer can consume without knowing about HTTP details.
class ApiError implements Exception {
  const ApiError({
    required this.message,
    this.statusCode,
    this.detail,
  });

  /// User-facing error message.
  final String message;

  /// HTTP status code, if available.
  final int? statusCode;

  /// Raw detail string from the backend, if any.
  final String? detail;

  /// Creates an [ApiError] from a [DioException].
  ///
  /// Inspects the response body for a `detail` field (standard in Nexus
  /// error responses) and falls back to generic status-code-based messages.
  factory ApiError.fromDioException(DioException e) {
    final statusCode = e.response?.statusCode;
    String? detail;

    // Try extracting `detail` from the response body.
    final data = e.response?.data;
    if (data is Map<String, dynamic> && data.containsKey('detail')) {
      final rawDetail = data['detail'];
      if (rawDetail is String) {
        detail = rawDetail;
      } else if (rawDetail is List && rawDetail.isNotEmpty) {
        // FastAPI validation errors return a list of detail objects.
        detail = rawDetail
            .map((item) {
              if (item is Map<String, dynamic>) {
                return item['msg'] as String? ?? item.toString();
              }
              return item.toString();
            })
            .join('; ');
      }
    }

    final message = detail ?? _messageForStatus(statusCode, e);

    return ApiError(
      message: message,
      statusCode: statusCode,
      detail: detail,
    );
  }

  /// Creates an [ApiError] from a generic exception (non-Dio).
  factory ApiError.fromException(Object error) {
    return ApiError(
      message: 'An unexpected error occurred. Please try again.',
      detail: error.toString(),
    );
  }

  /// Derives a user-facing message from the HTTP status code.
  static String _messageForStatus(int? statusCode, DioException e) {
    if (statusCode == null) {
      return switch (e.type) {
        DioExceptionType.connectionTimeout ||
        DioExceptionType.sendTimeout ||
        DioExceptionType.receiveTimeout =>
          'The request timed out. Please check your connection and try again.',
        DioExceptionType.connectionError =>
          'Could not connect to the server. Please check your connection.',
        DioExceptionType.cancel => 'The request was cancelled.',
        _ =>
          'Could not connect to the server. Please check your connection.',
      };
    }

    return switch (statusCode) {
      400 => 'Invalid request. Please check your input.',
      401 => 'Your session has expired. Please sign in again.',
      403 => 'You do not have permission to perform this action.',
      404 => 'The requested resource was not found.',
      409 => 'A conflict occurred. The resource may already exist.',
      422 => 'The submitted data is invalid. Please check and try again.',
      429 => 'Too many requests. Please wait a moment and try again.',
      >= 500 => 'A server error occurred. Please try again later.',
      _ => 'An unexpected error occurred (HTTP $statusCode).',
    };
  }

  @override
  String toString() => 'ApiError($statusCode): $message';
}
