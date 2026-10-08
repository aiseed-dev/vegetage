#!/usr/bin/env python3
"""web/site/ の公開前チェック: サイト内リンク切れを探す。

/ から始まるリンク(href・src)が web/site/ の中のファイルを指しているかを調べる。
外部リンク(https://…)は調べない。

Usage: python3 web/check_site.py   (リポジトリ直下で。build_all.py の後に)
"""

import re
import sys
from pathlib import Path
from urllib.parse import unquote

SITE = Path(__file__).resolve().parent / "site"


def main() -> int:
    if not (SITE / "index.html").exists():
        print("web/site/ がありません。先に python3 web/build_all.py を流してください。")
        return 1
    broken: dict[str, set[str]] = {}
    pages = list(SITE.rglob("*.html"))
    for page in pages:
        text = page.read_text(encoding="utf-8", errors="ignore")
        here = "/" + str(page.parent.relative_to(SITE)) + "/" if page.parent != SITE else "/"
        for url in re.findall(r'(?:href|src)="([^"#?]+)', text):
            if re.match(r"^(https?:|mailto:|data:|javascript:)", url):
                continue
            path = unquote(url if url.startswith("/") else here + url)
            target = (SITE / path.lstrip("/")).resolve()
            if target.is_file() or (target / "index.html").is_file():
                continue
            broken.setdefault(url, set()).add(str(page.relative_to(SITE)))
    print(f"{len(pages)} ページを確認")
    if not broken:
        print("✓ サイト内のリンク切れはありません")
        return 0
    for url, where in sorted(broken.items()):
        print(f"✗ {url}  ← {', '.join(sorted(where)[:3])}{' ほか' if len(where) > 3 else ''}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
