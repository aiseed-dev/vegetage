// lib/features/vegetable_detail/widgets/image_carousel_section.dart

import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import 'package:cached_network_image/cached_network_image.dart';
import 'package:vegetage/core/providers/providers.dart';
import 'package:vegetage/core/models/vegetable_image.dart';

class ImageCarouselSection extends ConsumerWidget {
  const ImageCarouselSection({
    super.key,
    required this.hasImages,
    required this.imageId,
    required this.imageCategory,
  });

  final bool hasImages;
  final String imageId;
  final String imageCategory;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // hasImages フラグが false なら、何も表示せずに終了
    if (!hasImages) {
      return const SizedBox.shrink();
    }

    // 画像情報を非同期で取得するためのProviderを監視
    final imageInfoAsync = ref.watch(imageInfoProvider(
        ImageInfoArgs(imageId: imageId, imageCategory: imageCategory)
    ));

    // AsyncValue.when を使って、データの状態に応じてUIを構築
    return imageInfoAsync.when(
      data: (imageInfoList) {
        // info.json が空、または存在しない場合は何も表示しない
        if (imageInfoList.isEmpty) {
          return const SizedBox.shrink();
        }

        // 画像が1枚だけの場合は、カルーセルではなく静的な画像として表示
        if (imageInfoList.length == 1) {
          final imageUrl = "https://aiseed.page/images/$imageCategory/$imageId/${imageInfoList.first.filename}";
          return _SingleStaticImage(
            imageUrl: imageUrl,
            caption: imageInfoList.first.caption,
          );
        }

        // 画像が2枚以上あれば、手動操作のカルーセルを表示
        return _ManualCarousel(
          imageId: imageId,
          imageCategory: imageCategory,
          imageInfoList: imageInfoList,
        );
      },
      // ローディング中やエラー時は、シンプルなプレースホルダーを表示
      loading: () => const _LoadingPlaceholder(),
      error: (err, stack) => const _ErrorPlaceholder(),
    );
  }
}

class _ManualCarousel extends StatefulWidget {
  const _ManualCarousel({
    required this.imageId,
    required this.imageCategory,
    required this.imageInfoList,
  });

  final String imageId;
  final String imageCategory;
  final List<VegetableImage> imageInfoList;

  @override
  State<_ManualCarousel> createState() => _ManualCarouselState();
}

class _ManualCarouselState extends State<_ManualCarousel> {
  // ★★★ PageViewを操作するためのコントローラー ★★★
  final PageController _pageController = PageController();
  int _currentImageIndex = 0;

  @override
  void dispose() {
    _pageController.dispose(); // 不要になったら必ずdisposeする
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final imageUrls = widget.imageInfoList.map((info) {
      return Uri.parse('https://aiseed.page')
          .replace(pathSegments: [
        'images',
        widget.imageCategory,
        widget.imageId,
        info.filename
      ])
          .toString();
    }).toList();

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: Column(
        children: [
          Stack(
            alignment: Alignment.center,
            children: [
              // ★★★ CarouselSlider の代わりに PageView を使う ★★★
              SizedBox(
                height: 250.0,
                child: PageView.builder(
                  controller: _pageController,
                  itemCount: imageUrls.length,
                  itemBuilder: (context, index) {
                    return _buildSingleImage(imageUrls[index]);
                  },
                  onPageChanged: (index) {
                    setState(() {
                      _currentImageIndex = index;
                    });
                  },
                ),
              ),
              // 左右のナビゲーションボタン
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  IconButton(
                    icon: const Icon(Icons.arrow_back_ios_new, color: Colors.white, size: 20),
                    onPressed: () {
                      _pageController.previousPage(
                        duration: const Duration(milliseconds: 300),
                        curve: Curves.easeInOut,
                      );
                    },
                    style: IconButton.styleFrom(backgroundColor: Colors.black.withOpacity(0.4)),
                  ),
                  IconButton(
                    icon: const Icon(Icons.arrow_forward_ios, color: Colors.white, size: 20),
                    onPressed: () {
                      _pageController.nextPage(
                        duration: const Duration(milliseconds: 300),
                        curve: Curves.easeInOut,
                      );
                    },
                    style: IconButton.styleFrom(backgroundColor: Colors.black.withOpacity(0.4)),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 8),

          // キャプションとページインジケータ
          _buildCaptionAndIndicator(context),
        ],
      ),
    );
  }

  Widget _buildCaptionAndIndicator(BuildContext context) {
    final currentCaption = widget.imageInfoList[_currentImageIndex].caption;

    return Column(
      children: [
        if (currentCaption != null && currentCaption.isNotEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16.0),
            child: Text(
              currentCaption,
              style: Theme.of(context).textTheme.bodySmall,
              textAlign: TextAlign.center,
            ),
          ),

        // ページインジケータ（点々）
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: widget.imageInfoList.asMap().entries.map((entry) {
            return GestureDetector(
              onTap: () {
                _pageController.animateToPage(
                  entry.key,
                  duration: const Duration(milliseconds: 300),
                  curve: Curves.easeInOut,
                );
              },
              child: Container(
                width: 8.0,
                height: 8.0,
                margin: const EdgeInsets.symmetric(vertical: 8.0, horizontal: 4.0),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: (Theme.of(context).brightness == Brightness.dark ? Colors.white : Colors.black)
                      .withOpacity(_currentImageIndex == entry.key ? 0.9 : 0.3),
                ),
              ),
            );
          }).toList(),
        ),
      ],
    );
  }
}
/// 画像が1枚だけの場合に表示する静的なウィジェット
class _SingleStaticImage extends StatelessWidget {
  const _SingleStaticImage({required this.imageUrl, this.caption});

  final String imageUrl;
  final String? caption;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(8.0),
      child: Column(
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(12.0),
            child: _buildSingleImage(imageUrl),
          ),
          /*
          if (caption != null && caption!.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              caption!,
              style: Theme.of(context).textTheme.bodySmall,
              textAlign: TextAlign.center,
            ),
          ]
           */
        ],
      ),
    );
  }
}

/// ローディング中に表示するプレースホルダー
class _LoadingPlaceholder extends StatelessWidget {
  const _LoadingPlaceholder();

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 250,
      margin: const EdgeInsets.all(8.0),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceVariant.withOpacity(0.5),
        borderRadius: BorderRadius.circular(12.0),
      ),
      child: const Center(child: CircularProgressIndicator()),
    );
  }
}

/// エラー時に表示するプレースホルダー
class _ErrorPlaceholder extends StatelessWidget {
  const _ErrorPlaceholder();

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 250,
      margin: const EdgeInsets.all(8.0),
      child: const Center(child: Text('画像の読み込みに失敗しました')),
    );
  }
}

/// 画像1枚を表示するための共通ウィジェット
Widget _buildSingleImage(String imageUrl) {
  return CachedNetworkImage(
    imageUrl: imageUrl,
    fit: BoxFit.cover,
    width: double.infinity,
    placeholder: (context, url) => const Center(child: CircularProgressIndicator()),
    errorWidget: (context, url, error) => const Center(
      child: Icon(Icons.error_outline, size: 48, color: Colors.grey),
    ),
  );
}