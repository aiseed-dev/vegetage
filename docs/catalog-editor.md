# カタログエディタ — aiseed-builder の「商品」プラグイン設計

2026-07-28。vegitage(イタリア野菜図鑑)の編集を最初の利用者として、
aiseed-builder に「品目カタログ」の編集能力を足す。WordPress の語彙で言えば、
site-editor が「投稿」、これは「カスタムフィールド付きカスタム投稿タイプ=商品」。
スキーマ駆動にすることで、野菜図鑑も将来の EC 商品も同じエディタで扱える。

**同日追記: 帰属と公開先を変更。** データの正本は独立リポジトリ
`/home/dev/dev/vegitage`(aiseed-dev/vegitage)の `vegitage-data/` に帰属させ、
公開は aiseed.dev 配下(/vegitage/)ではなく **独自ドメイン aiseed.page** で行う。
website 側は vegitage-data/ と symlink を削除済み、旧 URL は
`/vegitage/* → https://aiseed.page/:splat` の301で引き継ぐ。

## 二つのカタログ(2026-07-28 決定)

伝統野菜辞典は **別物の2カタログ**として両方サイトに出す。統合しない。

| カタログ | データ | 形式 | 品目 | 生成 |
|---|---|---|---|---|
| **イタリア図鑑** | `vegitage-data/web/italian/` | Markdown+YAML | 69 | `web/build.py`(既存) |
| **野菜辞典** | `frontend/vegitage/assets/data/` | 構造化JSON | 332 | **未整備(新規に要る)** |

重複する30品目も二重管理でよい(粒度・観点が違う——図鑑はイタリアの食文化史、
辞典は栽培/栄養/気候変動適応/環境再生農業までの汎用データ)。

### カタログA: イタリア図鑑(Markdown・69)
下記「現状の確認」と設計本文(スキーマ・バンドル・状態・UI)はこのカタログの話。

### カタログB: 野菜辞典(JSON・332)
- データ源: `frontend/vegitage/assets/data/` に `vegetable_summary/<名>.json`(一覧・
  カード用、content.ja に15項目)+ `vegetable_detail/<名>.json`(詳細、15セクション:
  basic_info / classification / cultivation_characteristics / nutritional_functional /
  culinary_applications / climate_change_adaptation / natural_hybridization_potential /
  regenerative_agriculture / conservation_priority ほか)+ `_index.json`(別名 redirect)
- **公開手段が無い**: これまで Flutter アプリが JSON を直接読んで表示していた。
  アプリの Web 版は退役 → **JSON→静的HTML ビルダーを新規に作る**必要がある。
  summary が一覧、detail が詳細ページに対応する自然な写像
- データの置き場所: 現在は Flutter アプリ配下(`frontend/vegitage/assets/data/`)。
  アプリ(iOS/Android)がまだ読むので**ここが正本のまま**。Web ビルダーは
  このディレクトリを入力にする(コピーせず参照)。要検討: 将来アプリと Web が
  同じ JSON を共有し続けるか、`vegitage-data/` 側へ寄せるか
- スキーマ駆動エディタの対象にもなるが、JSON は入れ子が深いので schema.yaml は
  カタログA より複雑。**まず「読める形で公開」を先にやり、編集は後**(A で
  エディタの型ができてから B に広げる)
- URL 設計案: `aiseed.page/vegetables/<名>.html`(図鑑の `/italian/` と併存)

## 現状の確認(カタログA・2026-07-28 時点)

- 正本: `vegitage/vegitage-data/web/italian/` に 69 品目。1品目 =
  `<作物>.md`(YAML フロントマター+概要文)+ `history|cultivation|cuisine/<作物>.md`
  (サブガイド計135ファイル、全651枠中は歯抜けあり=無いタブは出ない仕様)
- フロントマター: `id`(master_lists と突合・暫定)、`name_ja/it/en`、`aliases`、
  `family/family_latin/botanical`、`index_group`(目次「科」タブ)、`type`(複数)、
  `certification`、`regions`、`season`、`uses`、`hero_image`。
  **行内コメントが情報を持っている**(例: `id: … # master_lists と要突合せ（暫定）`)
- ビルド: `vegitage-data/web/build.py`(markdown+PyYAML、全ビルドのみ)。
  出力 `web/site/` をそのまま aiseed.page(Cloudflare Pages)へアップロードする。
  URL は `aiseed.page/italian/<作物>.html`(website 時代の /vegitage/ 接頭辞が
  取れるだけで、それ以下の構造は不変)
- たたき台: `data/deep_research/italian/<作物>/` に 71 品目分。
  正本 69 との差=未取込の「入荷待ち」
- 状態管理: 無し(draft の概念が build.py に無い)

