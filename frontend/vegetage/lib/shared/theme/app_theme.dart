import 'package:flutter/material.dart';

/// アプリ全体のデザインテーマを定義するクラス
///
/// このファイルで定義されたテーマを MaterialApp に設定することで、
/// アプリ内のウィジェットの見た目を一元管理できます。
/// 「マテリアル・ハーベスト」のデザインコンセプトに基づいています。
class AppTheme {
  // プライベートコンストラクタでインスタンス化を防止
  AppTheme._();

  // --- 1. カラー定義 ---
  // デザインの核となるシードカラー
  static const _seedColor = Color(0xFF4A6A59);

  // ライトモード用のColorScheme
  static final _lightColorScheme = ColorScheme.fromSeed(
    seedColor: _seedColor,
    brightness: Brightness.light,
    surface: const Color(0xFFFCFCF9), // 温かみのある白
    onSurface: const Color(0xFF1A1C1A), // コントラストを確保した黒
  );

  // ダークモード用のColorScheme
  static final _darkColorScheme = ColorScheme.fromSeed(
    seedColor: _seedColor,
    brightness: Brightness.dark,
    // 以下の2行を追加して、ダークモードの背景と文字色をカスタマイズ
    surface: const Color(0xFF1B1C1B), // 夜の森の土の色
    onSurface: const Color(0xFFE2E3E0), // 温かみのある白文字
  );

  // --- 2. ライト/ダーク共通のテーマを生成するメソッド ---
  static ThemeData _createTheme(ColorScheme colorScheme) {
    final baseTheme = ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      // 同梱のサブセット済み BIZ UDPGothic を使用
      // (Web版が Google Fonts へフォールバック取得しないようにするため)
      fontFamily: 'BIZUDPGothic',
    );

    // ベーステーマに対して、各コンポーネントの共通スタイルを適用
    return baseTheme.copyWith(
      // BIZ UDPGothic に無い文字(ハングル等)は同梱の Noto サブセットで補う
      textTheme: baseTheme.textTheme.apply(
        fontFamilyFallback: ['NotoSansCJKjp'],
      ),
      scaffoldBackgroundColor: colorScheme.surface,

      // AppBarのスタイル
      appBarTheme: baseTheme.appBarTheme.copyWith(
        elevation: 0,
        backgroundColor: colorScheme.surface,
        foregroundColor: colorScheme.onSurface,
        // スクロールしてもAppBarの色が変わらないように設定
        scrolledUnderElevation: 0,
      ),

      // Cardのスタイル
      cardTheme: baseTheme.cardTheme.copyWith(
        elevation: 1,
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(12)),
        ),
        // カード内の画像などが角丸からはみ出ないようにする
        clipBehavior: Clip.antiAlias,
      ),

      // FloatingActionButtonのスタイル
      floatingActionButtonTheme: baseTheme.floatingActionButtonTheme.copyWith(
        backgroundColor: colorScheme.tertiaryContainer,
        foregroundColor: colorScheme.onTertiaryContainer,
        shape: const CircleBorder(),
      ),

      // ElevatedButtonのスタイル
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          shape: const RoundedRectangleBorder(
            borderRadius: BorderRadius.all(Radius.circular(12)),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          backgroundColor: colorScheme.primary,
          foregroundColor: colorScheme.onPrimary,
        ),
      ),

      // TextFieldやTextFormFieldのスタイル
      inputDecorationTheme: baseTheme.inputDecorationTheme.copyWith(
        filled: true,
        fillColor: colorScheme.surfaceContainerHighest.withAlpha(127),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide.none,
        ),
      ),

      // Chip (タグなど) のスタイル
      chipTheme: baseTheme.chipTheme.copyWith(
        backgroundColor: colorScheme.secondaryContainer,
        labelStyle: TextStyle(
          color: colorScheme.onSecondaryContainer,
          fontWeight: FontWeight.w500,
        ),
        shape: const StadiumBorder(),
        side: BorderSide.none,
      ),
    );
  }

  // --- 3. 公開するThemeData ---
  // 上記のメソッドを使ってライト/ダークそれぞれのテーマを生成
  static final ThemeData lightTheme = _createTheme(_lightColorScheme);
  static final ThemeData darkTheme = _createTheme(_darkColorScheme);
}