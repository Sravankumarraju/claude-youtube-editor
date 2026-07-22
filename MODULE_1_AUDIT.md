# MODULE 1 — Repository Audit

**Date:** 2026-07-22
**Scope:** Honest, code-grounded audit of `claude-youtube-editor` before any Module 1 changes.
**Method:** Full read-only exploration of `tools/`, `remotion/`, `.claude/skills/`, and docs. No code was modified.

---

## 0. Headline finding (read this first)

**The Module 1 spec assumes a web application that does not exist in this repository.**

The spec describes landing pages, creation buttons (`Upload and Edit Footage`, `Create from a Source`),
an upload experience, a four-panel editing workspace, source-input screens, a storyboard editor, render
progress UI, tooltips, empty states, and a help panel. **None of these exist.** What exists is:

- A set of **Python command-line tools** (`tools/*.py`) run from a terminal.
- A **Remotion (React/TSX) project** (`remotion/`) that renders animated "shots" to video.
- **Claude Code "skills"** (`.claude/skills/`) — Markdown instruction files that tell Claude which tools
  to run in what order. *Claude is the orchestrator; there is no app server.*
- **One** small local web page: a 470-line vanilla-JS **cut editor** (`tools/editor/index.html`) served by
  a 150-line Python stdlib server (`tools/editor/server.py`). It reviews/trims a single track of footage.
  It is **not** a general editing workspace.

**Consequence:** "Simplify the existing footage editor" and "add faceless video generation" as *web-UI
flows* means **building a web front-end from scratch** over the CLI pipeline. That is a multi-phase
project, not a single incremental change. The enhanced plan in §13 reconciles the spec with this reality.

---

## 1. Current application architecture

| Layer | What it is | Entry point |
|---|---|---|
| Orchestration | Claude Code skills (prose instructions) | `.claude/skills/<name>/SKILL.md` invoked via chat or `/name` |
| Work engine | Python 3 CLI tools (ffmpeg, ASR, API calls) | `python tools/<tool>.py <project> ...` (run from repo root, using repo-root `venv`) |
| Visuals | Remotion 4.0.486 (React/TSX shots) | `cd remotion && npm run {studio,render,gen}` |
| Cut editor UI | Vanilla HTML/JS + Python stdlib server | `python tools/editor/server.py <project> [port]` → `http://localhost:8765` |
| Data | Loose JSON files per video | `videos/<project>/work/*.json` (ships empty) |
| Style contract | 3 files kept in sync | `brand.md` + `remotion/src/{brand.ts,fonts.ts}` |

No backend service, no database, no build step for the UI, no root `package.json` (only `remotion/`).

**Stale-docs hazard:** several tools' docstrings reference a *different, larger monorepo* (`core/`,
`longs/`, `MIGRATION.md`, video "types", `ch-N.mp4`) that does not exist here — e.g. `tools/bake.py:29-33`,
`tools/yt_upload.py:43-44`, `remotion/scripts/gen-registry.mjs:12-21`. This misleads anyone reading them.

---

## 2. Existing Remotion compositions

- **38 compositions**, all in `remotion/src/shots/` (37 example shots in `shots/example/` + `shots/brand/BrandProof.tsx`).
- **Every composition is 1920×1080 @ 30fps (16:9).** There is **no vertical/9:16 composition** anywhere.
  Width/height are per-shot in each file's `compositionConfig`, so 9:16 is *mechanically* possible but
  never used. The only vertical-aware code is `WebBrowserFrame`'s `uiScale` prop (`remotion/src/lib/browser.tsx`).
- **Registry is generated** by `remotion/scripts/gen-registry.mjs`, which **regex-scans** each file's
  `export const compositionConfig = {…}` block (it never executes the file). → `src/registry.gen.tsx` +
  `src/shots.manifest.json` (both git-ignored). Run `npm run gen` after adding/renaming a shot.
- **Every shot is a bespoke `.tsx` file with NO props** — content is hard-coded as module-level consts
  inside each file. There is **no data-driven composition** (no `getInputProps`/`defaultProps`/Zod schema).

---

## 3. Existing footage-editing workflow

Pipeline order: **cut → visuals → voice → SFX → packaging → upload** (`CLAUDE.md:18`).

