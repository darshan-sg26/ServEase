import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';

/// Structured result of a location acquisition attempt
class LocationResult {
  final bool isSuccess;
  final double? latitude;
  final double? longitude;
  final String? errorMessage;
  final bool isPermissionDeniedForever;
  final bool isServiceDisabled;

  const LocationResult({
    required this.isSuccess,
    this.latitude,
    this.longitude,
    this.errorMessage,
    this.isPermissionDeniedForever = false,
    this.isServiceDisabled = false,
  });

  factory LocationResult.success(double latitude, double longitude) {
    return LocationResult(
      isSuccess: true,
      latitude: latitude,
      longitude: longitude,
    );
  }

  factory LocationResult.failure(
    String message, {
    bool isPermissionDeniedForever = false,
    bool isServiceDisabled = false,
  }) {
    return LocationResult(
      isSuccess: false,
      errorMessage: message,
      isPermissionDeniedForever: isPermissionDeniedForever,
      isServiceDisabled: isServiceDisabled,
    );
  }
}

/// Standalone Device Location Manager for ServEase
/// Handles GPS status, permissions, and accurate device coordinate acquisition without fake mock coordinates.
class LocationService {
  LocationService._();

  /// Requests permission (if needed) and fetches the device's live GPS coordinates.
  /// Returns a clean failure state if permission is denied or GPS is turned off.
  static Future<LocationResult> getCurrentLocation({bool requestPermission = true}) async {
    try {
      // 1. Check if device location service is enabled
      final serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        return LocationResult.failure(
          'Location services are disabled on your device. Please turn on GPS.',
          isServiceDisabled: true,
        );
      }

      // 2. Check permission status
      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        if (!requestPermission) {
          return LocationResult.failure('Location permission is not granted.');
        }
        permission = await Geolocator.requestPermission();
        if (permission == LocationPermission.denied) {
          return LocationResult.failure('Location permission was denied.');
        }
      }

      if (permission == LocationPermission.deniedForever) {
        return LocationResult.failure(
          'Location permission is permanently denied. Please enable it in App Settings.',
          isPermissionDeniedForever: true,
        );
      }

      // 3. Obtain real GPS position
      final position = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
        timeLimit: const Duration(seconds: 15),
      );

      return LocationResult.success(position.latitude, position.longitude);
    } catch (e) {
      if (kDebugMode) {
        print('LocationService error: $e');
      }
      return LocationResult.failure('Failed to acquire GPS location: $e');
    }
  }

  /// Opens device location settings (useful if GPS hardware is turned off)
  static Future<bool> openLocationSettings() async {
    try {
      return await Geolocator.openLocationSettings();
    } catch (_) {
      return false;
    }
  }

  /// Opens app permissions settings (useful if permission was denied forever)
  static Future<bool> openAppSettings() async {
    try {
      return await Geolocator.openAppSettings();
    } catch (_) {
      return false;
    }
  }

  /// Client-side distance calculation helper in kilometers
  static double calculateDistanceKm(double lat1, double lon1, double lat2, double lon2) {
    try {
      final distanceInMeters = Geolocator.distanceBetween(lat1, lon1, lat2, lon2);
      return distanceInMeters / 1000.0;
    } catch (_) {
      return 0.0;
    }
  }
}
