#!/usr/bin/env python3
"""アプリ同梱フォントをサブセット生成する。

Web版で外部フォント(fonts.gstatic.com)を取得しないための同梱フォントを生成する。
アセットデータ(assets/data/**/*.json)と Dartソース(lib/**/*.dart)に現れる
全文字 + 基本レンジ(ASCII/かな/全角記号など)を収録する。

二段構成:
  1. 本文フォント: BIZ UDPGothic(tool/fonts_src/、OFL 1.1、Regular/Bold)
  2. フォールバック: 1 に無い文字(ハングル・稀な漢字など)だけを
     システムの Noto Sans CJK JP(fonts-noto-cjk、OFL 1.1)から抜き出す

野菜データを追加・更新したら再実行すること。収録外の文字が画面に出ると
Flutter は Google Fonts へのフォールバック取得を試みてしまう。

使い方:
    python3 -m venv .venv-fonts && .venv-fonts/bin/pip install fonttools
    .venv-fonts/bin/python tool/subset_fonts.py
"""

import glob
import io
import os
import sys
import unicodedata

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTCollection, TTFont

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(APP_ROOT, "tool", "fonts_src")
NOTO_TTC_DIR = "/usr/share/fonts/opentype/noto"
OUT_DIR = os.path.join(APP_ROOT, "assets", "fonts")

MAIN_FONTS = {
    "Regular": "BIZUDPGothic-Regular.ttf",
    "Bold": "BIZUDPGothic-Bold.ttf",
}
FALLBACK_FONTS = {
    "Regular": "NotoSansCJK-Regular.ttc",
    "Bold": "NotoSansCJK-Bold.ttc",
}

# データに無くても必ず収録する基本レンジ
BASE_RANGES = [
    (0x0020, 0x007E),  # ASCII
    (0x00A1, 0x00FF),  # Latin-1 補助
    (0x2000, 0x206F),  # 一般句読点(…‥“”など)
    (0x3000, 0x303F),  # CJK記号(、。「」など)
    (0x3041, 0x309F),  # ひらがな
    (0x30A0, 0x30FF),  # カタカナ
    (0xFF00, 0xFFEF),  # 全角英数・半角カナ
]


def collect_chars():
    chars = set()
    patterns = [
        os.path.join(APP_ROOT, "assets", "data", "**", "*.json"),
        os.path.join(APP_ROOT, "lib", "**", "*.dart"),
    ]
    for pattern in patterns:
        for path in glob.glob(pattern, recursive=True):
            with open(path, encoding="utf-8") as f:
                chars.update(f.read())
    for lo, hi in BASE_RANGES:
        chars.update(chr(cp) for cp in range(lo, hi + 1))
    # グリフを持たない制御・書式文字などは対象外
    invisible = {"Cc", "Cf", "Co", "Cn", "Zl", "Zp"}
    return {
        c for c in chars
        if ord(c) >= 0x20 and unicodedata.category(c) not in invisible
    }


def find_noto_jp(ttc_path):
    collection = TTCollection(ttc_path, lazy=True)
    for font in collection.fonts:
        # Regular は "Noto Sans CJK JP"、他は "Noto Sans CJK JP Bold" 等
        family = font["name"].getDebugName(1) or ""
        if family.startswith("Noto Sans CJK JP"):
            return font
    raise SystemExit(f"Noto Sans CJK JP not found in {ttc_path}")


def covered(font, chars):
    cmap = font.getBestCmap()
    return {c for c in chars if ord(c) in cmap}


def write_subset(font, chars, out_name):
    options = Options()
    options.name_IDs = ["*"]  # ライセンス表記等の name テーブルは残す
    subsetter = Subsetter(options)
    subsetter.populate(text="".join(chars))
    subsetter.subset(font)
    out_path = os.path.join(OUT_DIR, out_name)
    # TTC メンバーは直接 save できないためメモリ経由で書き出す
    buf = io.BytesIO()
    font.save(buf)
    with open(out_path, "wb") as f:
        f.write(buf.getvalue())
    print(f"{out_path}: {os.path.getsize(out_path) / 1024:.0f} KB")


def main():
    chars = collect_chars()
    print(f"収録対象: {len(chars)} 字")
    os.makedirs(OUT_DIR, exist_ok=True)

    # 本文フォント。カバレッジは Regular を基準にする(Bold と同一のはず)
    missing = None
    for style, filename in MAIN_FONTS.items():
        font = TTFont(os.path.join(SRC_DIR, filename))
        if missing is None:
            missing = chars - covered(font, chars)
            print(f"BIZ UDPGothic に無い文字: {len(missing)} 字 → Noto へ")
        write_subset(font, chars - missing, f"BIZUDPGothic-{style}.ttf")

    # フォールバック: 本文フォントに無い文字だけ
    for style, ttc_name in FALLBACK_FONTS.items():
        font = find_noto_jp(os.path.join(NOTO_TTC_DIR, ttc_name))
        not_in_noto = missing - covered(font, missing)
        if not_in_noto:
            # 多言語名(アラビア文字等)は現状 UI に表示されないため実害はないが、
            # 表示するようになったら対応フォントの追加が必要
            print(f"注意: Noto にも無い文字(未表示なら実害なし): "
                  f"{''.join(sorted(not_in_noto))}")
        write_subset(font, missing - not_in_noto, f"NotoSansCJKjp-{style}.otf")


if __name__ == "__main__":
    sys.exit(main())
