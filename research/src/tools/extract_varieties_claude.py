#!/usr/bin/env python3
"""Claude Agent SDKで栽培ガイドMDファイルから品種データを抽出するスクリプト

使い方:
  pip install claude-agent-sdk
  python src/tools/extract_varieties_claude.py
  python src/tools/extract_varieties_claude.py --only オリーブ,ブドウ,メロン
  python src/tools/extract_varieties_claude.py --src web/italian/cuisine
"""

import asyncio
import csv
import json
import sys
from pathlib import Path

from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage, TextBlock

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SRC_DIR = ROOT / "web" / "italian" / "cultivation"
OUT_FILE = ROOT / "data" / "extracted_varieties_claude.csv"

SYSTEM_PROMPT = """\
あなたはイタリア伝統野菜の品種データベース作成を支援するアシスタントです。
与えられたMarkdown文書から、具体的な品種名（cultivar / variety / landrace）を
すべて抽出してください。

抽出ルール:
- 品種名、品種のイタリア語名、認証（DOP/IGP/PAT/De.Co./Slow Food Presidio）、産地を抽出
- 一般的な栽培方法や説明文は不要。具体的な品種名のみ
- 表の中の品種も抽出すること
- テキスト中に埋め込まれた品種名も抽出すること
- 品種グループや一般名称（例:「チェリートマト」）ではなく、固有の品種名を抽出
- 日本の品種（桃太郎、千両ナスなど）は除外
- 品種が見つからない場合は空配列を返すこと
"""

# 構造化出力スキーマ
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "varieties": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name_ja": {
                        "type": "string",
                        "description": "品種の日本語名"
                    },
                    "name_it": {
                        "type": "string",
                        "description": "品種のイタリア語名"
                    },
                    "region": {
                        "type": "string",
                        "description": "産地・地域名"
                    },
                    "certification": {
                        "type": "string",
                        "description": "認証（DOP/IGP/PAT/De.Co./Slow Food Presidio、なければ空文字）"
                    }
                },
                "required": ["name_ja", "name_it", "region", "certification"],
                "additionalProperties": False
            }
        }
    },
    "required": ["varieties"],
    "additionalProperties": False
}


async def extract_from_file(filepath: Path) -> list[dict]:
    """Claude Agent SDKで1ファイルから品種を抽出"""
    text = filepath.read_text(encoding="utf-8")
    veg_name = filepath.stem

    # 長すぎる場合は先頭部分（品種カタログ部分）を優先
    if len(text) > 15000:
        text = text[:15000]

    prompt = f"以下は「{veg_name}」の栽培ガイドです。この文書から品種データを抽出してください。\n\n{text}"

    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        model="haiku",
        max_turns=1,
        output_format={
            "type": "json_schema",
            "schema": OUTPUT_SCHEMA,
        },
    )

    result_text = ""
    try:
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        result_text += block.text
            elif isinstance(message, ResultMessage):
                if message.structured_output:
                    data = message.structured_output
                    if isinstance(data, str):
                        data = json.loads(data)
                    varieties = data.get("varieties", [])
                    for v in varieties:
                        v["item"] = veg_name
                    return varieties

        # structured_output がない場合、テキストからパース
        if result_text:
            data = json.loads(result_text)
            varieties = data.get("varieties", [])
            for v in varieties:
                v["item"] = veg_name
            return varieties

    except Exception as e:
        print(f"\n    エラー: {e}")

    return []


async def main():
    # --src オプション
    src_dir = DEFAULT_SRC_DIR
    if "--src" in sys.argv:
        idx = sys.argv.index("--src")
        if idx + 1 < len(sys.argv):
            src_dir = ROOT / sys.argv[idx + 1]

    md_files = sorted(src_dir.glob("*.md"))
    print(f"ソース: {src_dir}")
    print(f"ファイル数: {len(md_files)}\n")

    # --only オプション
    only = None
    if "--only" in sys.argv:
        idx = sys.argv.index("--only")
        if idx + 1 < len(sys.argv):
            only = sys.argv[idx + 1].split(",")

    all_varieties = []

    for md in md_files:
        if only and md.stem not in only:
            continue

        print(f"  {md.stem}...", end=" ", flush=True)
        varieties = await extract_from_file(md)

        if varieties:
            print(f"{len(varieties)} 品種")
            all_varieties.extend(varieties)
        else:
            print("品種なし")

    # CSV出力
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["name_ja", "name_it", "item", "region", "certification"]
        )
        writer.writeheader()
        for v in all_varieties:
            writer.writerow({
                "name_ja": v.get("name_ja", ""),
                "name_it": v.get("name_it", ""),
                "item": v.get("item", ""),
                "region": v.get("region", ""),
                "certification": v.get("certification", ""),
            })

    print(f"\n合計: {len(all_varieties)} 品種")
    print(f"出力: {OUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
