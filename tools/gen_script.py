#!/usr/bin/env python3
"""AI script writer — turn source.json into an engaging, grounded storyboard.json.

This replaces the flat "slice the README into slides" heuristic with a real
YouTube script: a hook, a narrative arc (what it is → why it matters → how it
works → a concrete use → payoff/CTA), targeting a chosen duration. It is written
by Gemini but STRICTLY grounded in source.json — it may not invent features,
numbers, or claims. Output matches the Scene[] schema the Remotion engine and
tools/gen_narration.py consume, so the rest of the pipeline is unchanged.

Usage (repo root, venv python; needs GEMINI_API_KEY in .env):
    python tools/gen_script.py --project videos/studio --duration 120
    python tools/gen_script.py --project videos/studio --duration 300 --template midnight
Falls back with a clear error (exit 3) if the model/JSON fails, so the caller can
fall back to the heuristic generator.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import re
import sys
from pathlib import Path

from textutil import strip_emoji
from gen_faceless import build_repo_view

FPS = 30
WPS = 2.4  # spoken words per second (~145 wpm) — sets the word budget per duration
REPO = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = "gemini-flash-latest"  # resilient alias; override with --model (e.g. gemini-3.5-flash)
ALLOWED = {"title", "statement", "features", "steps", "code", "bullets", "repo_scroll", "cta"}

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:
        pass


def load_key() -> str:
    env = REPO / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("GEMINI_API_KEY=") and "=" in line:
                v = line.split("=", 1)[1].strip().strip('"').strip("'")
                if v:
                    return v
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"].strip()
    raise RuntimeError("GEMINI_API_KEY not set in .env")


def build_prompt(src: dict, target_sec: int, concept: dict | None = None) -> str:
    words = int(target_sec * WPS)
    # Pace for engagement: a fresh visual every ~5s -> many short scenes.
    lo, hi = max(6, target_sec // 7), min(34, max(8, target_sec // 4))
    concept_block = ""
    if concept:
        secs = " -> ".join(concept.get("sections", []))
        concept_block = f"""

