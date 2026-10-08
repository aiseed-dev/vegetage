"""
伝統野菜・料理辞典 リサーチエージェント

Claude Agent SDK (claude-code-sdk) を使用した自律的リサーチシステム。
Phase 1: サンマルツァーノトマトの完全調査で検証済み。

処理フロー（計画書 3.2 準拠）:
  1. 基本情報収集 (Stateless query)
  2. 栽培情報の深堀り (Stateful conversation)
  3. 料理・文化情報の調査 (Stateful conversation)
  4. 構造化・検証 (Final structuring)
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from claude_code_sdk import (
    ClaudeCodeOptions,
    Message,
    ResultMessage,
    AssistantMessage,
    TextBlock,
    query,
)

# ============================================================
# 定数
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# ============================================================
# システムプロンプト
# ============================================================

VEGETABLE_RESEARCH_PROMPT = """あなたは伝統野菜の専門研究者です。農学、食文化、地域史に精通しています。

## あなたの役割
イタリアと日本の伝統野菜について、包括的で正確な情報を収集・構造化します。

## 調査の進め方
1. まず基本情報（名称、学名、原産地）を確認
2. 次に栽培方法、病害虫、自然農法での育て方を調査
3. その野菜を使った伝統料理を調査
4. 文化的背景、祭事、歴史的逸話を調査
5. 複数ソースで情報をクロスチェック

## 情報源の優先順位
- イタリア野菜の場合: EU公式情報源（EUR-Lex, EC農業DB等）、イタリア政府・自治体サイト、
  イタリア語の専門サイト（.it ドメイン）を最優先で調査すること
- 日本野菜の場合: Web検索で見つかる情報を幅広く活用（公的機関のDB整備が不十分なため）
- 英語圏の情報は補足として使用

## 重要なルール
- すべての情報に出典URLを必ず付けてください（URLのない情報は不採用）
- 不確かな情報は「要確認」と明記してください
- イタリア語/日本語のサイトも直接調査してください
- 自然農法・有機栽培の観点を含めてください
- 最終出力は必ず有効なJSONで返してください
"""

RECIPE_RESEARCH_PROMPT = """あなたは伝統料理の専門研究者です。食文化、郷土料理、調理技法に精通しています。

## あなたの役割
イタリアと日本の伝統料理について、包括的で正確な情報を収集・構造化します。
特に、伝統野菜との関連を重視してください。

## 調査の進め方
1. 料理の基本情報（名称、発祥地、歴史）を確認
2. 伝統的な材料と調理法を詳細に調査
3. 使用する伝統野菜を特定
4. 地域バリエーション、家庭ごとの違いを調査
5. 文化的背景、食べ方の作法を調査

## 情報源の優先順位
- イタリア料理の場合: EU公式情報源（STG/DOP/IGP認証等）、イタリア政府・自治体サイト、
  イタリア語の専門サイト（.it ドメイン）を最優先で調査すること
- 日本料理の場合: Web検索で見つかる情報を幅広く活用
- 英語圏の情報は補足として使用

## 重要なルール
- すべての情報に出典URLを必ず付けてください（URLのない情報は不採用）
- 伝統野菜を使う場合は必ず野菜IDとの関連を記載
- 地域による違いを明記してください
- 最終出力は必ず有効なJSONで返してください
"""


def _vegetable_json_template(entry_id: str) -> str:
    return f"""
