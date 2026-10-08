"""
データバリデーションスクリプト

data/ 配下の全JSONファイルをスキーマに基づいて検証する
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ValidationError

from src.schemas.vegetable import VegetableEntry
from src.schemas.recipe import RecipeEntry

if TYPE_CHECKING:
    from pydantic import BaseModel

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"


def detect_entry_type(file_path: Path) -> type[BaseModel]:
    """ファイルパスからエントリタイプを判定"""
    if "vegetables" in file_path.parts:
        return VegetableEntry
    elif "recipes" in file_path.parts:
        return RecipeEntry
    else:
        raise ValueError(f"Unknown data type for: {file_path}")


def validate_file(file_path: Path) -> tuple[bool, list[str]]:
    """単一ファイルのバリデーション"""
    errors: list[str] = []

    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, [f"JSON parse error: {e}"]

    try:
        model_class = detect_entry_type(file_path)
    except ValueError as e:
        return False, [str(e)]

    try:
        model_class.model_validate(data)
    except ValidationError as e:
        for err in e.errors():
            loc = " -> ".join(str(l) for l in err["loc"])
            errors.append(f"  {loc}: {err['msg']}")

    return len(errors) == 0, errors


def validate_all() -> bool:
    """data/ 配下の全JSONを検証"""
    json_files = sorted(DATA_DIR.rglob("*.json"))

    if not json_files:
        print("No JSON files found in data/")
        return True

    total = len(json_files)
    passed = 0
    failed = 0

    print(f"Validating {total} data file(s)...\n")

    for fp in json_files:
        rel = fp.relative_to(PROJECT_ROOT)
        ok, errors = validate_file(fp)

        if ok:
            print(f"  PASS  {rel}")
            passed += 1
        else:
            print(f"  FAIL  {rel}")
            for e in errors:
                print(f"        {e}")
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed (total {total})")
    return failed == 0


def main_cli():
    success = validate_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main_cli()
