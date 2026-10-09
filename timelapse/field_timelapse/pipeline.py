"""被写体ごとのフォルダを処理する: 位置合わせ → 動画。

入力:  <ROOT>/<被写体>/*.jpg|heic …   (スマホから同期されたフォルダ)
出力:  <OUT>/<被写体>/
         timelapse.mp4      できあがりの動画
         aligned/*.jpg      基準の構図に重ねた写真(1枚ずつ)
         state.json         処理済みの記録(次回は新しい写真だけ処理する)
         report.txt         何枚使えて、どれが失敗したか

基準の構図は、その被写体でいちばん古い写真(または --reference で指定した写真)。
新しい写真は、撮影日時がいちばん近い位置合わせ済みの写真と、基準の写真の両方に合わせてみて、
対応点が多いほうを採る。作物は日に日に育つので、近い日の写真のほうが合わせやすい。
"""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from . import align, photos, video

log = logging.getLogger(__name__)

STATE_VERSION = 1
WORK_LONG_SIDE = 1920       # 位置合わせと動画の解像度(長辺)


@dataclass
class Options:
    fps: float = 8.0
    long_side: int = WORK_LONG_SIDE
    date_label: bool = True
    title: str | None = None
    crop: float = 0.03          # 端の揺れを隠すため、四辺をこの割合だけ切る
    reference: str | None = None


@dataclass
class Result:
    subject: str
    photos: int = 0
    new: int = 0
    aligned: int = 0
    failed: list[tuple[str, str]] = field(default_factory=list)
    video: Path | None = None


def subjects(root: Path) -> list[Path]:
    """ROOT の下の被写体フォルダ。ROOT 自体に写真があれば ROOT を1つの被写体として扱う。
    名前が _ や . で始まるフォルダは無視する(出力先など)。"""
    if any(photos.is_photo(p) for p in root.iterdir()):
        return [root]
    return sorted(p for p in root.iterdir()
                  if p.is_dir() and not p.name.startswith(("_", ".")) and
                  any(photos.is_photo(q) for q in p.iterdir()))


def _empty_state() -> dict:
    return {"version": STATE_VERSION, "reference": None, "canvas": None, "frames": {}}


def _remove_aligned(out: Path, rel: str | None) -> None:
    if rel:
        (out / rel).unlink(missing_ok=True)
        (out / rel).with_suffix(".mask.png").unlink(missing_ok=True)


def _load_state(path: Path) -> dict:
    if path.exists():
        try:
            state = json.loads(path.read_text("utf-8"))
            if state.get("version") == STATE_VERSION:
                return state
        except json.JSONDecodeError:
            log.warning("state.json が壊れているので作り直します: %s", path)
    return _empty_state()


def _save_state(path: Path, state: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1), "utf-8")
    tmp.replace(path)


def _fingerprint(p: Path) -> dict:
    st = p.stat()
    return {"mtime": st.st_mtime, "size": st.st_size}