CONCEPT (build the ENTIRE video to this creative direction — sustain it in EVERY scene; never break character):
- Name: {concept.get('name')}
- Premise: {concept.get('premise')}
- Metaphor to sustain throughout: {concept.get('metaphor')}
- Opening hook (use/adapt as the FIRST scene's narration): "{concept.get('hook')}"
- Tone: {', '.join(concept.get('mood', []))}
- Recurring motif to reference in the language: {concept.get('motif')}
- Follow THIS beat arc IN ORDER (about one scene per beat, split if a beat is rich): {secs}
Write narration and short scene eyebrows in the metaphor's voice (e.g. use the beat names as eyebrows). \
The whole video must feel like this one idea."""
    is_repo = bool(build_repo_view(src))
    repo_rule = (
        '\n- Include EXACTLY ONE scene of type "repo_scroll" early (right after you introduce what it is). '
        'Its narration should walk the viewer through the actual GitHub repo — what stands out, key files or '
        'sections, and how to start. The repo page itself is filled in automatically, so give it ONLY a '
        '"narration" and an optional short "eyebrow" (no other fields).' if is_repo else ""
    )
    repo_example = ('    {"type":"repo_scroll","eyebrow":"on github","narration":"walk the viewer through the repo"},\n'
                    if is_repo else "")
    types_line = ("title, statement, features, steps, code, bullets, repo_scroll, cta" if is_repo
                  else "title, statement, features, steps, code, bullets, cta")
    grounding = {
        "type": src.get("type"),
        "title": src.get("title"),
        "url": src.get("url"),
        "summary": src.get("summary"),
        "stars": src.get("stars"),
        "features": (src.get("features") or [])[:10],
        "tech_stack": (src.get("tech_stack") or [])[:12],
        "steps": (src.get("steps") or [])[:10],
        "key_points": (src.get("key_points") or [])[:10],
        "code_snippets": (src.get("code_snippets") or [])[:2],
        "structure": (src.get("structure") or [])[:25],
        "readme_excerpt": (src.get("raw_excerpt") or "")[:600],
    }
    return f"""You are a world-class YouTube scriptwriter and video director for a channel that \
showcases GitHub projects and AI dev tools (think punchy, benefit-led explainers — the kind that \
get views). Write the script + storyboard for ONE video about the project below.{concept_block}

TARGET LENGTH: about {target_sec} seconds of narration (~{words} words total). Use {lo}-{hi} scenes.

PACING (critical for retention): keep every scene SHORT — ONE punchy sentence of about 8-16 words \
(~4-6 seconds spoken). Favor MANY short scenes over a few long ones, so a fresh visual lands every \
~5 seconds. Vary the scene types scene-to-scene (don't repeat the same type back-to-back) to keep it \
visually fresh. Never write a paragraph as one scene's narration — split it across scenes.

HARD RULES:
- Ground EVERYTHING in the SOURCE below. Do NOT invent features, benchmarks, numbers, or claims.
  If a detail isn't in the source, don't state it. You may use the star count if present.
- This is a spoken video, not a slideshow. The `narration` is the voice-over — write it like a great \
creator talks: a strong hook in the first line, curiosity, momentum, plain language, one idea per scene.
  Explain WHY it matters and HOW it works — do not just read the README.
- On-screen text (titles, bullets, feature labels) must be SHORT; the narration carries the detail.
- No emojis anywhere. No hashtags. No "in this video". Don't address "subscribers".{repo_rule}

STRUCTURE (arc): open with a hook, then what it is, why it's different, show the repo, how it works \
(use a code scene if there are commands), a concrete use case / who it's for, then a payoff + call to action.

OUTPUT: return ONLY valid JSON (no markdown fence) shaped exactly as:
{{
  "title": "short punchy video title",
  "scenes": [
    {{"type":"title","title":"...", "subtitle":"one-line hook", "eyebrow":"optional short tag", "narration":"spoken hook line"}},
    {{"type":"statement","text":"one bold on-screen line","eyebrow":"optional","narration":"..."}},
    {{"type":"features","eyebrow":"optional","items":[{{"label":"short"}},{{"label":"short"}}],"narration":"..."}},
    {{"type":"steps","eyebrow":"optional","steps":["short","short"],"narration":"..."}},
    {{"type":"code","eyebrow":"optional","filename":"terminal","lines":["cmd one","cmd two"],"narration":"..."}},
    {{"type":"bullets","eyebrow":"optional","title":"short","points":["short point","short point"],"narration":"..."}},
{repo_example}    {{"type":"cta","title":"short CTA","sub":"url or short line","narration":"..."}}
  ]
}}
Allowed scene types: {types_line}. First scene MUST be "title"; last MUST be "cta". Only include a \
"code" scene if the source has real commands/snippets.

SOURCE (JSON):
{json.dumps(grounding, ensure_ascii=False, indent=2)}
"""


def call_gemini(key: str, model: str, prompt: str) -> str:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=key)
    resp = client.models.generate_content(
        model=model, contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.85),
    )
    return resp.text or ""


def parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        a, b = text.find("{"), text.rfind("}")
        if a != -1 and b != -1 and b > a:
            return json.loads(text[a:b + 1])
        raise


def _as_str_list(v, n=8):
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()][:n]
    if isinstance(v, str) and v.strip():
        return [v.strip()]
    return []


