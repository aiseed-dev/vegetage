# Vegetage Web — 操作ガイド

## 全部まとめてビルド(aiseed.page の公開物)

```bash
python3 web/build_all.py      # リポジトリ直下で → web/site/
python3 -m http.server 8099 --directory web/site   # 確認
```

| ビルダー | 正本 | 出力 |
|---|---|---|
| `build.py` | `web/italian/`(イタリア図鑑) | `site/index.html`, `site/italian/` |
| `build_dict.py` | `frontend/vegetage/assets/data/`(野菜辞典 JSON) | `site/vegetables/` |
| `build_pages.py` | `web/pages/`(読みもの) | `site/{natural-farming,light-farming,gallery,about,phosphorus-and-farming,en/…,css,images}/` |

各ビルダーは自分の出力だけを消す。`web/site/` を丸ごと消さないこと。

## 読みもの(web/pages/)

自然農法・Light Farming・畑の記録・私たちのアプローチ・連載「リン資源枯渇と自然農法」。
aiseed.dev から移したもので、**URL は aiseed.dev 時代と同じパス**にしてある
(website 側の 301 を `/<パス>/* → https://aiseed.page/<パス>/:splat` で済ませるため)。

- `web/pages/<パス>.md` → `/<パス>/`、`web/pages/<パス>/index.md` → `/<パス>/`
- 英語版は `web/pages/en/` に同じパスで置く。日英が揃っていれば言語切替リンクと hreflang が付く
- フロントマター: `title` `subtitle` `label` `description` `image`(`/images/…`、ヒーローと og:image)
- 連載: `phosphorus-and-farming/index.md` の `chapters:` が章の順番。章の slug は変えない
  (各章は `toc_title` `summary` `date` を持つ)
- 写真は `web/pages/images/`
- 見た目は `static/style.css` + `static/pages.css`
- 文章のライセンスは CC BY 4.0(辞典データは CC BY-SA 4.0)

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
