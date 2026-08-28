import 'package:flutter/material.dart';

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
      home: const Scaffold(
        body: Center(child: Text('WhatSize')),
      ),
    );
  }
}
