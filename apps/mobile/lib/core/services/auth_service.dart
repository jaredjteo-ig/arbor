import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../config/app_config.dart';

// ── Models ──────────────────────────────────────────────────────────────────

/// Represents an authenticated user returned from the API.
class User {
  const User({
    required this.id,
    required this.email,
    required this.name,
    required this.role,
    this.companyId,
  });

  final int id;
  final String email;
  final String name;
  final String role;
  final int? companyId;

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'] as int,
      email: json['email'] as String,
      name: json['name'] as String,
      role: (json['role'] as String?) ?? 'user',
      companyId: json['company_id'] as int?,
    );
  }
}

/// Response returned by login and registration endpoints.
class AuthResponse {
  const AuthResponse({
    required this.accessToken,
    required this.refreshToken,
    required this.user,
  });

  final String accessToken;
  final String refreshToken;
  final User user;

  factory AuthResponse.fromJson(Map<String, dynamic> json) {
    return AuthResponse(
      accessToken: json['access_token'] as String,
      refreshToken: json['refresh_token'] as String,
      user: User.fromJson(json['user'] as Map<String, dynamic>),
    );
  }
}

// ── Service ─────────────────────────────────────────────────────────────────

/// Service responsible for all authentication-related API calls and secure
/// token persistence.
///
/// Uses [Dio] for HTTP and [FlutterSecureStorage] for token storage.
class AuthService {
  AuthService({
    Dio? dio,
    FlutterSecureStorage? storage,
  })  : _dio = dio ?? Dio(BaseOptions(baseUrl: AppConfig.apiBaseUrl)),
        _storage = storage ?? const FlutterSecureStorage();

  final Dio _dio;
  final FlutterSecureStorage _storage;

  // ── API Calls ──────────────────────────────────────────

  /// Registers a new user account.
  Future<AuthResponse> register({
    required String email,
    required String password,
    required String name,
    int? companyId,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/api/auth/register',
      data: <String, dynamic>{
        'email': email,
        'password': password,
        'name': name,
        // ignore: use_null_aware_elements
        if (companyId != null) 'company_id': companyId,
      },
    );
    return AuthResponse.fromJson(response.data!);
  }

  /// Authenticates an existing user with email and password.
  Future<AuthResponse> login({
    required String email,
    required String password,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/api/auth/login',
      data: {
        'email': email,
        'password': password,
      },
    );
    return AuthResponse.fromJson(response.data!);
  }

  /// Exchanges a refresh token for a new access token.
  Future<String> refreshToken(String refreshToken) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/api/auth/refresh',
      data: {'refresh_token': refreshToken},
    );
    return response.data!['access_token'] as String;
  }

  /// Fetches the currently authenticated user's profile.
  Future<User> getMe(String accessToken) async {
    final response = await _dio.get<Map<String, dynamic>>(
      '/api/auth/me',
      options: Options(
        headers: {'Authorization': 'Bearer $accessToken'},
      ),
    );
    return User.fromJson(response.data!);
  }

  /// Requests a password-reset email for the given address.
  Future<void> requestPasswordReset(String email) async {
    await _dio.post<void>(
      '/api/auth/forgot-password',
      data: {'email': email},
    );
  }

  /// Resets the user's password using a one-time token.
  Future<void> resetPassword({
    required String token,
    required String newPassword,
  }) async {
    await _dio.post<void>(
      '/api/auth/reset-password',
      data: {
        'token': token,
        'new_password': newPassword,
      },
    );
  }

  // ── Token Management ──────────────────────────────────

  /// Persists both tokens to secure storage.
  Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    await Future.wait([
      _storage.write(key: AppConfig.accessTokenKey, value: accessToken),
      _storage.write(key: AppConfig.refreshTokenKey, value: refreshToken),
    ]);
  }

  /// Retrieves the stored access token, if any.
  Future<String?> getAccessToken() {
    return _storage.read(key: AppConfig.accessTokenKey);
  }

  /// Retrieves the stored refresh token, if any.
  Future<String?> getRefreshToken() {
    return _storage.read(key: AppConfig.refreshTokenKey);
  }

  /// Deletes all stored tokens (used on logout).
  Future<void> clearTokens() async {
    await Future.wait([
      _storage.delete(key: AppConfig.accessTokenKey),
      _storage.delete(key: AppConfig.refreshTokenKey),
    ]);
  }
}
