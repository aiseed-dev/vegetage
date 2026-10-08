#!/usr/bin/env python3
"""
Vegetage — 野菜辞典 Web サイトビルダー

正本ソース: web/<category>/ （人間が修正・確定する原稿）
  web/<category>/<作物>.md            → 概要（YAMLフロントマター + 短い概要文）= トップ
  web/<category>/history/<作物>.md     → 歴史
  web/<category>/cultivation/<作物>.md → 栽培
  web/<category>/cuisine/<作物>.md     → 料理
  → web/site/<category>/ に静的 HTML を生成

概要ファイルは先頭に YAML フロントマター（分類・別名・学名・科・認証・産地など）を
持つ。目次（index）は frontmatter を読み、index_group（科）と type の2タブで表示。

旧スタイル（フロントマター無しのフラット .md）も後方互換でビルドできる。

Usage: python3 web/build.py   (リポジトリ直下で)
"""

import csv
import re
import shutil
from pathlib import Path

import markdown
import yaml
from markdown.extensions.tables import TableExtension
from markdown.extensions.toc import TocExtension

# ── Paths ──────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent   # リポジトリ直下
WEB_DIR = ROOT / "web"
STATIC_DIR = WEB_DIR / "static"
DIST_DIR = WEB_DIR / "site"
ITEMS_CSV = ROOT / "research" / "data" / "master_lists" / "items.csv"

# ── Categories ────────────────────────────────────────
CATEGORIES = {
    "italian": {
        "title": "イタリア野菜図鑑",
        "subtitle": "Le Verdure Italiane — 地中海の恵みと食文化の物語",
        "description": "イタリア各地の風土と歴史が育んだ伝統野菜を紹介します。",
        "nav_label": "イタリア野菜一覧",
        "footer": "イタリア伝統野菜・料理データベース",
    },
}

# ── Markdown converter ─────────────────────────────────
md = markdown.Markdown(
    extensions=[
        TableExtension(),
        TocExtension(toc_depth="2-3", slugify=lambda value, separator: re.sub(r'\s+', separator, value.strip().lower())),
        "markdown.extensions.fenced_code",
        "markdown.extensions.nl2br",
    ],
    output_format="html",
)


