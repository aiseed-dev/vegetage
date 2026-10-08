// lib/core/models/vegetable.dart
import 'package:json_annotation/json_annotation.dart';
import 'package:vegetage/core/models/vegetable_image.dart';

part 'vegetable.g.dart';

// --- メインの野菜データモデル ---
@JsonSerializable(explicitToJson: true)
class Vegetable {
  @JsonKey(name: 'global_info')
  final GlobalInfo globalInfo;
  final Content content;

  Vegetable({
    required this.globalInfo,
    required this.content,
  });

  factory Vegetable.fromJson(Map<String, dynamic> json) => _$VegetableFromJson(json);
  Map<String, dynamic> toJson() => _$VegetableToJson(this);
}

// --- グローバル情報 ---
@JsonSerializable(explicitToJson: true)
class GlobalInfo {
  final String url;
  @JsonKey(name: 'kana_name')
  final String kanaName;
  final String? scientificName;
  final Classification? classification;
  final FoodClassification? foodClassification;
  @JsonKey(name: 'has_images')
  final bool? hasImages;
  final Names? names;

  GlobalInfo({
    required this.url,
    required this.kanaName,
    this.scientificName,
    this.classification,
    this.foodClassification,
    this.names,
    this.hasImages
  });

  factory GlobalInfo.fromJson(Map<String, dynamic> json) => _$GlobalInfoFromJson(json);
  Map<String, dynamic> toJson() => _$GlobalInfoToJson(this);
}

// --- コンテンツ本体（日本語） ---
@JsonSerializable(explicitToJson: true)
class Content {
  final ContentJa ja;

  Content({required this.ja});

  factory Content.fromJson(Map<String, dynamic> json) => _$ContentFromJson(json);
  Map<String, dynamic> toJson() => _$ContentToJson(this);
}

// --- 日本語コンテンツの詳細 ---
@JsonSerializable(explicitToJson: true)
class ContentJa {
  @JsonKey(name: 'display_name')
  final String displayName;
  final String oneliner;
  final String description;
  @JsonKey(name: 'practical_oneliner')
  final String practicalOneliner;
  @JsonKey(name: 'practical_tips')
  final String practicalTips;
  @JsonKey(name: 'nutrition_oneliner')
  final String nutritionOneliner;
  @JsonKey(name: 'nutrition_benefits')
  final String nutritionBenefits;
  @JsonKey(name: 'safety_oneliner')
  final String safetyOneliner;
  @JsonKey(name: 'safety_notes')
  final String safetyNotes;
  @JsonKey(name: 'honest_oneliner')
  final String honestOneliner;
  @JsonKey(name: 'honest_assessment')
  final String honestAssessment;
  @JsonKey(name: 'cultural_background')
  final String culturalBackground;
  final Relationships? relationships;
  final String? notes;

  ContentJa({
    required this.displayName,
    required this.oneliner,
    required this.description,
    required this.practicalOneliner,
    required this.practicalTips,
    required this.nutritionOneliner,
    required this.nutritionBenefits,
    required this.safetyOneliner,
    required this.safetyNotes,
    required this.honestOneliner,
    required this.honestAssessment,
    required this.culturalBackground,
    this.relationships,
    this.notes,
  });

  factory ContentJa.fromJson(Map<String, dynamic> json) => _$ContentJaFromJson(json);
  Map<String, dynamic> toJson() => _$ContentJaToJson(this);
}

// --- 分類情報 ---
@JsonSerializable()
class Classification {
  @JsonKey(name: 'family_ja')
  final String? familyJa;
  @JsonKey(name: 'genus_ja')
  final String? genusJa;

  Classification({this.familyJa, this.genusJa});

  factory Classification.fromJson(Map<String, dynamic> json) => _$ClassificationFromJson(json);
  Map<String, dynamic> toJson() => _$ClassificationToJson(this);
}

// --- 食用分類情報 ---
@JsonSerializable()
class FoodClassification {
  final String? primaryPart;
  final List<String>? edibleParts;

  FoodClassification({this.primaryPart, this.edibleParts});

  factory FoodClassification.fromJson(Map<String, dynamic> json) => _$FoodClassificationFromJson(json);
  Map<String, dynamic> toJson() => _$FoodClassificationToJson(this);
}

// --- 名称情報 ---
@JsonSerializable(explicitToJson: true)
class Names {
  final JapaneseNames? japanese;
  final InternationalNames? international;

  Names({this.japanese, this.international});

  factory Names.fromJson(Map<String, dynamic> json) => _$NamesFromJson(json);
  Map<String, dynamic> toJson() => _$NamesToJson(this);
}

@JsonSerializable()
class JapaneseNames {
  final List<String>? common;

  JapaneseNames({this.common});

  factory JapaneseNames.fromJson(Map<String, dynamic> json) => _$JapaneseNamesFromJson(json);
  Map<String, dynamic> toJson() => _$JapaneseNamesToJson(this);
}

@JsonSerializable()
class InternationalNames {
  final List<String>? en;

  InternationalNames({this.en});

  factory InternationalNames.fromJson(Map<String, dynamic> json) => _$InternationalNamesFromJson(json);
  Map<String, dynamic> toJson() => _$InternationalNamesToJson(this);
}

// --- 関連情報 ---
@JsonSerializable()
class Relationships {
  final List<String>? parentSpecies;
  final List<String>? children;
  final List<String>? similarVegetables;

  Relationships({this.parentSpecies, this.children, this.similarVegetables});

  factory Relationships.fromJson(Map<String, dynamic> json) => _$RelationshipsFromJson(json);
  Map<String, dynamic> toJson() => _$RelationshipsToJson(this);
}