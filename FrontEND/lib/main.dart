import 'package:flutter/material.dart';

import 'screens/chat_screen.dart';

void main() {
  runApp(const AsylBilimApp());
}

class AsylBilimApp extends StatelessWidget {
  const AsylBilimApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AsylBILIM',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF09090B),
        primaryColor: const Color(0xFF6366F1),
        fontFamily: 'Inter',
      ),
      home: const ChatScreen(),
    );
  }
}
