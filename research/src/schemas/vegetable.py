"""
野菜エントリーのデータスキーマ定義（Pydantic v2）

計画書 4.1 野菜エントリースキーマに準拠

## 分類体系（3レベル + 生物学的分類）
- 品目（item）: 料理分野の分類（トマト、ナス、ニンニク等）
- 細品目（sub_item）: 検索用の細分類（ミニトマト、加工用トマト等）
- 品種（variety）: 農業分類。遺伝的に固定された特徴で区別されるグループ
  = 各 VegetableEntry が1品種に対応
- 種（species）: 生物学的分類（学名で表現）

※ 1品種が複数の品目に属することがある
※ 1品種が複数の細品目に属することは多い
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# --- 分類サブモデル ---

class TaxonomyClassification(BaseModel):
    """分類情報（3レベル + 生物学的分類）"""
    items: list[str] = Field(
        description="品目（料理分野の分類）: トマト, ナス, ニンニク 等。複数可"
    )
    sub_items: list[str] = Field(
        default_factory=list,
        description="細品目（検索用細分類）: ミニトマト, 加工用トマト 等。複数可"
    )
    variety: str = Field(
        description="品種名（農業分類）: サンマルツァーノ, パキーノ 等"
    )
    species: Optional[str] = Field(
        default=None,
        description="種の学名（生物学的分類）: Solanum lycopersicum 等"
    )


# --- 共通サブモデル ---

class MultilingualName(BaseModel):
    """多言語名称"""
    local: str = Field(description="現地語名（イタリア語/日本語）")
    japanese: str = Field(description="日本語名")
    english: str = Field(description="英語名")
    scientific: str = Field(default="", description="学名")


class HistoricalReference(BaseModel):
    """歴史文献の参照"""
    author: str = Field(description="著者名（例: 大プリニウス、マッティオーリ）")
    work: Optional[str] = Field(default=None, description="著作名")
    year: Optional[str] = Field(default=None, description="年代")
    description: str = Field(description="記述内容の要約")


class History(BaseModel):
    """品種の歴史・文化情報（Deep Research PDFから抽出）

    Deep Research PDFには古代ローマから現代に至る豊富な歴史情報が
    含まれる。このモデルでその情報を構造的に保持する。
    """
    summary: str = Field(
        description="歴史的背景の要約（200-400文字）"
    )
    etymology: Optional[str] = Field(
        default=None,
        description="名称の語源・由来（ラテン語、方言、王朝名等）"
    )
    ancient_period: Optional[str] = Field(
        default=None,
        description="古代（ローマ・ギリシャ）における記録・利用"
    )
    medieval_renaissance: Optional[str] = Field(
        default=None,
        description="中世〜ルネサンス期の変遷（修道院農業、本草学等）"
    )
    modern_history: Optional[str] = Field(
        default=None,
        description="近現代の展開（品種固定、産地形成、認証取得等）"
    )
    key_references: list[HistoricalReference] = Field(
        default_factory=list,
        description="重要な歴史的文献・人物の参照"
    )
    traditional_preservation: Optional[str] = Field(
        default=None,
        description="伝統的な保存・加工方法"
    )
    regional_food_culture: Optional[str] = Field(
        default=None,
        description="地域の食文化との結びつき（郷土料理、祭事等）"
    )
    certification_history: Optional[str] = Field(
        default=None,
        description="DOP/IGP/PAT/Presidio認証の経緯"
    )


class Origin(BaseModel):
    """原産地情報"""
    country: str
    region: str
    specific_town: Optional[str] = None
    history: str | History = Field(description="歴史的背景。文字列またはHistoryオブジェクト")
    predecessor: Optional[str] = None


class AppearanceDetail(BaseModel):
    shape: str
    color: str
    size: str


class TasteDetail(BaseModel):
    description: str
    notes: Optional[str] = None


class TextureDetail(BaseModel):
    flesh: str
    seeds: Optional[str] = None
    skin: Optional[str] = None


class Characteristics(BaseModel):
    """特徴"""
    appearance: AppearanceDetail | str
    taste: TasteDetail | str
    texture: TextureDetail | str
    nutrition: dict[str, str]


class SoilRequirements(BaseModel):
    type: str
    ph: Optional[str] = None
    notes: Optional[str] = None


class ClimateInfo(BaseModel):
    ideal: str
    temperature: Optional[str] = None
    humidity: Optional[str] = None


class NaturalFarmingTips(BaseModel):
    companion_planting: Optional[str] = None
    pruning: Optional[str] = None
    watering: Optional[str] = None
    fertilizer: Optional[str] = None
    disease_prevention: Optional[str] = None
    notes: Optional[str] = None


class Cultivation(BaseModel):
    """栽培情報"""
    type: Optional[str] = None
    sowing_period: str = Field(description="播種期")
    transplant_timing: Optional[str] = None
    harvest_period: str = Field(description="収穫期")
    days_to_maturity: Optional[str] = None
    soil_requirements: SoilRequirements | str
    climate: ClimateInfo | str
    spacing: Optional[str] = None
    pests_diseases: list[str] = Field(default_factory=list)
    natural_farming_tips: NaturalFarmingTips | str = Field(
        default="", description="自然農法でのコツ"
    )
    harvesting: Optional[str] = None


class CulinaryUses(BaseModel):
    """調理用途"""
    best_for: list[str]
    why_suitable: Optional[dict[str, str]] = None
    not_recommended: Optional[str] = None


class RelatedRecipe(BaseModel):
    """関連料理"""
    id: str = Field(pattern=r"^[A-Z]{2}-RCP-[A-Z]{3}-\d{3}$")
    name: str
    relationship: Optional[str] = None


class Source(BaseModel):
    """出典情報"""
    url: str
    type: Optional[str] = None
    reliability: Optional[str] = Field(default=None, pattern=r"^(high|medium|low)$")
    language: Optional[str] = None


class CompletenessScores(BaseModel):
    basic_info: Optional[float] = None
    cultivation: Optional[float] = None
    culinary: Optional[float] = None
    cultural: Optional[float] = None
    sources: Optional[float] = None


class Metadata(BaseModel):
    """メタデータ"""
    collected_at: str = Field(description="ISO 8601形式の収集日時")
    agent_version: str = "1.0.0"
    research_method: Optional[str] = None
    confidence_score: float = Field(ge=0.0, le=1.0, description="信頼度スコア")
    completeness: Optional[CompletenessScores] = None
    languages_searched: list[str] = Field(default_factory=list)
    cross_check_status: Optional[str] = None
    needs_review: list[str] = Field(default_factory=list)


# --- メインモデル ---

class VegetableEntry(BaseModel):
    """野菜エントリー（計画書 4.1 準拠）

    各エントリーは1つの「品種」に対応する。
    品目・細品目との関係は classification フィールドで表現。
    """
    id: str = Field(pattern=r"^[A-Z]{2}-VEG-[A-Z]{3}-\d{3}$")
    names: MultilingualName
    classification: TaxonomyClassification = Field(
        description="分類情報（品目・細品目・品種・種）"
    )
    origin: Origin
    characteristics: Characteristics
    cultivation: Cultivation
    culinary_uses: CulinaryUses | list[str]
    related_recipes: list[RelatedRecipe | str] = Field(default_factory=list)
    cultural_significance: dict | str = ""
    sources: list[Source | str] = Field(default_factory=list)
    metadata: Metadata
