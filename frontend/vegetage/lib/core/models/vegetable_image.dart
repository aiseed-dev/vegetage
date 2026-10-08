import 'package:json_annotation/json_annotation.dart';

// この行は、このファイル名が `vegetable_image.dart` であることを前提としています。
// `build_runner` が `vegetable_image.g.dart` というファイルを生成します。
part 'vegetable_image.g.dart';

@JsonSerializable()
class VegetableImage {
  final String filename;
  final String? caption; // captionは存在しない可能性があるので `String?` にします

  VegetableImage({
    required this.filename,
    this.caption,
  });

  /// JSONデータから `VegetableImage` インスタンスを生成するためのファクトリコンストラクタ。
  factory VegetableImage.fromJson(Map<String, dynamic> json) => _$VegetableImageFromJson(json);

  /// `VegetableImage` インスタンスをJSONデータに変換するためのメソッド。
  Map<String, dynamic> toJson() => _$VegetableImageToJson(this);
}