Step 1 (`/clean-cut`), end to end:
1. Extract 16 kHz mono WAV per clip → `work/audio/<id>.wav` (manual ffmpeg).
2. Draft `work/keyterms.txt`.
3. `tools/transcribe.py` (AssemblyAI) → `work/transcripts/<id>.json`.
4. `tools/format_transcript.py` → `work/analysis/takes-<id>.txt`.
5. **Claude hand-authors `work/analysis/cuts.json`** from the takes (no separate LLM call).
6. QA: `tools/analyze_cut.py` → `qa-report.md`; `tools/make_review.py` → `review.md`.
7. `tools/make_proxy.py` → `work/editor/{proxy.mp4, waveform.png, manifest.json}`.
8. Preview renders (`tools/render_cuts.py --mode preview`) for `tight` + `natural`.
9. **Mandatory** `tools/verify_cut.py` (2nd ASR pass over the render — catches ghost/half-cut words + A/V drift).
10. **User-audit gate** in the cut editor (`tools/editor/server.py`).
11. Final render (`--mode final`, 4K60 HEVC) + A/V-duration gate + H.264 delivery transcode.
12. Produce `work/edited-transcript.json` (word times in the master) — the handoff spine to `/make-tsx`.

**The existing cut editor UI** (`tools/editor/`) covers step 10 only: a zoomable waveform timeline with
draggable keep/cut blocks, an inspector (play / cut / restore / ±50 ms nudge), fluff bands, flag markers,
edited-vs-raw playback, save (with backup), and "render preview" (spawns `render_cuts.py`). It has **no
transcript panel, no edit-suggestion accept/reject workflow, no overlay/shot awareness, no storyboard** —
those are greenfield relative to the spec's four-panel workspace.

---

## 4. Existing Claude / AI integrations

| Provider | Purpose | Key (`.env`) | Call site |
|---|---|---|---|
| AssemblyAI | Transcription | `ASSEMBLYAI_API_KEY` | `tools/transcribe.py` (REST via `requests`) |
| ElevenLabs | Voice isolation / SFX / music | `ELEVENLABS_API_KEY` | `tools/clean_voice.py` (curl), `tools/gen_sfx.py`, `tools/gen_music.py` (urllib) |
| Google Gemini | Thumbnails | `GEMINI_API_KEY` | `tools/gen_thumbnail.py` (`google-genai` SDK) |
| YouTube (OAuth) | Upload / stats | *no key* | `tools/yt_upload.py`, `tools/yt_stats.py` (`.youtube/` tokens) |
| Claude | Orchestrates + authors cuts.json | Claude Code plan | **No programmatic Anthropic API call** in `tools/` — Claude *is* the app |

RNNoise (`clean_voice.py --method rnnoise`) is a fully **local, key-free** denoise path.
`.env` parsing is **duplicated across ~6 tools** — a consistency hazard worth centralizing.

**Gap for Module 1:** script/storyboard *generation* would be the first place a programmatic Claude API
call (or a Claude-Code-driven skill) is needed. None exists today.

---

## 5. Existing script & transcript handling

- **No script writer exists** (`README.md:112`: "No script writer. This edits video; it doesn't write it.").
- Transcripts: verbatim word-level ASR (AssemblyAI, fillers on), one JSON per clip in `work/transcripts/`,
  `words[]` with `start`/`end` in **ms** + `confidence`. Loaded via `tools/cutlib.py:load_words`.
- `work/edited-transcript.json` (`{words:[{text,start,end}]}`, ms) is the spine every later step syncs to.
- **Implication:** a faceless flow inverts this — script comes *first* (generated from a source), and word
  timing must come from TTS/uploaded narration rather than ASR of footage. New front-end work.

---

## 6. Existing visual shot components (the reusable kit)

`remotion/src/lib/` — four parameterized modules (the real reuse surface; shots themselves are hard-coded):

- **`kit.tsx`** — `BrandBg`, `useRise`, `Sunburst`, `ClaudeCodePromptShot`, `LevelTitleShot`,
  `ImageRevealShot`, `VSCodeShell`, `ClaudeChatPanel`.
