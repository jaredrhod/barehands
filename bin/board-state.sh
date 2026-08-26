#!/bin/bash
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
# board-state.sh — your AI's EYES on the board. Read-only GET of the
# server's /state (the tracker's last scene heartbeat), rendered one
# line per item so an assistant can answer "what's on the board?" from
# truth instead of memory. Reaches nothing but localhost; changes nothing.
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
# Portable interpreter. python3 does not exist on Windows, where the
# python.org installer provides py and python instead. python3 is tried
# FIRST so macOS and Linux resolve exactly as before.
PYBIN=$(command -v python3 2>/dev/null || command -v python 2>/dev/null || command -v py 2>/dev/null || true)
if [ -z "$PYBIN" ]; then echo "No Python found (tried python3, python, py)." >&2; exit 1; fi
PORT=$("$PYBIN" -c "import json;print(json.load(open('$DIR/barehands.json')).get('port',8794))" 2>/dev/null || echo 8794)
STATE=$(curl -sS --max-time 3 "http://127.0.0.1:$PORT/state" 2>/dev/null) || {
    echo "The board is dark — the barehands server isn't running."; exit 1; }
export STATE
"$PYBIN" <<'PY'
import json, os

try:
    d = json.loads(os.environ["STATE"])
except ValueError:
    d = None
if not d:
    print("Server is up, but no tracker page has connected yet.")
    raise SystemExit
items = d.get("items") or []
if not items:
    print("The board is EMPTY (as of the tracker's last heartbeat).")
    raise SystemExit

def zone(x, y):
    h = "left" if x < 0.33 else ("center" if x < 0.67 else "right")
    v = "top" if y < 0.33 else ("middle" if y < 0.67 else "bottom")
    return "center" if (h == "center" and v == "middle") else f"{v}-{h}"

print(f"ON THE BOARD — {len(items)} item(s), last tracker heartbeat:")
for i in items:
    t = i.get("type", "?")
    title = i.get("title") or ""
    src = os.path.basename(i.get("src") or "")
    if t == "card":
        body = (i.get("body") or "").replace("\n", " ")[:70]
        desc = f'card "{title}"' + (f" — {body}" if body else "")
    elif t == "img":
        desc = f"image {src}" + (" (fx, frameless)" if i.get("fxf") else "") \
               + (" (video)" if i.get("vd") else "")
    elif t == "model":
        mode = "hologram wireframe" if i.get("mm") == "holo" else "solid"
        desc = f"3D model {src} ({mode})"
        ex = i.get("ex") or 0
        if ex > 0.02:
            desc += f", EXPLODED {round(ex * 100)}%"
    elif t == "panel":
        desc = f'open note "{title}"'
    elif t == "browser":
        desc = f'file browser "{title}"'
    elif t == "widget":
        desc = "the assistant ring"
    elif t == "orb":
        desc = f'orb "{title}"'
    else:
        desc = f'{t} "{title or src}"'
    flags = []
    if i.get("g"):
        flags.append("IN THE USER'S HAND")
    sc = i.get("scale") or 1
    if sc >= 1.6:
        flags.append("blown up large")
    elif sc <= 0.55:
        flags.append("shrunk small")
    op = i.get("op", 1)
    if op is not None and op < 0.5:
        flags.append("faded out")
    pos = zone(i.get("x") or 0.5, i.get("y") or 0.5)
    line = f"  - {desc} @ {pos}"
    if flags:
        line += "  [" + ", ".join(flags) + "]"
    print(line)
PY
