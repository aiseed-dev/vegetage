# Vegetage - 生きた伝統野菜&料理辞典 🌱

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Data License: CC BY-SA 4.0](https://img.shields.io/badge/Data%20License-CC%20BY--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-sa/4.0/)

『Vegetage（ベジテージ）』へようこそ。
このプロジェクトは、AIの力を借りて、世界中に眠る伝統野菜や伝統料理の「物語」を再発見し、未来へ繋ぐためのオープンなデータベースを構築する試みです。

**「Vegetage」は、Heritage Vegetables（伝統野菜）からの造語です。**

---

## 📖 このプロジェクトが目指すもの

> **AIエージェントが、私たちの食卓を豊かにする**

1970年代以降、効率を重視する農業の中で、地域の食文化を支えてきた多くの伝統野菜が、静かに姿を消そうとしています。
私たちは、それらが持つ豊かな物語、栽培の知恵、そして未来の気候変動に適応する可能性を、「オープンな共有資産」として編纂し、現代の生産者と消費者に届けたいと考えています。

## 課題：声なき野菜たちと、届かない物語

*   **生産者の方々:** 素晴らしい伝統野菜を作っても、その価値を伝える手段がない。
*   **私たち消費者:** 直売所で珍しい野菜に出会っても、その背景や美味しい食べ方が分からず、手に取ることをためらってしまう。

## ✨ 私たちのソリューション

`Vegetage`は、この断絶を、テクノロジーとコミュニティの力で繋ぎ直します。

1.  **AIによる物語の発見:**
    `Gemini API`を駆使した独自の2段階パイプラインで、忘れられた野菜の文化的価値や栽培法を、世界中の文献から体系的に発掘します。

2.  **QRコードによる体験の提供:**
    生産者は、自分の野菜にQRコードを貼るだけ。消費者は、それをスキャンするだけで、その野菜の「手紙」とも言える物語に、その場で出会うことができます。

3.  **コミュニティによる辞典の育成:**
    この辞典の主役は、AIではなく「人」です。AIが作った下書きを元に、生産者自身の生の声、協力者の知見を加えて、データベースを共に育てていきます。

## 🚀 ハッカソンでの成果

このリポジトリは、「第3回 AI Agent Hackathon with Google Cloud」で開発したプロトタイプです。
ハッカソン期間中に、以下の目標を達成しました。

*   **AIデータパイプラインの構築:** 300種類以上の野菜品目の「ファーストビュー用データ」を、AIを用いて自動生成。
*   **Flutter Webアプリの開発:** 生成したデータを表示する、美しい辞典アプリを開発。
*   **インフラ構築:** Google Compute Engine (GCE) 上に、Nginxを用いたWebサーバーを構築し、アプリをデプロイ。

**▶ ライブデモはこちら:**
https://aiseed.page

**▶ Zennでの開発記:**
作成中

## 📁 ディレクトリ構成

```
frontend/vegetage/   Flutter アプリ(iOS / Android / Web)。アプリと野菜辞典が読む JSON は assets/data/
web/                 辞典サイト。イタリア図鑑の正本(italian/)とビルダー(build_all.py → web/site/)
research/            調査データ(deep_research・master_lists)とリサーチエージェント(src/)
natural-farming/     自然農法のページ(website から移行中。web/ の形式へ書き直す予定)
data_processing/     ハッカソン版のデータ生成パイプライン(プロンプトと生成データ)
docs/                設計・計画・手順書
```

## 🛠️ 技術スタック

*   **AI & データ処理:** Google Gemini API, Python
*   **フロントエンド:** Flutter Web, Dart, Riverpod
*   **インフラ:** Google Compute Engine (GCE), Nginx, Let's Encrypt

将来的には、`Elasticsearch`による高度な検索機能や、`PostgreSQL`を用いたユーザー投稿機能の実装を計画しています。

## 🤝 仲間を募集しています！

`Vegetage`は、まだ生まれたばかりの「種」です。
この種を、共に水やりし、育ててくれる仲間を、心から募集しています。

*   伝統野菜のデータや写真を提供してくださる農家の方、郷土料理研究家の方
*   AIでの辞書の作成やFlutterアプリの機能を一緒に開発してくれるエンジニアの方
*   美しいUI/UXを考えてくれるデザイナーの方

少しでもこの活動に興味を持ってくださった方は、ぜひ **Issues** や **Discussions** を覗いてみてください。
共に、新しい時代の畑を耕しましょう。

## 📜 ライセンス

*   **ソースコード:** [GNU General Public License v3.0](LICENSE.code)
*   **データ・コンテンツ:** [Creative Commons Attribution-ShareAlike 4.0 International](LICENSE.data)