import 'dart:developer' as developer;

import 'package:dio/dio.dart';

import '../services/auth_service.dart';

/// Dio interceptor that attaches the stored access token to every outgoing
/// request and handles transparent token refresh on 401 responses.
///
/// When a request returns HTTP 401:
/// 1. The interceptor attempts to exchange the stored refresh token for a
///    new access token.
/// 2. If successful, the new token is saved and the original request is
///    retried with the updated `Authorization` header.
/// 3. If the refresh itself fails (e.g. expired refresh token), all stored
///    tokens are cleared and the error is forwarded so the auth layer can
///    redirect the user to the login screen.
class AuthInterceptor extends Interceptor {
  AuthInterceptor({required this.authService});

  final AuthService authService;

  /// Whether a token refresh is already in progress (prevents parallel
  /// refresh attempts).
  bool _isRefreshing = false;

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    // Skip adding auth header for auth endpoints that don't need it.
    final path = options.path;
    if (_isPublicPath(path)) {
      return handler.next(options);
    }

    final accessToken = await authService.getAccessToken();
    if (accessToken != null) {
      options.headers['Authorization'] = 'Bearer $accessToken';
    }
    handler.next(options);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    if (err.response?.statusCode != 401) {
      return handler.next(err);
    }

    // Don't try to refresh for auth endpoints themselves.
    final path = err.requestOptions.path;
    if (_isPublicPath(path) || path.contains('/auth/refresh')) {
      return handler.next(err);
    }

    if (_isRefreshing) {
      return handler.next(err);
    }

    _isRefreshing = true;

    try {
      final storedRefreshToken = await authService.getRefreshToken();
      if (storedRefreshToken == null) {
        await authService.clearTokens();
        return handler.next(err);
      }

      final newAccessToken =
          await authService.refreshToken(storedRefreshToken);

      await authService.saveTokens(
        accessToken: newAccessToken,
        refreshToken: storedRefreshToken,
      );

      // Retry the original request with the fresh token.
      final retryOptions = err.requestOptions;
      retryOptions.headers['Authorization'] = 'Bearer $newAccessToken';

      final dio = Dio(BaseOptions(baseUrl: retryOptions.baseUrl));
      final response = await dio.fetch<dynamic>(retryOptions);
      return handler.resolve(response);
    } on DioException catch (refreshError) {
      developer.log(
        'Token refresh failed: ${refreshError.message}',
        name: 'auth_interceptor',
      );
      await authService.clearTokens();
      return handler.next(err);
    } finally {
      _isRefreshing = false;
    }
  }

  /// Returns `true` for paths that do not require authentication.
  bool _isPublicPath(String path) {
    const publicPaths = [
      '/api/auth/login',
      '/api/auth/register',
      '/api/auth/forgot-password',
      '/api/auth/reset-password',
    ];
    return publicPaths.any(path.contains);
  }
}
