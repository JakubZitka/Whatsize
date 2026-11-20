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
          return _json({'data_version': 'v3.0', 'brands': 108, 'data_note': 'Test.'});
        }
        if (path == '/v1/brands') {
          return _json([
            {
              'brand_id': 'BR060',
              'brand_name': "Levi's",
              'segment': 'denim',
              'data_source': 'publisher_size_guide',
            },
            {
              'brand_id': 'BR109',
              'brand_name': 'Zara',
              'segment': 'fast_fashion',
              'data_source': 'derived_from_standard',
            },
          ]);
        }
        if (path == '/v1/brands/BR060/recommendations') {
          return _json({
            'brand_id': 'BR060',
            'results': [
              {
                'status': 'ok',
                'category_name': 'Džíny',
                'size_system': 'WL',
                'size_label': '29',
                'runner_up': '28',
                'also': <String, Object>{},
                'source': {'type': 'publisher_size_guide', 'market': 'DE'},
                'confidence': 0.54,
                'fit_code': 'plus',
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
    expect(find.textContaining('108 značek'), findsOneWidget);
  });

  testWidgets('brand flow shows the recommended size', (tester) async {
    await tester.pumpWidget(WhatSizeApp(api: _fakeApi()));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Najít velikost ve značce'));
    await tester.pumpAndSettle();
    expect(find.text('Zara'), findsOneWidget);
    expect(find.text('Rychlá móda · odvozeno z normy'), findsOneWidget);
    await tester.enterText(find.byType(TextField), 'lev');
    await tester.pumpAndSettle();
    expect(find.text('Zara'), findsNothing);
    await tester.tap(find.text("Levi's"));
    await tester.pumpAndSettle();
    expect(find.text('W 29'), findsOneWidget);
    expect(find.text('Střih Plus'), findsOneWidget);
    expect(find.text('Jsi na hranici — zvaž i 28.'), findsOneWidget);
    expect(find.text('Podle tabulky velikostí značky (DE).'), findsOneWidget);
  });
}
