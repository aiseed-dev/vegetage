#!/usr/bin/env python3
"""
Vegetage — 野菜辞典(JSON)Web サイトビルダー / カタログB

入力: frontend/vegetage/assets/data/(スマホアプリと共有する構造化JSON)
  _index.json                       … 一覧(vegetable)と別名(redirect)
  vegetable_summary/<名>.json        … 一覧カード + 人が書いた読み物(content.ja)
  vegetable_detail/<名>.json         … 詳細(15セクションの構造化データ)

出力: web/site/vegetables/
  index.html                        … 科で分類したカード一覧 + 絞り込み検索
  <名>.html                          … 概要(読み物)+ 詳細データ(汎用再帰描画)
  <別名>.html                        … redirect(meta refresh)

イタリア図鑑(build.py)とは別カタログ。出力先 vegetables/ 以下だけを掃除するので
両ビルダーは互いを壊さない。style.css は図鑑と共有し、辞典固有の意匠だけ足す。

Usage: python3 web/build_dict.py
"""

import html
import json
import re
import shutil
from pathlib import Path

# ── Paths ──────────────────────────────────────────────
WEB_DIR = Path(__file__).resolve().parent
REPO_ROOT = WEB_DIR.parent                 # リポジトリ直下
DATA_ROOT = REPO_ROOT / "frontend" / "vegetage" / "assets" / "data"
SUMMARY_DIR = DATA_ROOT / "vegetable_summary"
DETAIL_DIR = DATA_ROOT / "vegetable_detail"
INDEX_JSON = DATA_ROOT / "_index.json"
STATIC_DIR = WEB_DIR / "static"
DIST_DIR = WEB_DIR / "site" / "vegetables"

SITE = {
    "title": "世界の伝統野菜辞典",
    "subtitle": "Vegetables of the World — 栽培・栄養から気候変動適応まで",
    "description": "332種の野菜を、栽培特性・栄養・食文化・気候変動への適応、"
                   "環境再生農業までの視点で収録した辞典です。",
    "nav_label": "野菜辞典",
    "footer": "世界の伝統野菜辞典",
}

# ── 概要(読み物)の項目 ─────────────────────────────
# content.ja のキー → (見出し, 一行キー)。本文と対の oneliner があるものは束ねる。
SUMMARY_BLOCKS = [
    ("description", "解説", None),
    ("cultural_background", "文化的背景", None),
    ("practical_tips", "選び方・保存", "practical_oneliner"),
    ("nutrition_benefits", "栄養", "nutrition_oneliner"),
    ("safety_notes", "食べるときの注意", "safety_oneliner"),
    ("honest_assessment", "正直な評価", "honest_oneliner"),
    ("notes", "備考", None),
]

# 品目 url の集合(relationships の [[名前]] リンクを実在するものだけ張るため)
KNOWN_URLS: set[str] = set()

