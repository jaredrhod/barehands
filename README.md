# barehands v6.7.0

> **Never used Claude Code?** Start at [jaredrhod.com](https://jaredrhod.com): pick your situation and it routes you to the right path.

**Runs on:** a webcam and Chrome; works with any AI. Any program that writes a file or curls localhost can be its brain.

Move things on your screen with your bare hands. barehands turns your webcam into a hand-tracked interface: notes, images, and 3D models float over your camera as glass cards. You pinch them, throw them, and arrange your workspace with natural motion.

And it's a body waiting for a brain: wire in your AI and the on-screen ring becomes its face, while two small scripts give it hands and eyes on your board. Free to use, change, and build on, including commercially.

## Repository

This project is maintained in the GitHub repository: [@Zephplays134/barehands](https://github.com/Zephplays134/barehands)

## What's new in 6.7.0

This update keeps the same core experience but makes it feel more alive, smoother, and more responsive:

- Faster ring polling and live assistant state refreshes
- Smoother board interactions and lighter state handling
- More reliable version metadata for installs and updates
- Better compatibility with custom configs and AI-driven workflows
- Expanded config metadata for future feature flags and upgrades
- Preserved compatibility with the original barehands experience while adding modern improvements

## Updated features and upgrades

- Faster live board responsiveness with cleaner state sync
- Improved runtime metadata for version tracking and feature detection
- More robust config handling for custom orbs and setups
- Better compatibility with AI integrations and live assistant feedback
- Same glass-card workflow, gestures, and board feel — now more polished and efficient
- Updated project branding and repository references for the current fork

**Watch it in action:**

[![barehands demo video](https://img.youtube.com/vi/cV02finVi4o/maxresdefault.jpg)](https://youtu.be/cV02finVi4o)

## Run it (nothing needed)

```bash
git clone https://github.com/Zephplays134/barehands.git
cd barehands
python3 server.py
```

On Windows run `run.bat` instead: a clean Windows 11 has no Python but leaves a Microsoft Store stub on the PATH that looks like one, and `run.bat` finds an interpreter that actually works. Open `http://127.0.0.1:8794/stage.html` in Chrome.

**Already in a Claude Code session with your agent?** One sentence does it all: *"clone https://github.com/Zephplays134/barehands.git, then read barehands/barehands.md and set me up."* Your agent installs the setup wizard and wires your assistant in end to end.

Tap the ring → orbs bloom → tap an orb → your files unfold on glass. The sample notes teach the gestures from inside the board itself.

## Give it your notes

The "vault" on the board is just a folder of markdown, which means **an Obsidian vault works as-is**, and so does any folder of `.md` files. Point an orb at it in `barehands.json`:

```json
{
  "name": "Assistant",
  "orbs": [
    { "title": "Notes", "path": "~/MyVault", "kind": "notes" },
    { "title": "Props", "path": "media", "kind": "media" }
  ]
}
```

One line per orb. Add more folders, rename them, point them anywhere. The `media` orb is the props airlock: drop images in `media/misc/`, transparent props in `media/fx/`, 3D models in `media/models/`.

## Wire in your AI

**The easy way:** open the repo in Claude Code and say *"read barehands.md and set me up."* The setup wizard interviews you, writes the config, and wires your assistant in end to end.

**The manual way:** barehands speaks two dead-simple protocols:

- **The ring is a face.** It reads tiny files in `state/`: write `thinking` (or `idle` / `listening` / `speaking`) to `state/state` and the ring reacts. No files, no problem: it idles beautifully.
- **The board is a stage.** `bin/board.sh '{"a":"present","title":"THE PLAN","body":"..."}'` and the thing flies center stage, enlarged and spotlit, everything else dimmed: that's the show-me verb.

Anything that can write a file or curl localhost can be the brain: Claude, a local LLM, a cron job, a Stream Deck button.

If your assistant doesn't have a memory yet, pair this with [ai-memory-vault](https://github.com/jaredrhod/ai-memory-vault); the vault it builds becomes a notes orb on this board.

## The gestures

Tap (quick pinch) opens and closes. Pinch-drag moves. Hold still while carrying to rotate in 3D. Two hands scale. Flick to throw. **Clap** (palms together, fingers up) sweeps the board clean. **Throw** handles the fast motion interactions.

Every threshold was tuned on a real hand across weeks of live use, and because the gates measure hand *shape* as ratios, not size, they hold at any camera distance. The full cheat sheet is on the sample notes.

## Streaming / recording (advanced)

Two pages, one scene: the tracker page owns your camera; `stage.html?role=render` is a truly transparent mirror of it, built for an OBS browser source: the glass composites over your camera feed while you keep the board interactive.

## Credits

Hand tracking by [Google MediaPipe](https://developers.google.com/mediapipe) (Apache 2.0). 3D rendering by [three.js](https://threejs.org) (MIT). Both load from public CDNs; this repo redistributes them via runtime loading only.

## Updating

barehands improves continuously, and gesture fixes ship often. To update on macOS, double-click the `Update` icon setup left on your Desktop, or run `./update.sh` in this folder. On Windows, run `update.bat` or use the same git-based update flow. The 6.7.0 update keeps the same feel while improving responsiveness and adding faster live status handling.

## The rest of it

A board is better with an agent behind it. Give it a voice and you can talk while you move things around, and a memory vault turns the notes orb into your agent's actual brain instead of a folder of static notes.

- **The whole stack, one command.** [fullstack-agent](https://github.com/jaredrhod/fullstack-agent) installs the memory, the voice, the face, and the hands, and wires them together for you. Pick one and run it.
- **The videos.** [My YouTube](https://www.youtube.com/@homer-238)
- **The Discord.** Thousands of builders, and the fastest place to get unstuck: https://discord.gg/YSdsqMv3V8
- **Everything else,** free and open: https://jaredrhod.com

## Support

Free to use, and always will be. If this helped you out, you can buy me a coffee:

[![Support me on Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/jaredrhod)

## License

Copyright (c) 2026 Captain Pro.

Licensed under the GNU Affero General Public License, version 3 or later (AGPL-3.0-or-later). **Use it in your business, commercially, for free.** Run it, change it, build your workflow on top of it.

