"""手持ち撮影を模した写真で、位置合わせの精度と、運用の流れ(差分処理・失敗の扱い)を確かめる。

畑の写真を「景色」とみなし、毎日少しずつ違う向き・距離・傾きで撮った写真を作る。
写真ごとの本当の変換は分かっているので、推定した変換との誤差を画素で測れる。
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image

from field_timelapse import photos
from field_timelapse.cli import main
from field_timelapse.pipeline import Options, process_subject

REPO = Path(__file__).resolve().parents[2]
SCENE = REPO / "web" / "pages" / "images" / "IMG_3298.jpg"
W, H = 1600, 1200


def _camera(rng: np.random.Generator, strength: float = 1.0) -> np.ndarray:
    """景色 → 写真 の変換(手持ちのズレ: 回転・距離・移動・少しのあおり)。"""
    ang = np.deg2rad(rng.uniform(-4, 4) * strength)
    s = 1 + rng.uniform(-0.07, 0.07) * strength
    tx, ty = rng.uniform(-0.05, 0.05, 2) * strength * np.array([W, H])
    c = np.array([[1, 0, -W / 2], [0, 1, -H / 2], [0, 0, 1]])
    r = np.array([[s * np.cos(ang), -s * np.sin(ang), 0], [s * np.sin(ang), s * np.cos(ang), 0], [0, 0, 1]])
    p = np.eye(3)
    p[2, :2] = rng.uniform(-2e-5, 2e-5, 2) * strength
    t = np.array([[1, 0, W / 2 + tx], [0, 1, H / 2 + ty], [0, 0, 1]])
    return t @ p @ r @ c


def _shoot(scene: np.ndarray, G: np.ndarray, day: int, rng, path: Path, *, exif: bool = True):
    img = cv2.warpPerspective(scene, G, (W, H), borderMode=cv2.BORDER_REFLECT)
    # 日によって明るさが違う
    img = np.clip(img.astype(np.float32) * rng.uniform(0.8, 1.2), 0, 255).astype(np.uint8)
    # 作物が育つ: 真ん中あたりに毎日少しずつ違う緑の斑点を描く
    for _ in range(40 + day * 8):
        x, y = rng.integers(W // 3, 2 * W // 3), rng.integers(H // 3, 2 * H // 3)
        cv2.circle(img, (int(x), int(y)), int(rng.integers(6, 18)), (40, int(rng.integers(120, 200)), 40), -1)
    im = Image.fromarray(img)
    ex = Image.Exif()
    if exif:
        taken = datetime(2026, 5, 1, 7, 30) + timedelta(days=day, minutes=int(rng.integers(0, 90)))
        ex.get_ifd(0x8769)[36867] = taken.strftime("%Y:%m:%d %H:%M:%S")
    im.save(path, quality=90, exif=ex)


@pytest.fixture(scope="module")
def scene() -> np.ndarray:
    if not SCENE.exists():
        pytest.skip("景色の写真がありません")
    rgb = photos.load_rgb(SCENE, 2400)
    return cv2.resize(rgb, (int(W * 1.15), int(H * 1.15)))


@pytest.fixture()
def field(tmp_path, scene):
    rng = np.random.default_rng(7)
    src = tmp_path / "photos" / "オリーブ"
    src.mkdir(parents=True)
    truth = {}
    # 撮った順とファイル名の順をわざと食い違わせる
    for day in range(8):
        G = _camera(rng)
        name = f"IMG_{9000 - day * 7}.jpg"
        _shoot(scene, G, day, rng, src / name)
        truth[name] = G
    return src, truth


def _error_px(H_est: np.ndarray, H_true: np.ndarray) -> float:
    xs, ys = np.meshgrid(np.linspace(W * 0.1, W * 0.9, 9), np.linspace(H * 0.1, H * 0.9, 7))
    pts = np.float32(np.stack([xs.ravel(), ys.ravel()], 1)).reshape(-1, 1, 2)
    a = cv2.perspectiveTransform(pts, H_est).reshape(-1, 2)
    b = cv2.perspectiveTransform(pts, H_true).reshape(-1, 2)
    return float(np.linalg.norm(a - b, axis=1).max())


def test_capture_time_reads_exif(field):
    src, _ = field
    p = sorted(src.iterdir())[0]
    taken, source = photos.capture_time(p)
    assert source == "exif" and taken.year == 2026


def test_alignment_accuracy_and_video(field, tmp_path):
    src, truth = field
    out = tmp_path / "out"
    r = process_subject(src, out, Options(fps=8, long_side=1600))
    assert r.photos == 8 and r.aligned == 8 and not r.failed

    state = json.loads((out / "state.json").read_text())
    ref = state["reference"]
    # 基準は撮影日時がいちばん古い写真(ファイル名の順ではない)
    assert ref == min(state["frames"], key=lambda k: state["frames"][k]["taken"])
    G_ref = truth[ref]
    for name, rec in state["frames"].items():
        H_est = np.array(rec["H"]).reshape(3, 3)
        H_true = G_ref @ np.linalg.inv(truth[name])      # 写真 → 景色 → 基準の写真
        err = _error_px(H_est, H_true)
        assert err < 3.0, f"{name}: 誤差 {err:.2f}px"

    mp4 = out / "timelapse.mp4"
    assert mp4.exists() and mp4.stat().st_size > 10_000
    if shutil.which("ffprobe"):
        n = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                            "-show_entries", "stream=nb_read_frames,width,height", "-of", "json", str(mp4)],
                           capture_output=True, text=True, check=True)
        info = json.loads(n.stdout)["streams"][0]
        assert int(info["nb_read_frames"]) >= 8
        assert int(info["width"]) % 2 == 0 and int(info["height"]) % 2 == 0


def test_incremental_and_failure(field, tmp_path, scene):
    src, truth = field
    out = tmp_path / "out"
    process_subject(src, out, Options(long_side=1600))
    first = {k: v["H"] for k, v in json.loads((out / "state.json").read_text())["frames"].items()}

    # 次の日の写真が1枚増え、関係のない写真(空)も1枚混じる
    rng = np.random.default_rng(99)
    _shoot(scene, _camera(rng), 9, rng, src / "IMG_9100.jpg")
    sky = np.full((H, W, 3), (200, 220, 240), np.uint8)
    Image.fromarray(sky).save(src / "IMG_9101.jpg", quality=90)

    r = process_subject(src, out, Options(long_side=1600))
    assert r.new == 2
    assert r.aligned == 9
    assert [k for k, _ in r.failed] == ["IMG_9101.jpg"]
    state = json.loads((out / "state.json").read_text())
    # 前からある写真は計算し直していない
    assert all(state["frames"][k]["H"] == h for k, h in first.items())
    assert "IMG_9101.jpg" in (out / "report.txt").read_text()

    # 写真を消すと、その位置合わせ済みの画像も消える
    (src / "IMG_9100.jpg").unlink()
    r = process_subject(src, out, Options(long_side=1600))
    assert r.aligned == 8
    assert len(list((out / "aligned").glob("*.jpg"))) == 8


def test_cli_build_and_status(field, tmp_path, capsys):
    src, _ = field
    root = src.parent
    assert main(["build", str(root), "-q", "--size", "1600"]) == 0
    assert (root / "_timelapse" / "オリーブ" / "timelapse.mp4").exists()
    assert main(["status", str(root)]) == 0
    assert "オリーブ: 写真 8 枚 / 動画に使用 8 / 失敗 0" in capsys.readouterr().out
    # もう一度流しても、新しい写真が無ければ何もしない
    mp4 = root / "_timelapse" / "オリーブ" / "timelapse.mp4"
    before = mp4.stat().st_mtime
    assert main(["build", str(root), "-q", "--size", "1600"]) == 0
    assert mp4.stat().st_mtime == before
