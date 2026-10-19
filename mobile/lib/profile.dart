import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

/// The body profile. Storage is always metric; display is a presentation concern.
/// It lives on the device, so the in-store moment works without signal.
class Profile {
  Profile({this.gender = 'W', Map<String, double>? measurements})
      : measurements = measurements ?? {};

  factory Profile.fromJson(Map<String, dynamic> json) {
    final raw = json['measurements'] as Map? ?? {};
    return Profile(
      gender: json['gender'] as String? ?? 'W',
      measurements: {
        for (final e in raw.entries) e.key as String: (e.value as num).toDouble(),
      },
    );
  }

  String gender;
  final Map<String, double> measurements;

  bool get isEmpty => measurements.isEmpty;

  Map<String, dynamic> toJson() => {'gender': gender, 'measurements': measurements};
}

class ProfileStore {
  static const _key = 'whatsize_profile_v1';

  Future<Profile> load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key);
    if (raw == null) {
      return Profile();
    }
    try {
      return Profile.fromJson(jsonDecode(raw) as Map<String, dynamic>);
    } on FormatException {
      return Profile();
    }
  }

  Future<void> save(Profile profile) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, jsonEncode(profile.toJson()));
  }
}
