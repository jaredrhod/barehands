#!/usr/bin/env python3
# barehands: move things on your screen with your bare hands.
# Copyright (C) 2026 Jared Rhodenizer
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""barehands server — serves the hand-tracked air-board on localhost.

localhost = a secure context, which is what lets the browser open your
camera for the tracker page. Nothing here ever leaves your machine.

Endpoints:
  GET  /stage.html, /media/*   the pages + the media airlock
  POST /state                  tracker's ~45Hz scene heartbeat; the response
                               carries queued commands (the command channel)
  GET  /state                  the render page mirrors the scene from here
  POST /cmd                    board commands (your AI -> the board)
  GET  /config                 the barehands.json config (name + orbs)
  GET  /meta                   runtime metadata: version + feature flags
  GET  /tree?orb=N             a notes orb's folder tree — read-only, JAILED
  GET  /note?f=N/<rel>         one note's text — read-only, JAILED
  GET  /props                  the media airlock as a browsable tree
  GET  /orb                    your assistant's live state (the ring reads it)

Config lives in barehands.json next to this file:
  { "name": "Assistant", "port": 8794,
    "orbs": [ { "title": "Notes", "path": "sample-notes", "kind": "notes" },
              { "title": "Props", "path": "media", "kind": "media" } ] }

"notes" orbs may point at ANY folder of markdown (an Obsidian vault is
just a folder of markdown). The "media" orb may point anywhere too, so
your props can stay where they already live; a relative path resolves
against the repo. Wherever it points is the airlock: the only place
images and models ever stage from.

Your AI drives the ring by writing tiny files into ./state/ :
  state/state      one word: idle | listening | thinking | speaking
  state/mood.json  {"mood": "green"|"amber"|"red", "ts": <unix time>}
  state/wave.json  {"samples": [0..1 x 64], "ts": <unix time>}
Missing files are fine — the ring just idles.
"""
import json
import time
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP_VERSION = "6.7.0"
FEATURES = [
    "live-ring",
    "faster-polling",
    "notes-orbs",
    "media-airlock",
    "3d-models",
    "ai-state-sync",
]


def load_config():
    cfg = {
        "name": "Assistant",
        "version": APP_VERSION,
        "features": FEATURES[:],
        "port": 8794,
        "orbs": [],
        # Seconds before a non-idle ring state is treated as stale and
        # shown as idle. Only ever rescues a writer that died without
        # saying goodbye; see the note in /orb.
        "state_timeout_s": 600,
    }
    try:
        cfg.update(json.loads((HERE / "barehands.json").read_text()))
    except Exception:
        pass
    if not cfg.get("orbs"):
        cfg["orbs"] = [
            {"title": "Notes", "path": "sample-notes", "kind": "notes"},
            {"title": "Props", "path": "media", "kind": "media"},
        ]
    if not cfg.get("version"):
        cfg["version"] = APP_VERSION
    if not cfg.get("features"):
        cfg["features"] = FEATURES[:]
    for orb in cfg["orbs"]:
        orb["path"] = str(Path(str(orb.get("path", "")).expanduser()))
    return cfg


CONFIG = load_config()
try:
    STATE_TIMEOUT = float(CONFIG.get("state_timeout_s", 600))
except (TypeError, ValueError):
    STATE_TIMEOUT = 600.0


def media_root():
    """The Props orb's folder, resolved. Defaults to the repo's own ./media.

    A notes orb could always point at any folder on disk while the media orb
    was pinned to ./media, and that asymmetry cost real users something: with
    an existing library of props you had to COPY it into the repo to use it.
    Two copies of your own files, and the second one sitting inside a git
    working tree where a single `git add -A` publishes them.

    The Props orb's `path` is honoured the same way a notes orb's is now.
    Point this at the folder you already have; your files stay yours and stay
    out of the repo. A relative path still resolves against the repo, so the
    shipped default is unchanged and an existing config keeps working.
    """
    for orb in CONFIG.get("orbs", []):
        if orb.get("kind") == "media":
            q = Path(str(orb.get("path") or "media")).expanduser()
            return (q if q.is_absolute() else HERE / q).resolve()
    return (HERE / "media").resolve()


def orb_root(i):
    """Resolve a notes orb's jail root, or None."""
    try:
        orb = CONFIG["orbs"][int(i)]
        assert orb.get("kind") == "notes"
        p = Path(orb["path"])
        if not p.is_absolute():
            p = HERE / p
        return p.resolve()
    except Exception:
        return None


_STATE = b"{}"          # latest scene state: tracker POSTs, render GETs
_CMDS = []              # queued board commands (your AI -> tracker)
_ALLOWED = ("add_img", "add_card", "clear", "reset", "hand", "give",
            "yank", "hover", "scroll_note", "widget", "explode", "assemble",
            "present")


class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        """Serve /media/* from the configured Props folder, not blindly from ./media.

        THE THIRD PLACE, and the one that would have made this a half-fix. The
        airlock check and the props tree both honour media_root(), but static
        serving resolved against the repo because the base handler is built with
        directory=HERE. Left alone, the tree would have listed a viewer's real
        props and every one of them would have 404'd.
        """
        clean = path.split("?", 1)[0].split("#", 1)[0]
        if clean.startswith("/media/"):
            root = media_root()
            rel = urllib.parse.unquote(clean[len("/media/"):]).lstrip("/")
            target = (root / rel).resolve()
            # Same containment rule as the airlock: resolve first, then prove
            # the result is inside. A prefix comparison on strings is not it.
            if root == target or root in target.parents:
                return str(target)
            return str(root)
        return super().translate_path(path)

    def end_headers(self):
        # no-store on the page itself so a plain reload always serves
        # current code (Chrome happily caches through reloads otherwise)
        if self.path.split("?")[0].endswith("stage.html"):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(HERE), **k)

    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        global _STATE
        n = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(n) if 0 < n < 262144 else b"{}"
        if self.path == "/state":
            # the tracker's heartbeat doubles as the command channel
            _STATE = body
            out = json.dumps(_CMDS[:8]).encode()
            del _CMDS[:8]
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)
            return
        if self.path == "/cmd":
            try:
                cmd = json.loads(body)
                assert cmd.get("a") in _ALLOWED
                if cmd["a"] in ("add_img", "hand", "give", "present") and cmd.get("src"):
                    # THE AIRLOCK: only files really inside ./media/ ever
                    # stage — subfolders allowed, escapes 400. If the
                    # exact path misses, a UNIQUE basename match anywhere
                    # inside the airlock self-heals a wrong-folder guess;
                    # zero or many matches still 400.
                    rel = str(cmd.get("src", "")).lstrip("/")
                    if rel.startswith("media/"):
                        rel = rel[6:]
                    media = media_root()
                    target = (media / rel).resolve()
                    if media not in target.parents or not target.is_file():
                        name = Path(rel).name.lower()
                        hits = [p for p in media.rglob("*")
                                if p.is_file()
                                and p.name.lower() == name] if name else []
                        if len(hits) != 1:
                            raise ValueError("not in the media airlock")
                        target = hits[0]
                    cmd["src"] = "/media/" + target.relative_to(media).as_posix()
                _CMDS.append(cmd)
                self.send_response(204)
            except Exception:
                self.send_response(400)
            self.end_headers()
            return
        self.send_response(404)
        self.end_headers()

    def do_GET(self):
        if self.path == "/config":
            # the page builds its ring name + orb bloom from this
            self._json({
                "name": CONFIG.get("name", "Assistant"),
                "version": CONFIG.get("version", APP_VERSION),
                "features": CONFIG.get("features", FEATURES),
                "orbs": [{"title": o.get("title", "?"),
                          "kind": o.get("kind", "notes")}
                         for o in CONFIG["orbs"]],
            })
            return
        if self.path == "/meta":
            self._json({
                "name": CONFIG.get("name", "Assistant"),
                "version": CONFIG.get("version", APP_VERSION),
                "features": CONFIG.get("features", FEATURES),
                "state_timeout_s": STATE_TIMEOUT,
                "port": int(CONFIG.get("port", 8794)),
            })
            return
        if self.path.startswith("/tree"):
            # a notes orb's folder tree. Jailed to that orb's configured
            # folder, .md only, CLAUDE.md (AI config, not a note) excluded.
            q = urllib.parse.parse_qs(
                urllib.parse.urlparse(self.path).query)
            idx = (q.get("orb") or ["0"])[0]
            root = orb_root(idx)
            if root is None or not root.is_dir():
                self._json({"name": "?", "notes": [], "dirs": []}, 404)
                return

            def walk(d):
                out = {"name": d.name, "notes": [], "dirs": []}
                for p in sorted(d.iterdir()):
                    if p.name.startswith("."):
                        continue
                    if p.is_dir():
                        sub = walk(p)
                        if sub["notes"] or sub["dirs"]:
                            out["dirs"].append(sub)
                    elif p.suffix == ".md" and p.name != "CLAUDE.md":
                        # note files travel as "<orb>/<relpath>" so /note
                        # knows which jail to resolve them against
                        out["notes"].append(
                            {"title": p.stem,
                             "file": f"{int(idx)}/{p.relative_to(root).as_posix()}"})
                return out
            try:
                tree = walk(root)
                tree["name"] = CONFIG["orbs"][int(idx)].get("title", tree["name"])
                self._json(tree)
            except Exception:
                self._json({"name": "?", "notes": [], "dirs": []}, 500)
            return
        if self.path == "/props":
            # the media airlock as a browsable tree — live filesystem
            # read: drop a file in media/, reopen the orb, it's there
            EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".webm",
                    ".glb", ".gltf"}
            mroot = media_root()

            def walkm(d):
                out = {"name": d.name, "items": [], "dirs": []}
                for p in sorted(d.iterdir()):
                    if p.name.startswith("."):
                        continue
                    if p.is_dir():
                        sub = walkm(p)
                        # A folder carrying a README was made on purpose, so
                        # it stays listed even while empty. holo/ and models/
                        # ship exactly that way -- nothing in them but a
                        # README saying what to drop in -- and hiding every
                        # folder with no stageable file made them invisible
                        # until you had already found them. This board is HOW
                        # you discover a folder, so the one that teaches you
                        # the hologram cannot be the one you must know about
                        # first. Arbitrary empty folders still stay hidden.
                        documented = (p / "README.md").is_file()
                        if sub["items"] or sub["dirs"] or documented:
                            out["dirs"].append(sub)
                    elif p.suffix.lower() in EXTS:
                        out["items"].append(p.relative_to(mroot).as_posix())
                return out
            try:
                tree = walkm(mroot)
                tree["name"] = "Props"
                self._json(tree)
            except Exception:
                self._json({"name": "Props", "items": [], "dirs": []}, 500)
            return
        if self.path == "/orb":
            # the ring's heartbeat: your assistant's live state, read from
            # tiny files in ./state/. Every read fails soft — no files,
            # no assistant, no problem: the ring just breathes.
            s_dir = HERE / "state"
            out = {"state": "idle", "mood": "green", "wave": None}
            try:
                f = s_dir / "state"
                s = f.read_text().strip().lower()
                if s in ("idle", "listening", "thinking", "speaking"):
                    age = time.time() - f.stat().st_mtime
                    if s == "idle" or age < STATE_TIMEOUT:
                        out["state"] = s
            except Exception:
                pass
            try:
                m = json.loads((s_dir / "mood.json").read_text())
                if time.time() - float(m.get("ts", 0)) < 45.0:
                    out["mood"] = m.get("mood", "green")
            except Exception:
                pass
            if out["state"] == "speaking":
                try:
                    w = json.loads((s_dir / "wave.json").read_text())
                    if time.time() - float(w.get("ts", 0)) < 0.6:
                        out["wave"] = w.get("samples", [])[:64]
                except Exception:
                    pass
            self._json(out)
            return
        if self.path == "/state":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(_STATE)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(_STATE)
            return
        if not self.path.startswith("/note?"):
            return super().do_GET()
        # one note's text: f=<orb>/<relpath>, resolved against that orb's
        # jail. Inside the root, .md only, must exist — anything else 404s.
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        rel = (q.get("f") or [""])[0]
        idx, _, rel = rel.partition("/")
        root = orb_root(idx)
        if root is None:
            self.send_response(404)
            self.end_headers()
            return
        target = (root / rel).resolve()
        if (root not in target.parents) or target.suffix != ".md" \
                or not target.is_file():
            self.send_response(404)
            self.end_headers()
            return
        body = target.read_text(encoding="utf-8", errors="replace").encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    (HERE / "state").mkdir(exist_ok=True)  # the ring's runtime files land here
    port = int(CONFIG.get("port", 8794))
    print(f"barehands 6.7.0 up: http://127.0.0.1:{port}/stage.html", flush=True)
    print("  tracker (camera): open that URL in Chrome", flush=True)
    print("  render (overlay): same URL + ?role=render", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
