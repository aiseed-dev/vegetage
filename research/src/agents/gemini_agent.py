"""
Gemini リサーチエージェント

Google Gemini API を使用したバッチ処理向けリサーチシステム。
計画書 3.2 の処理フローにおける「初期収集」「クロスチェック」を担当。

使用方法:
  python -m src.agents.gemini_agent "ピッツァ・マルゲリータ" IT-RCP-PIZ-001 --type recipe
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from google import genai
from google.genai.types import GenerateContentConfig, GoogleSearch, Tool

# .env 読み込み
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

# research_agent から共通部品を再利用
from src.agents.research_agent import (
    PROJECT_ROOT,
    DATA_DIR,
    ResearchAgent,
    _extract_json,
    _vegetable_json_template,
    _recipe_json_template,
)

# ============================================================
# 定数
# ============================================================

GEMINI_MODEL = "gemini-3-pro-preview"

# ============================================================
# システムプロンプト
# ============================================================

VEGETABLE_SYSTEM = """あなたは伝統野菜の専門研究者です。農学、食文化、地域史に精通しています。
イタリアと日本の伝統野菜について、包括的で正確な情報を収集・構造化します。

## 情報源の優先順位
- イタリア野菜: EU公式情報源（EUR-Lex, EC農業DB等）、イタリア政府・自治体サイト、
  イタリア語の専門サイト（.it ドメイン）を最優先で調査
- 日本野菜: Web検索で見つかる情報を幅広く活用（公的機関のDB整備が不十分なため）
- 英語圏の情報は補足として使用

## 重要なルール
- すべての情報に出典URLを必ず付けること（URLのない情報は不採用）
- 出典は「URL」「出典タイプ」「信頼度(high/medium/low)」の3点セットで記載
- 不確かな情報は「要確認」と明記
- 自然農法・有機栽培の観点を含める"""

RECIPE_SYSTEM = """あなたは伝統料理の専門研究者です。食文化、郷土料理、調理技法に精通しています。
イタリアと日本の伝統料理について、包括的で正確な情報を収集・構造化します。
特に、伝統野菜との関連を重視してください。

## 情報源の優先順位
- イタリア料理: EU公式情報源（STG/DOP/IGP認証等）、イタリア政府・自治体サイト、
  イタリア語の専門サイト（.it ドメイン）を最優先で調査
- 日本料理: Web検索で見つかる情報を幅広く活用
- 英語圏の情報は補足として使用

## 重要なルール
- すべての情報に出典URLを必ず付けること（URLのない情報は不採用）
- 出典は「URL」「出典タイプ」「信頼度(high/medium/low)」の3点セットで記載
- 不確かな情報は「要確認」と明記"""


# ============================================================
# Gemini リサーチエージェント
# ============================================================

class GeminiResearchAgent:
    """
    Gemini API を使用したリサーチエージェント

    Google Search (Grounding) を活用して情報収集を行う。
    """

    def __init__(self, model: str = GEMINI_MODEL):
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GOOGLE_API_KEY が未設定です。.env に設定してください。"
            )
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def _generate(
        self,
        prompt: str,
        *,
        system: str = "",
        use_search: bool = True,
    ) -> str:
        """Gemini API 呼び出し"""
        tools = []
        if use_search:
            tools.append(Tool(google_search=GoogleSearch()))

        config = GenerateContentConfig(
            system_instruction=system if system else None,
            tools=tools,
            temperature=0.2,
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )
        return response.text or ""

    # ----------------------------------------------------------
    # 野菜調査
    # ----------------------------------------------------------

    def research_vegetable(
        self,
        name: str,
        entry_id: str,
        language: str = "italian",
    ) -> dict:
        """野菜の調査を実行"""
        lang_name = {"italian": "イタリア", "japanese": "日本"}.get(language, language)

        print(f"\n{'='*60}")
        print(f"  [Gemini] 調査開始: {name} ({entry_id})")
        print(f"{'='*60}\n")

        # Step 1: 基本情報 + 栽培 + 料理・文化を一括収集
        print("[1/2] 情報収集（Google Search Grounding）...")
        research_prompt = f"""「{name}」（{lang_name}の伝統野菜）について、以下のすべてを詳しく調査してください。

## 1. 基本情報
- 正式名称（現地語、日本語、英語、学名）
- 原産地（国、地域、歴史的背景）
- 保護認証（DOP/GI等）の有無

## 2. 特徴
- 外観（形、色、サイズ）
- 味の特徴
- 食感
- 主な栄養素

## 3. 栽培方法
- 播種時期と方法
- 適した土壌条件（pH含む）
- 気候条件
- 主な病害虫と対処法
- 自然農法・有機栽培でのポイント（コンパニオンプランツ等）
- 収穫時期

## 4. 料理・文化
- 代表的な調理用途
- この野菜を使う伝統料理（名前と簡単な説明）
- 文化的・歴史的意義
- 関連する祭事やイベント

イタリアの野菜の場合は、EU公式情報源やイタリア語サイト（.itドメイン）を優先してください。
すべての情報に出典URLを必ず付けてください。出典URLのない情報は不採用とします。
各出典は「参照URL」「出典タイプ」「信頼度(high/medium/low)」を明記してください。"""

        raw_text = self._generate(
            research_prompt,
            system=VEGETABLE_SYSTEM,
            use_search=True,
        )

        # Step 2: JSON構造化
        print("[2/2] データ構造化...")
        template = _vegetable_json_template(entry_id)
        structure_prompt = f"""以下の調査結果を、指定のJSON形式で出力してください。
JSONのみを出力し、それ以外のテキストは含めないでください。

