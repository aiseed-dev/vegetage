"""位置合わせ済みの写真を、タイムラプス動画(MP4)にする。

- 写っていない端(位置合わせで生じる黒い余白)は、1つ前のコマで埋める
- 四辺を少し切って、端の揺れを目立たなくする
- 左下に撮影日、左上に被写体の名前を入れる
- ffmpeg で H.264 / yuv420p(スマホやブラウザでそのまま再生できる形)に書き出す
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
    "C:/Windows/Fonts/meiryob.ttc",
]


def _font(size: int) -> ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            try:
                # Noto Sans CJK の .ttc は 0 番が JP
                return ImageFont.truetype(path, size, index=0)
            except OSError:
                continue
    return ImageFont.load_default()


def _label(img: Image.Image, text: str, xy: tuple[int, int], size: int, anchor: str) -> None:
    draw = ImageDraw.Draw(img)
    font = _font(size)
    draw.text(xy, text, font=font, fill=(255, 255, 255), anchor=anchor,
              stroke_width=max(2, size // 12), stroke_fill=(0, 0, 0))


def compose(frames: list[tuple[Path, datetime]], *, crop: float = 0.03,
            date_label: bool = True, title: str | None = None):
    """動画のコマを順に返す(RGB の PIL.Image)。"""
    prev = None
    for path, taken in frames:
        rgb = cv2.cvtColor(cv2.imread(str(path)), cv2.COLOR_BGR2RGB)
        mask = cv2.imread(str(path.with_suffix(".mask.png")), cv2.IMREAD_GRAYSCALE)
        if prev is not None and mask is not None and prev.shape == rgb.shape:
            # 境目がくっきり出ないよう、マスクを少しぼかして混ぜる
            m = cv2.GaussianBlur(cv2.erode(mask, np.ones((5, 5), np.uint8)), (0, 0), 3).astype(np.float32) / 255
            rgb = (rgb * m[..., None] + prev * (1 - m[..., None])).astype(np.uint8)
        prev = rgb
        h, w = rgb.shape[:2]
        cx, cy = int(w * crop), int(h * crop)
        out = rgb[cy:h - cy, cx:w - cx]
        # H.264(yuv420p)は縦横とも偶数が必要
        out = out[: out.shape[0] // 2 * 2, : out.shape[1] // 2 * 2]
        img = Image.fromarray(np.ascontiguousarray(out))
        size = max(18, img.height // 22)
        margin = size
        if date_label:
            _label(img, taken.strftime("%Y-%m-%d"), (margin, img.height - margin), size, "ls")
        if title:
            _label(img, title, (margin, margin), int(size * 0.8), "lt")
        yield img


def render(frames: list[tuple[Path, datetime]], dest: Path, *, fps: float = 8.0, crop: float = 0.03,
           date_label: bool = True, title: str | None = None) -> Path:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg が見つかりません(sudo apt install ffmpeg)")
    with tempfile.TemporaryDirectory(prefix="timelapse-") as tmp:
        n = 0
        for n, img in enumerate(compose(frames, crop=crop, date_label=date_label, title=title), 1):
            img.save(Path(tmp) / f"{n:05d}.jpg", quality=93)
        if n == 0:
            raise RuntimeError("動画にするコマがありません")
        part = dest.with_suffix(".part.mp4")
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", str(Path(tmp) / "%05d.jpg"),
               # 最後のコマ(いちばん新しい日)を 1.5 秒止めて見せる
               "-vf", "tpad=stop_mode=clone:stop_duration=1.5",
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium",
               "-movflags", "+faststart", "-r", str(fps), str(part)]
        subprocess.run(cmd, check=True)
        part.replace(dest)
    return dest
