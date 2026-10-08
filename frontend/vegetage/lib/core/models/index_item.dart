import 'package:json_annotation/json_annotation.dart';

part 'index_item.g.dart';

@JsonSerializable()
class IndexItem {
  final String id;
  final String type; // "vegetable" or "redirect"
  @JsonKey(name: 'display_name')
  final String? displayName;
  final String? oneliner;
  @JsonKey(name: 'redirect_to')
  final String? redirectTo;
  @JsonKey(name: 'kana_name')
  final String? kanaName;
  @JsonKey(name: 'search_keys')
  final List<String>? searchKeys;

  IndexItem({
    required this.id,
    required this.type,
    this.displayName,
    this.oneliner,
    this.redirectTo,
    this.kanaName,
    this.searchKeys
  });

  factory IndexItem.fromJson(Map<String, dynamic> json) => _$IndexItemFromJson(json);
  Map<String, dynamic> toJson() => _$IndexItemToJson(this);
}