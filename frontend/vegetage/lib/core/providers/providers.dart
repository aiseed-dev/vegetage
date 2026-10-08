import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:vegetage/core/models/vegetable_image.dart';
import 'package:vegetage/core/models/index_item.dart';
import 'package:vegetage/core/models/vegetable.dart';
import 'package:vegetage/core/repositories/vegetable_repository.dart';

// --- 1. Repositoryを提供するProvider ---
/// `AssetVegetableRepository` のインスタンスをアプリ全体で共有するためのProvider。
/// これにより、Repositoryのインスタンスをあちこちで生成する必要がなくなる。
final vegetableRepositoryProvider = Provider<IVegetableRepository>((ref) {
  return AssetVegetableRepository();
});

// --- 2. 一覧画面用のProvider ---
/// `_index.json` のデータを非同期で取得し、キャッシュするProvider。
/// `.autoDispose` を付けておくと、このProviderが使われなくなった時に
/// 自動的にキャッシュが破棄され、メモリを節約できる（今回は付けておく）。
final indexListProvider = FutureProvider.autoDispose<List<IndexItem>>((ref) {
  // `ref.watch` を使って、他のProvider（ここではrepository）を監視・取得する
  final repository = ref.watch(vegetableRepositoryProvider);
  return repository.getAllIndexItems();
});

/// `indexListProvider` の結果から、野菜 (`type: "vegetable"`) のみを取り出すProvider。
/// これをUIで使うことで、リダイレクト用の項目を意識する必要がなくなる。
final vegetableIndexProvider = Provider.autoDispose<List<IndexItem>>((ref) {
  // `indexListProvider` の非同期処理が終わるのを待って、その結果 (AsyncValue) を監視
  final asyncIndexList = ref.watch(indexListProvider);

  // `when` を使って、データの状態（成功、ローディング、エラー）に応じて処理を分岐
  return asyncIndexList.when(
    // 成功時: `type` が "vegetable" のものだけをフィルタリングして返す
    data: (items) => items.where((item) => item.type == 'vegetable').toList(),
    // 読み込み中やエラーの場合は空のリストを返す
    loading: () => [],
    error: (err, stack) => [],
  );
});


// --- 3. 詳細画面用のProvider ---
/// IDを引数として受け取り、特定の野菜の詳細データを非同期で取得するProvider。
/// `.family` を付けることで、Providerに外部から引数（ここではString型のid）を渡せるようになる。
final vegetableDetailProvider = FutureProvider.autoDispose.family<Vegetable, String>((ref, id) {
  final repository = ref.watch(vegetableRepositoryProvider);
  return repository.getVegetableById(id);
});

// --- 4. リダイレクト処理用のProvider ---
/// IDを受け取り、それがリダイレクト対象であれば転送先のIDを返すProvider。
/// 同期的に処理できるので `Provider` を使用。
final redirectProvider = Provider.autoDispose.family<String?, String>((ref, id) {
  final asyncIndexList = ref.watch(indexListProvider);

  return asyncIndexList.when(
    data: (items) {
      // itemsの中から、引数のidと一致するものを探す
      final targetItem = items.firstWhere((item) => item.id == id, orElse: () => IndexItem(id: '', type: ''));
      // もし `type` が "redirect" なら、`redirectTo` の値を返す
      if (targetItem.type == 'redirect') {
        return targetItem.redirectTo;
      }
      // そうでなければ null を返す
      return null;
    },
    loading: () => null,
    error: (err, stack) => null,
  );
});

// --- 検索機能用のProvider ---

/// ユーザーが検索バーに入力した文字列を保持するためのProvider。
/// UI側からこのProviderの状態を更新することで、検索クエリを管理する。
final searchQueryProvider = StateProvider.autoDispose<String>((ref) {
  return ''; // 初期値は空文字列
});


/// `vegetableIndexProvider` と `searchQueryProvider` の状態を元に、
/// フィルタリングされた最終的な野菜リストをUIに提供するProvider。
final filteredVegetableIndexProvider = Provider.autoDispose<List<IndexItem>>((ref) {
  // 元となる野菜リスト（フィルタリング前）を取得
  final allVegetables = ref.watch(vegetableIndexProvider);
  // 現在の検索クエリを取得
  final query = ref.watch(searchQueryProvider);

  // もし検索クエリが空なら、全ての野菜リストをそのまま返す
  if (query.isEmpty) {
    return allVegetables;
  }

  // 検索クエリがあれば、フィルタリングを実行
  // toLowerCase() で大文字・小文字を区別しないようにする
  final lowerCaseQuery = query.toLowerCase();

  return allVegetables.where((item) {
    // search_keys の中に、クエリを含むものがあるかどうかをチェック
    // item.id は displayName と同じことが多いが、念のため含めておく
    final searchTarget = [
      item.id.toLowerCase(),
      item.displayName?.toLowerCase() ?? '',
      ...(item.searchKeys ?? []).map((key) => key.toLowerCase())
    ];

    // searchTargetのいずれかの文字列がクエリを含んでいればtrueを返す
    return searchTarget.any((key) => key.contains(lowerCaseQuery));
  }).toList();
});

// 画像情報の引数を持つための、シンプルなクラス
class ImageInfoArgs {
  final String imageId;
  final String imageCategory;
  ImageInfoArgs({required this.imageId, required this.imageCategory});

  // Provider.familyで使うために、hashCodeと==をオーバーライドする必要がある
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
          other is ImageInfoArgs &&
              runtimeType == other.runtimeType &&
              imageId == other.imageId &&
              imageCategory == other.imageCategory;

  @override
  int get hashCode => imageId.hashCode ^ imageCategory.hashCode;
}

// ★★★ 画像情報 (info.json) を非同期で取得するProvider ★★★
final imageInfoProvider = FutureProvider.autoDispose.family<List<VegetableImage>, ImageInfoArgs>((ref, args) async {
  try {
    final uri = Uri.parse('https://aiseed.page/images/${args.imageCategory}/${args.imageId}/info.json');
    final response = await http.get(uri);
    if (response.statusCode == 200) {
      final List<dynamic> jsonList = json.decode(utf8.decode(response.bodyBytes));
      return jsonList.map((item) => VegetableImage.fromJson(item)).toList();
    } else {
      // info.json がない場合は、空のリストを返す
      return [];
    }
  } catch (e) {
    print('Failed to load image info: $e');
    return []; // エラーの場合も空リスト
  }
});