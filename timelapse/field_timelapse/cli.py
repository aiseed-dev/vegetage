"""コマンド: field-timelapse build / watch / status"""

from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
import time
from pathlib import Path

from . import photos
from .pipeline import Options, process_subject, subjects

log = logging.getLogger("field_timelapse")


def _out_dir(root: Path, out: Path | None) -> Path:
    return out if out else root / "_timelapse"


def _options(a) -> Options:
    return Options(fps=a.fps, long_side=a.size, date_label=not a.no_date, crop=a.crop)


def _targets(root: Path, only: str | None) -> list[Path]:
    subs = subjects(root)
    if only:
        subs = [s for s in subs if s.name == only]
        if not subs:
            raise SystemExit(f"被写体フォルダが見つかりません: {root / only}")
    return subs


def build(a) -> int:
    root = a.root.expanduser().resolve()
    out_root = _out_dir(root, a.out)
    subs = _targets(root, a.subject)
    if not subs:
        log.warning("写真のある被写体フォルダがありません: %s", root)
        return 1
    status = 0
    for src in subs:
        out = out_root if src == root else out_root / src.name
        opts = _options(a)
        opts.reference = a.reference
        log.info("▶ %s", src.name)
        try:
            r = process_subject(src, out, opts, rebuild=a.rebuild)
        except Exception:  # 1つの被写体の失敗で、ほかを止めない
            log.exception("  %s の処理に失敗しました", src.name)
            status = 1
            continue
        log.info("  写真 %d 枚(新しい写真 %d)/ 動画に使用 %d / 失敗 %d → %s",
                 r.photos, r.new, r.aligned, len(r.failed), r.video or "(動画なし)")
    return status


def _snapshot(root: Path) -> dict[str, tuple[float, int]]:
    snap = {}
    for src in subjects(root):
        for p in src.iterdir():
            if photos.is_photo(p):
                st = p.stat()
                snap[str(p)] = (st.st_mtime, st.st_size)
    return snap


def watch(a) -> int:
    """フォルダを見張り、写真が増えたら(同期が落ち着いてから)作り直す。"""
    root = a.root.expanduser().resolve()
    stop = False

    def _stop(*_):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    log.info("見張りを始めます: %s(%d 秒ごと)", root, a.interval)
    built: dict | None = None
    while not stop:
        try:
            snap = _snapshot(root)
            newest = max((m for m, _ in snap.values()), default=0)
            settled = time.time() - newest >= a.settle
            if snap != built and settled:
                build(a)
                built = snap
            elif snap != built:
                log.info("同期中の写真があるので、落ち着くまで待ちます")
        except FileNotFoundError:
            log.warning("フォルダが見つかりません: %s", root)
        except Exception:
            log.exception("処理中にエラー(次の回にもう一度試します)")
        for _ in range(a.interval):
            if stop:
                break
            time.sleep(1)
    log.info("見張りを終わります")
    return 0


def status(a) -> int:
    root = a.root.expanduser().resolve()
    out_root = _out_dir(root, a.out)
    for src in _targets(root, a.subject):
        out = out_root if src == root else out_root / src.name
        n = sum(1 for p in src.iterdir() if photos.is_photo(p))
        state_path = out / "state.json"
        if not state_path.exists():
            print(f"{src.name}: 写真 {n} 枚 / まだ処理していません")
            continue
        state = json.loads(state_path.read_text("utf-8"))
        frames = state["frames"]
        ok = [k for k, r in frames.items() if r.get("status") == "ok"]
        bad = [(k, r.get("reason", "")) for k, r in frames.items() if r.get("status") == "failed"]
        pending = n - len(frames) + sum(1 for r in frames.values() if r.get("status") == "pending")
        mp4 = out / "timelapse.mp4"
        when = time.strftime("%Y-%m-%d %H:%M", time.localtime(mp4.stat().st_mtime)) if mp4.exists() else "なし"
        print(f"{src.name}: 写真 {n} 枚 / 動画に使用 {len(ok)} / 失敗 {len(bad)} / 未処理 {max(pending, 0)}"
              f" / 基準 {state.get('reference')} / 動画 {when}")
        for k, why in sorted(bad):
            print(f"    ✗ {k}: {why}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="field-timelapse",
        description="スマホで毎日撮った畑の写真を、位置をそろえたタイムラプス動画にする")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp, *, render: bool = True):
        sp.add_argument("root", type=Path, help="写真のフォルダ(被写体ごとのサブフォルダを入れる)")
        sp.add_argument("--out", type=Path, help="出力先(既定: <root>/_timelapse)")
        sp.add_argument("--subject", help="この被写体フォルダだけ処理する")
        if render:
            sp.add_argument("--fps", type=float, default=8.0, help="1秒あたりの写真の枚数(既定 8)")
            sp.add_argument("--size", type=int, default=1920, help="動画の長辺の画素数(既定 1920)")
            sp.add_argument("--crop", type=float, default=0.03, help="四辺を切る割合(既定 0.03)")
            sp.add_argument("--no-date", action="store_true", help="撮影日を入れない")
            sp.add_argument("--reference", help="基準にする写真のファイル名(--subject と一緒に使う)")
            sp.add_argument("--rebuild", action="store_true", help="記録を消して最初から作り直す")
        sp.add_argument("-q", "--quiet", action="store_true")

    b = sub.add_parser("build", help="一度だけ処理する(新しい写真だけ位置合わせし、動画を作り直す)")
    common(b)
    b.set_defaults(func=build)
    w = sub.add_parser("watch", help="フォルダを見張り、写真が増えたら自動で処理する")
    common(w)
    w.add_argument("--interval", type=int, default=300, help="見に行く間隔(秒、既定 300)")
    w.add_argument("--settle", type=int, default=120,
                   help="最後の写真の変更からこの秒数たってから処理する(同期の途中を避ける。既定 120)")
    w.set_defaults(func=watch, rebuild=False)
    s = sub.add_parser("status", help="被写体ごとの状況(使えた枚数・失敗した写真)")
    common(s, render=False)
    s.set_defaults(func=status)

    a = p.parse_args(argv)
    if getattr(a, "reference", None) and not a.subject:
        p.error("--reference は --subject と一緒に指定してください")
    logging.basicConfig(level=logging.WARNING if a.quiet else logging.INFO,
                        format="%(asctime)s %(message)s", datefmt="%m-%d %H:%M:%S")
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
