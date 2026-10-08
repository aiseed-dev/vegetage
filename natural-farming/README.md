# natural-farming — 自然農法のページ(website からの移行)

aiseed.dev(リポジトリ `website`)にあった自然農法関係のページを、このリポジトリに移したもの。
元: `website` コミット 5a8a34d の時点。いまは **コピーしただけ** で、website 側にも同じものが残っている。

## 中身

```
natural-farming/
├── site/                         # website/html/ の一部を、同じ相対パスのまま
│   ├── natural-farming/            自然農法とは(日)   ← html/natural-farming/
│   ├── en/natural-farming/         同(英)
│   ├── light-farming/              光合成と土(日)     ← html/light-farming/
│   │   ├── full/  full-2/          Christine Jones 博士の論文の全訳(日のみ・博士の許可を得て翻訳)
│   ├── en/light-farming/           同(英)
│   ├── gallery/                    畑の記録(日のみ)
│   ├── about/  en/about/           サイト紹介(中身は自然農法の紹介が中心)
│   ├── phosphorus-and-farming/     連載「リン資源枯渇と自然農法」のビルド済み HTML(日)
│   ├── en/phosphorus-and-farming/  同(英)
│   ├── css/style.css  js/main.js   上のページが使う website のスタイルとスクリプト
│   └── images/IMG_*.jpg            上のページの写真 9 枚(IMG_3141・3285 は aiseed.dev の og:image でもあるので website にも残す)
└── articles/
    ├── phosphorus-and-farming.adoc        連載の原稿(序章〜第9章、日英)。website の pyasciidoc 系でビルドしていた
    └── assets/phosphorus-and-farming/     原稿の図
```

`site/` は相対パスを website と同じにしてあるので、そのまま開けば表示できる。
ただし次のものは website のサイト内を指したままになっている:

- ファビコン(`/images/favicon-32x32.png` など)
- ナビゲーションのリンク(`/blog/`、`/insights/`、`/about/` など)

## 決まったこと(2026-10-08)

- **形式**:`vegitage-data/web/build.py` の形式(Markdown+YAML)に書き直す。`site/` は書き直しの元にするための控え。
- **ブログと構造分析**:肥料・自然農法を扱ったブログ 004・013・044・045・006 と、構造分析 1-03・3-05 は website に残し、こちらのページからリンクを張る。
- **about**:こちらに移す。website 側は短い紹介に書き直す。
- **カタログエディタの設計書**:`docs/catalog-editor.md` に移した(元は website の `docs/plan/catalog-editor.md`)。

## まだ決まっていないこと

- **公開先と URL**:aiseed.page でよいか。aiseed.page ではまだハッカソン版の Flutter アプリを配信していて、切り替えは急がない。

## website 側の削除と転送の順番

website 側でページを消して 301 で転送するのは、新しい URL で実際にページが配信されてからにする。
先に転送を張るとリンク切れになる。新しい URL が決まったら、その一覧を website 側に渡す。
website 側はそれをもとに `_redirects`、トップページ、テンプレート、本文中のリンクを書き換える。

連載を書き直すときは、いまの日英の章の分け方と slug(`prologue`、`supply-constraint` …… `cuba-lessons` など)をそのまま使う。
website 側は、slug ごとに古い URL と新しい URL を対応づけて転送するため。
