/// アプリケーション全体で使用されるUIテキスト文字列を管理するクラス。
///
/// このクラスの目的は、マジックストリング（コード内に直接書き込まれた文字列）を排除し、
/// テキストの一元管理と、将来的な国際化（i18n）対応を容易にすることです。
///
/// 使用方法:
/// ```
/// Text(AppStrings.appTitle)
/// ```
class AppStrings {
  // このクラスはインスタンス化する必要がないため、プライベートコンストラクタを定義します。
  // これにより、誤って `AppStrings()` と書かれることを防ぎます。
  AppStrings._();

  // --- アプリ全体で使われる文字列 ---
  static const String appTitle = 'Vegetage';
  static const String searchHint = '野菜を検索...';
  static const String errorTitle = 'エラー';
  static const String errorMessage = '問題が発生しました。しばらくしてからもう一度お試しください。';
  static const String closeButton = '閉じる';

  // --- 野菜一覧画面 (VegetableListScreen) ---
  static const String vegetableListTitle = '伝統野菜一覧';
  static const String noVegetablesFound = '野菜データが見つかりません。';

  // --- 野菜詳細画面 (VegetableDetailScreen) ---
  // セクションタイトル
  static const String sectionTitleOneLiner = 'ひとこと';
  static const String sectionTitleDescription = 'どんな野菜？';
  static const String sectionTitlePracticalTips = '選び方・保存のコツ';
  static const String sectionTitleNutrition = '栄養について';
  static const String sectionTitleHonestAssessment = '正直なところ';
  static const String sectionTitleCulturalBackground = '文化・歴史';
  static const String sectionTitleSafetyNotes = 'ご利用上の注意';
  static const String sectionTitleRelationships = '関連する野菜';

  // プレースホルダーなど
  static const String imagePlaceholder = 'の画像'; // 例: "聖護院大根" + imagePlaceholder

}