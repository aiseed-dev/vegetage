// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'index_item.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

IndexItem _$IndexItemFromJson(Map<String, dynamic> json) => IndexItem(
  id: json['id'] as String,
  type: json['type'] as String,
  displayName: json['display_name'] as String?,
  oneliner: json['oneliner'] as String?,
  redirectTo: json['redirect_to'] as String?,
  kanaName: json['kana_name'] as String?,
  searchKeys: (json['search_keys'] as List<dynamic>?)
      ?.map((e) => e as String)
      .toList(),
);

Map<String, dynamic> _$IndexItemToJson(IndexItem instance) => <String, dynamic>{
  'id': instance.id,
  'type': instance.type,
  'display_name': instance.displayName,
  'oneliner': instance.oneliner,
  'redirect_to': instance.redirectTo,
  'kana_name': instance.kanaName,
  'search_keys': instance.searchKeys,
};
