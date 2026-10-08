import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:vegetage/features/home/vegetable_list_screen.dart';
import 'package:vegetage/features/vegetable_detail/vegetable_detail_screen.dart';

class AppShell extends StatelessWidget {
  const AppShell({super.key, required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) {
    // 将来的に、ボトムナビゲーションバーなどを置く場合は、
    // この Scaffold に追加していくことになります。
    return Scaffold(
      body: child,
    );
  }
}

final router = GoRouter(
  // アプリの初期ルート
  initialLocation: '/vegetables',
  routes: [
    // --- 親ルート：アプリの骨格（シェル）を定義 ---
    ShellRoute(
      builder: (context, state, child) {
        // このシェルの中に入る画面は、全て `AppShell` にラップされる
        return AppShell(child: child);
      },
      routes: [
        // --- 子ルート：シェルの中に表示される画面たち ---
        GoRoute(
          path: '/vegetables', // 品目一覧
          builder: (context, state) => const VegetableListScreen(), // 仮に品目一覧
          routes: [
            // ★★★ さらに孫ルートとして、詳細画面を定義 ★★★
            GoRoute(
              path: ':id', // `/vegetables/:id` というパスになる
              builder: (context, state) {
                final vegetableId = state.pathParameters['id']!;
                return VegetableDetailScreen(vegetableId: vegetableId);
              },
            ),
          ],
        ),
        // TODO: 品種 (`/varieties`) や料理 (`/dishes`) のルートも同様にネスト構造で追加
      ],
    ),
  ],
);