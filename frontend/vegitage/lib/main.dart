import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vegitage/core/routing/app_router.dart';
import 'package:vegitage/shared/theme/app_theme.dart'; // 作成したファイルをインポート

void main() {
  GoRouter.optionURLReflectsImperativeAPIs = true;
  runApp(
    const ProviderScope(
      child: MyApp(),
    ),
  );
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Vegetage',

      // AppThemeからテーマを読み込む
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: ThemeMode.system, // OS設定に追従

      routerConfig: router,
    );
  }
}