import 'package:flutter/material.dart';

class AppColors {
  static const forest900 = Color(0xFF16241F); // dark panels, primary buttons, header/footer
  static const forest800 = Color(0xFF1E332C); // secondary dark surface, hover/pressed states
  static const forest600 = Color(0xFF2F5245); // borders/dividers on dark panels
  static const cream50   = Color(0xFFF6F2E9); // primary page background
  static const cream100  = Color(0xFFEFE9DA); // alternating section background
  static const ink900    = Color(0xFF12140F); // headings on light surfaces
  static const slate600  = Color(0xFF4A5049); // body text on light backgrounds
  static const white     = Color(0xFFFFFFFF); // cards on dark panels, header bar on light
  static const border    = Color(0xFFE3DCC9); // hairline borders on cream surfaces
  static const goldAccent= Color(0xFFC9A227); // rare accent: trust badge, "verified" icon ONLY
  static const success   = Color(0xFF2E9E6B); // form success state
  static const error     = Color(0xFFB3412E); // form error state
}

class AppTheme {
  static ThemeData get themeData {
    return ThemeData(
      useMaterial3: true,
      scaffoldBackgroundColor: AppColors.cream50,
      colorScheme: const ColorScheme.light(
        primary: AppColors.forest900,
        secondary: AppColors.forest800,
        surface: AppColors.cream50,
        error: AppColors.error,
        onPrimary: AppColors.white,
        onSurface: AppColors.ink900,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.forest900,
        foregroundColor: AppColors.white,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: TextStyle(
          color: AppColors.white,
          fontSize: 20,
          fontWeight: FontWeight.w700,
          fontFamily: 'Sora',
        ),
      ),
      cardTheme: CardThemeData(
        color: AppColors.white,
        elevation: 1,
        shadowColor: AppColors.forest900.withValues(alpha: 0.08),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: const BorderSide(color: AppColors.border, width: 1),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.forest900,
          foregroundColor: AppColors.white,
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          textStyle: const TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w600,
            fontFamily: 'Inter',
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColors.forest900,
          side: const BorderSide(color: AppColors.forest600, width: 1.5),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.white,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.forest900, width: 2),
        ),
        labelStyle: const TextStyle(color: AppColors.slate600),
      ),
    );
  }
}
