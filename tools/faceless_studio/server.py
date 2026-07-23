#!/usr/bin/env python3
"""Faceless Studio — a tiny local web UI to create a faceless video from a source.

Paste a public GitHub repo URL, an article URL, or text; review what was
extracted; then generate + render a video and watch it inline. Zero dependencies
(Python stdlib only). It orchestrates the existing CLI tools:

    tools/ingest_source.py   (source -> source.json)
    tools/gen_faceless.py    (source.json -> storyboard.json + a Remotion shot)
    remotion/scripts/gen-registry.mjs + render-all.mjs   (register + render MP4)

Run from the repo root with the venv Python:
    venv/Scripts/python tools/faceless_studio/server.py            # Windows
    ./venv/bin/python  tools/faceless_studio/server.py             # macOS/Linux
Then open http://localhost:8770
"""
from __future__ import annotations
import json
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PROJECT = "videos/studio"                       # single working project for the UI
WORK = REPO / PROJECT / "work"
OUT = REPO / "remotion" / "out"
TEMPLATES_JSON = REPO / "remotion" / "src" / "templates.json"
MANIFEST = REPO / "remotion" / "src" / "shots.manifest.json"
PY = sys.executable                             # the venv python that launched us


def load_templates_list() -> list[dict]:
    """The template palette for the picker (id, name, description, colors, fonts)."""
    try:
        data = json.loads(TEMPLATES_JSON.read_text(encoding="utf-8"))
        return [t for t in data.get("templates", []) if isinstance(t, dict)]
    except Exception:
        return []


def list_videos() -> list[dict]:
    """Rendered videos in remotion/out, newest first — the dashboard library."""
    dims: dict[str, tuple[int, int]] = {}
    try:
        for shot in json.loads(MANIFEST.read_text(encoding="utf-8")):
            if isinstance(shot, dict) and shot.get("id"):
                dims[shot["id"]] = (int(shot.get("width", 0)), int(shot.get("height", 0)))
    except Exception:
        pass
    out: list[dict] = []
    if OUT.exists():
        for f in OUT.glob("*.mp4"):
            comp = f.stem
            st = f.stat()
            w, h = dims.get(comp, (0, 0))
            out.append({
                "id": comp,
                "size": st.st_size,
                "mtime": int(st.st_mtime),
                "width": w, "height": h,
                "vertical": bool(h and w and h > w),
                "url": f"/media/{comp}.mp4",
            })
    out.sort(key=lambda v: v["mtime"], reverse=True)
    return out

# ---- shared job state ------------------------------------------------------
LOCK = threading.Lock()
STATE: dict = {"phase": "idle", "log": [], "ok": False, "error": None, "compId": None, "running": False}
PKG_LOCK = threading.Lock()
PKG_STATE: dict = {"phase": "idle", "log": [], "ok": False, "error": None, "data": None, "running": False}
PKG_DIR = REPO / "media" / "projects" / Path(PROJECT).name / "packaging"

# ---- Remotion Studio (the "video editor" on :3000) -------------------------
STUDIO_PORT = 3000
STUDIO_LOCK = threading.Lock()
_studio_proc: subprocess.Popen | None = None


def _port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", port)) == 0


def studio_url(comp: str | None = None) -> str:
    return f"http://localhost:{STUDIO_PORT}" + (f"/{comp}" if comp else "")


def ensure_studio() -> dict:
    """Start Remotion Studio (npm run studio) if it isn't already up on :3000."""
    global _studio_proc
    if _port_open(STUDIO_PORT):
        return {"ok": True, "running": True, "url": studio_url()}
    with STUDIO_LOCK:
        if _port_open(STUDIO_PORT):
            return {"ok": True, "running": True, "url": studio_url()}
        npm = shutil.which("npm") or shutil.which("npm.cmd")
        if not npm:
            return {"ok": False, "running": False, "error": "npm not found on PATH."}
        try:
            _studio_proc = subprocess.Popen(
                [npm, "run", "studio"], cwd=str(REPO / "remotion"),
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "running": False, "error": f"could not start studio: {e}"}
        # first launch bundles the project — give it time to open the port
        for _ in range(80):
            if _port_open(STUDIO_PORT):
                return {"ok": True, "running": True, "url": studio_url()}
            time.sleep(0.5)
        return {"ok": True, "running": False, "starting": True, "url": studio_url(),
                "error": "Editor is still starting (bundling) — it will open shortly; try again in a few seconds."}


def _reset(phase: str) -> None:
    STATE.update(phase=phase, log=[], ok=False, error=None, compId=None, running=True)


