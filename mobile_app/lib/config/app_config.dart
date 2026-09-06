import 'package:flutter/foundation.dart';

/// Supported application environments
enum AppEnvironment {
  development,
  production,
}

/// Centralized configuration for ServEase Flutter mobile application.
/// 
/// Controls environment selection and backend API base URLs cleanly:
/// - In **DEVELOPMENT** (Debug/Profile mode by default): Connects to the local FastAPI backend on laptop LAN IP or Emulator.
/// - In **PRODUCTION** (Release mode by default): Connects to the live deployed Render FastAPI backend.
///
/// Compile-time overrides:
/// - Force production build: `--dart-define=ENV=prod`
/// - Force development build: `--dart-define=ENV=dev`
/// - Override base API URL: `--dart-define=API_URL=https://my-backend.com`
/// - Override dev LAN URL: `--dart-define=DEV_API_URL=http://192.168.1.50:8000`
class AppConfig {
  AppConfig._();

  // ---------------------------------------------------------------------------
  // Canonical URLs
  // ---------------------------------------------------------------------------

  /// Live Production Render FastAPI Backend (HTTPS)
  static const String prodBaseUrl = 'https://servease-wyu0.onrender.com';

  /// Default Laptop Wi-Fi LAN endpoint for physical Android phone testing
  static const String devLanBaseUrl = 'http://10.84.225.101:8000';

  /// Android Emulator loopback endpoint to laptop host
  static const String devEmulatorBaseUrl = 'http://10.0.2.2:8000';

  /// Localhost endpoint for Web / Desktop
  static const String devLocalhostBaseUrl = 'http://127.0.0.1:8000';

  // ---------------------------------------------------------------------------
  // Google Sign-In Configuration
  // ---------------------------------------------------------------------------

  /// Web Client ID (OAuth 2.0 Client ID for Web Application).
  /// Required as `serverClientId` by GoogleSignIn so the backend receives an ID token.
  static const String googleServerClientId = '345293252389-v8am6fn020elna3jb34spg58jb4mj4e9.apps.googleusercontent.com';

  // ---------------------------------------------------------------------------
  // Compile-time environment flags
  // ---------------------------------------------------------------------------
  static const String _envString = String.fromEnvironment('ENV', defaultValue: '');
  static const String _apiUrlOverride = String.fromEnvironment('API_URL', defaultValue: '');
  static const String _devApiUrlOverride = String.fromEnvironment('DEV_API_URL', defaultValue: '');

  /// Returns the active [AppEnvironment] based on compile-time flags or build mode.
  static AppEnvironment get environment {
    final lower = _envString.trim().toLowerCase();
    if (lower == 'prod' || lower == 'production') {
      return AppEnvironment.production;
    }
    if (lower == 'dev' || lower == 'development') {
      return AppEnvironment.development;
    }
    // Default: Release builds target Production, Debug builds target Development
    return kReleaseMode ? AppEnvironment.production : AppEnvironment.development;
  }

  /// True if currently in production mode
  static bool get isProduction => environment == AppEnvironment.production;

  /// True if currently in development mode
  static bool get isDevelopment => environment == AppEnvironment.development;

  /// Human-readable environment name ('PRODUCTION' or 'DEVELOPMENT')
  static String get activeEnvironmentName => isProduction ? 'PRODUCTION' : 'DEVELOPMENT';

  /// Returns the appropriate default Base URL for the active environment.
  static String get defaultBaseUrl {
    // 1. Direct explicit API_URL override takes top priority
    if (_apiUrlOverride.trim().isNotEmpty) {
      return _apiUrlOverride.trim();
    }

    // 2. Production Environment
    if (isProduction) {
      return prodBaseUrl;
    }

    // 3. Development Environment
    if (_devApiUrlOverride.trim().isNotEmpty) {
      return _devApiUrlOverride.trim();
    }

    // When running in a web browser on the same laptop, connect to localhost
    if (kIsWeb) {
      return devLocalhostBaseUrl;
    }

    // Development default for mobile devices: laptop LAN IP for physical device Wi-Fi connectivity
    return devLanBaseUrl;
  }
}
