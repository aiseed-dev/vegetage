"""extracted_varieties.csv の認証主張を、正典索引(canon-search)と照合する。

計画書v3の「辞典には正解器が無い」への回答: DOP/IGP などの登録事実は
正典(disciplinare・公式登録簿)との照合で機械的に検証できる。
照合できなかった行は「未収録」として明示する(暗黙に検証済み扱いしない)。

使い方:
  CANON_DB=../apps/canon-search/data/vegitage.db python3 src/verify_certifications.py
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "apps" / "canon-search" / "src"))

from canon_search.store import Store  # noqa: E402

CSV = ROOT / "data" / "extracted_varieties.csv"
DB = os.environ.get(
    "CANON_DB", str(ROOT.parent / "apps" / "canon-search" / "data" / "vegitage.db"))


def main() -> None:
    store = Store(DB)
    rows = list(csv.DictReader(CSV.open()))
    corroborated, contradicted, uncovered = [], [], []

    for row in rows:
        name = (row.get("name_it") or "").strip().rstrip("()").strip()
        cert = (row.get("certification") or "").strip()
        if not name:
            continue
        hits = store.search(name, k=3)
        if not hits:
            uncovered.append((name, cert))
            continue
        if not cert:
            corroborated.append((name, cert, hits[0]))
            continue
        cert_head = cert.split()[0]  # "DOP", "IGP", "Slow" ...
        joined = " ".join(h["title"] + " " + h["text"] for h in hits)
        if cert_head.lower() in joined.lower():
            corroborated.append((name, cert, hits[0]))
        else:
            contradicted.append((name, cert, hits[0]))

    total = len(rows)
    print(f"品種 {total} 行を照合 — 裏取りあり {len(corroborated)}"
          f" / 要確認 {len(contradicted)} / 正典未収録 {len(uncovered)}\n")

    for name, cert, hit in corroborated:
        print(f"✔ {name} [{cert}]")
        print(f"   ← {hit['title']}")
        print(f"     {hit['url']}")
    for name, cert, hit in contradicted:
        print(f"✘ {name} [{cert}] — 正典に記載はあるが認証表記が確認できず")
        print(f"   ← {hit['title']}")
    print(f"\n未収録 {len(uncovered)} 件(先頭10件): "
          + ", ".join(n for n, _ in uncovered[:10]))
    print("\n※「未収録」は誤りではなく、正典コーパスの未整備を意味する。"
          "disciplinare / 公式登録簿の索引を増やせば照合率が上がる。")


if __name__ == "__main__":
    main()