出力は以下のJSON構造に従ってください:
{{
  "id": "{entry_id}",
  "names": {{
    "local": "現地語名",
    "japanese": "日本語名",
    "english": "英語名",
    "scientific": "学名"
  }},
  "classification": {{
    "items": ["品目1", "品目2"],
    "sub_items": ["細品目1", "細品目2"],
    "variety": "品種名",
    "species": "学名（種レベル）"
  }},
  "origin": {{
    "country": "国名",
    "region": "地域名",
    "history": "歴史的背景（200-400文字）"
  }},
  "characteristics": {{
    "appearance": {{ "shape": "...", "color": "...", "size": "..." }},
    "taste": {{ "description": "...", "notes": "..." }},
    "texture": {{ "flesh": "...", "seeds": "...", "skin": "..." }},
    "nutrition": {{ "栄養素名": "含有量" }}
  }},
  "cultivation": {{
    "sowing_period": "播種期",
    "harvest_period": "収穫期",
    "soil_requirements": {{ "type": "...", "ph": "..." }},
    "climate": {{ "ideal": "..." }},
    "pests_diseases": ["病害虫1", "病害虫2"],
    "natural_farming_tips": {{ "companion_planting": "...", "notes": "..." }}
  }},
  "culinary_uses": {{
    "best_for": ["用途1", "用途2"],
    "why_suitable": {{ "理由キー": "説明" }}
  }},
  "related_recipes": [
    {{ "id": "XX-RCP-XXX-001", "name": "料理名", "relationship": "関連の説明" }}
  ],
  "cultural_significance": {{ "説明キー": "内容" }},
  "sources": [
    {{ "url": "https://...", "type": "出典タイプ", "reliability": "high/medium/low" }}
  ],
  "metadata": {{
    "collected_at": "{datetime.now(timezone.utc).isoformat()}",
    "agent_version": "1.0.0",
    "research_method": "Claude Agent SDK WebSearch",
    "confidence_score": 0.85,
    "languages_searched": ["english", "japanese", "italian"],
    "needs_review": []
  }}
}}
"""


def _recipe_json_template(entry_id: str) -> str:
    return f"""
