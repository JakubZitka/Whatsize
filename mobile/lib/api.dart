import 'dart:convert';

import 'package:http/http.dart' as http;

import 'profile.dart';

/// Injected at build time: --dart-define=WHATSIZE_API_URL=https://...
const apiUrl = String.fromEnvironment(
  'WHATSIZE_API_URL',
  defaultValue: 'http://localhost:8000',
);

class ApiException implements Exception {
  ApiException(this.message);

  final String message;

  @override
  String toString() => message;
}

class ApiClient {
  ApiClient({http.Client? client, this.baseUrl = apiUrl})
      : _client = client ?? http.Client();

  final http.Client _client;
  final String baseUrl;

  // The free test tier sleeps when idle; the first request can take a minute.
  static const _timeout = Duration(seconds: 90);

  Future<dynamic> _get(String path, [Map<String, String>? query]) async {
    var uri = Uri.parse('$baseUrl$path');
    if (query != null && query.isNotEmpty) {
      uri = uri.replace(queryParameters: query);
    }
    final response = await _client.get(uri).timeout(_timeout);
    return _decode(response);
  }

  Future<dynamic> _post(String path, Map<String, dynamic> body) async {
    final response = await _client
        .post(
          Uri.parse('$baseUrl$path'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode(body),
        )
        .timeout(_timeout);
    return _decode(response);
  }

  dynamic _decode(http.Response response) {
    // Decode as UTF-8 explicitly: the API sends Czech text without a charset.
    final text = utf8.decode(response.bodyBytes);
    if (response.statusCode >= 400) {
      var message = 'Server odpověděl chybou ${response.statusCode}.';
      try {
        final detail = (jsonDecode(text) as Map<String, dynamic>)['detail'];
        if (detail is String) {
          message = detail;
        }
      } on FormatException {
        message = 'Server odpověděl chybou ${response.statusCode}.';
      }
      throw ApiException(message);
    }
    return jsonDecode(text);
  }

  Future<Map<String, dynamic>> meta() async =>
      Map<String, dynamic>.from(await _get('/v1/meta') as Map);

  Future<List<Map<String, dynamic>>> brands({String? gender}) async {
    final data = await _get('/v1/brands', {if (gender != null) 'gender': gender});
    return [for (final b in data as List) Map<String, dynamic>.from(b as Map)];
  }

  Future<List<Map<String, dynamic>>> brandRecommendations(
    String brandId,
    Profile profile,
    String preference,
  ) async {
    final data = await _post('/v1/brands/$brandId/recommendations', {
      'gender': profile.gender,
      'measurements': profile.measurements,
      'preference': preference,
    });
    final results = (data as Map)['results'] as List;
    return [for (final r in results) Map<String, dynamic>.from(r as Map)];
  }

  Future<Map<String, dynamic>> validate(Profile profile) async {
    final data = await _post('/v1/measurements/validate', {
      'gender': profile.gender,
      'measurements': profile.measurements,
    });
    return Map<String, dynamic>.from(data as Map);
  }
}
