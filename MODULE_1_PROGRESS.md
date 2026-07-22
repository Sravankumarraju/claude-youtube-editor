# MODULE 1 — Progress

Tracking file per the Module 1 spec. Updated after each implementation step.

## Step 1 — Audit ✅ COMPLETE (2026-07-22)
- Full read-only audit of `tools/`, `remotion/`, `.claude/skills/`, docs.
- Deliverable: [`MODULE_1_AUDIT.md`](MODULE_1_AUDIT.md).
- **Key finding:** the spec assumes a web app that does not exist; the repo is a CLI + Claude-skills +
  Remotion pipeline with one small local cut-editor page. Plan reconciled in audit §13.
- Deliverable: **User Guide web page** documenting the real current workflow (see `docs/user-guide.html`).

## Step 2 — Improve existing footage editing ⏳ NOT STARTED
Blocked on decisions: web-UI vs CLI-first (see audit §13). Recommended prerequisite: Increment 0 (NVENC
CPU fallback, data-driven `Scene` composition, project schema).

### Data-driven faceless engine ✅ (2026-07-22)
- **Keystone:** `remotion/src/lib/storyboard.tsx` — a data-driven engine. Scene types: title,
  statement, features, steps, code, bullets, cta. Adapts to **landscape or vertical** (dims → props),
  optional **captions** track (with bottom safe-area), text truncation. Reuses `BrandBg`/`useRise`/brand.
- Proof shots: `faceless-demo/{RepoFaceless,StoryLandscape,StoryVertical}.tsx`. All `tsc --noEmit` clean.
- Rendered + frame-QA'd: `RepoFaceless.mp4`, `StoryLandscape.mp4` (1920×1080), `StoryVertical.mp4`
  (1080×1920) — **vertical + captions confirmed working**.

## Step 3 — Add source input ✅ (2026-07-22)
- `tools/ingest_source.py` — public GitHub repo / article URL / pasted text → `<project>/work/source.json`.
  GitHub via API (README, metadata, topics, structure, install commands); article via HTML extraction;
  text passthrough. No code execution, no private repos, clean error messages.

## Web UI — Faceless Studio ✅ (2026-07-22)
- `tools/faceless_studio/{server.py,index.html}` — a local web app (stdlib server + one HTML page, the
  same pattern as `tools/editor/`). Pick GitHub / Article / Text → paste link → **Analyze** (shows
  extracted title/summary/points, editable) → choose 16:9 or 9:16 + captions → **Create** → watch the
  MP4 inline / download. Orchestrates ingest → gen → render; live progress; ranged MP4 serving.
- Launch: `venv/Scripts/python tools/faceless_studio/server.py` → http://localhost:8770.
- Verified: index served (200), `/api/analyze` extracts correctly, `/api/status` polling works.

## Step 4 — Source review ✅
- In the Studio UI (editable title/summary/points before generate) and via editable `source.json` /
  `storyboard.json` (`--from-storyboard` re-emits after edits).

## Step 5–6 — Script + storyboard generation ✅ (2026-07-22)
- `tools/gen_faceless.py` — `source.json` → grounded `storyboard.json` (Scene[]) → emits a Remotion shot
  (`remotion/src/shots/src-<slug>/`). Landscape or vertical, `--captions`. Heuristic + fully editable.
- **Proven end to end:** ingested the real GitHub repo → 6 auto-generated scenes (title, statement,
  features from README headings, code from actual setup commands, bullets, cta) → rendered
  `SrcClaudeYoutubeEditor.mp4` (29s). Frame-QA'd; fixed a caption-overlap + text-overflow bug.

## Step 7 — Narration & captions 🟡 PARTIAL
- Captions ✅ (rendered from scene narration, on/off). No-voice mode ✅ (default).
- AI voice (ElevenLabs TTS) ⏳ BLOCKED — needs `ELEVENLABS_API_KEY` (not yet provided). Abstraction pending.

## Step 8 — Render & export 🟡 PARTIAL
- MP4 render ✅ (Remotion, CPU, no GPU). Storyboard JSON export ✅. Script.md / SRT export ⏳.

## Step 9 — Test & document ⏳ ONGOING
- `tsc --noEmit` clean after every change. No unit-test runner exists yet (would be new).

## Proof projects
- [ ] Example 1 — existing footage edit + overlay + captions + render (needs footage)
- [x] Example 2 — GitHub repo → faceless **landscape** video, 6 scenes (`SrcClaudeYoutubeEditor.mp4`)
- [~] Example 3 — article → faceless **vertical** video: engine + vertical proven (`StoryVertical.mp4`);
      article-specific run pending a chosen URL.

## Notes
- No lint/test runner exists yet; only quality gate is `npx tsc --noEmit` (from `remotion/`).
- NVENC CPU fallback is a hard prerequisite for any render-based acceptance test on non-NVIDIA machines.
