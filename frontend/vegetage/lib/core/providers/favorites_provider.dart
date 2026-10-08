// lib/core/providers/favorites_provider.dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:shared_preferences/shared_preferences.dart';

part 'favorites_provider.g.dart';

// お気に入り野菜のIDリスト（例: ["聖護院かぶ", "みょうが"]）を管理するNotifier
@Riverpod(keepAlive: true)
class Favorites extends _$Favorites { // ★★★ _$Favorites を継承 ★★★
  static const _favoritesKey = 'favorite_vegetable_ids';

  @override
  Future<List<String>> build() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getStringList(_favoritesKey) ?? [];
  }

  Future<void> toggleFavorite(String vegetableId) async {
    final prefs = await SharedPreferences.getInstance();

    // 現在の状態を取得
    // state.value が null の場合は空リストを使う
    final currentFavorites = state.value?.toList() ?? [];

    if (currentFavorites.contains(vegetableId)) {
      currentFavorites.remove(vegetableId);
    } else {
      currentFavorites.add(vegetableId);
    }

    // 端末に保存
    await prefs.setStringList(_favoritesKey, currentFavorites);

    // 状態を更新
    state = AsyncValue.data(currentFavorites);
  }
}
