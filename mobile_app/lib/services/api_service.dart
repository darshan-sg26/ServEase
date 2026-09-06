import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../config/app_config.dart';
import '../models/models.dart';

class ApiService {
  /// Default base URL resolved dynamically from [AppConfig] based on environment
  static String get defaultBaseUrl => AppConfig.defaultBaseUrl;

  static String _customBaseUrl = '';

  static String get baseUrl {
    if (_customBaseUrl.trim().isNotEmpty) {
      return _customBaseUrl.trim();
    }
    return defaultBaseUrl;
  }

  static set baseUrl(String value) {
    _customBaseUrl = value.trim();
  }

  static AppEnvironment get environment => AppConfig.environment;
  static bool get isProduction => AppConfig.isProduction;
  static bool get isDevelopment => AppConfig.isDevelopment;

  static String get formattedBaseUrl {
    var url = baseUrl;
    if (url.isEmpty) {
      url = defaultBaseUrl;
    }

    // Auto-map localhost / 127.0.0.1 to 10.0.2.2 when running on Android emulator
    if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
      if (url.contains('localhost')) {
        url = url.replaceAll('localhost', '10.0.2.2');
      } else if (url.contains('127.0.0.1')) {
        url = url.replaceAll('127.0.0.1', '10.0.2.2');
      }
    }

