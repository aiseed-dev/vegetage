#!/usr/bin/env python3
"""Gemini画像生成で野菜アイコンを一括作成"""

import mimetypes
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "web" / "italian"
OUT_DIR = ROOT / "web" / "static" / "icons"

load_dotenv(ROOT / ".env")

MODEL = "gemini-3-pro-image-preview"

PROMPT_TEMPLATE = """\
Generate a simple, clean icon illustration of {name} ({latin}).
Style: flat design, minimal, white background, suitable for a web encyclopedia.
The icon should clearly represent the vegetable/plant with vivid but not overwhelming colors.
No text, no labels, no background patterns. Just the plant/vegetable itself.
Size: square, centered composition.
"""


def get_items() -> list[tuple[str, str]]:
    """MDファイルから品目名と学名を取得"""
    items = []
    for md in sorted(SRC_DIR.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        lines = text.split("\n")

        name = md.stem
        latin = ""
        for line in lines:
            # *Cynara cardunculus* — サブタイトル のパターン
            m = re.match(r"^\*(.+?)\*", line)
            if m:
                latin = m.group(1).strip()
                break

        items.append((name, latin))
    return items


MAX_RETRIES = 5
RETRY_DELAYS = [5, 10, 30, 60, 120]  # 秒 (503用)
QUOTA_WAIT = 300  # 秒 (429 RESOURCE_EXHAUSTED用: 5分)
QUOTA_MAX_RETRIES = 3  # 429の最大リトライ回数


def generate_icon(client_holder: list, name: str, latin: str, out_path: Path) -> bool:
    """1品目のアイコンを生成（503/429エラー時リトライ付き）

    client_holder は [client] のリスト。429発生時にクライアントを再作成して差し替える。
    """
    prompt = PROMPT_TEMPLATE.format(name=name, latin=latin)

    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)],
        ),
    ]

    config = types.GenerateContentConfig(
        response_modalities=["IMAGE", "TEXT"],
        image_config=types.ImageConfig(image_size="1K"),
    )

    for attempt in range(MAX_RETRIES):
        try:
            client = client_holder[0]
            for chunk in client.models.generate_content_stream(
                model=MODEL,
                contents=contents,
                config=config,
            ):
                if (
                    chunk.candidates is None
                    or chunk.candidates[0].content is None
                    or chunk.candidates[0].content.parts is None
                ):
                    continue

                for part in chunk.candidates[0].content.parts:
                    if part.inline_data and part.inline_data.data:
                        ext = mimetypes.guess_extension(part.inline_data.mime_type) or ".png"
                        file_path = out_path.with_suffix(ext)
                        file_path.write_bytes(part.inline_data.data)
                        print(f"  ✓ {name} → {file_path.name}")
                        return True
            print(f"  ✗ {name}: 画像なし")
            return False

        except Exception as e:
            err_str = str(e)

            # 429 RESOURCE_EXHAUSTED: クライアント切断→5分待機→再接続
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                quota_attempt = attempt + 1
                if quota_attempt > QUOTA_MAX_RETRIES:
                    print(f"  ✗ {name}: RESOURCE_EXHAUSTED {QUOTA_MAX_RETRIES}回リトライ後も失敗")
                    return False
                print(f"  ⟳ {name}: 429 RESOURCE_EXHAUSTED 検出 ({quota_attempt}/{QUOTA_MAX_RETRIES})")
                print(f"    クライアント切断 → {QUOTA_WAIT}秒 (5分) 待機後に再接続...")
                # クライアント参照を解放
                client_holder[0] = None
                time.sleep(QUOTA_WAIT)
                # 新しいクライアントで再接続
                client_holder[0] = make_client()
                print(f"    再接続完了。{name} をリトライします。")
                continue

            # 503 overloaded: 短い待機でリトライ
            if "503" in err_str or "overloaded" in err_str.lower():
                delay = RETRY_DELAYS[attempt]
                print(f"  ⟳ {name}: 503エラー、{delay}秒後にリトライ ({attempt + 1}/{MAX_RETRIES})")
                time.sleep(delay)
                continue

            print(f"  ✗ {name}: {e}")
            return False

    print(f"  ✗ {name}: {MAX_RETRIES}回リトライ後も失敗")
    return False


def make_client() -> genai.Client:
    """Vertex AI優先、フォールバックでGemini APIキーを使用"""
    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GOOGLE_API_KEY")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")

    if project:
        print(f"Vertex AI API ({project} / {location})\n")
        return genai.Client(
            vertexai=True,
            project=project,
            location=location,
        )

    api_key = os.environ.get("GOOGLE_API_KEY")
    if api_key:
        print("Gemini API (APIキー)\n")
        return genai.Client(api_key=api_key)

    print("認証情報が見つかりません。以下のいずれかを設定してください:")
    print("  Vertex AI: GOOGLE_CLOUD_PROJECT (+ gcloud auth application-default login)")
    print("  Gemini:    GOOGLE_API_KEY")
    sys.exit(1)


def main():
    client_holder = [make_client()]

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    items = get_items()
    print(f"アイコン生成: {len(items)} 品目\n")

    # --only オプションで特定品目のみ生成
    only = None
    if "--only" in sys.argv:
        idx = sys.argv.index("--only")
        if idx + 1 < len(sys.argv):
            only = sys.argv[idx + 1].split(",")

    success = 0
    skip = 0
    fail = 0

    for name, latin in items:
        if only and name not in only:
            continue

        out_path = OUT_DIR / f"{name}.png"

        # 既存ファイルはスキップ (--force で上書き)
        if out_path.exists() and "--force" not in sys.argv:
            print(f"  - {name}: 既に存在 (--force で上書き)")
            skip += 1
            continue

        if generate_icon(client_holder, name, latin, out_path):
            success += 1
        else:
            fail += 1

        # レート制限対策
        time.sleep(5)

    print(f"\n完了: 成功 {success}, スキップ {skip}, 失敗 {fail}")


if __name__ == "__main__":
    main()
