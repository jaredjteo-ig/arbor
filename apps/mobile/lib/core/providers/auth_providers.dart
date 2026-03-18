import 'dart:developer' as developer;

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../services/auth_service.dart';

// ── Auth State ──────────────────────────────────────────────────────────────

/// Sealed hierarchy representing every possible authentication state.
sealed class AuthState {
  const AuthState();
}

/// Initial state before any auth check has been performed.
class AuthInitial extends AuthState {
  const AuthInitial();
}

/// An authentication operation is in progress (login, register, token check).
class AuthLoading extends AuthState {
  const AuthLoading();
}

/// The user is authenticated and their profile is available.
class AuthAuthenticated extends AuthState {
  const AuthAuthenticated({required this.user});
  final User user;
}

/// The user is not authenticated (no stored tokens or they have expired).
class AuthUnauthenticated extends AuthState {
  const AuthUnauthenticated();
}

/// An authentication operation failed with a user-visible error message.
class AuthError extends AuthState {
  const AuthError({required this.message});
  final String message;
}

// ── Service Provider ────────────────────────────────────────────────────────

/// Provides a singleton [AuthService] instance.
final authServiceProvider = Provider<AuthService>((ref) {
  return AuthService();
});

// ── Auth Notifier ───────────────────────────────────────────────────────────

/// Manages the full authentication lifecycle: checking stored tokens on
/// startup, logging in, registering, and logging out.
///
/// Uses the Riverpod 3 [Notifier] pattern (not the legacy StateNotifier).
class AuthNotifier extends Notifier<AuthState> {
  @override
  AuthState build() => const AuthInitial();

  AuthService get _authService => ref.read(authServiceProvider);

  /// Checks for stored tokens on app startup and attempts to restore the
  /// user session by fetching `/auth/me`.
  Future<void> checkAuth() async {
    state = const AuthLoading();

    try {
      final accessToken = await _authService.getAccessToken();
      if (accessToken == null) {
        state = const AuthUnauthenticated();
        return;
      }

      final user = await _authService.getMe(accessToken);
      state = AuthAuthenticated(user: user);
    } on DioException catch (e) {
      developer.log(
        'Auth check failed: ${e.message}',
        name: 'auth',
      );

      // Try refreshing the token before giving up.
      try {
        final refreshToken = await _authService.getRefreshToken();
        if (refreshToken == null) {
          await _authService.clearTokens();
          state = const AuthUnauthenticated();
          return;
        }

        final newAccessToken = await _authService.refreshToken(refreshToken);
        await _authService.saveTokens(
          accessToken: newAccessToken,
          refreshToken: refreshToken,
        );

        final user = await _authService.getMe(newAccessToken);
        state = AuthAuthenticated(user: user);
      } catch (_) {
        await _authService.clearTokens();
        state = const AuthUnauthenticated();
      }
    } catch (e) {
      developer.log(
        'Unexpected auth check error: $e',
        name: 'auth',
      );
      await _authService.clearTokens();
      state = const AuthUnauthenticated();
    }
  }

  /// Authenticates the user with email and password.
  Future<void> login(String email, String password) async {
    state = const AuthLoading();

    try {
      final response = await _authService.login(
        email: email,
        password: password,
      );

      await _authService.saveTokens(
        accessToken: response.accessToken,
        refreshToken: response.refreshToken,
      );

      state = AuthAuthenticated(user: response.user);
    } on DioException catch (e) {
      final message = _extractErrorMessage(e);
      state = AuthError(message: message);
    } catch (e) {
      state = const AuthError(message: 'An unexpected error occurred.');
    }
  }

  /// Registers a new user account and immediately authenticates.
  Future<void> register(
    String email,
    String password,
    String name, {
    int? companyId,
  }) async {
    state = const AuthLoading();

    try {
      final response = await _authService.register(
        email: email,
        password: password,
        name: name,
        companyId: companyId,
      );

      await _authService.saveTokens(
        accessToken: response.accessToken,
        refreshToken: response.refreshToken,
      );

      state = AuthAuthenticated(user: response.user);
    } on DioException catch (e) {
      final message = _extractErrorMessage(e);
      state = AuthError(message: message);
    } catch (e) {
      state = const AuthError(message: 'An unexpected error occurred.');
    }
  }

  /// Clears stored tokens and resets to unauthenticated state.
  Future<void> logout() async {
    await _authService.clearTokens();
    state = const AuthUnauthenticated();
  }

  /// Extracts a user-facing error message from a Dio error response.
  String _extractErrorMessage(DioException e) {
    final data = e.response?.data;
    if (data is Map<String, dynamic> && data.containsKey('detail')) {
      final detail = data['detail'];
      if (detail is String) return detail;
    }

    final statusCode = e.response?.statusCode;
    if (statusCode == null) {
      return 'Could not connect to the server. Please check your connection.';
    }
    return switch (statusCode) {
      400 => 'Invalid request. Please check your input.',
      401 => 'Invalid email or password.',
      409 => 'An account with this email already exists.',
      422 => 'Please check the form and try again.',
      429 => 'Too many attempts. Please wait and try again.',
      >= 500 => 'Server error. Please try again later.',
      _ => 'Could not connect to the server. Please check your connection.',
    };
  }
}

/// Provider for the main auth state.
final authStateProvider = NotifierProvider<AuthNotifier, AuthState>(
  AuthNotifier.new,
);

// ── Derived Providers (backward-compatible with router guards) ──────────────

/// Whether the user is currently authenticated.
///
/// Returns `false` while the initial auth check is still in progress,
/// which causes the router to show the login screen until the check
/// completes and confirms the user's session.
final isAuthenticatedProvider = Provider<bool>((ref) {
  final authState = ref.watch(authStateProvider);
  return authState is AuthAuthenticated;
});

/// Notifier that holds whether the current user has completed onboarding.
///
/// Defaults to `true` during development so the app skips the
/// onboarding flow.
class IsOnboardedNotifier extends Notifier<bool> {
  @override
  bool build() => true;

  // ignore: use_setters_to_change_properties
  void set(bool value) => state = value;
}

/// Provider exposing the current onboarding state.
final isOnboardedProvider = NotifierProvider<IsOnboardedNotifier, bool>(
  IsOnboardedNotifier.new,
);