def coerce(raw: dict, src: dict) -> tuple[str, list[dict]]:
    """Validate/normalize the model output to the engine's Scene[] schema."""
    title = str(raw.get("title") or "Untitled").strip()
    repo_view = build_repo_view(src)
    out: list[dict] = []
    for s in raw.get("scenes", []):
        if not isinstance(s, dict):
            continue
        t = str(s.get("type", "")).strip()
        if t not in ALLOWED:
            continue
        narr = strip_emoji(str(s.get("narration") or "").strip())
        sc: dict = {"type": t, "narration": narr}
        if s.get("eyebrow"):
            sc["eyebrow"] = strip_emoji(str(s["eyebrow"]).strip())[:32]
        if t == "title":
            sc["title"] = strip_emoji(str(s.get("title") or title).strip())
            if s.get("subtitle"):
                sc["subtitle"] = strip_emoji(str(s["subtitle"]).strip())
        elif t == "statement":
            sc["text"] = strip_emoji(str(s.get("text") or narr).strip())
        elif t == "features":
            items = s.get("items") or []
            norm = []
            for it in items[:5]:
                if isinstance(it, dict) and it.get("label"):
                    norm.append({"label": strip_emoji(str(it["label"]).strip())})
                elif isinstance(it, str) and it.strip():
                    norm.append({"label": strip_emoji(it.strip())})
            if not norm:
                continue
            sc["items"] = norm
        elif t == "steps":
            steps = _as_str_list(s.get("steps"), 6)
            if not steps:
                continue
            sc["steps"] = [strip_emoji(x) for x in steps]
        elif t == "code":
            lines = _as_str_list(s.get("lines"), 14)
            if not lines:
                continue
            sc["lines"] = lines  # code is literal — keep emoji-free but don't strip syntax
            sc["filename"] = str(s.get("filename") or "terminal").strip()[:40]
        elif t == "bullets":
            pts = _as_str_list(s.get("points"), 5)
            if not pts:
                continue
            sc["points"] = [strip_emoji(x) for x in pts]
            if s.get("title"):
                sc["title"] = strip_emoji(str(s["title"]).strip())
        elif t == "repo_scroll":
            if not repo_view:  # non-GitHub source — drop the scene
                continue
            sc["repo"] = repo_view
        elif t == "cta":
            sc["title"] = strip_emoji(str(s.get("title") or "Check it out").strip())
            if s.get("sub"):
                sc["sub"] = str(s["sub"]).strip()
        # duration from narration length (spoken time) + small breathing pad;
        # repo_scroll gets a longer floor so the page has room to scroll.
        w = max(1, len((narr or sc.get("text") or sc.get("title") or "").split()))
        floor = 240 if t == "repo_scroll" else 70
        sc["dur"] = max(floor, int(math.ceil((w / WPS + 0.5) * FPS)))
        out.append(sc)

    # enforce a title-first / cta-last shell
    if not out or out[0]["type"] != "title":
        out.insert(0, {"type": "title", "title": title, "dur": 90,
                       "narration": strip_emoji(title)})
    if out[-1]["type"] != "cta":
        out.append({"type": "cta", "title": "Check it out", "dur": 80, "narration": "Check it out."})
    return title, out


def main() -> int:
    ap = argparse.ArgumentParser(description="AI script writer (source.json -> storyboard.json via Gemini)")
    ap.add_argument("--project", required=True, help="project dir, e.g. videos/studio")
    ap.add_argument("--duration", type=int, default=120, help="target narration seconds (30-300)")
    ap.add_argument("--template", default="brand", help="template id to record in the storyboard")
    ap.add_argument("--concept-file", default=None, help="path to a chosen concept.json (concept-aware script)")
    ap.add_argument("--model", default=DEFAULT_MODEL, help="Gemini text model id")
    args = ap.parse_args()

    target = max(20, min(300, args.duration))
    work = Path(args.project) / "work"
    src_path = work / "source.json"
    if not src_path.exists():
        print(f"ERROR: {src_path} not found. Run tools/ingest_source.py first.", file=sys.stderr)
        return 1
    src = json.loads(src_path.read_text(encoding="utf-8"))

    concept = None
    if args.concept_file:
        cf = Path(args.concept_file)
        if cf.exists():
            concept = json.loads(cf.read_text(encoding="utf-8"))

    try:
        key = load_key()
        prompt = build_prompt(src, target, concept)
        raw_text = call_gemini(key, args.model, prompt)
        raw = parse_json(raw_text)
        title, scenes = coerce(raw, src)
    except Exception as e:  # noqa: BLE001 — caller falls back to the heuristic generator
        print(f"AI SCRIPT FAILED: {type(e).__name__}: {e}", file=sys.stderr)
        return 3
    if len(scenes) < 3:
        print("AI SCRIPT FAILED: too few valid scenes returned.", file=sys.stderr)
        return 3

    work.mkdir(parents=True, exist_ok=True)
    (work / "storyboard.json").write_text(
        json.dumps({"title": title, "source_url": src.get("url"),
                    "template": args.template, "scenes": scenes}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    total = sum(s["dur"] for s in scenes) / FPS
    print(f"OK  AI script: {len(scenes)} scenes, ~{total:.0f}s (target {target}s)  ({title})")
    print(f"    types: {', '.join(s['type'] for s in scenes)}")
    print(f"    plan -> {(work / 'storyboard.json').as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
