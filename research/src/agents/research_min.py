#!/usr/bin/env python3
"""
最小リサーチエージェント（Claude Agent SDK / cookbook の one-liner パターン）

1 作物ぶんの「たたき台」を自律調査で生成する。出力は ②:
    data/deep_research/italian/<作物>/
        ├── <作物>.md       概要（YAML フロントマター + 短い概要文）
        ├── history.md      歴史
        ├── cultivation.md  栽培
        └── cuisine.md      料理
各ファイルは末尾に出典（Sources: の markdown リンク）を持つ。

【重要 — このプロジェクトの作法】
  ・出力は「たたき台」にすぎない。**人間が web/italian/ で確認・修正して正本にする。**
    自動公開しない（AI は仮説を出す道具、確定は人間）。
  ・辞典には「現行システム」のような正解器が無い。DOP/IGP・学名・産地・統計などの
    事実は、**出典と、業務を知る人間で必ず検証する**こと。
  ・対象は公開知識（野菜）。機微データは扱わない。

前提（このサンドボックスでは未導入・未実行。ローカルで）:
    pip install claude-agent-sdk      # ./.venv に
    export ANTHROPIC_API_KEY=...
使い方:
    ./.venv/bin/python -m src.agents.research_min "アーティチョーク" --it Carciofo --en Artichoke
    ./.venv/bin/python -m src.agents.research_min "アーティチョーク" --model claude-sonnet-4-6
"""

import argparse
import asyncio
from pathlib import Path

try:
    from claude_agent_sdk import ClaudeAgentOptions, query
except ImportError:  # 未導入環境向けの明示メッセージ（自動インストールはしない）
    raise SystemExit(
        "claude-agent-sdk が無い。仮想環境に入れて、その Python で実行する:\n"
        "  ./.venv/bin/pip install claude-agent-sdk\n"
        "  export ANTHROPIC_API_KEY=...\n"
        "  ./.venv/bin/python -m src.agents.research_min '<作物名>'"
    )

ROOT = Path(__file__).resolve().parents[2]          # research/
OUT_BASE = ROOT / "data" / "deep_research" / "italian"
DEFAULT_MODEL = "claude-sonnet-4-6"                 # 必要に応じて差し替え（--model）

SHARED_RULES = (
    "あなたはイタリア伝統野菜の調査員。イタリア語・日本語・英語の一次情報を WebSearch で"
    "直接調べる。断定する事実（DOP/IGP・学名・産地・年代・統計）には必ず出典を付け、"
    "本文末尾に「## Sources」として [タイトル](URL) の markdown リンクで列挙する。"
    "不確かな点は「（要確認）」と明記する。憶測で数値を作らない。"
)

OVERVIEW_PROMPT = """{rules}

作物「{ja}」（伊: {it} / 英: {en}）の【概要】を作る。出力は次の形式の Markdown のみ:

---
id: {idg}
name_ja: {ja}
name_it: {it}
name_en: {en}
aliases: [別名・地方名があれば]
family: （科の和名・例: キク科）
family_latin: （科の学名・例: Asteraceae）
botanical: （種の学名）
index_group: （目次「科」タブの表示名。まずは family と同じでよい）
type: [花菜類 など。食用部位。複数可・はっきりする物だけ]
item: {ja}
certification: [DOP/IGP があれば]
regions: [主な産地（州）]
season: [旬]
uses: [生食/加熱/保存 など]
hero_image: images/hero.jpg
---

# {ja}

*（種の学名）* — （短いキャッチ）

（3〜4 段落の概要。何の野菜か、科・特徴、イタリアでの位置づけ。）

## Sources
- [タイトル](URL)
"""

SECTION_PROMPT = """{rules}

作物「{ja}」（伊: {it}）の【{label}】を、見出し付きの読み物として Markdown で書く。
先頭は「# {ja}{suffix}」。{detail}
本文末尾に「## Sources」を必ず付ける。
"""

SECTIONS = {
    "history": ("歴史", "の歴史", "起源・伝来・品種体系（DOP/IGP）・祭事や文化まで。"),
    "cultivation": ("栽培", "の栽培", "栽培環境・育て方。自然農法／有機栽培のコツを含める。"),
    "cuisine": ("料理", "の料理", "代表的な伝統料理・調理法・相性の良い食材。"),
}


async def _run(prompt: str, model: str) -> str:
    """one-liner：WebSearch だけ許可した自律調査。最終テキストを返す。"""
    chunks: list[str] = []
    async for msg in query(
        prompt=prompt,
        options=ClaudeAgentOptions(model=model, allowed_tools=["WebSearch"]),
    ):
        text = getattr(msg, "text", None) or getattr(msg, "result", None)
        if isinstance(text, str):
            chunks.append(text)
    return "\n".join(chunks).strip()


async def main_async(ja: str, it: str, en: str, idg: str, model: str) -> None:
    out_dir = OUT_BASE / ja
    out_dir.mkdir(parents=True, exist_ok=True)

    # 概要
    overview = await _run(
        OVERVIEW_PROMPT.format(rules=SHARED_RULES, ja=ja, it=it, en=en, idg=idg),
        model,
    )
    (out_dir / f"{ja}.md").write_text(overview + "\n", encoding="utf-8")
    print(f"  ✓ {ja}.md（概要・たたき台）")

    # 歴史・栽培・料理
    for key, (label, suffix, detail) in SECTIONS.items():
        body = await _run(
            SECTION_PROMPT.format(rules=SHARED_RULES, ja=ja, it=it,
                                  label=label, suffix=suffix, detail=detail),
            model,
        )
        (out_dir / f"{key}.md").write_text(body + "\n", encoding="utf-8")
        print(f"  ✓ {key}.md（{label}・たたき台）")

    print(f"\n出力: {out_dir.relative_to(ROOT)}/")
    print("→ これはたたき台。web/italian/ で人間が確認・修正して正本にすること。")


def main_cli() -> None:
    ap = argparse.ArgumentParser(description="最小リサーチエージェント（たたき台生成）")
    ap.add_argument("name_ja", help="作物の和名（例: アーティチョーク）")
    ap.add_argument("--it", default="", help="イタリア語名")
    ap.add_argument("--en", default="", help="英語名")
    ap.add_argument("--index-group", default="", help="目次「科」タブの表示名（省略可）")
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"モデル（既定 {DEFAULT_MODEL}）")
    args = ap.parse_args()
    asyncio.run(main_async(args.name_ja, args.it, args.en, args.index_group, args.model))


if __name__ == "__main__":
    main_cli()
