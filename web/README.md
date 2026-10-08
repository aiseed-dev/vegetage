# Vegetage Web — 操作ガイド

## ディレクトリ構成

```
web/
  build.py          ← サイトビルダー（MD → HTML）
  deploy.sh         ← scp デプロイスクリプト
  static/
    style.css       ← スタイルシート
  italian/           ← イタリア野菜 MD ソース
    cultivation/     ← 栽培ガイド MD（Gemini生成）
  site/              ← ビルド出力（HTML）
    italian/
scripts/
  gen_cultivation.py ← 栽培ガイド生成（Gemini API）
```

## サイトビルド

```bash
python web/build.py
```

- `web/<category>/*.md` → `web/site/<category>/*.html` を生成
- カテゴリは `build.py` 内の `CATEGORIES` dict で管理
- 2カラムレイアウト（本文 + サイドバー目次）
- 目次は h2/h3 から自動生成

### カテゴリの追加

`build.py` の `CATEGORIES` に追加:

```python
CATEGORIES = {
    "italian": { ... },
    "east_asian": {
        "title": "東アジア野菜図鑑",
        "subtitle": "...",
        "description": "...",
        "nav_label": "東アジア野菜一覧",
        "footer": "東アジア伝統野菜データベース",
    },
}
```

対応する `web/east_asian/` ディレクトリに MD を配置してビルド。

## 栽培ガイド生成（Gemini API）

事前準備: `.env` に API キーを設定

```
GOOGLE_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-3-pro-preview   # 省略時のデフォルト
```

```bash
# 1品目
python scripts/gen_cultivation.py アスパラガス

# 複数品目
python scripts/gen_cultivation.py アスパラガス トマト ナス

# 全品目
python scripts/gen_cultivation.py --all
```

- ソース: `web/italian/*.md` + `data/master_lists/italian_vegetables.csv`
- 出力: `web/italian/cultivation/野菜名.md`
- 既存ファイルはスキップ（再生成は手動削除後に実行）
- 品種データ（DOP/IGP等）を自動でプロンプトに含める

## デプロイ

事前準備: `.env` にデプロイ先を設定

```
DEPLOY_HOST=aiseed.dev
DEPLOY_USER=youruser
DEPLOY_PATH=/var/www/aiseed.dev/vegitage
DEPLOY_PORT=22
```

```bash
# ビルド + デプロイ
./web/deploy.sh

# ビルドのみ
./web/deploy.sh --build-only

# デプロイのみ（既存の site/ を送信）
./web/deploy.sh --deploy-only
```

rsync が使える場合は rsync、なければ scp でデプロイ。

## データファイル

| ファイル | 内容 |
|---|---|
| `data/master_lists/items.csv` | 野菜品目マスタ（49品目） |
| `data/master_lists/italian_vegetables.csv` | イタリア認定品種（239品種） |
| `web/italian/*.md` | 野菜解説（Web用、です/ます調） |
| `web/italian/cultivation/*.md` | 栽培ガイド（Gemini生成） |
