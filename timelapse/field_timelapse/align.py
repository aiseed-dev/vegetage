"""特徴点マッチングで、手持ちの写真を基準の構図に重ねる。

SIFT で特徴点を取り、比率テストで対応を絞り、RANSAC でホモグラフィ(射影変換)を推定する。
推定した変換が手持ち撮影のズレとして妥当か(縮尺・回転・歪み)を確かめ、
おかしければ相似変換(移動・回転・拡大縮小だけ)で推定し直す。
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

RATIO = 0.75            # Lowe の比率テスト
RANSAC_PX = 4.0         # RANSAC の許容誤差(作業解像度の画素)
MIN_INLIERS = 25        # これ未満の対応では信用しない
MAX_SCALE = 1.6         # 基準に対する縮尺の許容範囲(1/MAX_SCALE 〜 MAX_SCALE)
MAX_AREA_RATIO = 2.2    # 変換後の画像の面積比の許容範囲


@dataclass
class Features:
    keypoints: np.ndarray       # (N, 2) float32 の座標
    descriptors: np.ndarray     # (N, 128) float32
    size: tuple[int, int]       # (幅, 高さ)


@dataclass
class Match:
    ok: bool
    H: np.ndarray | None        # 3x3。写真 → 基準キャンバス
    inliers: int
    model: str                  # "homography" / "similarity"
    reason: str = ""


_sift = None


def _detector():
    global _sift
    if _sift is None:
        _sift = cv2.SIFT_create(nfeatures=5000)
    return _sift


def features(rgb: np.ndarray, mask: np.ndarray | None = None) -> Features:
    """特徴点。mask(uint8, 0/255)を渡すと、その範囲だけから取る(位置合わせ後の黒い余白を避ける)。"""
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    # 明るさの違い(朝・夕・曇り)に強くするため、局所コントラストをそろえる
    gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    if mask is not None:
        mask = cv2.erode(mask, np.ones((15, 15), np.uint8))
    kps, desc = _detector().detectAndCompute(gray, mask)
    pts = np.array([k.pt for k in kps], dtype=np.float32).reshape(-1, 2)
    if desc is None:
        desc = np.zeros((0, 128), np.float32)
    return Features(pts, desc.astype(np.float32), (rgb.shape[1], rgb.shape[0]))


def _good_matches(src: Features, dst: Features) -> tuple[np.ndarray, np.ndarray]:
    if len(src.descriptors) < 2 or len(dst.descriptors) < 2:
        return np.zeros((0, 2), np.float32), np.zeros((0, 2), np.float32)
    matcher = cv2.FlannBasedMatcher({"algorithm": 1, "trees": 5}, {"checks": 64})
    pairs = matcher.knnMatch(src.descriptors, dst.descriptors, k=2)
    good = [m for m, n in (p for p in pairs if len(p) == 2) if m.distance < RATIO * n.distance]
    s = np.float32([src.keypoints[m.queryIdx] for m in good]).reshape(-1, 2)
    d = np.float32([dst.keypoints[m.trainIdx] for m in good]).reshape(-1, 2)
    return s, d


def plausible(H: np.ndarray, src_size: tuple[int, int], dst_size: tuple[int, int]) -> str:
    """手持ちのズレとして妥当なら ""、だめなら理由。"""
    w, h = src_size
    corners = np.float32([[0, 0], [w, 0], [w, h], [0, h]]).reshape(-1, 1, 2)
    warped = cv2.perspectiveTransform(corners, H).reshape(-1, 2)
    if not np.all(np.isfinite(warped)):
        return "変換が発散"
    if not cv2.isContourConvex(warped.astype(np.float32)):
        return "変換後の形がねじれている"
    area = cv2.contourArea(warped.astype(np.float32))
    ratio = area / float(w * h) if w * h else 0
    if not (1 / MAX_AREA_RATIO < ratio < MAX_AREA_RATIO):
        return f"縮尺が大きく違う(面積比 {ratio:.2f})"
    sides = np.linalg.norm(np.roll(warped, -1, axis=0) - warped, axis=1)
    if sides.max() / max(sides.min(), 1e-6) > 3.0 * max(w, h) / min(w, h):
        return "歪みが大きすぎる"
    # 変換後の画像が基準の画面とほとんど重ならないなら失敗
    dw, dh = dst_size
    canvas = np.float32([[0, 0], [dw, 0], [dw, dh], [0, dh]])
    inter, _ = cv2.intersectConvexConvex(warped.astype(np.float32), canvas)
    if inter < 0.3 * dw * dh:
        return "基準の構図と重なりが少ない"
    return ""


def match(src: Features, dst: Features) -> Match:
    """写真(src)を基準キャンバス(dst)へ重ねる変換を求める。"""
    s, d = _good_matches(src, dst)
    if len(s) < MIN_INLIERS:
        return Match(False, None, len(s), "", f"対応点が少ない({len(s)})")

    H, inl = cv2.findHomography(s, d, cv2.RANSAC, RANSAC_PX, maxIters=5000, confidence=0.999)
    n = int(inl.sum()) if inl is not None else 0
    if H is not None and n >= MIN_INLIERS and not plausible(H, src.size, dst.size):
        return Match(True, H, n, "homography")

    # 射影変換がだめなら、移動・回転・拡大縮小だけで推定し直す
    A, inl2 = cv2.estimateAffinePartial2D(s, d, method=cv2.RANSAC, ransacReprojThreshold=RANSAC_PX,
                                          maxIters=5000, confidence=0.999)
    n2 = int(inl2.sum()) if inl2 is not None else 0
    if A is not None and n2 >= MIN_INLIERS:
        H2 = np.vstack([A, [0, 0, 1]])
        scale = float(np.sqrt(abs(np.linalg.det(A[:, :2]))))
        why = plausible(H2, src.size, dst.size)
        if not why and 1 / MAX_SCALE < scale < MAX_SCALE:
            return Match(True, H2, n2, "similarity")
        return Match(False, None, n2, "similarity", why or f"縮尺が大きく違う({scale:.2f})")
    return Match(False, None, max(n, n2), "", f"一致する対応点が少ない({max(n, n2)})")


def warp(rgb: np.ndarray, H: np.ndarray, size: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    """写真を基準キャンバスへ変形する。返り値は(画像, 写っている範囲のマスク)。"""
    out = cv2.warpPerspective(rgb, H, size, flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_CONSTANT)
    mask = cv2.warpPerspective(np.full(rgb.shape[:2], 255, np.uint8), H, size,
                               flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT)
    return out, mask
