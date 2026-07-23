#!/usr/bin/env python3
"""Assemble a set of clips into a short montage of a target length.

For B-roll / recipe / product footage where you'll add voice-over later — NOT the
speech-cut pipeline (that's /clean-cut). Takes a centered slice from each clip so
the total lands near --seconds, in filename order, and concatenates them into one
clean H.264 file. CPU-encoded (no GPU needed). Original audio is kept unless --mute.

Usage (repo root; ffmpeg + ffprobe on PATH):
    python tools/montage.py videos/video-1 --seconds 55
    python tools/montage.py videos/video-1 --seconds 55 --mute
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path

VID_EXT = (".mov", ".mp4", ".m4v", ".mkv", ".avi")


def probe_dur(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def solve_base(durs: list[float], target: float) -> float:
    """Largest per-clip slice length `base` with sum(min(d, base)) ~= target."""
    lo, hi = 0.3, max(durs)
    for _ in range(48):
        mid = (lo + hi) / 2
        if sum(min(d, mid) for d in durs) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def main() -> int:
    ap = argparse.ArgumentParser(description="Assemble clips into a short montage.")
    ap.add_argument("project", help="project dir, e.g. videos/video-1")
    ap.add_argument("--seconds", type=float, default=55.0, help="target total length")
    ap.add_argument("--mute", action="store_true", help="drop audio (VO added later)")
    ap.add_argument("--fps", default="30000/1001", help="output fps")
    ap.add_argument("--vertical", action="store_true", help="9:16 output (phone/Reel/Short)")
    args = ap.parse_args()
    W, H = (1080, 1920) if args.vertical else (1920, 1080)

    proj = Path(args.project)
    clips = sorted(p for p in proj.glob("*") if p.suffix.lower() in VID_EXT)
    if not clips:
        print(f"ERROR: no video clips in {proj}", file=sys.stderr)
        return 1

    durs = [probe_dur(c) for c in clips]
    base = solve_base(durs, args.seconds)
    plan = []  # (clip, start, length)
    for c, d in zip(clips, durs):
        length = min(d, base)
        start = max(0.0, (d - length) / 2)
        plan.append((c, start, length))
    total = sum(length for _, _, length in plan)
    print(f"{len(plan)} clips -> montage ~{total:.1f}s (target {args.seconds:.0f}s), "
          f"~{base:.1f}s each")

    work = proj / "work" / "montage"
    work.mkdir(parents=True, exist_ok=True)
    ts_files = []
    for i, (c, start, length) in enumerate(plan):
        seg = work / f"seg_{i:02d}.mp4"
        af = f"afade=t=in:d=0.02,afade=t=out:st={max(length - 0.02, 0):.3f}:d=0.02"
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.3f}", "-i", str(c),
               "-t", f"{length:.3f}",
               "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
                      f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,fps={args.fps},format=yuv420p",
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "20"]
        if args.mute:
            cmd += ["-an"]
        else:
            cmd += ["-af", af, "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
        cmd += [str(seg)]
        subprocess.run(cmd, check=True)
        # TS intermediate keeps the concat frame-exact (no per-file trailing-gap drift)
        ts = seg.with_suffix(".ts")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(seg), "-c", "copy",
                        "-bsf:v", "h264_mp4toannexb", "-f", "mpegts", str(ts)], check=True)
        ts_files.append(ts)
        print(f"  seg {i:02d}: {c.name}  {start:.1f}s +{length:.1f}s")

    listf = work / "list.txt"
    listf.write_text("\n".join(f"file '{t.resolve().as_posix()}'" for t in ts_files), encoding="utf-8")
    out_dir = proj / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "montage.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", str(listf), "-c", "copy", "-fflags", "+genpts", str(out)], check=True)
    print(f"\nOK  wrote {out.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
