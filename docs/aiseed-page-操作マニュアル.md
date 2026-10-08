# aiseed.page 操作マニュアル

aiseed.page(Vegetage の公開サイト)を更新・確認・公開するための手順。
コマンドはすべて**リポジトリ直下**で実行する。

- 作ったもの・決めたことの経緯: [`../natural-farming/README.md`](../natural-farming/README.md)
- ビルダーの細かい仕様: [`../web/README.md`](../web/README.md)

---

## 1. サイトの構成

aiseed.page は `web/site/` をそのまま配信する静的サイト。`web/site/` はビルドで作るもので、git では管理しない。

| URL | 中身 | 正本(ここを直す) | ビルダー |
|---|---|---|---|
| `/` | トップ(入口) | `web/build.py` の中 | `web/build.py` |
| `/vegetables/` | 世界の伝統野菜辞典(332種) | `frontend/vegetage/assets/data/` | `web/build_dict.py` |
| `/italian/` | イタリア野菜図鑑(69種) | `web/italian/` | `web/build.py` |
| `/natural-farming/` `/light-farming/`(`full/` `full-2/`) `/gallery/` `/about/` | 自然農法の読みもの | `web/pages/` | `web/build_pages.py` |
| `/phosphorus-and-farming/` と 10 章 | 連載「リン資源枯渇と自然農法」 | `web/pages/phosphorus-and-farming/` | `web/build_pages.py` |
| `/en/…` | 上の読みものの英語版 | `web/pages/en/` | `web/build_pages.py` |
| `/images/IMG_*.jpg` | 読みものの写真 | `web/pages/images/` | `web/build_pages.py` |

Cloudflare Pages のプロジェクト名は **`vegetage`**。

---

## 2. いつもの流れ

```bash
python3 web/build_all.py                            # 1. ビルド(3つのビルダーをまとめて流す)
python3 web/check_site.py                           # 2. リンク切れチェック
python3 -m http.server 8099 --directory web/site    # 3. http://localhost:8099 で目視
cf-publish web/site --project vegetage --dry-run    # 4. 送るものを確認
cf-publish web/site --project vegetage              # 5. 公開
```

- 5 の公開は、外部に出す操作なので**人が実行する**(Claude に頼むときは、その都度「公開して」と伝える)。
- git の push も、人が中身を確認してから行う。
- 公開後、`https://aiseed.page/` と直したページを開いて確認する。

### 公開前の目視チェック

- トップの4つの入口(野菜辞典・イタリア図鑑・自然農法・連載)が開く
- 直したページが表示され、写真が出る
- スマホ幅でも横にはみ出さない
- 英語版があるページでは、右上の English / 日本語 で切り替わる

---

## 3. 中身を直す

### 読みもの(自然農法・Light Farming・畑の記録・私たちのアプローチ)

`web/pages/<パス>.md` を直す。先頭の `---` で囲まれた部分がフロントマター。

```yaml
---
lang: ja
title: 自然農法とは                # ページの見出し・<title>
subtitle: 福岡正信の哲学と……        # 見出しの下の一文
label: About Natural Farming       # 見出しの上の小さな英字(なくてもよい)
description: ……                    # 検索結果・SNS に出る説明
image: /images/IMG_3141.jpg        # 見出しの背景写真・SNS の画像
---
```

- 本文は普通の Markdown。写真は `![説明](/images/IMG_xxxx.jpg)`。
- 見出し(`##`)が3つ以上あると、右側に目次が付く。
- 畑の記録の写真の並び(`<div class="gallery-grid">…</div>`)は HTML のまま書く。
- 英語版は `web/pages/en/` の同じ名前のファイル。片方だけ直したら、もう片方も直すか確認する。

### 新しいページを足す

`web/pages/<新しいパス>.md` を作るだけで `/<新しいパス>/` ができる。
英語版も作るなら `web/pages/en/<新しいパス>.md`。日英が揃うと切替リンクが自動で付く。
ヘッダーのメニューに出したいときは `web/build_pages.py` の `NAV` に足す。

### 連載の章

- 章の本文: `web/pages/phosphorus-and-farming/<slug>.md`(英語は `en/` の下)
- 章の順番: `web/pages/phosphorus-and-farming/index.md` の `chapters:`
- 目次に出る名前と説明: 各章のフロントマターの `toc_title` と `summary`
- **既存の章の slug(ファイル名)は変えない。** aiseed.dev からの転送が slug をそのまま使っている。

### 写真を足す

1. `web/pages/images/` に置く(長辺 1600px 程度に縮めてから。1 枚 25MB が上限)
2. 本文やフロントマターから `/images/ファイル名` で参照する

### イタリア図鑑

`web/italian/` を直す。手順は [`../research/README.md`](../research/README.md) の「作物を1つ追加・更新する手順」。

### 野菜辞典

`frontend/vegetage/assets/data/` の JSON を直す。アプリ(iOS/Android)も同じ JSON を読むので、アプリへの影響も確認する。

---

## 4. 初めて切り替えるとき(1回だけ)