    if (url.endsWith('/')) {
      url = url.substring(0, url.length - 1);
    }
    if (!url.endsWith('/api/v1')) {
      url = '$url/api/v1';
    }
    return url;
  }

  static String? authToken;
  static int? currentUserId;
  static String currentRole = 'worker';
  static String currentUserEmail = '';
  static String currentUserName = '';

  static Map<String, String> get _headers => {
    'Content-Type': 'application/json',
    'Cache-Control': 'no-cache, no-store, must-revalidate',
    'Pragma': 'no-cache',
    'Expires': '0',
    'Bypass-Tunnel-Reminder': 'true',
    'bypass-tunnel-reminder': 'true',
    if (authToken != null) 'Authorization': 'Bearer $authToken',
  };

  static Future<Map<String, dynamic>> login(String email, String password) async {
    try {
      final targetUrl = '$formattedBaseUrl/auth/login';
      if (kDebugMode) print('ApiService.login -> Calling: $targetUrl');

      final res = await http.post(
        Uri.parse(targetUrl),
        headers: _headers,
        body: jsonEncode({'email': email, 'password': password}),
      );

      if (kDebugMode) print('ApiService.login -> Response Code: ${res.statusCode}');

      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        authToken = data['access_token'];
        currentRole = data['role'];
        currentUserId = data['user_id'];
        currentUserEmail = email;

        // Fetch actual profile name
        if (currentRole == 'worker') {
          final wp = await fetchMyWorkerProfile();
          if (wp != null) currentUserName = wp.fullName;
        } else if (currentRole == 'provider') {
          final pp = await fetchMyProviderProfile();
          if (pp != null) currentUserName = pp.fullName;
        }
        if (currentUserName.isEmpty) {
          currentUserName = email.split('@')[0].toUpperCase();
        }

        return {'success': true, 'role': currentRole};
      } else {
        final err = jsonDecode(res.body);
        return {'success': false, 'message': err['detail'] ?? 'Login failed'};
      }
    } catch (e) {
      if (kDebugMode) print('ApiService.login -> Exception: $e');
      // Demo fallback if network is completely unreachable
      if (email.contains('worker') || email.contains('arsha') || email.contains('ramesh')) {
        authToken = 'demo_token';
        currentRole = 'worker';
        currentUserId = 1;
        currentUserEmail = email;
        currentUserName = email.contains('arsha') ? 'Arsha' : 'Ramesh Kumar';
        return {'success': true, 'role': 'worker'};
      } else if (email.contains('provider') || email.contains('bharath') || email.contains('priya')) {
        authToken = 'demo_token';
        currentRole = 'provider';
        currentUserId = 2;
        currentUserEmail = email;
        currentUserName = email.contains('bharath') ? 'Bharath' : 'Priya Sharma';
        return {'success': true, 'role': 'provider'};
      } else if (email.contains('admin')) {
        authToken = 'demo_token';
        currentRole = 'admin';
        currentUserId = 0;
        currentUserEmail = email;
        currentUserName = 'System Admin';
        return {'success': true, 'role': 'admin'};
      }
      return {'success': false, 'message': 'Network error ($e). Please verify server endpoint.'};
    }
  }

  static Future<Map<String, dynamic>> googleLogin({
    required String idToken,
    String? role,
  }) async {
    try {
      final targetUrl = '$formattedBaseUrl/auth/google';
      if (kDebugMode) print('ApiService.googleLogin -> Calling: $targetUrl');

      final payload = <String, dynamic>{
        'id_token': idToken,
        if (role != null) 'role': role,
      };

      final res = await http.post(
        Uri.parse(targetUrl),
        headers: _headers,
        body: jsonEncode(payload),
      );

      if (kDebugMode) print('ApiService.googleLogin -> Response Code: ${res.statusCode}');

      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        authToken = data['access_token'];
        currentRole = data['role'];
        currentUserId = data['user_id'];

        // Fetch actual profile name
        if (currentRole == 'worker') {
          final wp = await fetchMyWorkerProfile();
          if (wp != null) {
            currentUserName = wp.fullName;
          }
        } else if (currentRole == 'provider') {
          final pp = await fetchMyProviderProfile();
          if (pp != null) {
            currentUserName = pp.fullName;
          }
        }
        if (currentUserName.isEmpty) {
          currentUserName = 'ServEase User';
        }

        return {'success': true, 'role': currentRole};
      } else {
        final err = jsonDecode(res.body);
        return {'success': false, 'message': err['detail'] ?? 'Google sign-in failed'};
      }
    } catch (e) {
      if (kDebugMode) print('ApiService.googleLogin -> Exception: $e');
      return {'success': false, 'message': 'Network error ($e). Please verify server endpoint.'};
    }
  }

  static Future<Map<String, dynamic>> register({
    required String email,
    required String password,
    required String fullName,
    required String role,
    String? phone,
    String? gender,
  }) async {
    try {
      final res = await http.post(
        Uri.parse('$formattedBaseUrl/auth/register'),
        headers: _headers,
        body: jsonEncode({
          'email': email,
          'password': password,
          'full_name': fullName,
          'role': role,
          'phone': phone ?? '+919876543210',
          'gender': gender ?? 'prefer_not_to_say',
          'latitude': 12.9716,
          'longitude': 77.5946,
        }),
      );
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        return {
          'success': true,
          'requires_verification': data['requires_verification'] ?? true,
          'email': data['email'] ?? email,
          'message': data['message'] ?? 'Verification code sent to your email',
        };
      } else {
        final err = jsonDecode(res.body);
        return {'success': false, 'message': err['detail'] ?? 'Registration failed'};
      }
    } catch (e) {
      if (kDebugMode) print('ApiService.register -> Exception: $e');
      return {'success': false, 'message': 'Network error ($e). Please check backend connection.'};
    }
  }

  static Future<Map<String, dynamic>> verifyOtp({
    required String email,
    required String otp,
  }) async {
    try {
      final res = await http.post(
        Uri.parse('$formattedBaseUrl/auth/verify-otp'),
        headers: _headers,
        body: jsonEncode({'email': email, 'otp': otp}),
      );
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        authToken = data['access_token'];
        currentRole = data['role'];
        currentUserId = data['user_id'];
        currentUserEmail = email;

        // Fetch user profile
        if (currentRole == 'worker') {
          final wp = await fetchMyWorkerProfile();
          if (wp != null) currentUserName = wp.fullName;
        } else if (currentRole == 'provider') {
          final pp = await fetchMyProviderProfile();
          if (pp != null) currentUserName = pp.fullName;
        }
        if (currentUserName.isEmpty) {
          currentUserName = email.split('@')[0].toUpperCase();
        }

        return {'success': true, 'role': currentRole};
      } else {
        final err = jsonDecode(res.body);
        return {'success': false, 'message': err['detail'] ?? 'Verification failed'};
      }
    } catch (e) {
      if (kDebugMode) print('ApiService.verifyOtp -> Exception: $e');
      return {'success': false, 'message': 'Network error ($e). Please check connection.'};
    }
  }

  static Future<Map<String, dynamic>> resendOtp({required String email}) async {
    try {
      final res = await http.post(
        Uri.parse('$formattedBaseUrl/auth/resend-otp'),
        headers: _headers,
        body: jsonEncode({'email': email}),
      );
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        return {'success': true, 'message': data['message'] ?? 'New verification code sent'};
      } else {
        final err = jsonDecode(res.body);
        return {'success': false, 'message': err['detail'] ?? 'Failed to resend code'};
      }
    } catch (e) {
      if (kDebugMode) print('ApiService.resendOtp -> Exception: $e');
      return {'success': false, 'message': 'Network error ($e).'};
    }
  }

  static void logout() {
    authToken = null;
    currentUserId = null;
    currentRole = 'worker';
    currentUserEmail = '';
    currentUserName = '';
  }

  static Future<WorkerProfile?> fetchMyWorkerProfile() async {
    try {
      final res = await http.get(Uri.parse('$formattedBaseUrl/workers/me'), headers: _headers);
      if (res.statusCode == 200) {
        final wp = WorkerProfile.fromJson(jsonDecode(res.body));
        currentUserName = wp.fullName;
        return wp;
      }
    } catch (e) {
      if (kDebugMode) print('fetchMyWorkerProfile error: $e');
    }
    return null;
  }

  static Future<ProviderProfile?> fetchMyProviderProfile() async {
    try {
      final res = await http.get(Uri.parse('$formattedBaseUrl/auth/providers/me'), headers: _headers);
      if (res.statusCode == 200) {
        final pp = ProviderProfile.fromJson(jsonDecode(res.body));
        currentUserName = pp.fullName;
        return pp;
      }
    } catch (e) {
      if (kDebugMode) print('fetchMyProviderProfile error: $e');
    }
    return null;
  }

  static Future<WorkerProfile?> updateWorkerProfile(Map<String, dynamic> body) async {
    try {
      final res = await http.put(
        Uri.parse('$formattedBaseUrl/workers/me'),
        headers: _headers,
        body: jsonEncode(body),
      );
      if (res.statusCode == 200) {
        final wp = WorkerProfile.fromJson(jsonDecode(res.body));
        currentUserName = wp.fullName;
        return wp;
      }
    } catch (e) {
      if (kDebugMode) print('updateWorkerProfile error: $e');
    }
    return null;
  }

  static Future<WorkerProfile?> updateWorkerLocation(double lat, double lng, {String? locationName}) async {
    try {
      final res = await http.put(
        Uri.parse('$formattedBaseUrl/workers/me/location'),
        headers: _headers,
        body: jsonEncode({
          'latitude': lat,
          'longitude': lng,
          if (locationName != null && locationName.isNotEmpty) 'location_name': locationName,
        }),
      );
      if (res.statusCode == 200) {
        final wp = WorkerProfile.fromJson(jsonDecode(res.body));
        currentUserName = wp.fullName;
        return wp;
      }
    } catch (e) {
      if (kDebugMode) print('updateWorkerLocation error: $e');
    }
    return null;
  }

  static Future<bool> addWorkerSkill(Map<String, dynamic> skillData) async {
    try {
      final res = await http.post(
        Uri.parse('$formattedBaseUrl/workers/me/skills'),
        headers: _headers,
        body: jsonEncode(skillData),
      );
      return res.statusCode == 200 || res.statusCode == 201;
    } catch (e) {
      if (kDebugMode) print('addWorkerSkill error: $e');
    }
    return false;
  }

  static Future<bool> postJob(Map<String, dynamic> jobData) async {
    try {
      final res = await http.post(
        Uri.parse('$formattedBaseUrl/jobs'),
        headers: _headers,
        body: jsonEncode(jobData),
      );
      if (kDebugMode) print('postJob -> Status: ${res.statusCode}, Body: ${res.body}');
      return res.statusCode == 200 || res.statusCode == 201;
    } catch (e) {
      if (kDebugMode) print('postJob error: $e');
    }
    return false;
  }

  static Future<bool> applyJob(int jobId) async {
    try {
      final res = await http.post(
        Uri.parse('$formattedBaseUrl/jobs/$jobId/apply'),
        headers: _headers,
      );
      return res.statusCode == 200 || res.statusCode == 201;
    } catch (e) {
      if (kDebugMode) print('applyJob error: $e');
    }
    return false;
  }

  static Future<bool> deleteJob(int jobId) async {
    try {
      final res = await http.delete(
        Uri.parse('$formattedBaseUrl/jobs/$jobId'),
        headers: _headers,
      );
      return res.statusCode == 200;
    } catch (e) {
      if (kDebugMode) print('deleteJob error: $e');
    }
    return false;
  }

  static Future<List<Job>> fetchJobs({
    String? skill,
    String? query,
    String? statusFilter,
    double? nearLat,
    double? nearLng,
    double? radiusKm,
  }) async {
    try {
      final params = <String, String>{};
      if (skill != null && skill.isNotEmpty) params['skill'] = skill;
      if (query != null && query.isNotEmpty) params['q'] = query;
      if (statusFilter != null && statusFilter.isNotEmpty) params['status_filter'] = statusFilter;
      if (nearLat != null) params['near_lat'] = nearLat.toString();
      if (nearLng != null) params['near_lng'] = nearLng.toString();
      if (radiusKm != null) params['radius_km'] = radiusKm.toString();

      final baseUri = Uri.parse('$formattedBaseUrl/jobs');
      final uri = params.isNotEmpty ? baseUri.replace(queryParameters: params) : baseUri;

      final res = await http.get(uri, headers: _headers);
      if (kDebugMode) print('fetchJobs -> Status: ${res.statusCode}');
      if (res.statusCode == 200) {
        final List list = jsonDecode(res.body);
        return list.map((j) => Job.fromJson(j)).toList();
      }
    } catch (e) {
      if (kDebugMode) print('fetchJobs error: $e');
    }
    return [];
  }

  static Future<List<JobApplication>> fetchJobApplications(int jobId) async {
    try {
      final res = await http.get(
        Uri.parse('$formattedBaseUrl/jobs/$jobId/applications'),
        headers: _headers,
      );
      if (res.statusCode == 200) {
        final List list = jsonDecode(res.body);
        return list.map((a) => JobApplication.fromJson(a)).toList();
      }
    } catch (e) {
      if (kDebugMode) print('fetchJobApplications error: $e');
    }
    return [];
  }

  static Future<bool> respondJobApplication(int jobId, int appId, String action) async {
    try {
      final res = await http.post(
        Uri.parse('$formattedBaseUrl/jobs/$jobId/applications/$appId/respond?action=$action'),
        headers: _headers,
      );
      return res.statusCode == 200;
    } catch (e) {
      if (kDebugMode) print('respondJobApplication error: $e');
    }
    return false;
  }

  static Future<bool> completeJob(int jobId) async {
    try {
      final res = await http.post(
        Uri.parse('$formattedBaseUrl/jobs/$jobId/complete'),
        headers: _headers,
      );
      return res.statusCode == 200;
    } catch (e) {
      if (kDebugMode) print('completeJob error: $e');
    }
    return false;
  }

  static Future<List<MatchedWorker>> fetchJobMatches(int jobId) async {
    try {
      final res = await http.get(Uri.parse('$formattedBaseUrl/jobs/$jobId/matches'), headers: _headers);
      if (res.statusCode == 200) {
        final List list = jsonDecode(res.body);
        return list.map((m) => MatchedWorker.fromJson(m)).toList();
      }
    } catch (e) {
      if (kDebugMode) print('fetchJobMatches error: $e');
    }
    return [];
  }

  static Future<List<WorkerProfile>> fetchWorkers({String? skill, String? query}) async {
    try {
      final params = <String, String>{};
      if (skill != null && skill.isNotEmpty) params['skill'] = skill;
      if (query != null && query.isNotEmpty) params['q'] = query;

      final baseUri = Uri.parse('$formattedBaseUrl/workers');
      final uri = params.isNotEmpty ? baseUri.replace(queryParameters: params) : baseUri;

      final res = await http.get(uri, headers: _headers);
      if (kDebugMode) print('fetchWorkers -> Status: ${res.statusCode}');
      if (res.statusCode == 200) {
        final List list = jsonDecode(res.body);
        return list.map((w) => WorkerProfile.fromJson(w)).toList();
      }
    } catch (e) {
      if (kDebugMode) print('fetchWorkers error: $e');
    }
    return [];
  }

  static Future<List<DirectOffer>> fetchDirectOffers({String? query}) async {
    try {
      final params = <String, String>{};
      if (query != null && query.isNotEmpty) params['q'] = query;

      final baseUri = Uri.parse('$formattedBaseUrl/direct-offers');
      final uri = params.isNotEmpty ? baseUri.replace(queryParameters: params) : baseUri;

      final res = await http.get(uri, headers: _headers);
      if (res.statusCode == 200) {
        final List list = jsonDecode(res.body);
        return list.map((o) => DirectOffer.fromJson(o)).toList();
      }
    } catch (e) {
      if (kDebugMode) print('fetchDirectOffers error: $e');
    }
    return [];
  }

  static Future<bool> sendDirectOffer(Map<String, dynamic> data) async {
    try {
      final res = await http.post(
        Uri.parse('$formattedBaseUrl/direct-offers'),
        headers: _headers,
        body: jsonEncode(data),
      );
      return res.statusCode == 200 || res.statusCode == 201;
    } catch (e) {
      if (kDebugMode) print('sendDirectOffer error: $e');
    }
    return false;
  }

  static Future<bool> respondDirectOffer(int offerId, String action) async {
    try {
      final res = await http.patch(
        Uri.parse('$formattedBaseUrl/direct-offers/$offerId'),
        headers: _headers,
        body: jsonEncode({'action': action}),
      );
      return res.statusCode == 200;
    } catch (e) {
      if (kDebugMode) print('respondDirectOffer error: $e');
    }
    return false;
  }

  static Future<PlatformAnalytics?> fetchAnalytics() async {
    try {
      final res = await http.get(
        Uri.parse('$formattedBaseUrl/admin/analytics'),
        headers: _headers,
      );
      if (res.statusCode == 200) {
        return PlatformAnalytics.fromJson(jsonDecode(res.body));
      }
    } catch (e) {
      if (kDebugMode) print('fetchAnalytics error: $e');
    }
    return null;
  }

  static Future<List<FraudFlag>> fetchFraudFlags() async {
    try {
      final res = await http.get(
        Uri.parse('$formattedBaseUrl/admin/fraud-flags'),
        headers: _headers,
      );
      if (res.statusCode == 200) {
        final List list = jsonDecode(res.body);
        return list.map((f) => FraudFlag.fromJson(f)).toList();
      }
    } catch (e) {
      if (kDebugMode) print('fetchFraudFlags error: $e');
    }
    return [];
  }

  static Future<Map<String, dynamic>> submitRating({
    required int jobId,
    required int overallRating,
    Map<String, int>? categoryRatings,
    String? comment,
  }) async {
    try {
      final res = await http.post(
        Uri.parse('$formattedBaseUrl/jobs/reviews'),
        headers: _headers,
        body: jsonEncode({
          'job_id': jobId,
          'overall_rating': overallRating,
          'category_ratings': categoryRatings ?? {},
          'comment': comment,
        }),
      );
      if (res.statusCode == 200 || res.statusCode == 201) {
        return {'success': true, 'data': jsonDecode(res.body)};
      } else {
        final err = jsonDecode(res.body);
        return {'success': false, 'message': err['detail'] ?? 'Failed to submit rating'};
      }
    } catch (e) {
      return {'success': false, 'message': 'Network error: $e'};
    }
  }

  static Future<JobRatingsStatus?> fetchJobRatings(int jobId) async {
    try {
      final res = await http.get(
        Uri.parse('$formattedBaseUrl/jobs/$jobId/ratings'),
        headers: _headers,
      );
      if (res.statusCode == 200) {
        return JobRatingsStatus.fromJson(jsonDecode(res.body));
      }
    } catch (e) {
      if (kDebugMode) print('fetchJobRatings error: $e');
    }
    return null;
  }

  static Future<Map<String, dynamic>?> fetchUserRatingSummary(int userId) async {
    try {
      final res = await http.get(
        Uri.parse('$formattedBaseUrl/jobs/users/$userId/rating-summary'),
        headers: _headers,
      );
      if (res.statusCode == 200) {
        return jsonDecode(res.body);
      }
    } catch (e) {
      if (kDebugMode) print('fetchUserRatingSummary error: $e');
    }
    return null;
  }
}
