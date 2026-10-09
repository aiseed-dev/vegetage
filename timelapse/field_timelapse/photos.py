"""写真を読む: 向きの補正、撮影日時(EXIF)。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

try:  # iPhone の HEIC。入っていなければ JPEG だけ扱う
    from pillow_heif import register_heif_opener

    register_heif_opener()
    HEIF = True
except ImportError:  # pragma: no cover
    HEIF = False

SUFFIXES = {".jpg", ".jpeg", ".png"} | ({".heic", ".heif"} if HEIF else set())

_EXIF_IFD = 0x8769
_DATETIME_ORIGINAL = 36867
_OFFSET_TIME_ORIGINAL = 36881
_DATETIME = 306


def is_photo(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUFFIXES and not path.name.startswith(".")


def load_rgb(path: Path, long_side: int | None = None) -> np.ndarray:
    """RGB の配列で読む。EXIF の向きを反映し、long_side を指定すれば長辺をそこまで縮める。"""
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        if long_side and max(im.size) > long_side:
            scale = long_side / max(im.size)
            im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
        return np.asarray(im)


def _parse_exif_time(value: str, offset: str | None) -> datetime | None:
    try:
        dt = datetime.strptime(value.strip().rstrip("\x00"), "%Y:%m:%d %H:%M:%S")
    except (ValueError, AttributeError):
        return None
    if offset:
        try:
            sign = -1 if offset.strip()[0] == "-" else 1
            hh, mm = offset.strip()[1:].split(":")
            dt = dt.replace(tzinfo=timezone(sign * timedelta(hours=int(hh), minutes=int(mm))))
        except (ValueError, IndexError):
            pass
    return dt


def capture_time(path: Path) -> tuple[datetime, str]:
    """撮影日時と、その出どころ("exif" か "mtime")。

    スマホの写真は EXIF の DateTimeOriginal に撮影時刻が入っている。無ければファイルの更新時刻。
    タイムゾーンの情報があれば付けるが、並べ替えには現地時刻(naive)だけを使う。
    """
    try:
        with Image.open(path) as im:
            exif = im.getexif()
            sub = exif.get_ifd(_EXIF_IFD)
            dt = _parse_exif_time(sub.get(_DATETIME_ORIGINAL) or exif.get(_DATETIME) or "",
                                  sub.get(_OFFSET_TIME_ORIGINAL))
            if dt:
                return dt, "exif"
    except OSError:
        pass
    return datetime.fromtimestamp(path.stat().st_mtime), "mtime"