# ── 詳細セクションの日本語ラベル ─────────────────────
LABELS = {
    "basic_info": "基本情報", "global_names": "各地の名称",
    "classification": "分類", "global_cultural_value": "文化的価値",
    "cultivation_characteristics": "栽培特性",
    "nutritional_functional": "栄養・機能性",
    "culinary_applications": "料理での利用",
    "climate_change_adaptation": "気候変動への適応",
    "natural_hybridization_potential": "自然交雑の可能性",
    "regenerative_agriculture": "環境再生農業",
    "modern_applications": "現代的な応用",
    "conservation_priority": "保全の優先度",
    "global_dictionary_evaluation": "辞典としての評価",
    "representative_varieties": "代表的な品種",
    "variety_profile": "品種プロファイル", "narrative": "物語",
    "structured_data": "構造化データ", "relationships": "近縁・仲間",
    # よく出る下位キー
    "primary_name": "主な名称", "scientific_name": "学名",
    "plant_type": "植物型", "edible_parts": "食用部位",
    "origin_region": "原産地", "wild_relatives": "野生近縁種",
    "family": "科", "genus": "属", "species": "種",
    "international": "国際名", "regional": "地域名", "indigenous": "在来名",
    "nutritional_profile": "栄養成分", "bioactive_compounds": "生理活性成分",
    "traditional_medicinal_uses": "伝統的な薬用", "modern_research": "現代の研究",
    "compound": "成分", "concentration": "含有量", "health_effect": "効能",
    "difficulty_level": "難易度", "climate_adaptability": "気候適応性",
    "growing_seasons": "栽培時期", "productivity": "生産性",
    "global_production": "世界の生産",
    "heat_stress_tolerance": "高温耐性",
    "optimal_temperature_range": "最適温度域",
    "extreme_heat_survival": "極端な高温での生存",
    "cold_tolerance": "耐寒性",
    "water_stress_adaptation": "水ストレス適応",
    "extreme_weather_resilience": "異常気象への耐性",
    "soil_health_benefits": "土壌の健康への寄与",
    "biodiversity_enhancement": "生物多様性の向上",
    "carbon_sequestration": "炭素固定",
    "companion_planting_benefits": "コンパニオンプランツ効果",
    "variety_name": "品種名", "local_name": "現地名",
    "world_prevalence": "世界的な普及",
    "cultural_importance_by_region": "地域ごとの文化的重要性",
    "culinary_traditions": "料理の伝統",
    "historical_significance": "歴史的意義",
    "global_cooking_methods": "各地の調理法",
    "processing_preservation": "加工・保存",
    "flavor_characteristics": "風味の特徴",
}

# metadata 内のキー(本文からは隠し、source_comment だけ小さく出す)
META_KEYS = {"data_availability", "confidence_level", "source_comment",
             "metadata", "processing_metadata"}


def label(key: str) -> str:
    if key in LABELS:
        return LABELS[key]
    # 未知キーは snake_case を見やすく
    return key.replace("_", " ").strip().capitalize()


def esc(s) -> str:
    return html.escape(str(s))


def slug(name: str) -> str:
    """id/名前 → ファイル名・URL 安全形。日本語はそのまま、パス記号だけ潰す。"""
    s = str(name).strip()
    s = re.sub(r"\s*[\\/]\s*", "-", s)   # " / " などを "-" に
    s = re.sub(r"\s+", " ", s)
    return s


# ── 汎用再帰レンダラ(dict/list/scalar → HTML) ─────────
def render_value(value, depth: int = 3) -> str:
    """詳細JSONの任意の値を HTML に描く。depth は見出しレベルの目安。"""
    if isinstance(value, dict):
        return _render_dict(value, depth)
    if isinstance(value, list):
        return _render_list(value, depth)
    if isinstance(value, bool):
        return "はい" if value else "いいえ"
    text = str(value).strip()
    return esc(text) if text else ""


def _is_scalar_record(d: dict) -> bool:
    """全値がスカラー(または空)の dict = 定義表で描ける。"""
    return all(not isinstance(v, (dict, list)) for v in d.values())


def _render_meta(meta: dict) -> str:
    """metadata ブロックは source_comment だけ控えめな注記として出す。"""
    note = meta.get("source_comment")
    return f'<p class="data-note">{esc(note)}</p>' if note else ""


def _render_dict(d: dict, depth: int) -> str:
    parts = []
    # metadata は隠し、注記だけ
    if "metadata" in d and isinstance(d["metadata"], dict):
        parts.append(_render_meta(d["metadata"]))
    body = {k: v for k, v in d.items() if k not in META_KEYS}

    scalars = {k: v for k, v in body.items()
               if not isinstance(v, (dict, list)) and str(v).strip()}
    nested = {k: v for k, v in body.items() if isinstance(v, (dict, list))}

    if scalars:
        rows = "".join(
            f'<tr><th>{esc(label(k))}</th><td>{esc(v)}</td></tr>'
            for k, v in scalars.items()
        )
        parts.append(f'<table class="data-table"><tbody>{rows}</tbody></table>')

    tag = "h4" if depth >= 4 else "h3"
    for k, v in nested.items():
        inner = render_value(v, depth + 1)
        if inner.strip():
            parts.append(f'<div class="data-group"><{tag}>{esc(label(k))}'
                         f'</{tag}>{inner}</div>')
    return "\n".join(parts)