# ── Items master list ──────────────────────────────────
def load_items_csv() -> dict:
    """items.csv を読み込み、name_ja → row の dict を返す。"""
    items = {}
    if ITEMS_CSV.exists():
        with open(ITEMS_CSV, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                items[row["name_ja"]] = row
    return items


# ── Frontmatter ────────────────────────────────────────
def parse_frontmatter(md_text: str) -> tuple[dict | None, str]:
    """先頭の YAML フロントマター（--- ... ---）を取り出す。

    返り値: (frontmatter dict または None, フロントマターを除いた本文)
    """
    if md_text.lstrip().startswith("---"):
        text = md_text.lstrip()
        parts = text.split("\n---", 1)
        # 先頭行 "---" の次から閉じ "---" まで
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
        if m:
            try:
                data = yaml.safe_load(m.group(1)) or {}
            except yaml.YAMLError:
                return None, md_text
            if isinstance(data, dict):
                return data, m.group(2)
    return None, md_text


def _as_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [s.strip() for s in str(value).split(",") if s.strip()]


# ── Metadata extraction ────────────────────────────────
def extract_metadata(md_text: str) -> dict:
    """タイトル・学名・サブタイトルと、（あれば）フロントマターを抽出する。

    新スタイル: 先頭の YAML フロントマター + 本文（H1・キャッチ・概要文）。
    旧スタイル: フロントマター無し。従来どおり本文先頭から推定。
    """
    fm, body = parse_frontmatter(md_text)

    # 本文先頭の "# タイトル" と "*学名* — キャッチ" 行を拾う（両スタイル共通）
    title = ""
    subtitle_line = ""
    for line in body.strip().split("\n"):
        stripped = line.strip()
        if stripped.startswith("# ") and not title:
            title = stripped[2:].strip()
        elif stripped and not stripped.startswith("#") and stripped != "---" and title and not subtitle_line:
            subtitle_line = stripped
            break

    latin = ""
    subtitle = ""
    if subtitle_line:
        m = re.search(r"\*([^*]+)\*", subtitle_line)
        if m:
            latin = m.group(1)
        m2 = re.search(r"—\s*(.+)", subtitle_line)
        if m2:
            subtitle = m2.group(1).strip()

    # フロントマターがあれば優先・補完
    if fm:
        title = fm.get("name_ja") or title
        if fm.get("botanical"):
            latin = str(fm["botanical"])
        if not subtitle:
            subtitle = "／".join(_as_list(fm.get("type"))) or str(fm.get("family", ""))

    short_name = title.replace("イタリアの", "")

    return {
        "title": title,
        "short_name": short_name,
        "latin": latin,
        "subtitle": subtitle,
        "subtitle_line": subtitle_line,
        "frontmatter": fm,
        "body": body,
        "index_group": (fm.get("index_group") or fm.get("family") or "") if fm else "",
        "types": _as_list(fm.get("type")) if fm else [],
    }


# ── Overview header (frontmatter → HTML) ───────────────
def render_overview_header(fm: dict) -> str:
    """概要フロントマターを、ページ先頭の type バッジ + メタ表に描画する。"""
    types = _as_list(fm.get("type"))
    badges = "".join(f'<span class="type-badge">{t}</span>' for t in types)
    badge_html = f'<div class="type-badges">{badges}</div>' if badges else ""

    rows = []

    def add(label: str, value: str):
        if value:
            rows.append(f'<tr><th>{label}</th><td>{value}</td></tr>')

    aliases = "、".join(_as_list(fm.get("aliases")))
    family = str(fm.get("family", ""))
    if fm.get("family_latin"):
        family = f'{family}（{fm["family_latin"]}）' if family else str(fm["family_latin"])
    botanical = str(fm.get("botanical", ""))
    cert = "、".join(_as_list(fm.get("certification")))
    regions = "、".join(_as_list(fm.get("regions")))
    season = "、".join(_as_list(fm.get("season")))
    uses = "、".join(_as_list(fm.get("uses")))

    add("別名", aliases)
    add("学名", f"<em>{botanical}</em>" if botanical else "")
    add("科", family)
    add("認証", cert)
    add("主な産地", regions)
    add("旬", season)
    add("用途", uses)

    table = f'<table class="overview-meta"><tbody>{"".join(rows)}</tbody></table>' if rows else ""
    if not badge_html and not table:
        return ""
    return f'<div class="overview-header">{badge_html}{table}</div>\n'


# ── .md link → .html link conversion ──────────────────
def convert_md_links(html: str) -> str:
    """HTML 内の .md リンクを .html に変換する。"""
    return re.sub(r'href="([^"]*?)\.md"', r'href="\1.html"', html)


# ── Table wrapper ──────────────────────────────────────
def wrap_tables(html: str) -> str:
    """<table> を div.table-wrapper で囲む。"""
    return html.replace("<table>", '<div class="table-wrapper"><table>').replace(
        "</table>", "</table></div>"
    )


# ── HTML Templates ─────────────────────────────────────
def html_page(title: str, body: str, cat: dict,
              css_path: str = "style.css", index_path: str = "index.html") -> str:
    """公開用HTMLページを生成する。"""
    nav_label = cat["nav_label"]
    footer_text = cat["footer"]
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — Vegetage</title>
<link rel="stylesheet" href="{css_path}">
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-6V2KRRWHS8"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', 'G-6V2KRRWHS8');
</script>
</head>
<body>

<header class="site-header">
  <div class="site-header-inner">
    <a href="{index_path}" class="site-logo">Vegetage</a>
    <nav class="site-nav">
      <a href="{index_path}">{nav_label}</a>
    </nav>
  </div>
</header>

<main class="container">
{body}
</main>

<footer class="site-footer">
  <p>Vegetage — {footer_text}</p>
  <p>データは <a href="https://creativecommons.org/licenses/by-sa/4.0/deed.ja">CC BY-SA 4.0</a> で提供されています。</p>
</footer>

</body>
</html>"""


# ── Article body (content only) ───────────────────────
def build_article_body(md_text: str) -> tuple[str, str]:
    """MD → 本文HTMLと目次HTMLを生成する。テンプレートは含まない。"""
    md.reset()
    html_body = md.convert(md_text)
    html_body = convert_md_links(html_body)
    html_body = wrap_tables(html_body)
    toc_html = md.toc
    return html_body, toc_html


# ── Guide navigation buttons ─────────────────────────
# ボタン定義: (subdir, label)  — None は親記事（概要）
GUIDE_BUTTONS = [
    (None, "概要"),
    ("history", "歴史"),
    ("cultivation", "栽培"),
    ("cuisine", "料理"),
]


def build_guide_nav(veg_name: str, current: str | None,
                    available: set[str], prefix: str = "") -> str:
    """概要・歴史・栽培・料理のナビボタンHTMLを生成する。

    current: 現在のページの subdir (None=概要, "history", "cultivation", "cuisine")
    available: 存在するサブガイドの subdir 集合
    prefix: リンクの接頭辞 ("" for 概要, "../" for サブガイド)
    """
    buttons = []
    for subdir, label in GUIDE_BUTTONS:
        is_current = (subdir == current)
        if is_current:
            buttons.append(f'<span class="guide-nav-current">{label}</span>')
        elif subdir is None:
            href = f'{prefix}{veg_name}.html'
            buttons.append(f'<a href="{href}">{label}</a>')
        elif subdir in available:
            if current is None:
                href = f'{subdir}/{veg_name}.html'
            else:
                href = f'../{subdir}/{veg_name}.html'
            buttons.append(f'<a href="{href}">{label}</a>')
    return '<nav class="guide-nav">' + "".join(buttons) + "</nav>"


# ── 2-column layout wrapper ──────────────────────────
def wrap_two_column(article_html: str, toc_html: str, guide_nav: str, back_link: str) -> str:
    """本文HTMLを2カラムの公開用レイアウトに入れ込む。"""
    sidebar = f"""<aside class="sidebar">
  <div class="sidebar-toc">
    <h2 class="sidebar-heading">目次</h2>
    {toc_html}
  </div>
  <div class="sidebar-ad">
    <!-- AdSense placeholder -->
  </div>
</aside>"""

    return f"""{guide_nav}
<div class="two-column">
  <div class="column-main">
    <article class="article-content">
{article_html}
    </article>
    {back_link}
  </div>
  {sidebar}
</div>"""


# ── Sub-guide preprocessing ──────────────────────────
def preprocess_subguide(md_text: str, veg_name: str, guide_type: str) -> str:
    """サブガイドMDの前処理: 導入文を削除し、タイトルを統一する。"""
    # フロントマターがあれば落とす
    _, md_text = parse_frontmatter(md_text)
    lines = md_text.split("\n")

    start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "---" or stripped.startswith("# "):
            start = i
            break

    if lines[start].strip() == "---":
        start += 1

    while start < len(lines) and not lines[start].strip():
        start += 1

    body_lines = lines[start:]

    new_title = f"# {veg_name}{guide_type}"
    for i, line in enumerate(body_lines):
        if line.strip().startswith("# "):
            body_lines[i] = new_title
            break

    return "\n".join(body_lines)


# ── Sub-guide types ──────────────────────────────────
SUBGUIDES = {
    "history": "の歴史",
    "cultivation": "の栽培",
    "cuisine": "の料理",
}


# ── Build sub-guide page ────────────────────────────
def build_subguide(md_path: Path, out_dir: Path, cat: dict,
                   subdir: str, guide_type: str,
                   available_guides: set[str]) -> dict:
    """サブガイドMDを前処理してHTMLに変換する。"""
    veg_name = md_path.stem
    text = md_path.read_text(encoding="utf-8")
    text = preprocess_subguide(text, veg_name, guide_type)

    article_html, toc_html = build_article_body(text)

    guide_nav = build_guide_nav(veg_name, current=subdir,
                                available=available_guides, prefix="../")

    nav_label = cat["nav_label"]
    back_link = f'<a href="../index.html" class="back-link">← {nav_label}に戻る</a>'

    content = wrap_two_column(article_html, toc_html, guide_nav, back_link)

    title = f"{veg_name}{guide_type}"
    out_path = out_dir / (md_path.stem + ".html")
    out_path.write_text(
        html_page(title, content, cat, css_path="../style.css",
                  index_path="../index.html"), encoding="utf-8"
    )
    return {"title": title, "veg_name": veg_name, "filename": md_path.stem + ".html"}


# ── Build article page (概要 = トップ) ─────────────────
def build_article(md_path: Path, out_dir: Path, cat: dict,
                  available_guides: set[str] | None = None) -> dict:
    """概要 MD を2カラムHTMLに変換して出力する。"""
    text = md_path.read_text(encoding="utf-8")
    meta = extract_metadata(text)

    article_html, toc_html = build_article_body(meta["body"])

    # フロントマターがあれば、概要ヘッダ（type バッジ + メタ表）を先頭に付ける
    if meta.get("frontmatter"):
        article_html = render_overview_header(meta["frontmatter"]) + article_html

    veg_name = md_path.stem
    guide_nav = build_guide_nav(veg_name, current=None,
                                available=available_guides or set())

    nav_label = cat["nav_label"]
    back_link = f'<a href="index.html" class="back-link">← {nav_label}に戻る</a>'

    content = wrap_two_column(article_html, toc_html, guide_nav, back_link)

    out_path = out_dir / (md_path.stem + ".html")
    out_path.write_text(html_page(meta["title"], content, cat), encoding="utf-8")
    return meta


# ── Index (科 / type の2タブ・事前生成) ────────────────
def _render_card(art: dict) -> str:
    return (
        f'<a href="{art["filename"]}" class="vegetable-card">\n'
        f'  <div class="card-name">{art["short_name"]}</div>\n'
        f'  <div class="card-latin">{art["latin"]}</div>\n'
        f'  <div class="card-desc">{art["subtitle"]}</div>\n'
        f"</a>"
    )


def _render_groups(groups: dict[str, list[dict]]) -> str:
    """グループ名 → 記事リスト を、見出し付きのカードグリッドに描画する。"""
    out = []
    # 「果樹」「未分類」はこの順で最後に（科タブで果樹を末尾にまとめる）
    last = ["果樹", "未分類"]
    keys = sorted(k for k in groups if k not in last)
    keys += [k for k in last if k in groups]
    for key in keys:
        arts = sorted(groups[key], key=lambda a: a["short_name"])
        cards = "\n".join(_render_card(a) for a in arts)
        out.append(
            f'<section class="index-group">\n'
            f'  <h2 class="group-heading">{key}<span class="group-count">{len(arts)}</span></h2>\n'
            f'  <div class="vegetable-grid">\n{cards}\n  </div>\n'
            f'</section>'
        )
    return "\n".join(out)


def build_index(articles: list[dict], out_dir: Path, cat: dict) -> None:
    """カテゴリのトップページ（科 / type の2タブ一覧）を生成する。"""
    # 科タブ: index_group ごと
    by_family: dict[str, list[dict]] = {}
    for art in articles:
        key = art.get("index_group") or "未分類"
        by_family.setdefault(key, []).append(art)

    # type タブ: type ごと（複数所属可）
    by_type: dict[str, list[dict]] = {}
    for art in articles:
        types = art.get("types") or []
        if not types:
            by_type.setdefault("未分類", []).append(art)
        for t in types:
            by_type.setdefault(t, []).append(art)

    cat_title = cat["title"]
    cat_subtitle = cat["subtitle"]
    cat_desc = cat["description"]

    body = f"""<div class="index-hero">
  <h1>{cat_title}</h1>
  <p class="subtitle">{cat_subtitle}</p>
</div>

<p class="index-description">
  {cat_desc}<br>
  DOP・IGP認定品種から地方の在来品種まで、{len(articles)}種の野菜の世界をお楽しみください。
</p>

<div class="index-tabs">
  <input type="radio" name="index-tab" id="tab-family" checked>
  <label for="tab-family">科で見る</label>
  <input type="radio" name="index-tab" id="tab-type">
  <label for="tab-type">種類で見る</label>

  <div class="tab-panel panel-family">
{_render_groups(by_family)}
  </div>
  <div class="tab-panel panel-type">
{_render_groups(by_type)}
  </div>
</div>
"""

    (out_dir / "index.html").write_text(
        html_page(cat_title, body, cat), encoding="utf-8"
    )


# ── Root index (aiseed.page のトップ) ─────────────────
def build_root_index():
    """サイトルート。2つのカタログ(野菜辞典・イタリア図鑑)への入口。"""
    (DIST_DIR / "index.html").write_text("""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Vegetage — 世界の伝統野菜辞典</title>
<style>
  body { font-family: serif; background: #faf9f6; color: #2c2c2c;
    max-width: 720px; margin: 0 auto; padding: 3em 1.5em; line-height: 1.8; }
  h1 { font-family: sans-serif; color: #4a7c59; }
  .cards { display: grid; gap: 1em; margin-top: 2em; }
  a.card { display: block; padding: 1.2em 1.5em; background: #fff;
    border: 1px solid #e0ddd8; border-radius: 6px; text-decoration: none;
    color: inherit; }
  a.card:hover { border-color: #4a7c59; }
  a.card b { font-family: sans-serif; color: #4a7c59; font-size: 1.1rem; }
  a.card span { color: #5a5a5a; font-size: .9rem; }
</style>
</head>
<body>
<h1>Vegetage</h1>
<p>忘れられた伝統野菜の物語を、未来へ繋ぐためのオープンな辞典です。</p>
<div class="cards">
  <a class="card" href="/vegetables/"><b>世界の伝統野菜辞典 →</b><br>
    <span>332種。栽培・栄養・食文化から気候変動への適応まで。</span></a>
  <a class="card" href="/italian/"><b>イタリア野菜図鑑 →</b><br>
    <span>69種。地中海の風土が育んだ伝統野菜と、その食文化の物語。</span></a>
</div>
</body>
</html>""", encoding="utf-8")


def main():
    # 掃除するのは**このビルダーの出力だけ**(カテゴリ配下とルートindex)。
    # web/site/ を丸ごと消すと、別カタログ(build_dict.py の vegetables/)を
    # 巻き込んでしまう。
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    for cat_key in CATEGORIES:
        cat_out = DIST_DIR / cat_key
        if cat_out.exists():
            shutil.rmtree(cat_out)
    build_root_index()

    total = 0

    for cat_key, cat in CATEGORIES.items():
        src_dir = WEB_DIR / cat_key
        out_dir = DIST_DIR / cat_key
        out_dir.mkdir(parents=True, exist_ok=True)

        # Copy CSS
        shutil.copy2(STATIC_DIR / "style.css", out_dir / "style.css")

        # サブガイドの存在マップ
        guides_map: dict[str, set[str]] = {}
        for subdir in SUBGUIDES:
            sub_src = src_dir / subdir
            if sub_src.exists():
                for p in sub_src.glob("*.md"):
                    guides_map.setdefault(p.stem, set()).add(subdir)

        # 概要（トップ）を各作物ぶんビルド
        articles = []
        md_files = sorted(src_dir.glob("*.md"))
        print(f"\n[{cat_key}] {cat['title']}: {len(md_files)} files")

        for md_path in md_files:
            available = guides_map.get(md_path.stem, set())
            meta = build_article(md_path, out_dir, cat, available)
            meta["filename"] = md_path.stem + ".html"
            articles.append(meta)
            print(f"  ✓ {md_path.name} → {meta['filename']}")

        build_index(articles, out_dir, cat)
        print(f"  ✓ index.html (科/種類の2タブ一覧)")
        total += len(articles) + 1

        # サブガイド（歴史・栽培・料理）
        for subdir, guide_type in SUBGUIDES.items():
            sub_src = src_dir / subdir
            if not sub_src.exists():
                continue
            sub_out = out_dir / subdir
            sub_out.mkdir(parents=True, exist_ok=True)

            sub_files = sorted(sub_src.glob("*.md"))
            print(f"\n[{cat_key}/{subdir}] {guide_type}: {len(sub_files)} files")

            for md_path in sub_files:
                veg_name = md_path.stem
                available = guides_map.get(veg_name, set())
                build_subguide(md_path, sub_out, cat, subdir, guide_type, available)
                print(f"  ✓ {md_path.name} → {subdir}/{veg_name}.html")
                total += 1

    print(f"\nDone! {total} files generated in {DIST_DIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