出力は以下のJSON構造に従ってください:
{{
  "id": "{entry_id}",
  "names": {{
    "local": "現地語名",
    "japanese": "日本語名",
    "english": "英語名"
  }},
  "origin": {{
    "country": "国名",
    "region": "地域名",
    "history": "歴史的背景"
  }},
  "category": "料理カテゴリ",
  "ingredients": [
    {{ "name": "材料名", "amount": "分量", "is_traditional_vegetable": false, "vegetable_id": null }}
  ],
  "traditional_method": {{
    "steps": ["手順1", "手順2"]
  }},
  "variations": [
    {{ "name": "バリエーション名", "description": "説明" }}
  ],
  "cultural_context": {{
    "eating_style": "...",
    "symbolism": "..."
  }},
  "related_vegetables": [
    {{ "id": "XX-VEG-XXX-001", "name": "野菜名", "role": "役割" }}
  ],
  "sources": [
    {{ "url": "https://...", "type": "出典タイプ", "reliability": "high/medium/low" }}
  ],
  "metadata": {{
    "collected_at": "{datetime.now(timezone.utc).isoformat()}",
    "agent_version": "1.0.0",
    "research_method": "Claude Agent SDK WebSearch",
    "confidence_score": 0.85,
    "needs_review": []
  }}
}}
"""


# ============================================================
# ヘルパー関数
# ============================================================

def _extract_text(messages: list[Message]) -> str:
    """メッセージリストからテキストを抽出"""
    parts: list[str] = []
    for msg in messages:
        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    parts.append(block.text)
        elif isinstance(msg, ResultMessage):
            if msg.result:
                parts.append(msg.result)
    return "\n".join(parts)


def _extract_json(text: str) -> dict | None:
    """テキストからJSONブロックを抽出してパース"""
    import re

    # 1. ```json ... ``` ブロックを探す
    pattern = re.compile(r"```json\s*\n?(.*?)\n?\s*```", re.DOTALL)
    match = pattern.search(text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 2. ``` ... ``` ブロック（json指定なし）
    pattern2 = re.compile(r"```\s*\n?(.*?)\n?\s*```", re.DOTALL)
    for m in pattern2.finditer(text):
        candidate = m.group(1).strip()
        if candidate.startswith("{"):
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue

    # 3. ブレース対応で最外のJSONオブジェクトを探す
    brace_start = text.find("{")
    if brace_start == -1:
        return None

    depth = 0
    in_string = False
    escape_next = False
    for i in range(brace_start, len(text)):
        c = text[i]
        if escape_next:
            escape_next = False
            continue
        if c == "\\":
            escape_next = True
            continue
        if c == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[brace_start : i + 1])
                except json.JSONDecodeError:
                    return None

    return None


# ============================================================
# リサーチエージェント
# ============================================================

class ResearchAgent:
    """
    Claude Agent SDK を使用したリサーチエージェント

    query() で単発リサーチ、ClaudeSDKClient でマルチターン深堀りを行う。
    """

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.model = model

    # ----------------------------------------------------------
    # 野菜調査
    # ----------------------------------------------------------

    async def research_vegetable(
        self,
        name: str,
        entry_id: str,
        language: str = "italian",
    ) -> dict:
        """野菜の完全調査を実行（計画書 Phase 1 フロー）"""

        print(f"\n{'='*60}")
        print(f"  調査開始: {name} ({entry_id})")
        print(f"{'='*60}\n")

        # Phase 1: 基本情報収集 (Stateless)
        print("[1/4] 基本情報収集...")
        basic_info = await self._query_basic_info(name, entry_id, language)
        print(f"  → {len(basic_info)} 文字取得")

        # Phase 2-3: 栽培 + 料理・文化の深堀り
        print("[2/4] 栽培情報の深堀り...")
        print("[3/4] 料理・文化情報の調査...")
        detailed_info = await self._deep_research_vegetable(name, entry_id, basic_info)
        print(f"  → {len(detailed_info)} 文字取得")

        # raw text を保存（デバッグ・再構造化用）
        self._save_raw_text(entry_id, "vegetable", {
            "basic_info": basic_info,
            "detailed_info": detailed_info,
        })

        # Phase 4: 構造化・検証
        print("[4/4] データ構造化・検証...")
        final = await self._finalize_vegetable(name, entry_id, detailed_info)

        print(f"\n{'='*60}")
        print(f"  調査完了: {name}")
        print(f"{'='*60}\n")

        return final

    async def _query_basic_info(
        self, name: str, entry_id: str, language: str
    ) -> str:
        """基本情報収集 — Stateless query"""
        lang_name = {"italian": "イタリア", "japanese": "日本"}.get(language, language)

        prompt = f"""「{name}」（{lang_name}の伝統野菜）について基本情報を調査してください。

以下の情報を収集してください:
1. 正式名称（現地語、日本語、英語、学名）
2. 原産地（国、地域、なぜそこで生まれたか）
3. 外観の特徴（形、色、サイズ）
4. 味の特徴
5. 主な栄養素
6. 保護認証（DOP/GI等）の有無

出典URLを必ず含めてください。"""

        messages: list[Message] = []
        async for msg in query(
            prompt=prompt,
            options=ClaudeCodeOptions(
                model=self.model,
                system_prompt=VEGETABLE_RESEARCH_PROMPT,
                allowed_tools=["WebSearch"],
                permission_mode="bypassPermissions",
                max_turns=3,
            ),
        ):
            messages.append(msg)

        return _extract_text(messages)

    async def _deep_research_vegetable(
        self, name: str, entry_id: str, basic_context: str
    ) -> str:
        """栽培 + 料理・文化の深堀り — コンテキスト引き継ぎで連続 query"""

        # ターン1: 栽培情報
        cultivation_prompt = f"""これまでの基本調査結果:
{basic_context[:3000]}

上記を踏まえて「{name}」の栽培方法を深堀りしてください:
1. 播種時期と方法
2. 適した土壌条件
3. 主な病害虫と対処法
4. 自然農法・有機栽培でのポイント
5. 収穫時期と方法