def _render_list(items: list, depth: int) -> str:
    if not items:
        return ""
    # スカラーの配列 → 箇条書き
    if all(not isinstance(x, (dict, list)) for x in items):
        lis = "".join(f"<li>{esc(x)}</li>" for x in items if str(x).strip())
        return f"<ul>{lis}</ul>" if lis else ""
    # dict の配列 → 各要素をカード状に
    blocks = []
    for x in items:
        inner = render_value(x, depth + 1)
        if inner.strip():
            blocks.append(f'<div class="data-card">{inner}</div>')
    return "\n".join(blocks)


# ── 詳細セクション(15項目)を順に描く ───────────────
# 概要と重複しがちな最初の3つ(basic_info/global_names/classification)は
# ヘッダのメタ表に集約するので、詳細本文からは外す。
DETAIL_SKIP_TOP = {"basic_info", "processing_metadata"}


def render_detail(detail: dict) -> tuple[str, list[tuple[str, str]]]:
    """詳細JSON → (本文HTML, [(アンカー, 見出し)])。目次用に見出しを返す。"""
    sections, toc = [], []
    for key, value in detail.items():
        if key in DETAIL_SKIP_TOP:
            continue
        inner = render_value(value, depth=3)
        if not inner.strip():
            continue
        anchor = "sec-" + re.sub(r"[^a-z0-9]+", "-", key.lower()).strip("-")
        toc.append((anchor, label(key)))
        sections.append(
            f'<section class="detail-section" id="{anchor}">\n'
            f'  <h2>{esc(label(key))}</h2>\n{inner}\n</section>'
        )
    return "\n".join(sections), toc


# ── ヘッダ(名称・学名・科の要約表) ──────────────────
def render_header(gi: dict, cja: dict) -> str:
    disp = cja.get("display_name") or gi.get("url", "")
    kana = gi.get("kana_name", "")
    sci = gi.get("scientificName", "")
    cls = gi.get("classification", {})
    fam = cls.get("family_ja", "")
    oneliner = cja.get("oneliner", "")

    names = gi.get("names", {})
    en = ""
    intl = names.get("international", {})
    if isinstance(intl, dict) and intl.get("en"):
        en = "、".join(intl["en"]) if isinstance(intl["en"], list) else str(intl["en"])

    rows = []

    def add(lbl, val):
        if val:
            rows.append(f"<tr><th>{lbl}</th><td>{esc(val)}</td></tr>")

    add("よみ", kana)
    add("英名", en)
    rows_sci = f"<em>{esc(sci)}</em>" if sci else ""
    if rows_sci:
        rows.append(f"<tr><th>学名</th><td>{rows_sci}</td></tr>")
    add("科", fam)
    part = gi.get("foodClassification", {}).get("primaryPart", "")
    add("主な食用部位", part)
    table = (f'<table class="overview-meta"><tbody>{"".join(rows)}</tbody></table>'
             if rows else "")

    catch = f'<p class="veg-oneliner">{esc(oneliner)}</p>' if oneliner else ""
    return (f'<div class="veg-header">\n<h1>{esc(disp)}</h1>\n{catch}\n'
            f'{table}\n</div>')


# ── 概要(読み物)ブロック ────────────────────────────
def _link_wiki(name: str) -> str:
    """"[[名前]]" 内の名前 → 実在すればリンク、無ければただの語。"""
    n = name.strip().strip("[]").strip()
    if n in KNOWN_URLS:
        return f'<a href="{esc(slug(n))}.html">{esc(n)}</a>'
    return esc(n)


