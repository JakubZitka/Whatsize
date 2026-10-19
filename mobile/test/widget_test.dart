import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:whatsize/api.dart';
import 'package:whatsize/main.dart';

http.Response _json(Object body) => http.Response.bytes(
      utf8.encode(jsonEncode(body)),
      200,
      headers: {'content-type': 'application/json'},
    );

ApiClient _fakeApi() => ApiClient(
      baseUrl: 'http://test',
      client: MockClient((request) async {
        final path = request.url.path;
        if (path == '/v1/meta') {
          return _json({'data_version': 'seed-v1.0', 'brands': 100, 'data_note': 'Test.'});
        }
        if (path == '/v1/brands') {
          return _json([
            {'brand_id': 'levis', 'brand_name': "Levi's", 'segment': 'denim'},
            {'brand_id': 'zara', 'brand_name': 'Zara', 'segment': 'fast_fashion'},
          ]);
        }
        if (path == '/v1/brands/levis/recommendations') {
          return _json({
            'brand_id': 'levis',
            'results': [
              {
                'status': 'ok',
                'category_name': 'Džíny',
                'size_system': 'WL',
                'size_label': 'W27',
                'runner_up': null,
                'confidence': 0.49,
                'fit_code': 'curvy',
                'warnings': <Object>[],
                'notes': ['Odvozeno z normy.'],
                'explanation': 'Velikost určuje obvod pasu.',
              },
            ],
          });
        }
        return http.Response('not found', 404);
      }),
    );

void main() {
  setUp(() => SharedPreferences.setMockInitialValues({
        'whatsize_profile_v1':
            '{"gender":"W","measurements":{"waist_cm":76,"hip_cm":106}}',
      }));

  testWidgets('home shows the saved profile and data notice', (tester) async {
    await tester.pumpWidget(WhatSizeApp(api: _fakeApi()));
    await tester.pumpAndSettle();
    expect(find.text('Moje míry'), findsOneWidget);
    expect(find.text('Obvod pasu: 76 cm'), findsOneWidget);
    expect(find.textContaining('100 značek'), findsOneWidget);
  });

  testWidgets('brand flow shows the recommended size', (tester) async {
    await tester.pumpWidget(WhatSizeApp(api: _fakeApi()));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Najít velikost ve značce'));
    await tester.pumpAndSettle();
    expect(find.text('Zara'), findsOneWidget);
    await tester.enterText(find.byType(TextField), 'lev');
    await tester.pumpAndSettle();
    expect(find.text('Zara'), findsNothing);
    await tester.tap(find.text("Levi's"));
    await tester.pumpAndSettle();
    expect(find.text('W27'), findsOneWidget);
    expect(find.text('Střih Curvy'), findsOneWidget);
  });
}
