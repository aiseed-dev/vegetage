import 'dart:convert';
import 'package:flutter/services.dart';
import 'package:vegetage/core/models/index_item.dart';
import 'package:vegetage/core/models/vegetable.dart';

/// 野菜データの取得に関するインターフェース（抽象クラス）
/// これを定義することで、将来APIからデータを取得する場合などに
/// 実装を差し替えるのが容易になります。
abstract class IVegetableRepository {
  /// 全てのインデックス項目（野菜とリダイレクト）を取得する
  Future<List<IndexItem>> getAllIndexItems();

  /// IDを指定して、特定の野菜の詳細データを取得する
  Future<Vegetable> getVegetableById(String id);
}


/// assetsからデータを読み込むRepositoryの実装
class AssetVegetableRepository implements IVegetableRepository {
  // データをキャッシュして、毎回ファイルを読み込まないようにする
  List<IndexItem>? _indexCache;

  @override
  Future<List<IndexItem>> getAllIndexItems() async {
    // もしキャッシュがあれば、それを即座に返す
    if (_indexCache != null) {
      return _indexCache!;
    }

    try {
      // 1. _index.json ファイルを文字列として読み込む
      final jsonString = await rootBundle.loadString('assets/data/_index.json');

      // 2. JSON文字列をList<dynamic>にデコードする
      final List<dynamic> jsonList = json.decode(jsonString);

      // 3. リストの各要素を IndexItem オブジェクトに変換する
      final items = jsonList
          .map((jsonItem) => IndexItem.fromJson(jsonItem as Map<String, dynamic>))
          .toList();

      // 4. キャッシュに保存
      _indexCache = items;

      return items;
    } catch (e) {
      // エラーハンドリング
      print('Error loading or parsing _index.json: $e');
      // エラーが発生した場合は空のリストを返し、アプリがクラッシュしないようにする
      return [];
    }
  }

  @override
  Future<Vegetable> getVegetableById(String id) async {
    // ファイルパスを生成 (例: assets/data_ja/聖護院大根.json)
    final path = 'assets/data/vegetable_summary/$id.json';

    try {
      // 1. IDに対応するJSONファイルを文字列として読み込む
      final jsonString = await rootBundle.loadString(path);

      // 2. JSON文字列をMap<String, dynamic>にデコードする
      final jsonMap = json.decode(jsonString);

      // 3. 自動生成された fromJson を使って Vegetable オブジェクトに変換
      return Vegetable.fromJson(jsonMap as Map<String, dynamic>);
    } catch (e) {
      print('Error loading or parsing vegetable data for ID "$id": $e');
      // エラーが発生した場合は、リポジトリの呼び出し元に例外をスローする
      // UI側でこのエラーをキャッチして、エラー画面を表示する
      throw Exception('Failed to load vegetable: $id');
    }
  }
}

/*
#### Step 3: 画面と状態管理 (Riverpod)
Riverpodを使って、モックリポジトリからデータを取得し、UIに表示します。


*/