def render_relationships(rel: dict) -> str:
    groups = [("parentSpecies", "親種"), ("children", "派生・品種"),
              ("similarVegetables", "似た野菜")]
    rows = []
    def flatten(x):
        if isinstance(x, list):
            for i in x:
                yield from flatten(i)
        elif x is not None and str(x).strip():
            yield str(x)

    for key, lbl in groups:
        vals = list(flatten(rel.get(key)))
        links = [_link_wiki(v) for v in vals]
        if links:
            rows.append(f'<tr><th>{lbl}</th><td>{"、".join(links)}</td></tr>')
    if not rows:
        return ""
    return (f'<h2>近縁・仲間</h2>'
            f'<table class="data-table"><tbody>{"".join(rows)}</tbody></table>')


def render_overview(cja: dict) -> str:
    out = []
    for key, heading, oneliner_key in SUMMARY_BLOCKS:
        body = str(cja.get(key) or "").strip()
        lead = str(cja.get(oneliner_key) or "").strip() if oneliner_key else ""
        if not body and not lead:
            continue
        block = [f'<h2>{heading}</h2>']
        if lead:
            block.append(f'<p class="lead">{esc(lead)}</p>')
        if body:
            for para in re.split(r"\n{2,}", body):
                para = para.strip()
                if para:
                    block.append(f"<p>{esc(para)}</p>")
        out.append("\n".join(block))
    rel = cja.get("relationships")
    if isinstance(rel, dict):
        rel_html = render_relationships(rel)
        if rel_html:
            out.append(rel_html)
    return "\n".join(out)


# ── HTML ページ骨格 ────────────────────────────────
def html_page(title: str, body: str, *, css="style.css", index="index.html") -> str:
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)} — Vegetage 野菜辞典</title>
<link rel="stylesheet" href="{css}">
</head>
<body>
<header class="site-header">
  <div class="site-header-inner">
    <a href="{index}" class="site-logo">Vegetage 野菜辞典</a>
    <nav class="site-nav"><a href="{index}">{SITE['nav_label']}</a></nav>
  </div>
</header>
<main class="container">
{body}
</main>
<footer class="site-footer">
  <p>Vegetage — {SITE['footer']}</p>
  <p>データは <a href="https://creativecommons.org/licenses/by-sa/4.0/deed.ja">CC BY-SA 4.0</a> で提供されています。</p>
</footer>
</body>
</html>"""


# ── 個別ページ ────────────────────────────────────
def build_item(url: str) -> dict | None:
    """1品目のページを書き、一覧カード用のメタを返す。"""
    sp = SUMMARY_DIR / f"{url}.json"
    if not sp.exists():
        return None
    summary = json.loads(sp.read_text(encoding="utf-8"))
    gi = summary.get("global_info", {})
    cja = summary.get("content", {}).get("ja", {})

    header = render_header(gi, cja)
    overview = render_overview(cja)

    detail_html, toc = "", []
    dp = DETAIL_DIR / f"{url}.json"
    if dp.exists():
        detail = json.loads(dp.read_text(encoding="utf-8"))
        detail_html, toc = render_detail(detail)

    toc_items = "".join(f'<li><a href="#{a}">{esc(t)}</a></li>' for a, t in toc)
    sidebar = (f'<aside class="sidebar"><div class="sidebar-toc">'
               f'<h2 class="sidebar-heading">詳細データ</h2>'
               f'<ul>{toc_items}</ul></div></aside>') if toc else ""

    detail_wrap = (f'<div class="detail-data"><h2 class="detail-lead">詳細データ</h2>'
                   f'{detail_html}</div>') if detail_html else ""

    body = f"""{header}
<div class="two-column">
  <div class="column-main">
    <article class="article-content">
{overview}
{detail_wrap}
    </article>
    <a href="index.html" class="back-link">← {SITE['nav_label']}に戻る</a>
  </div>
  {sidebar}