- **`browser.tsx`** — `WebBrowserFrame` (Chrome-style window, `uiScale` for vertical), `Marker`, `Ring`.
- **`screencast.tsx`** — `Screencast` (data-driven `pages[]`/`cursor[]`/`clicks[]` fake screen recording).
  The most data-driven component in the repo.
- **`vscode.tsx`** — `VSCodeWindow` + `baseExplorer` (data-driven `ExplorerRow[]` file tree),
  `CodeEditorPane` (data-driven `CodeLine[]` typed code), `ImageViewerPane`, `VSCodeSplitReveal`.

Styling flows from `brand.ts`/`fonts.ts`; `BrandProof.tsx` renders the current brand as a proof card.

---

## 7. Existing audio & caption support

- **Audio:** rich, but footage-centric — extraction, ASR, denoise (`clean_voice.py`), SFX/music generation
  + mixing (`gen_sfx`/`mix_sfx`/`gen_music`/`mix_music`) with sidechain ducking and loudness normalization.
- **Captions:** **none.** No `@remotion/captions`, no `.srt`/`.vtt`, no on-screen caption renderer. Word
  timing exists only in `edited-transcript.json` and is used to *time reveals*, not to burn captions.
  Caption rendering (spec Part B) is **build-from-scratch**.

---

## 8. Existing render process

Three distinct paths:
- **A — Cut master** (`tools/render_cuts.py`): drift-free video/audio assembly from `cuts.json`.
  ⚠️ **Hard-requires an NVIDIA GPU** (`h264_nvenc`/`hevc_nvenc` + `-hwaccel cuda`, no CPU fallback,
  undocumented). This will fail on most laptops, all Macs, and CI.
- **B — Composited bake** (`tools/bake.py`): overlays shots on the master per `timeline.json`. Uses **CPU
  `libx264`** (GPU-free) — so the visuals bake works even where the cut render does not.
- **C — Remotion shot render** (`remotion/scripts/render-all.mjs`): bundles + `renderMedia` per shot →
  `out/<id>.mp4` (opaque) or `out/<id>.mov` (ProRes 4444 alpha for overlays).

---

## 9. Hard-coded assumptions about talking-head footage

The pipeline assumes **a master video with a recorded audio track exists**. Break points with no footage:
- `cutlib.AudioProbe` opens `work/audio/<clip>.wav` directly → `FileNotFoundError` with no footage.
- `render_cuts.py`, `make_proxy.py` (maps stream 0 **and** 1), `bake.py` (always muxes master audio),
  `clean_voice.py` all assume a video+audio master.
- `edited-transcript.json`, `/make-tsx`, `/suggest-sfx` all sync to spoken word times.
- `gen_thumbnail.py` expects presenter face refs in `media/library/faces/`.

**Already footage-independent:** the entire Remotion visuals layer (the 37 example shots render standalone,
no footage). This is why faceless video is *feasible* — the visual engine needs no camera.

---

## 10. Components reusable for faceless videos

| Faceless scene type | Reuse | Location |
|---|---|---|
| Title | `LevelTitleShot` | `lib/kit.tsx` |
| Animated text | `BigStatement`/`MethodsTeaser` patterns | `shots/example/*` (inline; extract to reuse) |
| Code scene | `CodeEditorPane` (`CodeLine[]`) | `lib/vscode.tsx` |
| Repo file-tree | `VSCodeWindow`+`baseExplorer` (`ExplorerRow[]`) | `lib/vscode.tsx` |
| Browser / screenshot | `WebBrowserFrame`, `Screencast` (`pages[]`) | `lib/browser.tsx`, `lib/screencast.tsx` |
| Feature cards | `LevelsOverview`/`ThreePart` patterns | `shots/example/*` (inline; extract to reuse) |
| Diagram / pipeline | `EnginePipeline`/`PipelineStages` patterns | `shots/example/*` (inline; extract) |
| Image scene | `ImageRevealShot`, `Level2Gallery` | `lib/kit.tsx`, `shots/example/*` |
| Summary / recap | `LevelsRecap`/`ChecklistFree` patterns | `shots/example/*` (inline; extract) |
| CTA / end card | `EndCard`, transparent overlay chips | `shots/example/*` |

