#!/usr/bin/env python3
"""Module 1 — storyboard + shot generator for faceless videos.

Reads a source.json (from tools/ingest_source.py), builds a grounded storyboard
(Scene[]), writes it to <project>/work/storyboard.json for review/editing, and
emits a thin Remotion shot .tsx that embeds the scenes and renders them through
the data-driven engine (remotion/src/lib/storyboard.tsx). Landscape (16:9) or
vertical (9:16). No external AI video API; no network.

The storyboard is heuristic and STRICTLY grounded in source.json — it never
invents features. Claude can hand-edit storyboard.json for a better script, then
re-run with --from-storyboard to regenerate the shot.

Usage (repo root, venv Python):
    python tools/gen_faceless.py --project videos/demo --format landscape
    python tools/gen_faceless.py --project videos/demo --format vertical --captions
    python tools/gen_faceless.py --project videos/demo --from-storyboard   # re-emit after editing
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

from textutil import strip_emoji

FPS = 30
REPO = Path(__file__).resolve().parent.parent
SHOTS_DIR = REPO / "remotion" / "src" / "shots"
TEMPLATES_JSON = REPO / "remotion" / "src" / "templates.json"


def load_templates() -> dict[str, dict]:
    """id -> template dict, from the shared templates.json (source of truth)."""
    try:
        data = json.loads(TEMPLATES_JSON.read_text(encoding="utf-8"))
        return {t["id"]: t for t in data.get("templates", [])}
    except Exception:
        return {}


def apply_layout(scenes: list[dict], layout: dict) -> list[dict]:
    """Reorder scenes to the template's preferred type order and scale pacing.

    Applied once at build time (never on --from-storyboard) so pacing can't
    compound. Each scene type appears at most once, so a stable sort by the
    template's `order` just re-sequences the scenes.
    """
    order = layout.get("order") or []
    pacing = float(layout.get("pacing", 1.0) or 1.0)
    rank = {t: i for i, t in enumerate(order)}
    ordered = sorted(scenes, key=lambda s: rank.get(s.get("type"), len(order)))
    for s in ordered:
        s["dur"] = max(1, int(round(s.get("dur", 60) * pacing)))
    return ordered

# Windows consoles default to cp1252 and choke on emoji/unicode in source text.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:
        pass


def _pascal(s: str) -> str:
    parts = re.findall(r"[A-Za-z0-9]+", s)
    out = "".join(p[:1].upper() + p[1:] for p in parts) or "Source"
    if out[0].isdigit():
        out = "S" + out
    return out[:32]


def _wrap(text: str, width: int, maxlines: int) -> list[str]:
    """Greedy word-wrap into up to `maxlines` lines of ~`width` chars."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width and cur:
            lines.append(cur)
            cur = w
            if len(lines) >= maxlines:
                break
        else:
            cur = f"{cur} {w}".strip()
    if cur and len(lines) < maxlines:
        lines.append(cur)
    return lines


def build_repo_view(src: dict) -> dict | None:
    """The GitHub page shown in a repo_scroll scene — grounded in source.json.

    Returns None for non-GitHub sources (the scene is skipped then)."""
    url = src.get("url") or ""
    m = re.search(r"github\.com/([^/]+)/([^/#?]+)", url)
    if not m:
        return None
    owner, name = m.group(1), m.group(2).replace(".git", "")
    summ = strip_emoji((src.get("summary") or "").strip())
    readme: list[str] = _wrap(summ, 88, 2) if summ else []
    feats = [strip_emoji(f) for f in (src.get("features") or []) if f][:6]
    if feats:
        readme += ["## Features"] + [f"- {f}" for f in feats]
    pts = [strip_emoji(p) for p in (src.get("key_points") or []) if p][:6]
    if pts:
        readme += ["## Highlights"] + [f"- {p}" for p in pts]
    tech = [t for t in (src.get("tech_stack") or []) if t][:8]
    if tech:
        readme += ["## Built with", ", ".join(tech)]
    return {
        "owner": owner, "name": name, "url": url,
        "stars": src.get("stars"),
        "description": summ[:140],
        "topics": tech[:6],
        "files": [f for f in (src.get("structure") or []) if f][:12],
        "readme": readme[:26],
    }