def process_subject(src: Path, out: Path, opts: Options, *, rebuild: bool = False) -> Result:
    name = src.name
    out.mkdir(parents=True, exist_ok=True)
    state_path = out / "state.json"
    if rebuild:
        shutil.rmtree(out / "aligned", ignore_errors=True)
        state_path.unlink(missing_ok=True)
    state = _load_state(state_path)
    if opts.reference and state.get("reference") != opts.reference:
        # 基準を変えたら全部やり直し
        shutil.rmtree(out / "aligned", ignore_errors=True)
        state = _empty_state()
    aligned_dir = out / "aligned"
    aligned_dir.mkdir(exist_ok=True)
    res = Result(name)

    files = sorted(p for p in src.iterdir() if photos.is_photo(p))
    res.photos = len(files)
    frames: dict = state["frames"]

    # 消えた写真の記録を落とす
    names = {p.name for p in files}
    for gone in [k for k in frames if k not in names]:
        _remove_aligned(out, frames.pop(gone).get("aligned"))

    # 撮影日時を読む(新しい写真・変わった写真だけ)
    todo = []
    for p in files:
        fp = _fingerprint(p)
        rec = frames.get(p.name)
        if rec and rec.get("mtime") == fp["mtime"] and rec.get("size") == fp["size"]:
            continue
        taken, source = photos.capture_time(p)
        if rec:
            _remove_aligned(out, rec.get("aligned"))
        frames[p.name] = {**fp, "taken": taken.replace(tzinfo=None).isoformat(timespec="seconds"),
                          "taken_source": source, "status": "pending"}
        todo.append(p.name)
    res.new = len(todo)

    # 基準の写真とキャンバス
    if not state.get("reference") or state["reference"] not in frames:
        ref = opts.reference if opts.reference in frames else \
            min(frames, key=lambda k: frames[k]["taken"]) if frames else None
        if ref is None:
            _save_state(state_path, state)
            return res
        if state.get("reference"):
            # 基準の写真が消えた → やり直し
            for k, r in frames.items():
                _remove_aligned(out, r.get("aligned"))
                frames[k] = {key: r[key] for key in ("mtime", "size", "taken", "taken_source")} | {"status": "pending"}
            todo = list(frames)
        state["reference"] = ref
        state["canvas"] = None

    ref_name = state["reference"]
    ref_rgb = photos.load_rgb(src / ref_name, opts.long_side)
    canvas = (ref_rgb.shape[1], ref_rgb.shape[0])
    state["canvas"] = list(canvas)
    ref_feat = align.features(ref_rgb)

    feat_cache: dict[str, align.Features] = {}

    def aligned_features(key: str) -> align.Features | None:
        if key in feat_cache:
            return feat_cache[key]
        rec = frames[key]
        img_path = out / rec["aligned"]
        if not img_path.exists():
            return None
        rgb = cv2.cvtColor(cv2.imread(str(img_path)), cv2.COLOR_BGR2RGB)
        mask = cv2.imread(str(img_path.with_suffix(".mask.png")), cv2.IMREAD_GRAYSCALE)
        feat_cache[key] = align.features(rgb, mask)
        return feat_cache[key]

    # 撮影日時の順に処理する
    for key in sorted(todo, key=lambda k: frames[k]["taken"]):
        rec = frames[key]
        rgb = photos.load_rgb(src / key, opts.long_side)
        stem = f'{rec["taken"].replace(":", "").replace("-", "")}_{Path(key).stem}'
        if key == ref_name:
            m = align.Match(True, np.eye(3), len(ref_feat.keypoints), "reference")
            if rgb.shape[:2] != ref_rgb.shape[:2]:
                rgb = ref_rgb
        else:
            feat = align.features(rgb)
            candidates = [("基準", ref_feat)]
            done = [k for k, r in frames.items() if r.get("status") == "ok" and k != key]
            if done:
                t = datetime.fromisoformat(rec["taken"])
                near = min(done, key=lambda k: abs((datetime.fromisoformat(frames[k]["taken"]) - t).total_seconds()))
                nf = aligned_features(near)
                if nf is not None and near != ref_name:
                    candidates.insert(0, (f"近い日の写真 {near}", nf))
            m, via, last_fail = None, "", None
            for label, target in candidates:
                cand = align.match(feat, target)
                if cand.ok and (m is None or cand.inliers > m.inliers):
                    m, via = cand, label
                elif m is None and not cand.ok:
                    last_fail = cand
            if m is None:
                rec.update(status="failed", reason=last_fail.reason, inliers=last_fail.inliers)
                res.failed.append((key, last_fail.reason))
                log.info("  ✗ %s: %s", key, last_fail.reason)
                continue
            rec["via"] = via
        warped, mask = align.warp(rgb, m.H, canvas)
        rel = f"aligned/{stem}.jpg"
        cv2.imwrite(str(out / rel), cv2.cvtColor(warped, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
        cv2.imwrite(str((out / rel).with_suffix(".mask.png")), mask)
        rec.update(status="ok", aligned=rel, inliers=m.inliers, model=m.model,
                   H=[round(float(v), 8) for v in m.H.ravel()], reason="")
        log.info("  ✓ %s (%s, 対応点 %d)", key, m.model, m.inliers)
        _save_state(state_path, state)

    _save_state(state_path, state)

    ok = sorted((k for k, r in frames.items() if r.get("status") == "ok"), key=lambda k: frames[k]["taken"])
    res.aligned = len(ok)
    res.failed = sorted((k, r.get("reason", "")) for k, r in frames.items() if r.get("status") == "failed")
    if ok and (res.new or not (out / "timelapse.mp4").exists()):
        res.video = video.render(
            [(out / frames[k]["aligned"], datetime.fromisoformat(frames[k]["taken"])) for k in ok],
            out / "timelapse.mp4", fps=opts.fps, crop=opts.crop,
            date_label=opts.date_label, title=opts.title or name)
    elif ok:
        res.video = out / "timelapse.mp4"
    _write_report(out / "report.txt", name, state, res)
    return res


def _write_report(path: Path, name: str, state: dict, res: Result) -> None:
    frames = state["frames"]
    lines = [f"被写体: {name}",
             f"更新: {datetime.now().isoformat(timespec='seconds')}",
             f"写真: {res.photos} 枚 / 動画に使った写真: {res.aligned} 枚 / 合わせられなかった写真: {len(res.failed)} 枚",
             f"基準の写真: {state.get('reference')}",
             ""]
    if res.failed:
        lines.append("合わせられなかった写真(撮り直すか、基準の写真を変えると入ることがある):")
        lines += [f"  {k}: {why}" for k, why in res.failed]
        lines.append("")
    mtimes = [k for k, r in frames.items() if r.get("taken_source") == "mtime"]
    if mtimes:
        lines.append("撮影日時が EXIF に無く、ファイルの日時で並べた写真:")
        lines += [f"  {k}" for k in sorted(mtimes)]
    path.write_text("\n".join(lines) + "\n", "utf-8")
