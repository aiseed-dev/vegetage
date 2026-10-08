"""
Gemini バッチ処理ランナー

マスターリスト (CSV) を読み込み、Gemini API で全品目を順次処理する。
レート制限、リトライ、レジューム（途中再開）に対応。

使用方法:
  python -m src.agents.batch_runner data/master_lists/italian_vegetables.csv --type vegetable
  python -m src.agents.batch_runner data/master_lists/italian_recipes.csv --type recipe

オプション:
  --resume          処理済みをスキップして続行（デフォルト: 有効）
  --no-resume       最初からやり直す
  --limit N         最大N件処理して停止
  --delay SECONDS   API呼び出し間隔（デフォルト: 4秒）
  --language LANG   言語（italian/japanese, デフォルト: italian）
"""

from __future__ import annotations

import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from src.agents.gemini_agent import GeminiResearchAgent
from src.agents.research_agent import ResearchAgent, PROJECT_ROOT

# ============================================================
# 進捗管理
# ============================================================

PROGRESS_DIR = PROJECT_ROOT / "data" / "progress"


def _load_progress(csv_path: Path) -> dict:
    """進捗ファイルを読み込む"""
    progress_file = PROGRESS_DIR / f"{csv_path.stem}_progress.json"
    if progress_file.exists():
        with open(progress_file, encoding="utf-8") as f:
            return json.load(f)
    return {"completed": [], "failed": [], "started_at": None, "last_updated": None}


def _save_progress(csv_path: Path, progress: dict):
    """進捗ファイルを保存"""
    PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
    progress_file = PROGRESS_DIR / f"{csv_path.stem}_progress.json"
    progress["last_updated"] = datetime.now(timezone.utc).isoformat()
    with open(progress_file, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


# ============================================================
# バッチ処理
# ============================================================

def run_batch(
    csv_path: Path,
    entry_type: Literal["vegetable", "recipe"],
    *,
    language: str = "italian",
    resume: bool = True,
    limit: int | None = None,
    delay: float = 4.0,
    model: str | None = None,
):
    """マスターリストのバッチ処理を実行"""

    # CSV 読み込み
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        items = list(reader)

    total = len(items)
    print(f"\n{'='*60}")
    print(f"  バッチ処理開始")
    print(f"  リスト: {csv_path.name}")
    print(f"  タイプ: {entry_type}")
    print(f"  合計: {total} 件")
    print(f"  API間隔: {delay} 秒")
    if limit:
        print(f"  処理上限: {limit} 件")
    print(f"{'='*60}\n")

    # 進捗読み込み
    progress = _load_progress(csv_path)
    if not progress["started_at"]:
        progress["started_at"] = datetime.now(timezone.utc).isoformat()

    completed_ids = set(progress["completed"])
    failed_ids = set(progress["failed"])

    if resume and completed_ids:
        print(f"  レジューム: {len(completed_ids)} 件処理済み, {len(failed_ids)} 件失敗")

    # エージェント初期化
    agent = GeminiResearchAgent(model=model) if model else GeminiResearchAgent()

    processed = 0
    succeeded = 0
    errors = 0

    for idx, item in enumerate(items):
        entry_id = item.get("entry_id", "")

        # レジューム: 処理済みスキップ
        if resume and entry_id in completed_ids:
            continue

        # 処理上限チェック
        if limit and processed >= limit:
            print(f"\n  処理上限 ({limit}件) に到達。停止します。")
            break

        # 名前を決定（優先順位: name_it > name_ja > name_en > name_local）
        name = (
            item.get("name_it")
            or item.get("name_ja")
            or item.get("name_en")
            or item.get("name_local")
            or "Unknown"
        )

        remaining = total - len(completed_ids) - processed
        print(f"\n[{processed + 1}/{remaining}残] {name} ({entry_id})")

        try:
            # API 呼び出し
            if entry_type == "vegetable":
                result = agent.research_vegetable(name, entry_id, language)
            else:
                result = agent.research_recipe(name, entry_id, language)

            # 保存
            ResearchAgent.save_entry(result, entry_type, draft_source="gemini")

            # 成功記録
            progress["completed"].append(entry_id)
            completed_ids.add(entry_id)
            succeeded += 1

        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}")

            # エラー記録
            if entry_id not in failed_ids:
                progress["failed"].append(entry_id)
                failed_ids.add(entry_id)
            errors += 1

            # リトライ不要なエラー（認証系）は即停止
            error_str = str(e).lower()
            if "api key" in error_str or "authentication" in error_str or "quota" in error_str:
                print("  FATAL: 認証またはクォータエラー。バッチ処理を中断します。")
                _save_progress(csv_path, progress)
                sys.exit(1)

        processed += 1

        # 進捗保存（10件ごと）
        if processed % 10 == 0:
            _save_progress(csv_path, progress)
            print(f"\n  --- 進捗保存: {succeeded}/{processed} 成功 ---\n")

        # レート制限
        if processed < (limit or total):
            time.sleep(delay)

    # 最終進捗保存
    _save_progress(csv_path, progress)

    # サマリー
    print(f"\n{'='*60}")
    print(f"  バッチ処理完了")
    print(f"  処理: {processed} 件")
    print(f"  成功: {succeeded} 件")
    print(f"  失敗: {errors} 件")
    print(f"  累計完了: {len(completed_ids)} / {total} 件")
    print(f"{'='*60}\n")


# ============================================================
# CLI
# ============================================================

def main_cli():
    import argparse

    parser = argparse.ArgumentParser(
        description="Gemini バッチ処理ランナー"
    )
    parser.add_argument(
        "csv_file",
        type=Path,
        help="マスターリスト CSV ファイルパス",
    )
    parser.add_argument(
        "--type",
        choices=["vegetable", "recipe"],
        required=True,
        help="エントリタイプ",
    )
    parser.add_argument(
        "--language",
        choices=["italian", "japanese"],
        default="italian",
        help="調査言語（default: italian）",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=True,
        help="処理済みスキップ（デフォルト有効）",
    )
    parser.add_argument(
        "--no-resume",
        dest="resume",
        action="store_false",
        help="最初からやり直す",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="最大処理件数",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=4.0,
        help="API呼び出し間隔（秒, default: 4.0）",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Gemini モデル名（default: gemini_agent のデフォルト）",
    )
    args = parser.parse_args()

    # CSV パスの解決
    csv_path = args.csv_file
    if not csv_path.is_absolute():
        csv_path = PROJECT_ROOT / csv_path

    if not csv_path.exists():
        print(f"ERROR: CSV ファイルが見つかりません: {csv_path}")
        sys.exit(1)

    run_batch(
        csv_path=csv_path,
        entry_type=args.type,
        language=args.language,
        resume=args.resume,
        limit=args.limit,
        delay=args.delay,
        model=args.model,
    )


if __name__ == "__main__":
    main_cli()