出典URLを必ず含めてください。"""

        cultivation_msgs: list[Message] = []
        async for msg in query(
            prompt=cultivation_prompt,
            options=ClaudeCodeOptions(
                model=self.model,
                system_prompt=VEGETABLE_RESEARCH_PROMPT,
                allowed_tools=["WebSearch"],
                permission_mode="bypassPermissions",
                max_turns=3,
            ),
        ):
            cultivation_msgs.append(msg)

        cultivation_text = _extract_text(cultivation_msgs)

        # ターン2: 料理・文化
        culinary_prompt = f"""これまでの調査結果:
{basic_context[:1500]}
{cultivation_text[:1500]}

次に「{name}」の料理・文化面を調査してください:
1. 代表的な調理用途
2. この野菜を使う伝統料理
3. なぜこの野菜が料理に適しているか
4. 文化的・歴史的意義
5. 関連する祭事やイベント

出典URLを必ず含めてください。"""

        culinary_msgs: list[Message] = []
        async for msg in query(
            prompt=culinary_prompt,
            options=ClaudeCodeOptions(
                model=self.model,
                system_prompt=VEGETABLE_RESEARCH_PROMPT,
                allowed_tools=["WebSearch"],
                permission_mode="bypassPermissions",
                max_turns=3,
            ),
        ):
            culinary_msgs.append(msg)

        culinary_text = _extract_text(culinary_msgs)

        return "\n\n".join([cultivation_text, culinary_text])

    async def _finalize_vegetable(
        self, name: str, entry_id: str, research_text: str
    ) -> dict:
        """収集データの最終構造化"""
        template = _vegetable_json_template(entry_id)

        prompt = f"""以下は「{name}」に関する調査結果です。
この情報を整理して、指定のJSON形式で出力してください。
JSONのみを出力してください。説明文やマークダウンは不要です。

不足している情報は「要確認」と記載し、needs_review に追加してください。
confidence_score は情報の充実度に応じて 0.0-1.0 で設定してください。

{template}

--- 調査結果 ---
{research_text[:8000]}
"""

        messages: list[Message] = []
        async for msg in query(
            prompt=prompt,
            options=ClaudeCodeOptions(
                model=self.model,
                system_prompt="あなたはデータ構造化の専門家です。調査結果を正確にJSON形式に変換してください。JSON以外のテキストは一切出力しないでください。",
                permission_mode="bypassPermissions",
                max_turns=3,
            ),
        ):
            messages.append(msg)

        # デバッグ: メッセージ型を表示
        print(f"  構造化レスポンス: {len(messages)} メッセージ")
        for i, msg in enumerate(messages):
            print(f"    [{i}] {type(msg).__name__}", end="")
            if isinstance(msg, ResultMessage):
                print(f" (result={len(msg.result or '')} chars, is_error={msg.is_error})")
            elif isinstance(msg, AssistantMessage):
                print(f" (blocks={len(msg.content)})")
            else:
                print()

        text = _extract_text(messages)
        result = _extract_json(text)

        if result is None:
            print("  WARNING: JSON抽出失敗。テキストを保存します。")
            print(f"  抽出テキスト長: {len(text)} 文字")
            if text:
                print(f"  先頭200文字: {text[:200]}")
            return {"_raw_text": text, "id": entry_id}

        return result

    # ----------------------------------------------------------
    # 料理調査
    # ----------------------------------------------------------

    async def research_recipe(
        self,
        name: str,
        entry_id: str,
        language: str = "italian",
    ) -> dict:
        """料理の完全調査を実行"""

        print(f"\n{'='*60}")
        print(f"  調査開始: {name} ({entry_id})")
        print(f"{'='*60}\n")

        print("[1/3] 基本情報・材料・調理法の収集...")
        basic_info = await self._query_recipe_basic(name, entry_id, language)
        print(f"  → {len(basic_info)} 文字取得")

        print("[2/3] 文化的背景・バリエーションの深堀り...")
        detailed_info = await self._deep_research_recipe(name, entry_id, basic_info)
        print(f"  → {len(detailed_info)} 文字取得")

        # raw text を保存（デバッグ・再構造化用）
        self._save_raw_text(entry_id, "recipe", {
            "basic_info": basic_info,
            "detailed_info": detailed_info,
        })

        print("[3/3] データ構造化・検証...")
        final = await self._finalize_recipe(name, entry_id, detailed_info)

        print(f"\n{'='*60}")
        print(f"  調査完了: {name}")
        print(f"{'='*60}\n")

        return final

    async def _query_recipe_basic(
        self, name: str, entry_id: str, language: str
    ) -> str:
        """料理の基本情報収集"""
        lang_name = {"italian": "イタリア", "japanese": "日本"}.get(language, language)

        prompt = f"""「{name}」（{lang_name}の伝統料理）について調査してください。

