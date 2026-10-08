# research — 伝統野菜の調査データとリサーチエージェント

伝統野菜・伝統料理の構造化データベースを、AIリサーチエージェントで自動構築するプロジェクト。
辞典の正本(`../web/italian/`)とビルダー(`../web/build.py`)はリポジトリ直下の `web/` にある。
(旧 `vegitage-data/`。2026-10 にリポジトリ直下の `web/`・`research/`・`docs/` へ分けた)

## 概要

イタリアと日本の伝統野菜（850品種）と伝統料理（1,300レシピ）の情報を、Claude Agent SDK と Gemini API を活用して収集・構造化します。

野菜と料理を双方向にリンクし、「この野菜でどんな料理が作れるか」「この料理にはどの品種が最適か」に答えられる実践的な知識基盤を提供します。

## 特徴

- **マルチAIリサーチ**: Claude（深堀り調査）+ Gemini（バッチ処理）のハイブリッド
- **多言語調査**: イタリア語・日本語・英語のソースを直接調査
- **構造化データ**: JSON形式で野菜と料理を相互リンク
- **自然農法対応**: 栽培情報に自然農法・有機栽培のコツを含む
- **文化的背景**: 祭事、歴史、食べ方の作法まで収録

## 対象データ

| 地域 | カテゴリ | 目標数 |
|------|---------|--------|
| イタリア | 伝統野菜 | 350品種 |
| イタリア | 伝統料理 | 500レシピ |
| 日本 | 伝統野菜 | 500品種 |
| 日本 | 伝統料理 | 800レシピ |

## プロジェクト構成

```
<リポジトリ直下>/
├── web/                          # 辞典サイト(→ web/README.md)
│   ├── italian/                  # ★正本（人間が修正・確定する原稿）
│   │   ├── <作物>.md              #   概要（YAMLフロントマター＋短い概要文）
│   │   ├── history/<作物>.md      #   歴史
│   │   ├── cultivation/<作物>.md  #   栽培
│   │   └── cuisine/<作物>.md      #   料理
│   ├── build.py                  # ★正本ビルダー（MD → web/site/ の HTML）
│   ├── static/                   # CSS・アイコン（gen_icons.py の出力先）
│   └── site/                     # ビルド出力（.gitignore）
├── research/                     # ここ
│   ├── data/
│   │   ├── deep_research/
│   │   │   ├── イタリア野菜/       # ① Gemini 調査報告書（一次資料）
│   │   │   └── italian/<作物>/     # ② ①をAIが要約した「たたき台」→ 人手で web/italian へ仕上げる
│   │   ├── master_lists/         # 調査対象の品目リスト・種子店一覧(items.csv は web/build.py も読む)
│   │   ├── vegetables/ , recipes/ # 構造化JSON DB（将来目標・現状サンプルのみ＝保留）
│   │   └── extracted_varieties*.csv # 品種抽出（検索用・保留）
│   ├── src/                      # Python パッケージ（research / DB / tools）
│   │   ├── agents/               #   リサーチエージェント（research_min ほか）＝一部保留
│   │   ├── schemas/ , validators/ #   構造化JSON DB のスキーマ/検証＝保留
│   │   └── tools/                #   gen_icons（アイコン生成）・extract_varieties*（品種抽出・保留）
│   ├── drafts/
│   └── pyproject.toml
└── docs/                         # 計画書(伝統野菜料理辞典_計画書v2/v3 など)
```

### 正本の流れ（イタリア野菜）

```
① research/data/deep_research/イタリア野菜/   Gemini 調査報告書（一次資料）
      │ AIが要約
② research/data/deep_research/italian/<作物>/  AI要約（たたき台）
      │ 人間がレビュー・修正
③ web/italian/                        ★正本（人間確定稿）
      │ web/build.py
④ web/site/italian/                   HTML（ビルド出力・.gitignore）
      │ cf-publish
   Cloudflare Pages(aiseed.page/italian/…)
```

### 概要フロントマター（各作物の `web/italian/<作物>.md` 冒頭）

```yaml
---
id: IT-VEG-ART-001
name_ja: アーティチョーク
name_it: Carciofo
name_en: Artichoke
aliases: [チョウセンアザミ]      # 別名・地方名・別表記
family: キク科                  # 科（植物学的事実・検索/参照）
family_latin: Asteraceae
botanical: Cynara cardunculus var. scolymus   # 種の学名
index_group: キク科             # 目次「科」タブのグループ名（family と別管理・自由命名）
type: [花菜類]                  # 複数可。概要先頭に表示・目次「type」タブ
item: アーティチョーク
certification: [DOP, IGP]
regions: [Lazio, Sardegna]
season: [春]
uses: [加熱, 保存]
hero_image: images/hero.jpg
---
```

目次（index）はビルド時に静的生成し、`index_group`（科）と `type` の2タブで切り替える。

## ビルド

```bash
# リポジトリ直下で。2カタログをまとめてビルド（出力: web/site/）
python3 web/build_all.py
```

生成された HTML（`web/site/`）は `.gitignore` 対象。正本ソースは `web/italian/` の
Markdown のみを管理する。公開は `web/site/` を Cloudflare Pages へ(→ `web/README.md`)。

> 旧 `scripts/build.py`（`data/deep_research` を読む経路）は退役・削除済み。`web/deploy.sh`（scp）
> も退役。構造化JSON DB（`src/`・`data/{vegetables,recipes}`）と品種抽出（`src/tools/`）は保留。

## 作物を1つ追加・更新する手順（運用）

