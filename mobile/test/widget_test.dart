import 'package:flutter_test/flutter_test.dart';
import 'package:whatsize/main.dart';

void main() {
  testWidgets('app renders home screen', (tester) async {
    await tester.pumpWidget(const WhatSizeApp());
    expect(find.text('WhatSize'), findsOneWidget);
    expect(find.text('Zkontrolovat API'), findsOneWidget);
  });
}