1. 正式名称（現地語、日本語、英語）
2. 発祥地域と歴史
3. 伝統的な材料と分量
4. 伝統的な調理法・手順
5. 使用する伝統野菜の特定

出典URLを必ず含めてください。"""

        messages: list[Message] = []
        async for msg in query(
            prompt=prompt,
            options=ClaudeCodeOptions(
                model=self.model,
                system_prompt=RECIPE_RESEARCH_PROMPT,
                allowed_tools=["WebSearch"],
                permission_mode="bypassPermissions",
                max_turns=3,
            ),
        ):
            messages.append(msg)

        return _extract_text(messages)

    async def _deep_research_recipe(
        self, name: str, entry_id: str, basic_context: str
    ) -> str:
        """料理の深堀り調査 — コンテキスト引き継ぎで query"""

        deep_prompt = f"""これまでの調査結果:
{basic_context[:3000]}

上記を踏まえて「{name}」について深堀りしてください:
1. 地域バリエーション
2. 家庭ごとの違い
3. 食べ方の作法・マナー
4. 関連する祭事・季節行事
5. 認証制度（あれば）

出典URLを必ず含めてください。"""

        messages: list[Message] = []
        async for msg in query(
            prompt=deep_prompt,
            options=ClaudeCodeOptions(
                model=self.model,
                system_prompt=RECIPE_RESEARCH_PROMPT,
                allowed_tools=["WebSearch"],
                permission_mode="bypassPermissions",
                max_turns=3,
            ),
        ):
            messages.append(msg)

        deep_text = _extract_text(messages)
        return basic_context + "\n\n" + deep_text

    async def _finalize_recipe(
        self, name: str, entry_id: str, research_text: str
    ) -> dict:
        """料理データの最終構造化"""
        template = _recipe_json_template(entry_id)

        prompt = f"""以下は「{name}」に関する調査結果です。
この情報を整理して、指定のJSON形式で出力してください。
JSONのみを出力してください。説明文やマークダウンは不要です。

{template}

