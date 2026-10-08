// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'vegetable.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

Vegetable _$VegetableFromJson(Map<String, dynamic> json) => Vegetable(
  globalInfo: GlobalInfo.fromJson(json['global_info'] as Map<String, dynamic>),
  content: Content.fromJson(json['content'] as Map<String, dynamic>),
);

Map<String, dynamic> _$VegetableToJson(Vegetable instance) => <String, dynamic>{
  'global_info': instance.globalInfo.toJson(),
  'content': instance.content.toJson(),
};

GlobalInfo _$GlobalInfoFromJson(Map<String, dynamic> json) => GlobalInfo(
  url: json['url'] as String,
  kanaName: json['kana_name'] as String,
  scientificName: json['scientificName'] as String?,
  classification: json['classification'] == null
      ? null
      : Classification.fromJson(json['classification'] as Map<String, dynamic>),
  foodClassification: json['foodClassification'] == null
      ? null
      : FoodClassification.fromJson(
          json['foodClassification'] as Map<String, dynamic>,
        ),
  names: json['names'] == null
      ? null
      : Names.fromJson(json['names'] as Map<String, dynamic>),
  hasImages: json['has_images'] as bool?,
);

Map<String, dynamic> _$GlobalInfoToJson(GlobalInfo instance) =>
    <String, dynamic>{
      'url': instance.url,
      'kana_name': instance.kanaName,
      'scientificName': instance.scientificName,
      'classification': instance.classification?.toJson(),
      'foodClassification': instance.foodClassification?.toJson(),
      'has_images': instance.hasImages,
      'names': instance.names?.toJson(),
    };

Content _$ContentFromJson(Map<String, dynamic> json) =>
    Content(ja: ContentJa.fromJson(json['ja'] as Map<String, dynamic>));

Map<String, dynamic> _$ContentToJson(Content instance) => <String, dynamic>{
  'ja': instance.ja.toJson(),
};

ContentJa _$ContentJaFromJson(Map<String, dynamic> json) => ContentJa(
  displayName: json['display_name'] as String,
  oneliner: json['oneliner'] as String,
  description: json['description'] as String,
  practicalOneliner: json['practical_oneliner'] as String,
  practicalTips: json['practical_tips'] as String,
  nutritionOneliner: json['nutrition_oneliner'] as String,
  nutritionBenefits: json['nutrition_benefits'] as String,
  safetyOneliner: json['safety_oneliner'] as String,
  safetyNotes: json['safety_notes'] as String,
  honestOneliner: json['honest_oneliner'] as String,
  honestAssessment: json['honest_assessment'] as String,
  culturalBackground: json['cultural_background'] as String,
  relationships: json['relationships'] == null
      ? null
      : Relationships.fromJson(json['relationships'] as Map<String, dynamic>),
  notes: json['notes'] as String?,
);

Map<String, dynamic> _$ContentJaToJson(ContentJa instance) => <String, dynamic>{
  'display_name': instance.displayName,
  'oneliner': instance.oneliner,
  'description': instance.description,
  'practical_oneliner': instance.practicalOneliner,
  'practical_tips': instance.practicalTips,
  'nutrition_oneliner': instance.nutritionOneliner,
  'nutrition_benefits': instance.nutritionBenefits,
  'safety_oneliner': instance.safetyOneliner,
  'safety_notes': instance.safetyNotes,
  'honest_oneliner': instance.honestOneliner,
  'honest_assessment': instance.honestAssessment,
  'cultural_background': instance.culturalBackground,
  'relationships': instance.relationships?.toJson(),
  'notes': instance.notes,
};

Classification _$ClassificationFromJson(Map<String, dynamic> json) =>
    Classification(
      familyJa: json['family_ja'] as String?,
      genusJa: json['genus_ja'] as String?,
    );

Map<String, dynamic> _$ClassificationToJson(Classification instance) =>
    <String, dynamic>{
      'family_ja': instance.familyJa,
      'genus_ja': instance.genusJa,
    };

FoodClassification _$FoodClassificationFromJson(Map<String, dynamic> json) =>
    FoodClassification(
      primaryPart: json['primaryPart'] as String?,
      edibleParts: (json['edibleParts'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
    );

Map<String, dynamic> _$FoodClassificationToJson(FoodClassification instance) =>
    <String, dynamic>{
      'primaryPart': instance.primaryPart,
      'edibleParts': instance.edibleParts,
    };

Names _$NamesFromJson(Map<String, dynamic> json) => Names(
  japanese: json['japanese'] == null
      ? null
      : JapaneseNames.fromJson(json['japanese'] as Map<String, dynamic>),
  international: json['international'] == null
      ? null
      : InternationalNames.fromJson(
          json['international'] as Map<String, dynamic>,
        ),
);

Map<String, dynamic> _$NamesToJson(Names instance) => <String, dynamic>{
  'japanese': instance.japanese?.toJson(),
  'international': instance.international?.toJson(),
};

JapaneseNames _$JapaneseNamesFromJson(Map<String, dynamic> json) =>
    JapaneseNames(
      common: (json['common'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
    );

Map<String, dynamic> _$JapaneseNamesToJson(JapaneseNames instance) =>
    <String, dynamic>{'common': instance.common};

InternationalNames _$InternationalNamesFromJson(Map<String, dynamic> json) =>
    InternationalNames(
      en: (json['en'] as List<dynamic>?)?.map((e) => e as String).toList(),
    );

Map<String, dynamic> _$InternationalNamesToJson(InternationalNames instance) =>
    <String, dynamic>{'en': instance.en};

Relationships _$RelationshipsFromJson(Map<String, dynamic> json) =>
    Relationships(
      parentSpecies: (json['parentSpecies'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      children: (json['children'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
      similarVegetables: (json['similarVegetables'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList(),
    );

Map<String, dynamic> _$RelationshipsToJson(Relationships instance) =>
    <String, dynamic>{
      'parentSpecies': instance.parentSpecies,
      'children': instance.children,
      'similarVegetables': instance.similarVegetables,
    };