## 必須事項
- sources 配列には、調査で参照した全URLを必ず含めてください。
  各ソースは {{"url": "https://...", "type": "出典タイプ", "reliability": "high/medium/low"}} の形式です。
- sources が空の場合は不合格です。最低3件以上の出典URLを含めてください。
- 不足している情報は「要確認」と記載し、needs_review に追加してください。
- confidence_score は情報の充実度に応じて 0.0-1.0 で設定してください。

{template}

--- 調査結果 ---
{raw_text[:15000]}
"""

        json_text = self._generate(
            structure_prompt,
            system="あなたはデータ構造化の専門家です。調査結果を正確にJSON形式に変換してください。JSONのみを出力してください。",
            use_search=False,
        )

        result = _extract_json(json_text)
        if result is None:
            print("  WARNING: JSON抽出失敗。テキストを保存します。")
            return {"_raw_text": raw_text, "id": entry_id}

        # メタデータ補完
        result.setdefault("metadata", {})
        result["metadata"]["research_method"] = f"Gemini API ({self.model}) + Google Search"
        result["metadata"]["collected_at"] = datetime.now(timezone.utc).isoformat()
        result["metadata"]["agent_version"] = "1.0.0"

        print(f"\n{'='*60}")
        print(f"  [Gemini] 調査完了: {name}")
        print(f"{'='*60}\n")

        return result

    # ----------------------------------------------------------
    # 料理調査
    # ----------------------------------------------------------

    def research_recipe(
        self,
        name: str,
        entry_id: str,
        language: str = "italian",
    ) -> dict:
        """料理の調査を実行"""
        lang_name = {"italian": "イタリア", "japanese": "日本"}.get(language, language)

        print(f"\n{'='*60}")
        print(f"  [Gemini] 調査開始: {name} ({entry_id})")
        print(f"{'='*60}\n")

        print("[1/2] 情報収集（Google Search Grounding）...")
        research_prompt = f"""「{name}」（{lang_name}の伝統料理）について、以下のすべてを詳しく調査してください。

## 1. 基本情報
- 正式名称（現地語、日本語、英語）
- 発祥地域と歴史的背景
- 料理カテゴリ

## 2. 材料
- 伝統的な材料と分量
- 使用する伝統野菜の特定
- 材料の選び方のポイント

## 3. 調理法
- 伝統的な調理手順
- 重要なコツやポイント
- 必要な調理器具

## 4. バリエーション
- 地域バリエーション
- 家庭ごとの違い

## 5. 文化的背景
- 食べ方の作法
- 関連する祭事・季節
- 認証制度（あれば）
- 文化的象徴としての意味

イタリアの料理の場合は、EU公式情報源（STG/DOP/IGP認証等）やイタリア語サイト（.itドメイン）を優先してください。
すべての情報に出典URLを必ず付けてください。出典URLのない情報は不採用とします。
各出典は「参照URL」「出典タイプ」「信頼度(high/medium/low)」を明記してください。"""

        raw_text = self._generate(
            research_prompt,
            system=RECIPE_SYSTEM,
            use_search=True,
        )

        print("[2/2] データ構造化...")
        template = _recipe_json_template(entry_id)
        structure_prompt = f"""以下の調査結果を、指定のJSON形式で出力してください。
JSONのみを出力し、それ以外のテキストは含めないでください。

## 必須事項
- sources 配列には、調査で参照した全URLを必ず含めてください。
  各ソースは {{"url": "https://...", "type": "出典タイプ", "reliability": "high/medium/low"}} の形式です。
- sources が空の場合は不合格です。最低3件以上の出典URLを含めてください。
- 不足している情報は「要確認」と記載し、needs_review に追加してください。
- confidence_score は情報の充実度に応じて 0.0-1.0 で設定してください。

{template}

--- 調査結果 ---
{raw_text[:15000]}
"""

        json_text = self._generate(
            structure_prompt,
            system="あなたはデータ構造化の専門家です。調査結果を正確にJSON形式に変換してください。JSONのみを出力してください。",
            use_search=False,
        )

        result = _extract_json(json_text)
        if result is None:
            print("  WARNING: JSON抽出失敗。テキストを保存します。")
            return {"_raw_text": raw_text, "id": entry_id}

        result.setdefault("metadata", {})
        result["metadata"]["research_method"] = f"Gemini API ({self.model}) + Google Search"
        result["metadata"]["collected_at"] = datetime.now(timezone.utc).isoformat()
        result["metadata"]["agent_version"] = "1.0.0"

        print(f"\n{'='*60}")
        print(f"  [Gemini] 調査完了: {name}")
        print(f"{'='*60}\n")

        return result


# ============================================================
# CLI エントリポイント
# ============================================================

def _run(
    name: str,
    entry_id: str,
    entry_type: Literal["vegetable", "recipe"],
    language: str,
    model: str,
):
    agent = GeminiResearchAgent(model=model)

    if entry_type == "vegetable":
        result = agent.research_vegetable(name, entry_id, language)
    else:
        result = agent.research_recipe(name, entry_id, language)

    path = ResearchAgent.save_entry(result, entry_type, draft_source="gemini")
    print(f"\nDone. Output: {path}")


def main_cli():
    import argparse

    parser = argparse.ArgumentParser(
        description="伝統野菜・料理辞典 Geminiリサーチエージェント"
    )
    parser.add_argument("name", help="調査対象名（例: ピッツァ・マルゲリータ）")
    parser.add_argument("entry_id", help="エントリID（例: IT-RCP-PIZ-001）")
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
        default=GEMINI_MODEL,
        help=f"使用モデル（default: {GEMINI_MODEL}）",
    )
    args = parser.parse_args()

    _run(args.name, args.entry_id, args.type, args.language, args.model)


if __name__ == "__main__":
    main_cli()