--- 調査結果 ---
{research_text[:8000]}
"""

        messages: list[Message] = []
        async for msg in query(
            prompt=prompt,
            options=ClaudeCodeOptions(
                model=self.model,
                system_prompt="あなたはデータ構造化の専門家です。調査結果を正確にJSON形式に変換してください。JSON以外のテキストは一切出力しないでください。",
                permission_mode="bypassPermissions",
                max_turns=3,
            ),
        ):
            messages.append(msg)

        # デバッグ: メッセージ型を表示
        print(f"  構造化レスポンス: {len(messages)} メッセージ")
        for i, msg in enumerate(messages):
            print(f"    [{i}] {type(msg).__name__}", end="")
            if isinstance(msg, ResultMessage):
                print(f" (result={len(msg.result or '')} chars, is_error={msg.is_error})")
            elif isinstance(msg, AssistantMessage):
                print(f" (blocks={len(msg.content)})")
            else:
                print()

        text = _extract_text(messages)
        result = _extract_json(text)

        if result is None:
            print("  WARNING: JSON抽出失敗。テキストを保存します。")
            print(f"  抽出テキスト長: {len(text)} 文字")
            if text:
                print(f"  先頭200文字: {text[:200]}")
            return {"_raw_text": text, "id": entry_id}

        return result

    # ----------------------------------------------------------
    # データ保存
    # ----------------------------------------------------------

    @staticmethod
    def _save_raw_text(
        entry_id: str,
        entry_type: str,
        phases: dict[str, str],
    ) -> Path:
        """各フェーズのraw textをデバッグ用に保存"""
        raw_dir = PROJECT_ROOT / "drafts" / "claude" / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)

        out_path = raw_dir / f"{entry_id}_{entry_type}_raw.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(
                {"id": entry_id, "type": entry_type, "phases": phases},
                f,
                ensure_ascii=False,
                indent=2,
            )
        print(f"  Raw text saved: {out_path.relative_to(PROJECT_ROOT)}")
        return out_path

    @staticmethod
    def save_entry(
        data: dict,
        entry_type: Literal["vegetable", "recipe"],
        *,
        draft_source: str | None = None,
        item_dir: str | None = None,
    ) -> Path:
        """調査結果をJSONファイルとして保存

        Args:
            data: エントリデータ
            entry_type: "vegetable" or "recipe"
            draft_source: AI名を指定すると drafts/{ai名}/ に保存。
                          None の場合は data/ に直接保存（確定版）。
            item_dir: 品目ディレクトリ名（例: "tomato", "garlic"）。
                      指定すると vegetables/{item_dir}/ 以下に保存。
        """
        subdir = "vegetables" if entry_type == "vegetable" else "recipes"

        if draft_source:
            out_dir = PROJECT_ROOT / "drafts" / draft_source / subdir
        else:
            out_dir = DATA_DIR / subdir

        # 品目ディレクトリが指定されていれば配下に保存
        if item_dir:
            out_dir = out_dir / item_dir

        out_dir.mkdir(parents=True, exist_ok=True)

        entry_id = data.get("id", "UNKNOWN")
        name_en = data.get("names", {}).get("english", "unknown")
        filename = f"{name_en.lower().replace(' ', '_')}_{entry_id}.json"

        out_path = out_dir / filename
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"  Saved: {out_path.relative_to(PROJECT_ROOT)}")
        return out_path


# ============================================================
# CLI エントリポイント
# ============================================================

async def _run(
    name: str,
    entry_id: str,
    entry_type: Literal["vegetable", "recipe"],
    language: str,
    model: str,
):
    agent = ResearchAgent(model=model)

    if entry_type == "vegetable":
        result = await agent.research_vegetable(name, entry_id, language)
    else:
        result = await agent.research_recipe(name, entry_id, language)

    path = agent.save_entry(result, entry_type, draft_source="claude")
    print(f"\nDone. Output: {path}")


def main_cli():
    import argparse

    parser = argparse.ArgumentParser(
        description="伝統野菜・料理辞典 リサーチエージェント"
    )
    parser.add_argument("name", help="調査対象名（例: サンマルツァーノトマト）")
    parser.add_argument("entry_id", help="エントリID（例: IT-VEG-TOM-001）")
    parser.add_argument(
        "--type",
        choices=["vegetable", "recipe"],
        default="vegetable",
        help="エントリタイプ（default: vegetable）",
    )
    parser.add_argument(
        "--language",
        choices=["italian", "japanese"],
        default="italian",
        help="主要調査言語（default: italian）",
    )
    parser.add_argument(
        "--model",
        default="claude-sonnet-4-20250514",
        help="使用モデル（default: claude-sonnet-4-20250514）",
    )
    args = parser.parse_args()

    asyncio.run(_run(args.name, args.entry_id, args.type, args.language, args.model))


if __name__ == "__main__":
    main_cli()
