#!/usr/bin/env python3
"""Lock in a chosen concept and build its theme.

Finds a concept by id across work/concepts.json + work/concepts_history.json,
writes it to work/concept.json (the single 'chosen concept' downstream tools read),
and upserts a matching template into remotion/src/templates.json derived from the
concept's palette + mood (dark cinematic base). gen_script --concept-file then
writes the storyboard to it, themed by templateId = concept-<id>.

Usage:
    python tools/apply_concept.py --project videos/studio --id global-nervous-system
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TEMPLATES_JSON = REPO / "remotion" / "src" / "templates.json"

# dark cinematic base (midnight) — concept palette overrides the accents + bg
BASE = {
    "signal": "#34d399", "warn": "#fbbf24", "danger": "#fb7185",
    "ink": "#e8edf6", "muted": "#94a3b8", "line": "#1e293b",
    "d600": "#334155", "d400": "#94a3b8", "d300": "#cbd5e1",
}


def find_concept(work: Path, cid: str) -> dict | None:
    pools: list[list] = []
    cj = work / "concepts.json"
    if cj.exists():
        pools.append(json.loads(cj.read_text(encoding="utf-8")).get("concepts", []))
    ch = work / "concepts_history.json"
    if ch.exists():
        pools.extend(json.loads(ch.read_text(encoding="utf-8")).get("rounds", []))
    for pool in pools:
        for c in pool:
            if c.get("id") == cid:
                return c
    return None


def build_theme(concept: dict) -> dict:
    pal = concept.get("palette") or {}
    bg = pal.get("bg", "#0b1120")
    accent = pal.get("accent", "#38bdf8")
    accent2 = pal.get("accent2", "#818cf8")
    return {
        "id": f"concept-{concept['id']}",
        "name": concept.get("name", "Concept"),
        "description": concept.get("premise", "")[:120],
        "colors": {
            "accent": accent, "accent2": accent2, "signal": BASE["signal"],
            "warn": BASE["warn"], "danger": BASE["danger"], "ink": BASE["ink"],
            "muted": BASE["muted"], "paper": bg, "cream": bg, "line": BASE["line"],
            "d900": bg, "d800": bg, "d600": BASE["d600"], "d400": BASE["d400"], "d300": BASE["d300"],
        },
        "gradient": [accent, accent2, BASE["signal"]],
        "fonts": {"display": "Sora", "body": "Manrope", "mono": "JetBrainsMono"},
        "radius": {"card": 18, "panel": 14, "window": 12, "pill": 999},
        "layout": {"pacing": 1.0,
                   "order": ["title", "statement", "repo_scroll", "features", "steps",
                             "code", "bullets", "cta"],
                   "captionsDefault": True},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Select a concept and build its theme.")
    ap.add_argument("--project", required=True)
    ap.add_argument("--id", required=True, help="concept id, e.g. global-nervous-system")
    args = ap.parse_args()

    work = Path(args.project) / "work"
    concept = find_concept(work, args.id)
    if not concept:
        print(f"ERROR: concept '{args.id}' not found in concepts.json / history.", file=sys.stderr)
        return 1
    (work / "concept.json").write_text(json.dumps(concept, indent=2, ensure_ascii=False), encoding="utf-8")

    theme = build_theme(concept)
    data = json.loads(TEMPLATES_JSON.read_text(encoding="utf-8"))
    data["templates"] = [t for t in data["templates"] if t.get("id") != theme["id"]] + [theme]
    TEMPLATES_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"OK  chosen concept: {concept.get('name')}  [{concept['id']}]")
    print(f"    theme -> templateId '{theme['id']}'  (accent {theme['colors']['accent']}, bg {theme['colors']['paper']})")
    print(f"    concept -> {(work / 'concept.json').as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
