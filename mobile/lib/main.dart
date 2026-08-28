import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

/// Injected at build time: --dart-define=WHATSIZE_API_URL=https://...
const apiUrl = String.fromEnvironment(
  'WHATSIZE_API_URL',
  defaultValue: 'http://localhost:8000',
);

void main() {
  runApp(const WhatSizeApp());
}

class WhatSizeApp extends StatelessWidget {
  const WhatSizeApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'WhatSize',
      theme: ThemeData(useMaterial3: true),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  String? _apiStatus;

  Future<void> _checkApi() async {
    setState(() => _apiStatus = 'Zjišťuji…');
    try {
      final response = await http
          .get(Uri.parse('$apiUrl/healthz'))
          .timeout(const Duration(seconds: 90)); // free tier wakes from sleep
      setState(() => _apiStatus = response.statusCode == 200
          ? 'API běží ($apiUrl)'
          : 'API odpovědělo ${response.statusCode}');
    } catch (_) {
      setState(() => _apiStatus = 'API nedostupné ($apiUrl)');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text('WhatSize', style: Theme.of(context).textTheme.headlineLarge),
            const SizedBox(height: 24),
            FilledButton(
              onPressed: _checkApi,
              child: const Text('Zkontrolovat API'),
            ),
            if (_apiStatus != null) ...[
              const SizedBox(height: 16),
              Text(_apiStatus!),
            ],
          ],
        ),
      ),
    );
  }
}