## 設計原則(aiseed-builder の既存原則を踏襲)

1. **パーサとスキーマの正はサイト(データ)側に一つだけ。** builder は読むだけ。
   → スキーマはカテゴリフォルダに置く: `vegitage-data/web/italian/schema.yaml`
2. **壊れる編集は拒否。** 保存時に必ず再パース+スキーマ検証し、通らなければ戻す
   (site-editor と同じ)。
3. **プラグインは登録制。** `plugins/catalog/` を足し、site.json の
   `builder.plugins` に `"catalog"` を追加するだけ。main.py に分岐は書かない。

## 1. スキーマ宣言 — schema.yaml

カテゴリ(=カタログ)ごとに1ファイル。フィールド定義・セクション構成・状態の
規約をここに集約する。builder はこれを読んでフォームを組み立てる。

```yaml
label: イタリア野菜図鑑
item_label: 品種            # UI の「新規追加」等の呼称
url_base: /italian            # aiseed.page 配下

fields:
  - {key: id,           label: 品目ID,  type: id}       # 読み取り専用表示
  - {key: name_ja,      label: 和名,    type: text, required: true}
  - {key: name_it,      label: 伊名,    type: text}
  - {key: name_en,      label: 英名,    type: text}
  - {key: aliases,      label: 別名,    type: tags}      # 自由入力の複数値
  - {key: family,       label: 科,      type: text}
  - {key: family_latin, label: 科(学名), type: text}
  - {key: botanical,    label: 学名,    type: text}
  - {key: index_group,  label: 目次グループ, type: select, options: existing}
  - {key: type,         label: 種類,    type: tags, options: existing}
  - {key: certification, label: 認証,   type: tags,
     options: [DOP, IGP, PAT, Slow Food], open: false}   # 閉じた語彙のみ検証で弾く
  - {key: regions,      label: 主な産地, type: tags, options: existing}
  - {key: season,       label: 旬,      type: tags,
     options: [春, 夏, 秋, 冬, 通年], open: false}
  - {key: uses,         label: 用途,    type: tags, options: existing}
  - {key: hero_image,   label: 画像,    type: image}

sections:                    # 本文タブ。dir: null は概要ファイル自身
  - {dir: null,        label: 概要}
  - {dir: history,     label: 歴史}
  - {dir: cultivation, label: 栽培}
  - {dir: cuisine,     label: 料理}

status:
  draft_key: draft           # フロントマターの draft: true で下書き
```

フィールド type は5種で足りる:

| type | UI | 検証 |
|---|---|---|
| `text` | 1行テキスト | required のみ |
| `tags` | チップ入力(複数値) | `open: false` なら options 外を拒否 |
| `select` | ドロップダウン(1値) | 同上 |
| `image` | ファイル選択+プレビュー | 参照先の存在 |
| `id` | 読み取り専用表示 | 触らない |

`options: existing` は「既存データから語彙を収集してサジェスト(開いた語彙)」。
閉じた語彙(`open: false`)だけが検証で弾かれる。**表記ゆれは閉じずに直す**——
一覧のファセットに「Lazio(12) / ラツィオ(1)」と出れば、ゆれは目で見える。

EC 商品への布石: `price` や `stock` が必要になったら type を足すのではなく
`text`+`format: number` を足す程度で済む。スキーマ形式自体は汎用。

## 2. 編集単位 — 品目バンドル

1品目 = 概要+サブガイド3+画像。エディタは品目単位で開く。

- **ファイル名(=URL)は日本語のまま。** 既公開 URL の維持が最優先。
  ファイル名がバンドルの結合キーなので、改名はエディタが4ファイル+画像を
  一括で改名する(手作業での不整合を防ぐのもエディタの仕事)。
- 概要ファイルのフロントマター書き戻しは **ruamel.yaml のラウンドトリップ**で
  行内コメントを保持する(`id: … # 要突合せ` のような注記が消えると困る)。
  依存は aiseed-builder 側にのみ追加。データ側 build.py は PyYAML のまま。
- サブガイドの追加: タブを開いて書き始めたらファイルが生まれる。空のまま
  保存したら作らない(歯抜けは仕様——ナビに出ないだけ)。

## 3. 状態管理 — 商品と同じ3状態

| 状態 | 定義 | 一覧での見え方 |
|---|---|---|
| たたき台 | `deep_research/italian/` にあり正本に無い | 灰色・「起こす」ボタン |
| 下書き | 正本にあり `draft: true` | 黄色バッジ・サイトに出ない |
| 公開 | 正本にあり draft 無し | 通常表示 |

- 「起こす」= たたき台のテキストを初期値に正本の雛形を生成(`draft: true` 付き)。
  deep_research → 人手仕上げ → 公開、という既存ワークフローをそのまま UI 化。