def _log(msg: str) -> None:
    STATE["log"].append(msg)


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    _log("$ " + " ".join(cmd))
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = (p.stdout or "").strip().splitlines()[-6:] + (p.stderr or "").strip().splitlines()[-6:]
    for ln in tail:
        if ln.strip():
            _log(ln.rstrip())
    return p


# ---- pipeline steps --------------------------------------------------------
def do_analyze(payload: dict) -> dict:
    """Run ingest only; return the extracted source.json for review."""
    stype = payload.get("type")
    WORK.mkdir(parents=True, exist_ok=True)
    cmd = [PY, "tools/ingest_source.py", stype, "--project", PROJECT]
    if stype in ("github", "article"):
        url = (payload.get("url") or "").strip()
        if not url:
            raise ValueError("Enter a URL.")
        cmd.insert(3, url)
    else:  # text
        text = payload.get("text") or ""
        if not text.strip():
            raise ValueError("Paste some text.")
        tf = WORK / "_paste.txt"
        tf.write_text(text, encoding="utf-8")
        cmd += ["--text-file", str(tf)]
    p = _run(cmd, REPO)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout or "ingest failed").strip().splitlines()[-1])
    return json.loads((WORK / "source.json").read_text(encoding="utf-8"))


def do_generate(payload: dict) -> None:
    """Apply edits, generate the storyboard + shot, register, and render."""
    try:
        src_path = WORK / "source.json"
        if not src_path.exists():
            raise RuntimeError("Analyze a source first.")
        src = json.loads(src_path.read_text(encoding="utf-8"))
        # apply user edits from the review screen
        for k in ("title", "summary"):
            if payload.get(k) is not None:
                src[k] = payload[k]
        if isinstance(payload.get("key_points"), list):
            src["key_points"] = [p for p in payload["key_points"] if p.strip()]
        src_path.write_text(json.dumps(src, indent=2, ensure_ascii=False), encoding="utf-8")

        fmt = "vertical" if payload.get("format") == "vertical" else "landscape"
        want_captions = bool(payload.get("captions"))
        want_voice = bool(payload.get("voiceover"))
        want_ai = payload.get("ai", True) is not False
        template = (payload.get("template") or "brand").strip() or "brand"
        try:
            duration = int(payload.get("duration") or 120)
        except (TypeError, ValueError):
            duration = 120

        # 1) storyboard — AI-written script (Gemini) targeting the chosen duration,
        #    with a graceful fall back to the basic heuristic generator.
        sb_ok = False
        if want_ai:
            STATE["phase"] = "writing AI script"
            ps = _run([PY, "tools/gen_script.py", "--project", PROJECT,
                       "--duration", str(duration), "--template", template], REPO)
            sb_ok = ps.returncode == 0
            if not sb_ok:
                _log("AI script unavailable — falling back to the basic generator.")
        if not sb_ok:
            STATE["phase"] = "generating storyboard"
            cmd = [PY, "tools/gen_faceless.py", "--project", PROJECT, "--format", fmt, "--template", template]
            if want_captions:
                cmd.append("--captions")
            pb = _run(cmd, REPO)
            if pb.returncode != 0:
                raise RuntimeError("Storyboard generation failed.")

        # 2) optional voice-over — speak each scene, fit scene durations to the audio
        if want_voice:
            STATE["phase"] = "generating voice-over"
            pv = _run([PY, "tools/gen_narration.py", "--project", PROJECT], REPO)
            if pv.returncode != 0:
                raise RuntimeError("Voice-over failed — check ELEVENLABS_API_KEY and account credits.")

        # 3) emit the shot from the final storyboard (audio + timings baked in)
        STATE["phase"] = "building shot"
        cmd2 = [PY, "tools/gen_faceless.py", "--project", PROJECT, "--from-storyboard",
                "--format", fmt, "--template", template]
        if want_captions:
            cmd2.append("--captions")
        p = _run(cmd2, REPO)
        if p.returncode != 0:
            raise RuntimeError("Building the shot failed.")

        m = re.search(r"composition '([^']+)'", p.stdout or "")
        if not m:
            raise RuntimeError("Could not determine composition id.")
        comp = m.group(1)

        STATE["phase"] = "registering shots"
        if _run(["node", "scripts/gen-registry.mjs"], REPO / "remotion").returncode != 0:
            raise RuntimeError("Registry generation failed (is node on PATH?).")

        STATE["phase"] = "rendering video"
        if _run(["node", "scripts/render-all.mjs", "--scale=1", comp], REPO / "remotion").returncode != 0:
            raise RuntimeError("Render failed.")

        if not (OUT / f"{comp}.mp4").exists():
            raise RuntimeError("Render finished but no MP4 was produced.")
        STATE.update(phase="done", ok=True, compId=comp)
        _log(f"OK -> remotion/out/{comp}.mp4")
    except Exception as e:  # noqa: BLE001
        STATE.update(phase="error", error=str(e))
        _log("ERROR: " + str(e))
    finally:
        STATE["running"] = False


