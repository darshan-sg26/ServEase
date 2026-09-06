import 'package:flutter/material.dart';
import 'core/theme.dart';
import 'screens/onboarding/login_register_screen.dart';

void main() {
  runApp(const ServEaseApp());
}

class ServEaseApp extends StatelessWidget {
  const ServEaseApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ServEase',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.themeData,
      initialRoute: '/',
      routes: {
        '/': (context) => const LoginRegisterScreen(),
      },
    );
  }
}
