import 'dart:developer' as developer;

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import '../config/app_config.dart';
import '../services/auth_service.dart';
import 'auth_interceptor.dart';

/// Centralized HTTP client for all Arbor backend API calls.
///
/// Configures [Dio] with:
/// - The correct base URL from [AppConfig]
/// - The [AuthInterceptor] for transparent token management
/// - Debug-only request/response logging
/// - Sensible timeouts
///
/// Feature repositories receive this client via Riverpod and use [dio]
/// directly for typed requests.
class ApiClient {
  ApiClient({required AuthService authService})
      : _dio = Dio(
          BaseOptions(
            baseUrl: AppConfig.apiBaseUrl,
            connectTimeout: const Duration(seconds: 30),
            receiveTimeout: const Duration(seconds: 30),
            headers: <String, dynamic>{
              'Content-Type': 'application/json',
              'Accept': 'application/json',
            },
          ),
        ) {
    _dio.interceptors.add(AuthInterceptor(authService: authService));

    // Log requests and responses in debug builds only.
    if (kDebugMode) {
      _dio.interceptors.add(
        LogInterceptor(
          requestBody: true,
          responseBody: true,
          logPrint: (object) => developer.log(
            object.toString(),
            name: 'api_client',
          ),
        ),
      );
    }
  }

  final Dio _dio;

  /// The configured [Dio] instance for making HTTP calls.
  ///
  /// Repositories use this to perform typed requests against the backend.
  Dio get dio => _dio;
}