```
1. たたき台を作る（AI・任意）
   cd research && ./.venv/bin/python -m src.agents.research_min "アーティチョーク" --it Carciofo --en Artichoke
   → research/data/deep_research/italian/アーティチョーク/ に 概要・歴史・栽培・料理（出典付き）

2. 人間が確定する ★ここが正本
   ② を読んで確認・修正し、web/italian/ に仕上げる:
     web/italian/アーティチョーク.md            概要（YAMLフロントマター＋短い概要文）
     web/italian/history/アーティチョーク.md     歴史
     web/italian/cultivation/アーティチョーク.md 栽培
     web/italian/cuisine/アーティチョーク.md     料理
   ・事実（DOP/IGP・学名・産地・統計）は出典と人手で必ず検証する
   ・index_group / type / certification / regions などフロントマターを整える

3. ビルドして確認
   python3 web/build_all.py                                # リポジトリ直下で
   python3 -m http.server --directory web/site 8001        # localhost で目視

4. 公開
   web/site/ を Cloudflare Pages へ（詳細は web/README.md）。
```

> AI は「たたき台（②）」を機械の速さで出す道具。**確定するのは人間（③ web/italian）**。
> 辞典には「現行システム」のような正解器が無いので、検証は出典＋人間が担う。

## データスキーマ

### 野菜エントリー (例: IT-VEG-TOM-001)

```json
{
  "id": "IT-VEG-TOM-001",
  "names": {
    "local": "Pomodoro San Marzano",
    "japanese": "サンマルツァーノトマト",
    "english": "San Marzano Tomato",
    "scientific": "Solanum lycopersicum 'San Marzano'"
  },
  "origin": { "country": "イタリア", "region": "...", "history": "..." },
  "characteristics": { "appearance": "...", "taste": "...", "nutrition": {} },
  "cultivation": { "sowing_period": "...", "natural_farming_tips": "..." },
  "related_recipes": ["IT-RCP-PIZ-001", "IT-RCP-PAS-001"],
  "sources": ["https://..."],
  "metadata": { "confidence_score": 0.92 }
}
```

### 料理エントリー (例: IT-RCP-PIZ-001)

```json
{
  "id": "IT-RCP-PIZ-001",
  "names": {
    "local": "Pizza Margherita",
    "japanese": "ピッツァ・マルゲリータ",
    "english": "Margherita Pizza"
  },
  "category": "主食・ピッツァ",
  "ingredients": [
    { "name": "トマトソース", "vegetable_id": "IT-VEG-TOM-001" }
  ],
  "traditional_method": "...",
  "related_vegetables": ["IT-VEG-TOM-001"],
  "sources": ["https://..."]
}
```

## 技術スタック

- **リサーチエンジン**: Claude Agent SDK + WebSearch
- **バッチ処理**: Gemini API (2.0 Flash / 1.5 Pro)
- **バックエンド**: FastAPI + Go（認証）
- **フロントエンド**: Flutter（自己完結型Widget）
- **データ形式**: JSON

## ライセンス

このプロジェクトはダブルライセンスで提供されます。

### コード部分

| ライセンス | 用途 |
|-----------|------|
| **AGPL-3.0** | オープンソース利用（デフォルト） |
| **商用ライセンス** | App Store配布など、AGPLが適用できない場合 |

- オープンソースとして利用する場合は AGPL-3.0 が適用されます
- App Store への配布など、AGPL の条件を満たせない場合は商用ライセンスが必要です
- 商用ライセンスについては [Issues](../../issues) でお問い合わせください

### データ部分 (`data/` ディレクトリ)

**CC BY-SA 4.0** (Creative Commons Attribution-ShareAlike 4.0 International)

- 自由に利用・改変・再配布できます
- クレジット表記が必要です
- 改変した場合は同じライセンスで公開してください

## AIseed との関係

このプロジェクトは [AIseed](https://github.com/aiseed) プラットフォームの知識基盤として開発されています。

- **Grow**: 栽培記録アプリ、観察ガイドに野菜データを活用
- **Learn**: 伝統野菜・料理に関する学習コンテンツを自動生成
- **BYOA**: ユーザー自身のClaude Pro/Geminiでカスタム調査可能

## コントリビューション

伝統野菜・伝統料理の情報追加を歓迎します！

### 参加方法

1. Fork してローカルにクローン
2. `data/vegetables/` または `data/recipes/` に JSON ファイルを追加
3. Pull Request を送信

### ID 命名規則

- 野菜: `{国コード}-VEG-{カテゴリ}-{番号}` (例: `JP-VEG-KYO-001`)
- 料理: `{国コード}-RCP-{カテゴリ}-{番号}` (例: `JP-RCP-KYT-001`)

| 国コード | 国 |
|----------|-----|
| IT | イタリア |
| JP | 日本 |

### 求む情報

- 各地域の在来種・固定種の情報
- 郷土料理と使用される伝統野菜の関係
- 自然農法・有機栽培での栽培ノウハウ
- 多言語での名称・出典

## 関連リンク

- [AIseed](https://github.com/aiseed) - 神経多様性を持つ方々のための体験学習プラットフォーム
- [Claude Agent SDK Cookbook](https://platform.claude.com/cookbook/claude-agent-sdk-00-the-one-liner-research-agent) - リサーチエージェントの技術解説

## 作者

Yasuhiro Niji ([@awoni](https://github.com/awoni))

---

*伝統野菜は地域の食文化と農業遺産を体現する貴重な資源です。このプロジェクトを通じて、その知識を次世代に伝えていきます。* 🌱