</div>"""

    (DIST_DIR / f"{slug(url)}.html").write_text(
        html_page(cja.get("display_name") or url, body), encoding="utf-8")

    return {
        "url": url,
        "slug": slug(url),
        "display_name": cja.get("display_name") or url,
        "kana": gi.get("kana_name", ""),
        "oneliner": cja.get("oneliner", ""),
        "family": gi.get("classification", {}).get("family_ja", "") or "未分類",
        "search": " ".join([
            url, gi.get("kana_name", ""), cja.get("display_name", ""),
            gi.get("scientificName", ""),
        ]).lower(),
    }


# ── 別名リダイレクト ──────────────────────────────
def build_redirect(from_id: str, to_url: str) -> None:
    to_slug = slug(to_url)
    (DIST_DIR / f"{slug(from_id)}.html").write_text(
        f'<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8">'
        f'<meta http-equiv="refresh" content="0; url={esc(to_slug)}.html">'
        f'<link rel="canonical" href="{esc(to_slug)}.html">'
        f'<title>{esc(from_id)}</title></head>'
        f'<body><a href="{esc(to_slug)}.html">{esc(to_url)}</a></body></html>',
        encoding="utf-8")


# ── 一覧(科で分類 + 検索) ───────────────────────────
def build_index(cards: list[dict]) -> None:
    groups: dict[str, list[dict]] = {}
    for c in cards:
        groups.setdefault(c["family"], []).append(c)

    def card_html(c):
        return (
            f'<a href="{esc(c["slug"])}.html" class="vegetable-card" '
            f'data-search="{esc(c["search"])}">\n'
            f'  <div class="card-name">{esc(c["display_name"])}</div>\n'
            f'  <div class="card-kana">{esc(c["kana"])}</div>\n'
            f'  <div class="card-desc">{esc(c["oneliner"])}</div>\n'
            f"</a>"
        )

    sections = []
    last = ["未分類"]
    keys = sorted(k for k in groups if k not in last)
    keys += [k for k in last if k in groups]
    for key in keys:
        arts = sorted(groups[key], key=lambda c: c["kana"] or c["display_name"])
        cards_html = "\n".join(card_html(c) for c in arts)
        sections.append(
            f'<section class="index-group" data-family="{esc(key)}">\n'
            f'  <h2 class="group-heading">{esc(key)}'
            f'<span class="group-count">{len(arts)}</span></h2>\n'
            f'  <div class="vegetable-grid">\n{cards_html}\n  </div>\n</section>')

    body = f"""<div class="index-hero">
  <h1>{esc(SITE['title'])}</h1>
  <p class="subtitle">{esc(SITE['subtitle'])}</p>
</div>
<p class="index-description">{esc(SITE['description'])}<br>
  収録 {len(cards)} 種。名前・よみ・学名で絞り込めます。</p>
<div class="veg-search">
  <input type="search" id="veg-search" placeholder="野菜を検索(例: だいこん、Brassica)"
         autocomplete="off" aria-label="野菜を検索">
  <p class="search-empty" id="search-empty" hidden>該当する野菜がありません。</p>
