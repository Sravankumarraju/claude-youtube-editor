#!/usr/bin/env python3
"""Concept generator — invent unique creative directions for a repo video.

Stage 0 of the concept-first pipeline. Reads source.json and asks Gemini for
~3 DISTINCT concepts (each a sustained metaphor/framing tailored to THIS repo),
with the mood/palette + visual motif + section map that a concept-aware script
and theme are later built from. Writes <project>/work/concepts.json for review;
the user picks one, then gen_script (concept-aware) + an auto-matched theme build
the video to it.

Usage (repo root, venv python; needs GEMINI_API_KEY in .env):
    python tools/gen_concept.py --project videos/studio
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from textutil import strip_emoji
from gen_script import load_key, call_gemini, parse_json, DEFAULT_MODEL

REPO = Path(__file__).resolve().parent.parent

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:
        pass


def build_prompt(src: dict, avoid: list[str] | None = None) -> str:
    avoid_block = ""
    if avoid:
        avoid_block = ("\n\nAVOID these already-used angles (make the new three clearly different in "
                       "metaphor, domain, and tone):\n- " + "\n- ".join(avoid) +
                       "\nExplore fresh registers — e.g. borrow metaphors from unexpected domains "
                       "(a newsroom/wire service, air-traffic control, a weather service, a trading "
                       "floor, a spy thriller, a stadium scoreboard) and vary the tone (one playful, "
                       "one cinematic, one contrarian).")
    grounding = {
        "title": src.get("title"), "url": src.get("url"), "type": src.get("type"),
        "summary": src.get("summary"), "stars": src.get("stars"),
        "features": (src.get("features") or [])[:10],
        "tech_stack": (src.get("tech_stack") or [])[:10],
        "key_points": (src.get("key_points") or [])[:10],
        "readme_excerpt": (src.get("raw_excerpt") or "")[:600],
    }
    return f"""You are an award-winning creative director for a tech YouTube channel that turns GitHub \
projects into must-watch videos. A great video rides ONE strong concept — a fresh metaphor or framing \
tailored to THIS specific tool — sustained through every scene (like framing repos as "AI employees you \
hire for $0"). Generic templates are forbidden.

Invent 3 DISTINCT concepts for a video about the project below. Each must genuinely fit what THIS tool \
does (ground every claim in the SOURCE — no invented features or numbers). Make the three feel truly \
different from each other in metaphor and mood.

Return ONLY JSON (no fence):
{{
  "repo": "short repo name",
  "concepts": [
    {{
      "id": "kebab-id",
      "name": "2-4 word concept name",
      "premise": "one punchy sentence: the core idea/promise",
      "hook": "the first spoken line (a scroll-stopping opener)",
      "metaphor": "the sustained metaphor/framing in a few words",
      "mood": ["3", "tone", "words"],
      "palette": {{"bg": "#hex dark base", "accent": "#hex", "accent2": "#hex"}},
      "motif": "the recurring visual element the concept is built on",
      "sections": ["6-8 short beat labels that tell the story start to finish"],
      "why_it_fits": "one line: why this framing is right for this tool"
    }}
  ]
}}
Exactly 3 concepts. Keep every string tight. No emojis.{avoid_block}

SOURCE (JSON):
{json.dumps(grounding, ensure_ascii=False, indent=2)}
"""


def clean(obj):
    if isinstance(obj, str):
        return strip_emoji(obj)
    if isinstance(obj, list):
        return [clean(x) for x in obj]
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items()}
    return obj


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate 3 creative concepts for a repo video.")
    ap.add_argument("--project", required=True, help="project dir, e.g. videos/studio")
    ap.add_argument("--model", default=DEFAULT_MODEL, help="Gemini text model")
    args = ap.parse_args()

    work = Path(args.project) / "work"
    src_path = work / "source.json"
    if not src_path.exists():
        print(f"ERROR: {src_path} not found. Run tools/ingest_source.py first.", file=sys.stderr)
        return 1
    src = json.loads(src_path.read_text(encoding="utf-8"))

    # if a prior round exists, tell the model to avoid repeating it, and archive it
    cpath = work / "concepts.json"
    prior: list = []
    avoid: list[str] = []
    if cpath.exists():
        try:
            prior = json.loads(cpath.read_text(encoding="utf-8")).get("concepts", [])
            avoid = [f"{c.get('name')} — {c.get('metaphor')}" for c in prior if c.get("name")]
        except Exception:
            pass

    try:
        key = load_key()
        data = clean(parse_json(call_gemini(key, args.model, build_prompt(src, avoid or None))))
    except Exception as e:  # noqa: BLE001
        print(f"CONCEPT GEN FAILED: {type(e).__name__}: {e}", file=sys.stderr)
        return 3
    concepts = data.get("concepts", [])[:3]
    if not concepts:
        print("CONCEPT GEN FAILED: no concepts returned.", file=sys.stderr)
        return 3

    if prior:  # keep earlier rounds so their concepts stay selectable
        hist = work / "concepts_history.json"
        h = json.loads(hist.read_text(encoding="utf-8")) if hist.exists() else {"rounds": []}
        h["rounds"].append(prior)
        hist.write_text(json.dumps(h, indent=2, ensure_ascii=False), encoding="utf-8")
    (work / "concepts.json").write_text(
        json.dumps({"repo": data.get("repo"), "concepts": concepts}, indent=2, ensure_ascii=False),
        encoding="utf-8")

    for i, c in enumerate(concepts):
        print(f"\n=== CONCEPT {i + 1}: {c.get('name')}  [{c.get('id')}] ===")
        print(f"  premise : {c.get('premise')}")
        print(f"  hook    : {c.get('hook')}")
        print(f"  metaphor: {c.get('metaphor')}")
        print(f"  mood    : {', '.join(c.get('mood', []))}")
        print(f"  motif   : {c.get('motif')}")
        print(f"  sections: {' -> '.join(c.get('sections', []))}")
        print(f"  fits    : {c.get('why_it_fits')}")
    print(f"\nOK  wrote {(work / 'concepts.json').as_posix()}  ({len(concepts)} concepts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
