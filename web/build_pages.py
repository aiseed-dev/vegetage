#!/usr/bin/env python3
"""
Vegetage — 読みものページのビルダー(自然農法・Light Farming・連載など)

正本ソース: web/pages/ (Markdown + YAML フロントマター)
  web/pages/<path>.md        → web/site/<path>/index.html
  web/pages/<path>/index.md  → web/site/<path>/index.html
  web/pages/images/          → web/site/images/
  英語版は web/pages/en/ 以下に同じパスで置く(→ /en/<path>/)

フロントマター:
  title, subtitle, label, description, image(/images/…), lang(ja|en)
  連載の目次ページ(index.md)は chapters: [slug, …] で章の順番を持つ。
  各章は summary・toc_title・date を持つ。

URL は aiseed.dev 時代と同じパスにしてある(website 側の 301 が splat 1 本で済むように)。
連載の章の slug は変えないこと。

Usage: python3 web/build_pages.py   (リポジトリ直下で)
"""

import html
import re
import shutil
from pathlib import Path

import markdown
import yaml
from markdown.extensions.tables import TableExtension
from markdown.extensions.toc import TocExtension

# ── Paths ──────────────────────────────────────────────
WEB_DIR = Path(__file__).resolve().parent
PAGES_DIR = WEB_DIR / "pages"
STATIC_DIR = WEB_DIR / "static"
DIST_DIR = WEB_DIR / "site"
SITE_URL = "https://aiseed.page"

# ── Language strings ───────────────────────────────────
NAV = {
    "ja": [("/vegetables/", "野菜辞典"), ("/italian/", "イタリア図鑑"),
           ("/natural-farming/", "自然農法"), ("/light-farming/", "Light Farming"),
           ("/phosphorus-and-farming/", "連載"), ("/gallery/", "畑の記録")],
    "en": [("/en/natural-farming/", "Natural Farming"), ("/en/light-farming/", "Light Farming"),
           ("/en/phosphorus-and-farming/", "Series"), ("/en/about/", "About")],
}
TEXT = {
    "ja": {"lang_link": "English", "toc": "目次", "series_toc": "連載の章",
           "prev": "← 前の章", "next": "次の章 →", "series_index": "連載の目次へ",
           "footer": "Vegetage — 伝統野菜と自然農法",
           "license": '文章は <a href="https://creativecommons.org/licenses/by/4.0/deed.ja">CC BY 4.0</a> で提供しています。',
           "more": '<a href="/about/">私たちのアプローチ</a> · 構造分析やブログは <a href="https://aiseed.dev/">aiseed.dev</a> にあります。'},
    "en": {"lang_link": "日本語", "toc": "Contents", "series_toc": "Chapters",
           "prev": "← Previous", "next": "Next →", "series_index": "Back to the series",
           "footer": "Vegetage — heritage vegetables and natural farming",
           "license": 'Text licensed under <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>.',
           "more": 'Analysis and blog posts live at <a href="https://aiseed.dev/en/">aiseed.dev</a>.'},
}

md = markdown.Markdown(
    extensions=[
        TableExtension(),
        TocExtension(toc_depth="2-3", slugify=lambda value, separator: re.sub(r"\s+", separator, value.strip().lower())),
        "markdown.extensions.fenced_code",
        "markdown.extensions.attr_list",
    ],
    output_format="html",
)