aiseed.page は、まだ古い Cloudflare Pages のプロジェクト **`vegitage`**(ハッカソン版の Flutter アプリ)を配信している。
新しいプロジェクト `vegetage` へ、次の順で切り替える。

1. 2 章の 1〜5 を行う。初回の `cf-publish` でプロジェクト `vegetage` が作られる
2. `https://vegetage.pages.dev/` で、トップ・`/natural-farming/`・`/phosphorus-and-farming/`・`/vegetables/` を確認する
3. Cloudflare ダッシュボード → Workers & Pages → **`vegitage`** → Custom domains → `aiseed.page` → Remove domain
4. Workers & Pages → **`vegetage`** → Custom domains → Set up a custom domain → `aiseed.page`
   (DNS は同じアカウントにあるので自動で設定される)
5. `https://aiseed.page/` が新しいトップになったことを確認する。
   古い QR コードの URL も試す: `https://aiseed.page/#/vegetables/カーボロネロ` → 辞典のカーボロネロのページへ移る
6. website 側(aiseed.dev)に、切り替えが済んだことを知らせる → 7 章

3 と 4 の間の数分は、aiseed.page が表示されない。

### 元に戻すとき

4 で付けたドメインを `vegetage` から外し、`vegitage` に付け直す。
古いプロジェクトは、新しいサイトが落ち着くまで消さない(ハッカソン版は `https://vegitage.pages.dev/` で見られる)。

### 古いプロジェクトの後片付け(落ち着いてから)

Workers & Pages → `vegitage` → Settings → Delete project。
Cloudflare Pages はプロジェクト名を変えられないので、「改名」ではなく「新しく作って移す」形になっている。

---

## 5. 古いアプリの URL

ハッカソン版アプリの QR コードは `https://aiseed.page/#/vegetables/<id>` を指して印刷済み。
`#` から後ろはサーバーに届かないので `_redirects` では扱えない。
トップページ(`web/build.py` の `build_root_index`)の JavaScript で振り替えている。

| 古い URL | 移る先 |
|---|---|
| `/#/vegetables` | `/vegetables/` |
| `/#/vegetables/<名前>` | `/vegetables/<名前>.html` |
| `/#/vegetables/<別名>`(Goma など) | 辞典の転送ページ経由で正しい品目へ |

トップページを書き換えるときは、この JavaScript を消さないこと。

---

## 6. 注意

- **`web/site/` を丸ごと消さない。** 各ビルダーは自分の出力だけを消して作り直す。全部作り直したいときは `build_all.py` を流す。
- **Flutter の Web 版は、もう aiseed.page には出さない。** `cf-publish build/web --project vegetage` を流すと、このサイトが Flutter アプリで上書きされる。[`web-publish.md`](web-publish.md) は旧手順。
- **ライセンス**: 読みものの文章は CC BY 4.0、辞典データは CC BY-SA 4.0。各ページのフッターに出ている。
- **個人情報**: 協力者の名前や、その人の事業の予定をリポジトリに書かない。
- **Light Farming の全訳**(`/light-farming/full/`、`/full-2/`)は、Christine Jones 博士の許可を得た翻訳。冒頭の「翻訳について」を消さない。

---

## 7. aiseed.dev(website)との関係

自然農法のページは aiseed.dev から移してきたもので、URL は**パスがそのまま**(ドメインだけ変わる)。

| aiseed.dev | aiseed.page |
|---|---|
| `/natural-farming/` | `/natural-farming/` |
| `/light-farming/`、`/light-farming/full/`、`/full-2/` | 同じ |
| `/gallery/`、`/about/` | 同じ |
| `/phosphorus-and-farming/<slug>/` | 同じ |
| `/en/…` | 同じ |

- 切り替え(4 章)が済んで配信を確認してから、website 側で旧ページの削除と 301 を行う。**順番を逆にしない**(先に 301 を張るとリンク切れになる)。
- website 側の作業: `_redirects`(フォルダごとの splat 転送)、共通メニューのリンク、sitemap、about の書き直し。
- 肥料・自然農法のブログ(004・013・044・045・006)と構造分析(1-03・3-05)は aiseed.dev に残る。こちらのページからは `https://aiseed.dev/…` でリンクしている。

---

## 8. 困ったとき

| 症状 | 確認すること |
|---|---|
| `cf-publish` が認証エラー | `~/.config/cloudflare/pages.env` に `CLOUDFLARE_API_TOKEN` と `CLOUDFLARE_ACCOUNT_ID` があるか。トークンは「Cloudflare Pages: 編集」権限 |
| `cf-publish` が見つからない | `pip install --user cf-publish`(または `/home/dev/dev/cf-publish` から `pip install -e .`) |
| 直したのに反映されない | `build_all.py` を流したか。ブラウザのキャッシュ(再読み込み)。公開まで済んでいるか |
| `check_site.py` がリンク切れを出す | 表示された URL の参照元ページを開き、リンク先のパスを直す。移していないページは `https://aiseed.dev/…` で書く |
| 写真が出ない | `web/pages/images/` にあるか。参照が `/images/…`(先頭の `/` あり)か |
| ビルドが「章が見つかりません」で止まる | `chapters:` にある slug と、章のファイル名が一致しているか |
