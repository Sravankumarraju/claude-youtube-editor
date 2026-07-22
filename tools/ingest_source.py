#!/usr/bin/env python3
"""Module 1 — source ingestion for faceless videos.

Turns ONE public source into a clean, structured source.json that grounds the
script/storyboard. Supported source types (Module 1 scope only):

    github   a public GitHub repository URL
    article  a public article / webpage URL
    text     pasted text (via --text or --text-file)

It does NOT execute repo code, install dependencies, or read private repos.
Output schema (videos/<project>/work/source.json):

    { type, url, title, summary, key_points[], features[], tech_stack[],
      steps[], code_snippets[{filename, lines[]}], structure[], images[],
      missing[], raw_excerpt }

Usage (run from repo root, venv Python):
    python tools/ingest_source.py github  https://github.com/owner/repo   --project videos/demo
    python tools/ingest_source.py article https://example.com/post        --project videos/demo
    python tools/ingest_source.py text    --text-file notes.txt           --project videos/demo
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    print("ERROR: 'requests' not installed. Activate the repo venv:\n"
          "  venv/Scripts/python tools/ingest_source.py ...   (Windows)", file=sys.stderr)
    sys.exit(2)

UA = {"User-Agent": "claude-youtube-editor/ingest (+https://github.com)"}
TIMEOUT = 20

# Windows consoles default to cp1252 and choke on emoji/unicode in READMEs.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:
        pass


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", unescape(s or "")).strip()


def _first_sentences(text: str, n: int = 2, limit: int = 240) -> str:
    parts = re.split(r"(?<=[.!?])\s+", _clean(text))
    out = " ".join(parts[:n]).strip()
    return (out[: limit - 1] + "…") if len(out) > limit else out


def _bullets_from_markdown(md: str, limit: int = 8) -> list[str]:
    pts: list[str] = []
    for line in md.splitlines():
        m = re.match(r"^\s*[-*+]\s+(.*)$", line)
        if m:
            txt = _clean(re.sub(r"[`*_\[\]()]|https?://\S+", "", m.group(1)))
            txt = re.sub(r"\s+", " ", txt).strip(" -:")
            if 8 <= len(txt) <= 90:
                pts.append(txt)
        if len(pts) >= limit:
            break
    return pts


def _headings_from_markdown(md: str, limit: int = 8) -> list[str]:
    hs = []
    for line in md.splitlines():
        m = re.match(r"^#{2,3}\s+(.*)$", line)
        if m:
            h = _clean(re.sub(r"[`*_#]", "", m.group(1)))
            if 3 <= len(h) <= 48 and not re.match(r"(?i)table of contents|license|contributing", h):
                hs.append(h)
        if len(hs) >= limit:
            break
    return hs


def _first_code_block(md: str) -> list[str]:
    m = re.search(r"```[a-zA-Z0-9]*\n(.*?)```", md, re.S)
    if not m:
        return []
    lines = [ln.rstrip() for ln in m.group(1).splitlines() if ln.strip()]
    return lines[:12]


def _install_steps(md: str) -> list[str]:
    """Grab short shell-ish command lines from fenced blocks (install/usage)."""
    steps: list[str] = []
    for block in re.findall(r"```(?:bash|sh|shell|console|zsh)?\n(.*?)```", md, re.S):
        for ln in block.splitlines():
            ln = ln.strip().lstrip("$ ").strip()
            if 3 <= len(ln) <= 60 and re.match(r"(?i)(npm|npx|pip|python|git|yarn|pnpm|cargo|go|docker|make|brew|cd|curl)\b", ln):
                steps.append(ln)
            if len(steps) >= 6:
                return steps
    return steps


# --------------------------------------------------------------------------- #
# GitHub
# --------------------------------------------------------------------------- #
def ingest_github(url: str) -> dict:
    m = re.match(r"https?://github\.com/([^/]+)/([^/#?]+)", url.strip())
    if not m:
        raise ValueError(f"Not a GitHub repo URL: {url}")
    owner, repo = m.group(1), m.group(2).removesuffix(".git")
    api = f"https://api.github.com/repos/{owner}/{repo}"
    missing: list[str] = []

    r = requests.get(api, headers=UA, timeout=TIMEOUT)
    if r.status_code == 404:
        raise ValueError(f"Repo not found or private: {owner}/{repo}")
    if r.status_code == 403:
        raise RuntimeError("GitHub API rate limit hit (60/hr unauthenticated). Try again later.")
    r.raise_for_status()
    meta = r.json()

    # README (default branch, common names)
    branch = meta.get("default_branch", "main")
    readme = ""
    for name in ("README.md", "readme.md", "README.MD", "README.rst", "README.txt", "README"):
        rr = requests.get(f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{name}", headers=UA, timeout=TIMEOUT)
        if rr.status_code == 200 and rr.text.strip():
            readme = rr.text
            break
    if not readme:
        missing.append("README not found")

    # top-level structure
    structure: list[str] = []
    tr = requests.get(f"{api}/contents", headers=UA, timeout=TIMEOUT)
    if tr.status_code == 200:
        for item in tr.json():
            nm = item.get("name", "")
            if item.get("type") == "dir":
                nm += "/"
            if not nm.startswith("."):
                structure.append(nm)
    structure = structure[:12]

    topics = meta.get("topics", []) or []
    lang = meta.get("language")
    tech = ([lang] if lang else []) + [t for t in topics if t.lower() != (lang or "").lower()]

    features = _headings_from_markdown(readme) or _bullets_from_markdown(readme)
    steps = _install_steps(readme)
    if not steps:
        missing.append("no install/usage commands detected")
    snippet = _first_code_block(readme)

    # strip markdown for a readable summary
    body = re.sub(r"```.*?```", " ", readme, flags=re.S)
    body = re.sub(r"[#>*_`\[\]()!]|https?://\S+", " ", body)
    summary = _first_sentences(meta.get("description") or body, 2) or "(no description)"

    return {
        "type": "github",
        "url": url,
        "title": repo,
        "summary": summary,
        "key_points": _bullets_from_markdown(readme)[:5],
        "features": features[:6],
        "tech_stack": tech[:8],
        "steps": steps,
        "code_snippets": ([{"filename": "example", "lines": snippet}] if snippet else []),
        "structure": structure,
        "images": [f"{meta['html_url']}"] if meta.get("html_url") else [],
        "stars": meta.get("stargazers_count", 0),
        "missing": missing,
        "raw_excerpt": _clean(body)[:600],
    }


# --------------------------------------------------------------------------- #
# Article / webpage
# --------------------------------------------------------------------------- #
def ingest_article(url: str) -> dict:
    r = requests.get(url, headers=UA, timeout=TIMEOUT)
    r.raise_for_status()
    html = r.text
    missing: list[str] = []

    tm = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    title = _clean(tm.group(1)) if tm else urlparse(url).netloc

    # kill non-content regions
    for tag in ("script", "style", "nav", "footer", "header", "aside", "form", "noscript", "svg"):
        html = re.sub(rf"<{tag}\b.*?</{tag}>", " ", html, flags=re.S | re.I)

    headings = [_clean(h) for h in re.findall(r"<h[12][^>]*>(.*?)</h[12]>", html, re.S | re.I)]
    headings = [re.sub(r"<[^>]+>", "", h) for h in headings if _clean(h)][:8]

    paras = re.findall(r"<p[^>]*>(.*?)</p>", html, re.S | re.I)
    paras = [_clean(re.sub(r"<[^>]+>", "", p)) for p in paras]
    paras = [p for p in paras if len(p) > 60]
    if not paras:
        missing.append("no article paragraphs extracted (page may be JS-rendered)")

    imgs = re.findall(r'<img[^>]+src="([^"]+)"', html, re.I)
    imgs = [i for i in imgs if i.startswith("http")][:5]

    body_text = " ".join(paras)
    summary = _first_sentences(body_text, 2) if body_text else title

    return {
        "type": "article",
        "url": url,
        "title": title,
        "summary": summary,
        "key_points": [p[:90].rstrip() + ("…" if len(p) > 90 else "") for p in paras[:5]],
        "features": headings,
        "tech_stack": [],
        "steps": [],
        "code_snippets": [],
        "structure": [],
        "images": imgs,
        "missing": missing,
        "raw_excerpt": body_text[:600],
    }


# --------------------------------------------------------------------------- #
# Pasted text
# --------------------------------------------------------------------------- #
def ingest_text(text: str) -> dict:
    text = text.strip()
    if not text:
        raise ValueError("Empty text.")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    title = lines[0][:70] if lines else "Pasted text"
    paras = re.split(r"\n\s*\n", text)
    paras = [_clean(p) for p in paras if len(_clean(p)) > 0]
    return {
        "type": "text",
        "url": None,
        "title": title,
        "summary": _first_sentences(text, 2),
        "key_points": _bullets_from_markdown(text) or [p[:90] for p in paras[1:6]],
        "features": _headings_from_markdown(text),
        "tech_stack": [],
        "steps": _install_steps(text),
        "code_snippets": ([{"filename": "snippet", "lines": _first_code_block(text)}] if _first_code_block(text) else []),
        "structure": [],
        "images": [],
        "missing": [],
        "raw_excerpt": _clean(text)[:600],
    }


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description="Ingest a public source into source.json for a faceless video.")
    ap.add_argument("type", choices=["github", "article", "text"])
    ap.add_argument("url", nargs="?", help="URL (for github/article)")
    ap.add_argument("--text", help="pasted text (for type=text)")
    ap.add_argument("--text-file", help="read pasted text from a file (for type=text)")
    ap.add_argument("--project", required=True, help="project dir, e.g. videos/demo")
    ap.add_argument("--out", help="override output path (default <project>/work/source.json)")
    args = ap.parse_args()

    try:
        if args.type == "github":
            if not args.url:
                ap.error("github requires a URL")
            data = ingest_github(args.url)
        elif args.type == "article":
            if not args.url:
                ap.error("article requires a URL")
            data = ingest_article(args.url)
        else:
            txt = args.text
            if args.text_file:
                txt = Path(args.text_file).read_text(encoding="utf-8")
            if not txt:
                ap.error("text requires --text or --text-file")
            data = ingest_text(txt)
    except Exception as e:  # noqa: BLE001 — surface a clean message, not a stack trace
        print(f"INGEST FAILED: {e}", file=sys.stderr)
        return 1

    out = Path(args.out) if args.out else Path(args.project) / "work" / "source.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"OK  {data['type']}: {data['title']}")
    print(f"    summary : {data['summary'][:80]}")
    print(f"    features: {len(data['features'])}  points: {len(data['key_points'])}  "
          f"steps: {len(data['steps'])}  tech: {len(data['tech_stack'])}")
    if data["missing"]:
        print(f"    missing : {'; '.join(data['missing'])}")
    print(f"    -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