def build_storyboard(src: dict) -> list[dict]:
    """source.json -> Scene[] (grounded; no invented content)."""
    typ = src.get("type", "text")
    title = src.get("title") or "Untitled"
    summary = src.get("summary") or ""
    features = [f for f in (src.get("features") or []) if f][:3]
    steps = [s for s in (src.get("steps") or []) if s][:6]
    points = [p for p in (src.get("key_points") or []) if p][:5]
    tech = [t for t in (src.get("tech_stack") or []) if t][:6]
    snippet = (src.get("code_snippets") or [{}])[0]

    eyebrow = {"github": "open-source · github", "article": "article", "text": "from your notes"}.get(typ, "source")
    subtitle = summary[:60].rstrip() + ("…" if len(summary) > 60 else "") if summary else ""

    scenes: list[dict] = [
        {"type": "title", "dur": 110, "eyebrow": eyebrow, "title": title, "subtitle": subtitle,
         "narration": f"{title}. {subtitle}".strip()},
    ]
    if summary:
        scenes.append({"type": "statement", "dur": 140, "eyebrow": "overview", "text": summary,
                       "narration": summary})
    if features:
        scenes.append({"type": "features", "dur": 60 + 44 * len(features), "eyebrow": "highlights",
                       "items": [{"label": f} for f in features],
                       "narration": "Highlights: " + "; ".join(features) + "."})
    if tech:
        scenes.append({"type": "steps", "dur": 50 + 20 * len(tech[:6]), "eyebrow": "built with",
                       "steps": tech[:6], "narration": "Built with " + ", ".join(tech[:6]) + "."})
    if steps:
        scenes.append({"type": "code", "dur": 150, "eyebrow": "get started",
                       "filename": "terminal", "lines": steps,
                       "narration": "Getting started takes a few commands."})
    elif snippet.get("lines"):
        scenes.append({"type": "code", "dur": 150, "eyebrow": "example",
                       "filename": snippet.get("filename", "example"), "lines": snippet["lines"],
                       "narration": "Here is a quick example."})
    if points:
        scenes.append({"type": "bullets", "dur": 60 + 26 * len(points), "eyebrow": "key points",
                       "title": "What matters", "points": points,
                       "narration": "The key points at a glance."})

    cta = {
        "github": ("Star it on GitHub", src.get("url") or ""),
        "article": ("Read the full article", (src.get("url") or "").split("//")[-1].split("/")[0]),
        "text": ("Made with claude-youtube-editor", "cd remotion && npm run studio"),
    }.get(typ, ("Learn more", src.get("url") or ""))
    scenes.append({"type": "cta", "dur": 90, "title": cta[0], "sub": cta[1],
                   "narration": cta[0] + "."})

    # Show the actual repo scrolling (GitHub sources only) right after the overview.
    repo = build_repo_view(src)
    if repo:
        insert_at = 2 if len(scenes) > 2 else len(scenes) - 1
        scenes.insert(insert_at, {"type": "repo_scroll", "dur": 300, "eyebrow": "on github",
                                  "repo": repo,
                                  "narration": f"Here's the {repo['name']} repo on GitHub — {int(repo['stars']):,} stars and everything you need to get going." if repo.get("stars") else f"Here's the {repo['name']} repo on GitHub."})

    # Narration is the source of truth for BOTH the voice-over (TTS) and the
    # on-screen captions — keep it emoji-free so the voice never reads "rocket
    # robot" and the caption band never shows pictographs.
    for s in scenes:
        if s.get("narration"):
            s["narration"] = strip_emoji(s["narration"])
    return scenes


