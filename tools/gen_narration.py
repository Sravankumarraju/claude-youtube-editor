#!/usr/bin/env python3
"""Module 1 — AI voice narration for faceless videos (ElevenLabs TTS).

Reads a storyboard.json (from tools/gen_faceless.py), speaks each scene's
`narration` text with ElevenLabs, writes one MP3 per scene under
media/projects/<name>/narration/, measures each clip, stretches each scene's
duration to fit its voiceover, and writes the `audio` path back into the
storyboard. Then re-emit the shot with:

    python tools/gen_faceless.py --project <p> --from-storyboard [--captions] [--format ...]

Only one provider (ElevenLabs), per Module 1 scope. The app still works with no
key — this step is optional (no-voice mode uses captions/on-screen text).

Usage (repo root, venv python; needs ELEVENLABS_API_KEY in .env):
    python tools/gen_narration.py --project videos/crawl4ai
    python tools/gen_narration.py --project videos/crawl4ai --voice <voice_id> --speed 1.05
"""
from __future__ import annotations
import argparse
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

from textutil import strip_emoji

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:
        pass

try:
    import requests
except ImportError:
    print("ERROR: 'requests' not installed — use the repo venv python.", file=sys.stderr)
    sys.exit(2)

FPS = 30
REPO = Path(__file__).resolve().parent.parent
API = "https://api.elevenlabs.io/v1"


def load_key() -> str:
    env = REPO / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("ELEVENLABS_API_KEY=") and "=" in line:
                v = line.split("=", 1)[1].strip().strip('"').strip("'")
                if v:
                    return v
    raise RuntimeError("ELEVENLABS_API_KEY not set in .env")


def pick_voice(key: str, voice: str | None) -> tuple[str, str]:
    if voice:
        return voice, voice
    r = requests.get(f"{API}/voices", headers={"xi-api-key": key}, timeout=30)
    r.raise_for_status()
    voices = r.json().get("voices", [])
    if not voices:
        raise RuntimeError("No voices available on this ElevenLabs account.")
    # prefer a premade narration-friendly voice if present, else the first
    for v in voices:
        if v.get("name", "").lower() in ("rachel", "adam", "antoni", "bill", "brian", "george"):
            return v["voice_id"], v["name"]
    return voices[0]["voice_id"], voices[0].get("name", "voice")


def tts(key: str, voice_id: str, text: str, model: str, speed: float, out: Path) -> None:
    body = {
        "text": text,
        "model_id": model,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "speed": speed},
    }
    r = requests.post(
        f"{API}/text-to-speech/{voice_id}?output_format=mp3_44100_128",
        headers={"xi-api-key": key, "Content-Type": "application/json"},
        json=body, timeout=120,
    )
    if r.status_code != 200:
        detail = ""
        try:
            detail = json.dumps(r.json())[:300]
        except Exception:
            detail = r.text[:300]
        raise RuntimeError(f"ElevenLabs TTS {r.status_code}: {detail}")
    out.write_bytes(r.content)


def audio_seconds(path: Path) -> float:
    ff = shutil.which("ffprobe")
    if ff:
        try:
            p = subprocess.run(
                [ff, "-v", "error", "-show_entries", "format=duration", "-of",
                 "default=nw=1:nk=1", str(path)],
                capture_output=True, text=True,
            )
            return float(p.stdout.strip())
        except Exception:
            pass
    # fallback estimate from file size (mp3 128kbps ≈ 16 KB/s)
    return max(1.5, path.stat().st_size / 16000)


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate ElevenLabs voice narration for a storyboard.")
    ap.add_argument("--project", required=True, help="project dir, e.g. videos/crawl4ai")
    ap.add_argument("--voice", help="ElevenLabs voice_id (default: auto-pick)")
    ap.add_argument("--model", default="eleven_turbo_v2_5", help="TTS model id")
    ap.add_argument("--speed", type=float, default=1.0, help="0.7–1.2")
    ap.add_argument("--force", action="store_true", help="re-generate clips that already exist")
    args = ap.parse_args()

    sb_path = Path(args.project) / "work" / "storyboard.json"
    if not sb_path.exists():
        print(f"ERROR: {sb_path} not found. Run tools/gen_faceless.py first.", file=sys.stderr)
        return 1
    sb = json.loads(sb_path.read_text(encoding="utf-8"))
    scenes = sb["scenes"]

    name = Path(args.project).name
    ndir = REPO / "media" / "projects" / name / "narration"
    ndir.mkdir(parents=True, exist_ok=True)

    try:
        key = load_key()
        voice_id, voice_name = pick_voice(key, args.voice)
    except Exception as e:  # noqa: BLE001
        print(f"NARRATION FAILED: {e}", file=sys.stderr)
        return 1
    print(f"voice: {voice_name} ({voice_id})  model: {args.model}")

    made = 0
    for i, s in enumerate(scenes):
        # Strip emoji so the voice never tries to speak pictographs, and so the
        # spoken words match the emoji-free captions rendered from the same text.
        text = strip_emoji((s.get("narration") or "").strip())
        if not text:
            continue
        mp3 = ndir / f"{i:02d}.mp3"
        try:
            if args.force or not mp3.exists():
                tts(key, voice_id, text, args.model, args.speed, mp3)
                made += 1
            secs = audio_seconds(mp3)
        except Exception as e:  # noqa: BLE001
            print(f"NARRATION FAILED on scene {i}: {e}", file=sys.stderr)
            return 1
        # fit the scene to its voiceover (0.5s head + 0.8s tail breathing room)
        need = int(math.ceil((secs + 1.3) * FPS))
        s["dur"] = max(int(s.get("dur", 60)), need)
        s["audio"] = f"projects/{name}/narration/{i:02d}.mp3"
        print(f"  scene {i:2d} [{s['type']:9}] {secs:4.1f}s -> {s['dur']:4d}f  \"{text[:52]}\"")

    sb_path.write_text(json.dumps(sb, indent=2, ensure_ascii=False), encoding="utf-8")
    total_s = sum(s["dur"] for s in scenes) / FPS
    print(f"\nOK  {made} clip(s) generated -> {ndir.as_posix()}")
    print(f"    storyboard updated (total ~{total_s:.1f}s) -> {sb_path.as_posix()}")
    print("\nNext — re-emit the shot with audio, then render:")
    print(f"  python tools/gen_faceless.py --project {args.project} --from-storyboard --captions")
    print("  cd remotion && npm run gen && node scripts/render-all.mjs --scale=1 <CompId>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