**The three real gaps for faceless video:** (1) no 9:16 output, (2) no data-driven "Scene" composition
(every shot is bespoke TSX — a generated video needs either a code-gen step per scene or one new
parameterized `Scene` composition fed by input props), (3) no caption renderer.

---

## 11. Config, types & quality gates

- TS: only `remotion/tsconfig.json` (`strict: true`, `noEmit`). De-facto typecheck: `npx tsc --noEmit` from `remotion/`.
- **No ESLint, no test runner, no `test`/`lint` npm scripts** anywhere in the project.
- **No formal project data model/schema** — project state is loose JSON files. The spec's "strict
  TypeScript types + runtime validation" for a project would be *introducing* this (e.g. Zod schemas).

---

## 12. Current bugs / usability problems

1. **NVENC hard-requirement** (`render_cuts.py`, `make_proxy.py`) — no CPU fallback, undocumented; fails on
   non-NVIDIA machines. *Highest-impact portability bug.*
2. **Stale monorepo docs** in multiple tool docstrings (§1).
3. **Path-resolution inconsistency** — cut tools resolve project relative to repo root; `bake.py`/`mix_*`
   relative to CWD; `yt_upload.py` resolves plan paths *above* the repo (a real bug for this layout).
4. **Regex-parsed `compositionConfig`** — computed/spread/non-literal width/height silently fails to register.
5. **No input validation** — missing `cuts.json`/WAV/transcript throws raw stack traces; `transcribe.py`
   polls AssemblyAI **indefinitely** (no timeout); `editor/server.py` crashes the request thread on missing files.
6. **Duplicated `.env` parsing** across ~6 tools.
7. **Cut-editor edited-playback is only an approximation** of the real render (documented, but surprising).
8. **No footage-optional path** — the whole cut/proxy/verify chain assumes recorded footage exists.

---

## 13. Enhanced, realistic Module 1 plan (prompt audit → recommendation)

The spec's ordering is sound; the *framing* (a web app already exists to "simplify") is not. Recommended
reconciliation, still strictly incremental and reuse-first:

**Increment 0 — Foundation (do first; unblocks everything, low risk).**
- Fix the NVENC hard-requirement: add a CPU (`libx264`) fallback + capability probe so renders work on any
  machine. *Without this, no render-based acceptance test passes on non-NVIDIA hardware.*
- Add a data-driven **`Scene` composition** in Remotion (one parameterized composition fed by
  `getInputProps`/`defaultProps` with a Zod schema) that dispatches to the existing `lib/` components by
  `type`. This is the keystone that makes *both* faceless generation and future UI-driven edits possible
  without writing bespoke TSX per video. Reuses `CodeEditorPane`, `baseExplorer`, `Screencast`,
  `LevelTitleShot`, `WebBrowserFrame`.
- Add 9:16 support by making width/height a Scene input prop.
- Add a caption renderer component (Remotion `<Sequence>` + timed text), off by default.
- Define the **project schema** (Zod) — the formal `project.json` the spec's save/resume needs.

**Increment 1 — Faceless-from-source (highest new value, no footage dependency).**
- CLI-first: `tools/ingest_source.py` (GitHub URL / article URL / pasted text → clean `source.json`) →
  Claude-authored `script.json` → `storyboard.json` (maps script sections to `Scene` types) →
  render via the new `Scene` composition. No-voice mode first; uploaded/AI narration + captions next.
- This exercises the footage-independent path and produces the spec's Example 2 & 3 proof videos.

**Increment 2 — Footage-editor usability.**
- Extend the existing cut editor with a transcript panel + edit-suggestion accept/reject over `cuts.json`
  (reuse the existing server + timeline). Overlay/storyboard editing comes after the `Scene` composition exists.

**Increment 3 — Web front-end (only if desired).**
- A landing page + wizards wrapping the CLI increments above. This is the largest piece and should be its
  own module, not smuggled into "simplify the existing editor."

**Immediate deliverable this pass:** this audit + a **User Guide web page** documenting the *real* current
workflow so the tool is easier to use today, before any refactor lands.

See `MODULE_1_PROGRESS.md` for step tracking.
