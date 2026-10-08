// lib/features/home/vegetable_list_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vegetage/core/models/index_item.dart';
import 'package:vegetage/core/providers/providers.dart';
import 'package:vegetage/core/providers/favorites_provider.dart';
import 'package:vegetage/shared/constants/app_strings.dart'; // 定数ファイル（推奨）

class VegetableListScreen extends ConsumerWidget {
  const VegetableListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final filteredVegetables = ref.watch(filteredVegetableIndexProvider);
    // `vegetableIndexProvider` を監視。`type: "vegetable"` のみが入ってくる
    final vegetableIndexAsync = ref.watch(indexListProvider);
    // お気に入りリストの状態を監視
    final favoritesAsync = ref.watch(favoritesProvider);
    // 元のデータがロード中かエラーかを確認するために、元のProviderも監視
    final originalIndexAsync = ref.watch(indexListProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text(AppStrings.vegetableListTitle),
        // TODO: 将来ここに検索ボタンなどを追加
      ),
      // FutureProvider の状態をハンドルするのに最適な `when` を使用
      body: Column(
        children: [
          // --- ★★★ 検索バーを追加 ★★★ ---
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: TextField(
              decoration: InputDecoration(
                hintText: AppStrings.searchHint,
                prefixIcon: const Icon(Icons.search),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide.none,
                ),
                filled: true,
              ),
              // テキストが変更されるたびに、searchQueryProviderの状態を更新する
              onChanged: (value) {
                ref.read(searchQueryProvider.notifier).state = value;
              },
            ),
          ),
          Expanded(
            child: originalIndexAsync.when(
              data: (items) {
                // `items` は `indexListProvider` の生データ
                // ★★★ ここからが修正箇所 ★★★
                // 次に、お気に入りデータの状態をチェック
                return favoritesAsync.when(
                  data: (favoriteIds) {
                    // 両方のデータが揃ったので、UIを構築する

                    // `vegetableIndexProvider` からフィルタリング済みの野菜リストを取得
                    // (`originalIndexAsync` が成功しているので、こちらも必ず成功している)
                    final vegetables = ref.watch(vegetableIndexProvider);

                    // 検索クエリでさらにフィルタリング
                    final query = ref.watch(searchQueryProvider);
                    final filteredVegetables = query.isEmpty
                        ? vegetables
                        : vegetables.where((item) {
                            final lowerCaseQuery = query.toLowerCase();
                            final searchTarget = [
                              item.id.toLowerCase(),
                              item.displayName?.toLowerCase() ?? '',
                              ...(item.searchKeys ?? []).map(
                                (key) => key.toLowerCase(),
                              ),
                            ];
                            return searchTarget.any(
                              (key) => key.contains(lowerCaseQuery),
                            );
                          }).toList();

                    // お気に入りを優先してソート
                    final sortedVegetables = List<IndexItem>.from(
                      filteredVegetables,
                    );
                    sortedVegetables.sort((a, b) {
                      final isAFavorite = favoriteIds.contains(a.id);
                      final isBFavorite = favoriteIds.contains(b.id);
                      if (isAFavorite && !isBFavorite) return -1;
                      if (!isAFavorite && isBFavorite) return 1;
                      // 両方お気に入り、または両方お気に入りでない場合は、`kanaName` でソートする
                      return (a.kanaName ?? '').compareTo(b.kanaName ?? '');
                    });

                    if (sortedVegetables.isEmpty) {
                      return const Center(child: Text('該当する野菜が見つかりません。'));
                    }

                    // ListView.builder の部分は同じ
                    return ListView.builder(
                      itemCount: sortedVegetables.length,
                      itemBuilder: (context, index) {
                        final item = sortedVegetables[index];
                        final isFavorite = favoriteIds.contains(item.id);

                        return Card(
                          margin: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 4,
                          ),
                          child: ListTile(
                            title: Text(item.displayName ?? '名前なし'),
                            subtitle: Text(
                              item.oneliner ?? '',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                            trailing: IconButton(
                              icon: Icon(
                                isFavorite
                                    ? Icons.favorite
                                    : Icons.favorite_border,
                                color: isFavorite ? Colors.redAccent : null,
                              ),
                              onPressed: () {
                                ref
                                    .read(favoritesProvider.notifier)
                                    .toggleFavorite(item.id);
                              },
                            ),
                            onTap: () {
                              context.push('/vegetables/${item.id}');
                            },
                          ),
                        );
                      },
                    );
                  },
                  // `favoritesAsync` のローディングとエラーも必須
                  loading: () =>
                      const Center(child: CircularProgressIndicator()),
                  error: (err, stack) =>
                      Center(child: Text('お気に入りデータの読み込みエラー: $err')),
                );
              },
              // データ読み込み中
              loading: () => const Center(child: CircularProgressIndicator()),
              // エラー発生時
              error: (err, stack) => Center(child: Text('エラーが発生しました: $err')),
            ),
          ),
        ],
      ),
    );
  }
}
