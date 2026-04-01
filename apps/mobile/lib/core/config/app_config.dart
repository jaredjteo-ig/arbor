import 'dart:io' show Platform;

/// Application-wide configuration constants.
///
/// The API base URL is resolved at runtime based on the platform so that
/// Android emulators (which cannot reach `localhost` directly) use the
/// special `10.0.2.2` alias while iOS simulators and other platforms use
/// `localhost`.
abstract final class AppConfig {
  /// Base URL for the Arbor backend API.
  static String get apiBaseUrl {
    if (Platform.isAndroid) {
      return const String.fromEnvironment(
        'API_BASE_URL',
        defaultValue: 'http://10.0.2.2:8000',
      );
    }
    return const String.fromEnvironment(
      'API_BASE_URL',
      defaultValue: 'http://localhost:8000',
    );
  }

  /// Key used by [FlutterSecureStorage] for the access token.
  static const String accessTokenKey = 'access_token';

  /// Key used by [FlutterSecureStorage] for the refresh token.
  static const String refreshTokenKey = 'refresh_token';
}
