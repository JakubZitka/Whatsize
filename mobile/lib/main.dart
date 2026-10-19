import 'package:flutter/material.dart';

import 'api.dart';
import 'profile.dart';
import 'screens/home_screen.dart';

void main() {
  runApp(WhatSizeApp());
}

class WhatSizeApp extends StatelessWidget {
  WhatSizeApp({super.key, ApiClient? api, ProfileStore? store})
      : api = api ?? ApiClient(),
        store = store ?? ProfileStore();

  final ApiClient api;
  final ProfileStore store;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'WhatSize',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorSchemeSeed: const Color(0xFF35558A),
      ),
      darkTheme: ThemeData(
        useMaterial3: true,
        colorSchemeSeed: const Color(0xFF35558A),
        brightness: Brightness.dark,
      ),
      home: HomeScreen(api: api, store: store),
    );
  }
}
