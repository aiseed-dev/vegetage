// vegetable_detail_screen.dart
import 'dart:typed_data';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:flutter/rendering.dart';
import 'package:share_plus/share_plus.dart';
import 'package:vegetage/core/models/vegetable.dart';
import 'package:vegetage/core/providers/providers.dart';
import 'package:vegetage/shared/constants/app_strings.dart';
import 'package:vegetage/features/vegetable_detail/widgets/image_carousel_section.dart';

class VegetableDetailScreen extends ConsumerWidget {
  final String vegetableId;

  const VegetableDetailScreen({super.key, required this.vegetableId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // --- リダイレクト処理 ---
    final redirectTo = ref.watch(redirectProvider(vegetableId));
    if (redirectTo != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        context.replace('/vegetables/$redirectTo');
      });
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    // --- データ取得 ---
    final detailAsync = ref.watch(vegetableDetailProvider(vegetableId));

    return Scaffold(
      appBar: AppBar(
        title: detailAsync.when(
          data: (veg) => Text(veg.content.ja.displayName),
          loading: () => const Text(''), // ローディング中はタイトルなし
          error: (_, _) => const Text(AppStrings.errorTitle),
        ),
      ),
      body: detailAsync.when(
        data: (veg) {
          final jaContent = veg.content.ja;
          final globalInfo = veg.globalInfo;
          final bool hasImages = globalInfo.hasImages ?? false;

          return SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // --- 3. 全てのコンテンツを順番に配置 ---
                if (hasImages)
                ImageCarouselSection(
                  hasImages: hasImages,
                  imageId: globalInfo.url,
                  imageCategory: 'vegetable',
                ),
                _IntroductionSection(content: jaContent),
                _SectionWidget(
                  title: AppStrings.sectionTitlePracticalTips,
                  oneliner: jaContent.practicalOneliner,
                  content: jaContent.practicalTips,
                ),
                // --- 各セクションをウィジェットとして呼び出す ---
                _SectionWidget(
                  title: AppStrings.sectionTitleNutrition,
                  oneliner: jaContent.nutritionOneliner,
                  content: jaContent.nutritionBenefits,
                ),
                _SectionWidget(
                  title: AppStrings.sectionTitleHonestAssessment,
                  oneliner: jaContent.honestOneliner,
                  content: jaContent.honestAssessment,
                ),
                _SectionWidget(
                  title: AppStrings.sectionTitleCulturalBackground,
                  content: jaContent.culturalBackground,
                ),
                _SectionWidget(
                  title: AppStrings.sectionTitleSafetyNotes,
                  oneliner: jaContent.safetyOneliner,
                  content: jaContent.safetyNotes,
                ),
                // TODO: Relationships, GlobalInfoなどを表示するウィジェットもここに追加
                const SizedBox(height: 40),
                // ★★★ QRコードセクションをここに追加 ★★★
                _QrCodeSection(vegetableId: globalInfo.url),
                // _PromptSuggestionSection(vegetableName: jaContent.displayName),
                const SizedBox(height: 40),
              ],
            ),
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, stack) => _buildErrorView(context, err),
      ),
    );
  }

  Widget _buildErrorView(BuildContext context, Object error) {
    return Scaffold(
      appBar: AppBar(title: const Text(AppStrings.errorTitle)),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Text('データの読み込みに失敗しました:\n$error'),
        ),
      ),
    );
  }
}


/// 導入部分（oneliner と description）を表示する専用ウィジェット
class _IntroductionSection extends StatelessWidget {
  const _IntroductionSection({required this.content});
  final ContentJa content;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            content.oneliner,
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 16),
          // TODO: ここを将来的にMarkdown対応ウィジェットに差し替える
          Text(
            content.description,
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(height: 1.6),
          ),
        ],
      ),
    );
  }
}

/// 各セクションのUIを生成する再利用可能なウィジェット
class _SectionWidget extends StatelessWidget {
  const _SectionWidget({
    required this.title,
    required this.content,
    this.oneliner,
  });

  final String title;
  final String? oneliner;
  final String content;

  @override
  Widget build(BuildContext context) {
    // onelinerもcontentも空の場合は、セクション全体を表示しない
    if ((oneliner == null || oneliner!.isEmpty) && content.isEmpty) {
      return const SizedBox.shrink();
    }

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const Divider(thickness: 1, height: 24),
          if (oneliner != null && oneliner!.isNotEmpty) ...[
            Text(
              '“$oneliner”',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontStyle: FontStyle.italic,
                color: Theme.of(context).colorScheme.secondary,
              ),
            ),
            const SizedBox(height: 12),
          ],
          if (content.isNotEmpty)
          // TODO: ここを将来的にMarkdown対応ウィジェットに差し替える
            Text(
              content,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(height: 1.5),
            ),
        ],
      ),
    );
  }
}

class _QrCodeSection extends StatefulWidget {
  const _QrCodeSection({required this.vegetableId});
  final String vegetableId;

  @override
  State<_QrCodeSection> createState() => _QrCodeSectionState();
}

class _QrCodeSectionState extends State<_QrCodeSection> {
  // QrImageViewウィジェットを画像としてキャプチャするためのキー
  final GlobalKey _qrKey = GlobalKey();

  Future<void> _shareQrCode() async {
    try {
      // 1. QrImageView を画像データ (bytes) に変換
      RenderRepaintBoundary boundary =
      _qrKey.currentContext!.findRenderObject() as RenderRepaintBoundary;
      ui.Image image = await boundary.toImage(pixelRatio: 3.0);
      ByteData? byteData = await image.toByteData(
          format: ui.ImageByteFormat.png);
      if (byteData == null) {
        throw Exception("Failed to convert widget to image data.");
      }
      final Uint8List pngBytes = byteData.buffer.asUint8List();

      // --- 2. 共有処理 ---
      // share_plus は XFile を使ってプラットフォームの違いを吸収してくれる
      final xFile = XFile.fromData(
        pngBytes,
        name: '${widget.vegetableId}_qr.png',
        mimeType: 'image/png',
        // lastModified と length は自動で設定される
      );

      await Share.shareXFiles(
        [xFile],
        text: '${widget.vegetableId} - Vegetage QRコード',
      );
    } catch (e) {
      // mounted プロパティで、ウィジェットがまだ画面に存在するか確認
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('QRコードの共有に失敗しました: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final String qrData = "https://aiseed.page/#/vegetables/${widget.vegetableId}";

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 24.0),
      child: Center(
        child: Column(
          children: [
            // ... (Divider, Title などは同じ) ...

            // ★★★ RepaintBoundary で QrImageView をラップする ★★★
            RepaintBoundary(
              key: _qrKey,
              child: Container(
                padding: const EdgeInsets.all(12.0),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16.0),
                ),
                child: QrImageView(
                  data: qrData,
                  version: QrVersions.auto,
                  size: 180.0,
                  gapless: false,
                ),
              ),
            ),
            const SizedBox(height: 24),

            // ★★★ 共有ボタンを追加 ★★★
            ElevatedButton.icon(
              onPressed: _shareQrCode,
              icon: const Icon(Icons.share),
              label: const Text('QRコードを共有/保存'),
            ),

            const SizedBox(height: 16),
            Text(
              qrData,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