- **build.py への変更は draft スキップだけ**(数行)。スキーマ検証はエディタ側の
  仕事とし、ビルドは今までどおり寛容に通す(手書き修正を妨げない)。

## 4. UI — WooCommerce の商品画面に対応

```
一覧画面(カタログごと)
  検索(名前・別名) / 絞り込み(科・種類・旬・産地・状態) / 新規追加
  行: 名前 | 学名 | 科 | type | 状態 | セクション充足(○○○-)
編集画面
  左カラム: スキーマ駆動フォーム(フロントマター)
  右カラム: 公開ボックス(状態・更新・プレビュー・削除)+ 画像ボックス
  下: セクションタブ(概要|歴史|栽培|料理)= Markdown エディタ
```

サイドバーには site.json の `catalogs` 配列の順でカタログ名が並ぶ
(シリーズ一覧と同格)。「変更を記録(git)」「サイトを公開」は既存機能を共用。

## 5. vegitage を aiseed-builder の「サイト」として開く

website の site.json に相乗りさせるのではなく、**vegitage リポジトリ自身に
site.json を置き**、aiseed-builder でサイトとして開く(記事サイトと対等):

```json
{
  "site_name": "Vegitage",
  "builder": {
    "cf_project": "vegitage",
    "plugins": ["catalog"],
    "catalogs": [
      {"schema": "vegitage-data/web/italian/schema.yaml",
       "build": "vegitage-data/web/build.py",
       "output": "vegitage-data/web/site",
       "preview_path": "/italian/"}
    ]
  }
}
```

必要な本体側の変更: `store.init_site` は現在 `tools/build/series.py` と
`articles/` を必須にしている。**catalogs だけのサイトも開ける**ように緩める
(シリーズ機能はサイドバーに出ないだけ)。プレビューは builder が `output` を
簡易 HTTP で配信する。

公開は**済**: `store.deploy` を
[cf-publish](https://github.com/aiseed-dev/cf-publish)(自作PyPIパッケージ、
aiseed-builder の依存)に載せ替えた。サイト側に `tools/cloudflare_pages_deploy.py`
が無くても公開できるようになったので、vegitage も `publish_dir` を
`vegitage-data/web/site` に設定すれば公開対象になる(2026-07-28 時点で
932ファイルの dry-run 確認済み)。ドメイン aiseed.page の割当は完了済み、
Flutterアプリからの切り替えは保留中。

## 6. 実装の段取り

0. **aiseed.page の公開初期設定**(済ませてから編集機能へ): build.py に
   ルート index(/ → /italian/ への案内)を追加、Cloudflare Pages
   プロジェクト作成+ドメイン割当、初回アップロード。website 側の
   301(`/vegitage/*`)が生きているかの確認
1. **vegitage 側の受け入れ準備**(半日): schema.yaml を書く。build.py に
   draft スキップ。既存 69 品目をスキーマに通して表記ゆれの棚卸し
   (閉じた語彙は実データから確定させる)
2. **catalog プラグイン**(2〜3日): `plugins/catalog/`(store には触らず
   `catalog.py` を新設——記事の store.py と対になるデータ層)。
   一覧+編集+保存+ビルド。ruamel.yaml 追加
3. **取込フロー**(1日): たたき台一覧と「起こす」
4. **2カタログ目で汎用性を証明**: 日本野菜(build.py の CATEGORIES を
   設定駆動化して `web/japanese/` を追加)。ここまで来れば「EC の商品」も
   スキーマ1枚の距離

### カタログB(野菜辞典 JSON・332)の段取り — Aと独立に進行可

B1. **JSON→静的HTMLビルダー**(新規): `assets/data/{vegetable_summary,
    vegetable_detail}` を入力に、一覧(summaryのカード)+詳細(detailの
    15セクション)を生成。`_index.json` の redirect も反映。まず「読める形で
    公開」がゴール。図鑑の build.py とはテンプレートを共用できるか要検討
B2. **公開**: カタログA と同じ Cloudflare Pages に `/vegetables/` として相乗り
B3. **編集(後回し)**: JSON はネストが深い。A のエディタの型が固まってから、
    detail の主要セクションだけを対象にスキーマを起こす

## 決めたこと(推奨)と根拠

- スキーマの置き場所はデータ側(builder は汎用のまま) — 原則1
- ファイル名・URL は日本語維持 — 既公開 URL、品目の自然キー
- コメント保持に ruamel.yaml — フロントマターのコメントが台帳情報を持つ
- 検証はエディタで厳しく、ビルドは寛容 — 手書きの逃げ道を塞がない
- 閉じた語彙は certification と season だけから始める — ゆれの実態を
  ファセットで可視化してから閉じる
