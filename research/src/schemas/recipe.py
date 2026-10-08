"""
料理エントリーのデータスキーマ定義（Pydantic v2）

計画書 4.2 料理エントリースキーマに準拠
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class MultilingualRecipeName(BaseModel):
    """多言語名称（料理用 — scientificなし）"""
    local: str = Field(description="現地語名")
    japanese: str = Field(description="日本語名")
    english: str = Field(description="英語名")


class RecipeOrigin(BaseModel):
    """発祥地域情報"""
    country: str
    region: str
    history: str = Field(description="歴史的背景")
    predecessor: Optional[str] = None


class Ingredient(BaseModel):
    """材料"""
    name: str
    amount: Optional[str] = None
    components: Optional[list[dict]] = None
    is_traditional_vegetable: bool = False
    vegetable_id: Optional[str] = None
    notes: Optional[str] = None


class TraditionalMethod(BaseModel):
    """伝統的な調理法"""
    dough_preparation: Optional[dict] = None
    shaping: Optional[dict] = None
    topping: Optional[dict] = None
    baking: Optional[dict] = None
    steps: Optional[list[str]] = None
    notes: Optional[str] = None


class Certification(BaseModel):
    organization: Optional[str] = None
    established: Optional[str] = None
    purpose: Optional[str] = None
    requirements: list[str] = Field(default_factory=list)


class CulturalContext(BaseModel):
    """文化的背景"""
    eating_style: Optional[str] = None
    certification: Optional[Certification] = None
    symbolism: Optional[str] = None
    unesco: Optional[str] = None


class Variation(BaseModel):
    """バリエーション"""
    name: str
    description: str


class RelatedVegetable(BaseModel):
    """関連野菜"""
    id: str = Field(pattern=r"^[A-Z]{2}-VEG-[A-Z]{3}-\d{3}$")
    name: str
    role: Optional[str] = None


class RelatedRecipeLink(BaseModel):
    """関連料理（別の料理への参照）"""
    id: str = Field(pattern=r"^[A-Z]{2}-RCP-[A-Z]{3}-\d{3}$")
    name: str
    relationship: Optional[str] = None


class RecipeSource(BaseModel):
    """出典情報"""
    url: str
    type: Optional[str] = None
    reliability: Optional[str] = Field(default=None, pattern=r"^(high|medium|low)$")
    language: Optional[str] = None


class RecipeCompletenessScores(BaseModel):
    basic_info: Optional[float] = None
    ingredients: Optional[float] = None
    method: Optional[float] = None
    cultural: Optional[float] = None


class RecipeMetadata(BaseModel):
    """メタデータ"""
    collected_at: str
    agent_version: str = "1.0.0"
    research_method: Optional[str] = None
    confidence_score: float = Field(ge=0.0, le=1.0)
    completeness: Optional[RecipeCompletenessScores] = None
    cross_check_status: Optional[str] = None
    needs_review: list[str] = Field(default_factory=list)


# --- メインモデル ---

class RecipeEntry(BaseModel):
    """料理エントリー（計画書 4.2 準拠）"""
    id: str = Field(pattern=r"^[A-Z]{2}-RCP-[A-Z]{3}-\d{3}$")
    names: MultilingualRecipeName
    origin: RecipeOrigin
    category: str = Field(description="料理カテゴリ（前菜、主菜、保存食など）")
    subcategory: Optional[str] = None
    ingredients: list[Ingredient]
    traditional_method: TraditionalMethod | str
    variations: list[Variation | str] = Field(default_factory=list)
    cultural_context: CulturalContext | str = ""
    related_vegetables: list[RelatedVegetable | str] = Field(default_factory=list)
    related_recipes: list[RelatedRecipeLink | str] = Field(default_factory=list)
    sources: list[RecipeSource | str] = Field(default_factory=list)
    metadata: RecipeMetadata