# ── Sources ────────────────────────────────────────────
def parse(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
    if not m:
        return {}, text
    return yaml.safe_load(m.group(1)) or {}, m.group(2)


def url_of(path: Path) -> str:
    rel = path.relative_to(PAGES_DIR).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "index":
        parts = parts[:-1]
    return "/" + "/".join(parts) + "/" if parts else "/"


def load_pages() -> dict[str, dict]:
    pages = {}
    for path in sorted(PAGES_DIR.rglob("*.md")):
        if "images" in path.relative_to(PAGES_DIR).parts:
            continue
        fm, body = parse(path)
        url = url_of(path)
        fm.setdefault("lang", "en" if url.startswith("/en/") else "ja")
        pages[url] = {"fm": fm, "body": body, "url": url, "src": path}
    return pages


def alternate_url(url: str, pages: dict) -> str | None:
    alt = url[3:] if url.startswith("/en/") else "/en" + url
    return alt if alt in pages else None


# ── HTML parts ─────────────────────────────────────────
def esc(s) -> str:
    return html.escape(str(s or ""), quote=True)


def wrap_tables(body: str) -> str:
    return re.sub(r"<table>(.*?)</table>", r'<div class="table-wrapper"><table>\1</table></div>', body, flags=re.S)


def render_markdown(text: str) -> tuple[str, str]:
    md.reset()
    body = wrap_tables(md.convert(text))
    return body, md.toc


def header_html(lang: str, alt: str | None) -> str:
    links = "".join(f'<a href="{href}">{label}</a>' for href, label in NAV[lang])
    if alt:
        links += f'<a href="{alt}" class="lang-link" hreflang="{"ja" if lang == "en" else "en"}">{TEXT[lang]["lang_link"]}</a>'
    return f"""<header class="site-header">
  <div class="site-header-inner">
    <a href="/" class="site-logo">Vegetage</a>
    <nav class="site-nav">{links}</nav>
  </div>
</header>"""


def hero_html(fm: dict) -> str:
    style = f' style="background-image: url(\'{esc(fm["image"])}\')"' if fm.get("image") else ""
    cls = "page-hero has-image" if fm.get("image") else "page-hero"
    label = f'<p class="hero-label">{esc(fm["label"])}</p>' if fm.get("label") else ""
    sub = f'<p class="hero-subtitle">{esc(fm["subtitle"])}</p>' if fm.get("subtitle") else ""
    return f"""<section class="{cls}"{style}>
  <div class="page-hero-inner">
    {label}
    <h1 class="hero-title">{esc(fm.get("title"))}</h1>
    {sub}
  </div>
</section>"""


def page_html(page: dict, main: str, alt: str | None) -> str:
    fm, url = page["fm"], page["url"]
    lang = fm["lang"]
    t = TEXT[lang]
    title = esc(fm.get("title"))
    desc = esc(fm.get("description") or fm.get("subtitle"))
    image = f'{SITE_URL}{fm["image"]}' if fm.get("image") else ""
    alt_links = ""
    if alt:
        ja_url, en_url = (alt, url) if lang == "en" else (url, alt)
        alt_links = (f'<link rel="alternate" hreflang="ja" href="{SITE_URL}{ja_url}">\n'
                     f'<link rel="alternate" hreflang="en" href="{SITE_URL}{en_url}">\n')
    og_image = f'<meta property="og:image" content="{image}">\n<meta name="twitter:card" content="summary_large_image">\n' if image else ""
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — Vegetage</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{SITE_URL}{url}">
{alt_links}<meta property="og:type" content="article">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{SITE_URL}{url}">
{og_image}<link rel="stylesheet" href="/css/style.css">
<link rel="stylesheet" href="/css/pages.css">
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-6V2KRRWHS8"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', 'G-6V2KRRWHS8');
</script>
</head>
<body class="reading-page">

{header_html(lang, alt)}

{hero_html(fm)}

<main class="container">
{main}
</main>

<footer class="site-footer">
  <p>{t["footer"]}</p>
  <p>{t["license"]} {t["more"]}</p>
</footer>

</body>
</html>
"""


def two_column(article: str, sidebar: str, after: str = "") -> str:
    return f"""<div class="two-column">
  <div class="column-main">
    <article class="article-content">
{article}
    </article>
    {after}
  </div>
  <aside class="sidebar">
{sidebar}
  </aside>
</div>"""


def toc_block(heading: str, toc: str) -> str:
    if "<li>" not in toc:
        return ""
    return f'<div class="sidebar-toc"><h2 class="sidebar-heading">{heading}</h2>{toc}</div>'


def series_list(index: dict, pages: dict, current: str | None) -> str:
    base = index["url"]
    items = []
    for slug in index["fm"].get("chapters", []):
        ch = pages.get(f"{base}{slug}/")
        if not ch:
            continue
        name = esc(ch["fm"].get("toc_title") or ch["fm"].get("title"))
        if ch["url"] == current:
            items.append(f'<li class="current"><span>{name}</span></li>')
        else:
            items.append(f'<li><a href="{ch["url"]}">{name}</a></li>')
    return '<ol class="series-chapters">' + "".join(items) + "</ol>"


# ── Page builders ──────────────────────────────────────
def build_plain(page: dict, pages: dict) -> str:
    body, toc = render_markdown(page["body"])
    lang = page["fm"]["lang"]
    sidebar = toc_block(TEXT[lang]["toc"], toc)
    main = two_column(body, sidebar) if sidebar and body.count("<h2") >= 3 else \
        f'<article class="article-content single-column">\n{body}\n</article>'
    return page_html(page, main, alternate_url(page["url"], pages))


def build_series_index(page: dict, pages: dict) -> str:
    body, _ = render_markdown(page["body"])
    cards = []
    for slug in page["fm"].get("chapters", []):
        ch = pages.get(f'{page["url"]}{slug}/')
        if not ch:
            raise SystemExit(f'章が見つかりません: {page["url"]}{slug}/')
        f = ch["fm"]
        cards.append(f"""<a class="series-card" href="{ch["url"]}">
  <span class="series-card-title">{esc(f.get("toc_title") or f.get("title"))}</span>
  <span class="series-card-summary">{esc(f.get("summary"))}</span>
</a>""")
    main = f"""<div class="series-cards">
{chr(10).join(cards)}
</div>
<article class="article-content single-column">
{body}
</article>"""
    return page_html(page, main, alternate_url(page["url"], pages))


def build_chapter(page: dict, index: dict, pages: dict) -> str:
    body, toc = render_markdown(page["body"])
    lang = page["fm"]["lang"]
    t = TEXT[lang]
    chapters = index["fm"]["chapters"]
    slug = page["url"].rstrip("/").rsplit("/", 1)[-1]
    i = chapters.index(slug)
    prev_a = f'<a class="prev" href="{index["url"]}{chapters[i - 1]}/">{t["prev"]}</a>' if i > 0 else "<span></span>"
    next_a = f'<a class="next" href="{index["url"]}{chapters[i + 1]}/">{t["next"]}</a>' if i + 1 < len(chapters) else "<span></span>"
    nav = f"""<nav class="chapter-nav">{prev_a}<a href="{index["url"]}">{t["series_index"]}</a>{next_a}</nav>"""
    date = f'<p class="chapter-date">{esc(page["fm"]["date"])}</p>\n' if page["fm"].get("date") else ""
    sidebar = toc_block(t["toc"], toc) + \
        f'<div class="sidebar-toc"><h2 class="sidebar-heading">{t["series_toc"]}</h2>{series_list(index, pages, page["url"])}</div>'
    main = two_column(date + body, sidebar, nav)
    return page_html(page, main, alternate_url(page["url"], pages))


# ── Main ───────────────────────────────────────────────
def output_path(url: str) -> Path:
    return DIST_DIR / url.strip("/") / "index.html"


def main():
    pages = load_pages()

    # 掃除するのは**このビルダーの出力だけ**(build.py / build_dict.py の出力は残す)
    tops = {"css", "images"}
    for url in pages:
        parts = url.strip("/").split("/")
        tops.add("/".join(parts[:2]) if parts[0] == "en" else parts[0])
    for top in tops:
        target = DIST_DIR / top
        if target.exists():
            shutil.rmtree(target)

    css_dir = DIST_DIR / "css"
    css_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(STATIC_DIR / "style.css", css_dir / "style.css")
    shutil.copy2(STATIC_DIR / "pages.css", css_dir / "pages.css")
    shutil.copytree(PAGES_DIR / "images", DIST_DIR / "images")

    series = {url: p for url, p in pages.items() if p["fm"].get("chapters")}
    count = 0
    for url, page in pages.items():
        if url in series:
            out = build_series_index(page, pages)
        else:
            parent = url.rstrip("/").rsplit("/", 1)[0] + "/"
            out = build_chapter(page, series[parent], pages) if parent in series else build_plain(page, pages)
        dest = output_path(url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(out, encoding="utf-8")
        count += 1
        print(f"  ✓ {url}")
    print(f"\nDone! {count} pages → {DIST_DIR.relative_to(WEB_DIR.parent)}/")


if __name__ == "__main__":
    main()