def do_package(count: int) -> None:
    """Generate title/description/thumbnails for the current project."""
    PKG_STATE.update(phase="writing copy + rendering thumbnails", log=[], ok=False, error=None, data=None, running=True)
    try:
        cmd = [PY, "tools/gen_package.py", "--project", PROJECT, "--count", str(count)]
        PKG_STATE["log"].append("$ " + " ".join(cmd))
        p = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace")
        for ln in ((p.stdout or "") + "\n" + (p.stderr or "")).strip().splitlines()[-12:]:
            if ln.strip():
                PKG_STATE["log"].append(ln.rstrip())
        if p.returncode != 0:
            raise RuntimeError("Packaging failed — check GEMINI_API_KEY and image-model access.")
        pkg = json.loads((WORK / "packaging.json").read_text(encoding="utf-8"))
        PKG_STATE.update(phase="done", ok=True, data=pkg)
    except Exception as e:  # noqa: BLE001
        PKG_STATE.update(phase="error", error=str(e))
        PKG_STATE["log"].append("ERROR: " + str(e))
    finally:
        PKG_STATE["running"] = False


# ---- HTTP ------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj: dict, code: int = 200) -> None:
        self._send(code, json.dumps(obj).encode("utf-8"), "application/json")

    def log_message(self, *a):  # quiet console
        pass

    def do_GET(self):
        # Strip the query string (the UI appends a ?t=<ts> cache-buster) before
        # routing — otherwise it becomes part of the requested media filename.
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._send(200, (HERE / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif path == "/api/status":
            self._json(STATE)
        elif path == "/api/templates":
            self._json({"templates": load_templates_list()})
        elif path == "/api/videos":
            self._json({"videos": list_videos()})
        elif path == "/api/editor":
            self._json({"running": _port_open(STUDIO_PORT), "url": studio_url()})
        elif path == "/api/package-status":
            self._json(PKG_STATE)
        elif path.startswith("/pkg/"):
            self._serve_pkg(path.split("/pkg/", 1)[1])
        elif path.startswith("/media/"):
            self._serve_media(path.split("/media/", 1)[1])
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError:
            return self._json({"error": "bad JSON"}, 400)

        if self.path == "/api/analyze":
            try:
                src = do_analyze(payload)
                self._json({"ok": True, "source": src})
            except Exception as e:  # noqa: BLE001
                self._json({"ok": False, "error": str(e)}, 400)
        elif self.path == "/api/generate":
            with LOCK:
                if STATE["running"]:
                    return self._json({"error": "A render is already running."}, 409)
                _reset("starting")
            threading.Thread(target=do_generate, args=(payload,), daemon=True).start()
            self._json({"ok": True})
        elif self.path == "/api/editor/start":
            self._json(ensure_studio())
        elif self.path == "/api/package":
            with PKG_LOCK:
                if PKG_STATE["running"]:
                    return self._json({"error": "Packaging already running."}, 409)
                PKG_STATE["running"] = True
            try:
                count = int(payload.get("count") or 2)
            except (TypeError, ValueError):
                count = 2
            threading.Thread(target=do_package, args=(count,), daemon=True).start()
            self._json({"ok": True})
        else:
            self._json({"error": "not found"}, 404)

    def _serve_media(self, name: str):
        f = OUT / Path(name).name
        if not f.exists():
            return self._send(404, b"no video", "text/plain")
        data = f.read_bytes()
        rng = self.headers.get("Range")
        if rng and rng.startswith("bytes="):
            s, _, e = rng[6:].partition("-")
            start = int(s) if s else 0
            end = int(e) if e else len(data) - 1
            end = min(end, len(data) - 1)
            chunk = data[start:end + 1]
            self.send_response(206)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Range", f"bytes {start}-{end}/{len(data)}")
            self.send_header("Content-Length", str(len(chunk)))
            self.end_headers()
            self.wfile.write(chunk)
        else:
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    def _serve_pkg(self, name: str):
        f = PKG_DIR / Path(name).name
        if not f.exists():
            return self._send(404, b"no file", "text/plain")
        ctype = "image/jpeg" if f.suffix.lower() in (".jpg", ".jpeg") else "image/png"
        self._send(200, f.read_bytes(), ctype)


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8770
    if not (REPO / "tools" / "ingest_source.py").exists():
        print("Run this from the repo root with the venv python.", file=sys.stderr)
        return 1
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Faceless Studio -> http://localhost:{port}   (Ctrl+C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
