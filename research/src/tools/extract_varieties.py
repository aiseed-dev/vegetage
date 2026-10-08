#!/usr/bin/env python3
"""栽培ガイドMDファイルから品種データを抽出するスクリプト"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "web" / "italian" / "cultivation"
OUT_FILE = ROOT / "data" / "extracted_varieties.csv"

# 認証パターン
CERT_RE = re.compile(
    r'\b(DOP|IGP|PAT|De\.?Co\.?|Presidio|Slow Food Presidio)\b', re.IGNORECASE
)

# スキップする日本語キーワード
SKIP_JA = {"特徴", "味", "栽培メモ", "栽培法", "注意", "ポイント", "おすすめ",
            "自然栽培", "有機栽培", "日本", "イタリア", "品種", "播種",
            "発芽", "収穫", "覆土", "種子", "休眠", "対策", "メカニズム",
            "土作り", "害虫", "まとめ", "データ", "保存", "用途",
            "コツ", "ここがポイント", "栽培計画"}


def normalize_cert(raw: list[str]) -> str:
    """認証名を正規化"""
    certs = set()
    for c in raw:
        cl = c.lower()
        if "presidio" in cl or "slow" in cl:
            certs.add("Slow Food Presidio")
        elif "de.co" in cl or "deco" in cl:
            certs.add("De.Co.")
        else:
            certs.add(c.upper())
    return ", ".join(sorted(certs))


def is_italian_name(text: str) -> bool:
    """イタリア語の品種名かどうかを判定"""
    # ラテン文字を含むか
    return bool(re.search(r'[A-Za-zÀ-ÿ]{3,}', text))


def extract_varieties(filepath: Path) -> list[dict]:
    """1つのMDファイルから品種名・イタリア名・認証を抽出"""
    text = filepath.read_text(encoding="utf-8")
    veg_name = filepath.stem
    varieties = []
    seen = set()  # 重複排除

    # --- パターン1: **日本語名 (Italian Name CERT)** ---
    # 例: **サン・マルツァーノ (San Marzano dell'Agro Sarnese-Nocerino DOP)**
    for m in re.finditer(r'\*\*([^*\(]+?)\s*\(([^)]+)\)\*\*', text):
        ja_name = m.group(1).strip().rstrip('・').strip()
        it_part = m.group(2).strip()

        if not is_italian_name(it_part):
            continue

        cert_match = CERT_RE.findall(it_part)
        certification = normalize_cert(cert_match) if cert_match else ""
        it_name = CERT_RE.sub("", it_part).strip().rstrip(",").strip()

        if len(ja_name) < 2 or len(it_name) < 3:
            continue
        if any(w in ja_name for w in SKIP_JA):
            continue

        key = it_name.lower()
        if key not in seen:
            seen.add(key)
            varieties.append({
                "name_ja": ja_name,
                "name_it": it_name,
                "item": veg_name,
                "certification": certification,
            })

    # --- パターン2: **Italian Name CERT** (括弧なし、独立行) ---
    # 例: **Carciofo Romanesco del Lazio IGP**
    # 例: **Melanzana Rossa di Rotonda DOP**
    for m in re.finditer(r'^\*\*([A-ZÀ-Ÿ][^*]+?)\*\*\s*$', text, re.MULTILINE):
        it_part = m.group(1).strip()

        if not is_italian_name(it_part):
            continue
        # 短すぎるものはスキップ
        if len(it_part) < 10:
            continue

        cert_match = CERT_RE.findall(it_part)
        certification = normalize_cert(cert_match) if cert_match else ""
        it_name = CERT_RE.sub("", it_part).strip().rstrip(",").strip()

        # 見出し行から日本語名を探す（直前の ### 行）
        ja_name = ""
        pos = m.start()
        preceding = text[:pos].rstrip()
        lines_before = preceding.split("\n")
        for line in reversed(lines_before[-5:]):
            line = line.strip()
            if line.startswith("###"):
                # ### ① ラツィオの王様：ロマネスコ種
                cleaned = re.sub(r'^#{1,4}\s*[①-⑳\d]*\.?\s*', '', line).strip()
                # コロンの後の部分を取る
                if "：" in cleaned:
                    ja_name = cleaned.split("：")[-1].strip()
                elif ":" in cleaned:
                    ja_name = cleaned.split(":")[-1].strip()
                else:
                    ja_name = cleaned
                # 「種」を除去
                ja_name = ja_name.rstrip("種").strip()
                break

        if not ja_name:
            # イタリア名から日本語名を生成できない場合、イタリア名をそのまま使用
            ja_name = it_name

        key = it_name.lower()
        if key not in seen:
            seen.add(key)
            varieties.append({
                "name_ja": ja_name,
                "name_it": it_name,
                "item": veg_name,
                "certification": certification,
            })

    # --- パターン3: ### 見出しにイタリア名と認証が含まれる ---
    # 例: ### ① ロトンダの赤ナス (Melanzana Rossa di Rotonda DOP)
    for m in re.finditer(r'^#{2,4}\s*.+?\(([A-ZÀ-Ÿ][^)]+)\)', text, re.MULTILINE):
        it_part = m.group(1).strip()

        if not is_italian_name(it_part):
            continue

        cert_match = CERT_RE.findall(it_part)
        certification = normalize_cert(cert_match) if cert_match else ""
        it_name = CERT_RE.sub("", it_part).strip().rstrip(",").strip()

        # 見出しから日本語名を抽出
        full_line = m.group(0)
        ja_part = re.sub(r'^#{2,4}\s*[①-⑳\d]*\.?\s*', '', full_line)
        ja_part = re.sub(r'\s*\([^)]*\)\s*$', '', ja_part).strip()
        # コロン分割
        if "：" in ja_part:
            ja_name = ja_part.split("：")[-1].strip()
        elif ":" in ja_part:
            ja_name = ja_part.split(":")[-1].strip()
        else:
            ja_name = ja_part

        if len(ja_name) < 2:
            ja_name = it_name

        key = it_name.lower()
        if key not in seen:
            seen.add(key)
            varieties.append({
                "name_ja": ja_name,
                "name_it": it_name,
                "item": veg_name,
                "certification": certification,
            })

    # --- パターン4: *  **品名 (Italian Name CERT)** ---
    # リストアイテム内の品種
    for m in re.finditer(r'\*\s+\*\*([^*]+?)\s*\(([A-ZÀ-Ÿ][^)]+)\)\*\*', text):
        ja_name = m.group(1).strip().rstrip('・').strip()
        it_part = m.group(2).strip()

        if not is_italian_name(it_part):
            continue

        cert_match = CERT_RE.findall(it_part)
        certification = normalize_cert(cert_match) if cert_match else ""
        it_name = CERT_RE.sub("", it_part).strip().rstrip(",").strip()

        if len(ja_name) < 2 or len(it_name) < 3:
            continue
        if any(w in ja_name for w in SKIP_JA):
            continue

        key = it_name.lower()
        if key not in seen:
            seen.add(key)
            varieties.append({
                "name_ja": ja_name,
                "name_it": it_name,
                "item": veg_name,
                "certification": certification,
            })

    return varieties


def main():
    md_files = sorted(SRC_DIR.glob("*.md"))
    print(f"栽培ガイド: {len(md_files)} ファイル\n")

    all_varieties = []

    for md in md_files:
        varieties = extract_varieties(md)
        if varieties:
            print(f"  {md.stem}: {len(varieties)} 品種")
            all_varieties.extend(varieties)
        else:
            print(f"  {md.stem}: 品種なし")

    # CSV出力
    header = "name_ja,name_it,item,certification"
    lines = [header]
    for v in all_varieties:
        name_ja = v["name_ja"].replace('"', '""')
        name_it = v["name_it"].replace('"', '""')
        item = v["item"].replace('"', '""')
        cert = v["certification"]
        lines.append(f'"{name_ja}","{name_it}","{item}","{cert}"')

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\n合計: {len(all_varieties)} 品種")
    print(f"出力: {OUT_FILE}")


if __name__ == "__main__":
    main()