</div>
{"".join(sections)}
<script>
(function() {{
  var box = document.getElementById('veg-search');
  var cards = Array.prototype.slice.call(document.querySelectorAll('.vegetable-card'));
  var groups = Array.prototype.slice.call(document.querySelectorAll('.index-group'));
  var empty = document.getElementById('search-empty');
  box.addEventListener('input', function() {{
    var q = box.value.trim().toLowerCase();
    var hits = 0;
    cards.forEach(function(c) {{
      var ok = !q || c.getAttribute('data-search').indexOf(q) !== -1;
      c.style.display = ok ? '' : 'none';
      if (ok) hits++;
    }});
    groups.forEach(function(g) {{
      var any = g.querySelector('.vegetable-card:not([style*="none"])');
      g.style.display = any ? '' : 'none';
    }});
    empty.hidden = hits !== 0;
  }});
}})();
</script>
"""
    (DIST_DIR / "index.html").write_text(html_page(SITE["title"], body),
                                         encoding="utf-8")


# ── 辞典固有CSS(図鑑のstyle.cssに追記コピー) ───────────
EXTRA_CSS = """
/* --- 野菜辞典(カタログB)固有 --- */
.veg-header h1 { margin-bottom: .2em; }
.veg-oneliner { color: var(--color-text-secondary); font-size: 1.05rem; margin: 0 0 1em; }
.veg-search { margin: 1.5em 0; }
.veg-search input { width: 100%; padding: .7em 1em; font-size: 1rem;
  border: 1px solid var(--color-border); border-radius: var(--radius);
  background: var(--color-surface); color: var(--color-text); }
.card-kana { color: var(--color-text-secondary); font-size: .82rem; }
.data-table { width: 100%; border-collapse: collapse; margin: .5em 0 1em; }
.data-table th, .data-table td { text-align: left; vertical-align: top;
  padding: .4em .7em; border-bottom: 1px solid var(--color-border-light); }
.data-table th { width: 34%; color: var(--color-text-secondary); font-weight: 600;
  font-family: var(--font-heading); font-size: .9rem; }
.data-group { margin: .8em 0 .8em; }
.data-group h3 { font-size: 1.05rem; color: var(--color-accent-dark);
  margin: 1em 0 .3em; }
.data-group h4 { font-size: .95rem; color: var(--color-text-secondary);
  margin: .8em 0 .2em; }
.data-card { background: var(--color-blockquote-bg); border-radius: var(--radius);
  padding: .3em 1em; margin: .5em 0; }
.data-note { font-size: .8rem; color: var(--color-text-secondary);
  font-style: italic; margin: .2em 0 .6em; }
.detail-data { margin-top: 2.5em; border-top: 2px solid var(--color-border); padding-top: 1em; }
.detail-lead { font-family: var(--font-heading); }
.detail-section { margin: 1.5em 0; }
.detail-section > h2 { border-bottom: 1px solid var(--color-border-light); padding-bottom: .2em; }
"""


def write_styles() -> None:
    base = (STATIC_DIR / "style.css").read_text(encoding="utf-8")
    (DIST_DIR / "style.css").write_text(base + EXTRA_CSS, encoding="utf-8")


# ── main ──────────────────────────────────────────
def main() -> None:
    if not DATA_ROOT.is_dir():
        raise SystemExit(f"入力データが見つかりません: {DATA_ROOT}")
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True)

    write_styles()
    index = json.loads(INDEX_JSON.read_text(encoding="utf-8"))

    # relationships のリンク先判定用に、実在する summary の url を先に集める
    KNOWN_URLS.clear()
    KNOWN_URLS.update(p.stem for p in SUMMARY_DIR.glob("*.json"))

    cards, redirects, missing = [], [], []
    for entry in index:
        if entry.get("type") == "vegetable":
            card = build_item(entry["id"])
            if card:
                cards.append(card)
            else:
                missing.append(entry["id"])
        elif entry.get("type") == "redirect":
            redirects.append((entry["id"], entry.get("redirect_to", "")))

    # redirect 先が実在するものだけ
    urls = {c["url"] for c in cards}
    r_ok = 0
    for from_id, to_url in redirects:
        if to_url in urls:
            build_redirect(from_id, to_url)
            r_ok += 1

    build_index(cards)

    print(f"[野菜辞典] {len(cards)} 品目 + index + redirect {r_ok}/{len(redirects)} 件"
          f" → {DIST_DIR.relative_to(WEB_DIR.parent)}/")
    if missing:
        print(f"  ⚠ summary 欠落で未生成: {len(missing)} 件 {missing[:5]}")


if __name__ == "__main__":
    main()