def emit_shot(scenes: list[dict], slug: str, vertical: bool, captions: bool, template_id: str) -> tuple[str, Path]:
    total = sum(max(1, int(round(s["dur"]))) for s in scenes)
    dur_s = round(total / FPS, 3)
    w, h = (1080, 1920) if vertical else (1920, 1080)
    comp_id = f"Src{slug}{'V' if vertical else ''}"
    data = json.dumps(scenes, ensure_ascii=False, indent=2)
    tsx = f"""// GENERATED by tools/gen_faceless.py — do not edit by hand.
// Edit <project>/work/storyboard.json and re-run with --from-storyboard.
import React from 'react';
import {{ StoryboardVideo, type Scene }} from '../../lib/storyboard';

export const compositionConfig = {{ id: '{comp_id}', durationInSeconds: {dur_s}, fps: {FPS}, width: {w}, height: {h} }};

const SCENES = ({data}) as unknown as Scene[];

const {comp_id}: React.FC = () => (
  <StoryboardVideo scenes={{SCENES}} width={{{w}}} height={{{h}}} captions={{{str(captions).lower()}}} templateId={{'{template_id}'}} />
);
export default {comp_id};
"""
    out_dir = SHOTS_DIR / f"src-{slug.lower()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{comp_id}.tsx"
    out_file.write_text(tsx, encoding="utf-8")
    return comp_id, out_file


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate a faceless-video shot from source.json")
    ap.add_argument("--project", required=True, help="project dir, e.g. videos/demo")
    ap.add_argument("--format", choices=["landscape", "vertical"], default="landscape")
    ap.add_argument("--captions", action="store_true", help="burn captions from narration")
    ap.add_argument("--template", default=None, help="template id (see remotion/src/templates.json)")
    ap.add_argument("--from-storyboard", action="store_true",
                    help="skip rebuild; re-emit shot from an edited storyboard.json")
    args = ap.parse_args()

    work = Path(args.project) / "work"
    sb_path = work / "storyboard.json"
    templates = load_templates()

    if args.from_storyboard:
        if not sb_path.exists():
            print(f"ERROR: {sb_path} not found. Run without --from-storyboard first.", file=sys.stderr)
            return 1
        sb = json.loads(sb_path.read_text(encoding="utf-8"))
        scenes, title = sb["scenes"], sb.get("title", "Source")
        # layout was baked at build time; only the theme (templateId) can change here
        template_id = args.template or sb.get("template") or "brand"
    else:
        src_path = work / "source.json"
        if not src_path.exists():
            print(f"ERROR: {src_path} not found. Run tools/ingest_source.py first.", file=sys.stderr)
            return 1
        src = json.loads(src_path.read_text(encoding="utf-8"))
        scenes = build_storyboard(src)
        title = src.get("title", "Source")
        template_id = args.template or "brand"
        tmpl = templates.get(template_id)
        if tmpl:
            scenes = apply_layout(scenes, tmpl.get("layout", {}))
        elif args.template:
            print(f"WARNING: unknown template '{args.template}' — using brand default.", file=sys.stderr)
            template_id = "brand"
        sb_path.parent.mkdir(parents=True, exist_ok=True)
        sb_path.write_text(json.dumps({"title": title, "source_url": src.get("url"),
                                       "template": template_id, "scenes": scenes},
                                      indent=2, ensure_ascii=False), encoding="utf-8")

    if template_id not in templates:
        template_id = "brand"
    slug = _pascal(title)
    comp_id, out_file = emit_shot(scenes, slug, vertical=(args.format == "vertical"),
                                  captions=args.captions, template_id=template_id)
    rel = out_file.relative_to(REPO).as_posix()

    print(f"OK  storyboard: {len(scenes)} scenes  ({title})  template: {template_id}")
    print(f"    scene types: {', '.join(s['type'] for s in scenes)}")
    print(f"    plan  -> {sb_path.as_posix()}")
    print(f"    shot  -> {rel}   (composition '{comp_id}', {args.format})")
    print("\nNext:")
    print("  cd remotion && npm run gen")
    print(f"  node scripts/render-all.mjs --scale=1 {comp_id}")
    print(f"  # output: remotion/out/{comp_id}.mp4")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
