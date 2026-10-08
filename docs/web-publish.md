# Vegetage Web版 公開マニュアル (Cloudflare Pages)

設計の背景・決定事項は [`../DESIGN.md`](../DESIGN.md) を参照。
これはコマンドだけをまとめた実行手順。

旧 GCE + Nginx の手順([`deployment.md`](deployment.md))は、
ドメイン切替(手順4)完了までの間の後方互換として残してある。
切替後は不要になる。

## 前提

- Flutter SDK: `~/development/flutter`
- cf-publish: `~/.local/bin/cf-publish`(`pip install --user cf-publish` 済み)
- Cloudflare認証情報: `~/.config/cloudflare/pages.env` に設定済み

いずれも初回セットアップ済みなら、以下は `frontend/vegetage` ディレクトリで
実行するだけでよい。Zed を使っている場合は同じコマンドがタスクメニュー
(`.zed/tasks.json`)からも実行できる。

## 1. ビルド

```bash
cd frontend/vegetage
flutter build web --release --dart-define=FLUTTER_WEB_CANVASKIT_URL=canvaskit/
```

成果物は `build/web`(このディレクトリ配下は git 管理外)。

**野菜データを追加・更新した場合**は、ビルド前にフォントを再生成する
(収録外の文字があると Google Fonts への外部フェッチが復活するため):

```bash
[ -d .venv-fonts ] || (python3 -m venv .venv-fonts && .venv-fonts/bin/pip install fonttools)
.venv-fonts/bin/python tool/subset_fonts.py
```

## 2. デプロイ前確認(dry-run)

```bash
cf-publish build/web --project vegetage --dry-run
```

ファイル数・サイズが Pages の制限内であることと、送信対象を確認する。
実際のアップロードは行われない。

## 3. デプロイ

```bash
cf-publish build/web --project vegetage
```

初回はプロジェクト `vegetage` が自動作成される。
完了すると `https://vegetage.pages.dev` で確認できる
(2回目以降は `https://<デプロイID>.vegetage.pages.dev` のプレビューURLも出る)。

表示確認したいポイント:

- 野菜一覧・検索・詳細画面が表示される
- 詳細画面の QR コードが `https://aiseed.page/#/vegetables/...` を指している
  (ドメイン切替前でもこれは元々の仕様通り)
- ブラウザの開発者ツール Network タブで、外部ドメインへのリクエストが
  無いこと(gstatic.com 等が出ていたら [`../DESIGN.md`](../DESIGN.md) の
  「外部フェッチの扱い」を参照)

## 4. ドメイン切替(aiseed.page へ切替。GCE 停止前に実施)

Cloudflare ダッシュボードで:

1. Workers & Pages → `vegetage` プロジェクトを開く
2. Custom domains → `aiseed.page` を追加
   (DNS は既に Cloudflare 管理下のためワンクリックで反映)
3. 反映を確認したら GCE インスタンスを停止してよい

`aiseed.page/images/*` は 404 のままだが、これは GCE 時代から未配置で
変わらない(写真の R2 移行は別タスク)。

## トラブルシューティング

- **`cf-publish` が認証エラーを出す**: `~/.config/cloudflare/pages.env` に
  `CLOUDFLARE_API_TOKEN` と `CLOUDFLARE_ACCOUNT_ID` があるか確認
  (Pages編集権限のトークンが必要)。
- **ビルド後もフォントが外部から取得される**: `flutter build web` の
  `--dart-define` を付け忘れていないか、`pubspec.yaml` の fonts 定義と
  `assets/fonts/` の中身が一致しているか確認。
- **文字化け・表示崩れ**: 新しく追加した文字がフォントに未収録の可能性。
  `tool/subset_fonts.py` を再実行すると不足文字を警告として表示する。
