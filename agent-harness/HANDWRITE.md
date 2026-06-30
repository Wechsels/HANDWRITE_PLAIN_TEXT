# HANDWRITE_PLAIN_TEXT — CLI Harness SOP

Software-specific analysis and standard operating procedure for turning the
**HandWrite Plain Text** generator (Electron + Vue 3 + Node.js) into an
agent-usable, stateful CLI: `cli-anything-handwrite`.

This file follows [`HARNESS.md`](../../.claude/plugins/...) (the cli-anything
methodology). It does not duplicate the harness; it records what is specific to
this software.

---

## 1. What the software is

HandWrite Plain Text renders plain text as "handwritten" PNG images — for
filling official forms, pledge letters, thought reports, etc. with meaningless
handwritten-looking text. Stack: **Electron + Vue 3 + TypeScript + Node.js**.
The render pipeline uses `@napi-rs/canvas` for font rasterization and a
vendored `handright` (BSD-3-Clause) stroke-perturbation kernel.

- **GUI**: `src/renderer/` (Vue editor + preview windows), driven by Electron
  IPC in `src/main/ipc.ts`.
- **Backend engine**: `src/main/render/` — `layout.ts` (pagination + line
  breaking), `perturb.ts` (per-glyph stroke jitter), `fontCache.ts` (TTF
  rasterization + ink-bbox), `renderer.ts` (composes pages, encodes PNG).
- **Data model**: `src/shared/settings.ts` — `DocumentModel`
  `{ text, global_params, overrides[] }` and `DocumentModelOps` (range
  split/merge/clear). This is the **native project state**.
- **Native project format**: TOML, via `src/main/persistence.ts`
  (`saveModel`/`loadModel` → `smol-toml`). A `.toml` file is round-trippable
  with the GUI.
- **Output**: paginated PNGs (`outputs/0.png`, `1.png`, …) at
  `paper_w*rate × paper_h*rate` resolution.

## 2. GUI action → backend mapping

| GUI action (IPC) | Backend function | CLI operation |
|---|---|---|
| `handwrite:listFonts` | `fonts.listFonts()` (scan `ttf_library/`) | `font list` |
| `handwrite:render` | `renderPages(model, seed, save=true)` | `render run` |
| `handwrite:saveConfig` | `persistence.saveModel` | `project save` |
| `handwrite:loadConfig` | `persistence.loadModel` | `project open` |
| Editor: set global param | `model.global_params[k] = v` | `param set` |
| Editor: select span + override | `DocumentModelOps.setRange` | `override set` |
| Editor: clear span override | `DocumentModelOps.clearRange` | `override clear` |
| Editor: edit text | `model.text = ...; trimToText` | `text set` |
| Preview: open outputs | `shell.openPath(OUTPUTS_DIR)` | `render open` / paths in JSON |

## 3. Backend invocation strategy (the #1 rule)

HARNESS rule: **use the real software, do not reimplement it.** Here the "real
software" is the project's own Node.js render pipeline — not a separate
executable like `libreoffice`. We do **not** reimplement layout/perturb in
Python.

### Headless render backend bundle

`agent-harness/cli_src/cli_render_entry.ts` is a headless entry that imports the
**real** modules (`renderPages`, `saveModel`, `loadModel`, `documentFromDict`).
It is bundled by `vite.config.cli.ts` (SSR/Node mode) into
`cli_anything/handwrite/scripts/render_backend.mjs`, with:

- `@shared` alias resolved → `src/shared`
- `electron` aliased to a stub (`electron-stub.js`) — the render path never
  touches Electron because `renderPages` is called with `save=false`, skipping
  `saveOutputs` (the only Electron reference, a lazy `require('../paths')`).
- `@napi-rs/canvas` and `smol-toml` kept external (resolved from `node_modules`
  at runtime via `NODE_PATH`).

The bundle subcommands (stdout = JSON):

```
node render_backend.mjs render <model.json> <outdir> [seed]
node render_backend.mjs serialize-toml <model.json> <out.toml>
node render_backend.mjs load-toml <in.toml> [out.json]
node render_backend.mjs list-fonts [out.json] [ttf_dir]
node render_backend.mjs probe
```

### Python backend wrapper

`utils/handwrite_backend.py` finds `node` (`shutil.which`), locates the bundled
`render_backend.mjs` relative to the package, resolves the **project root** (env
`HANDWRITE_PROJECT_ROOT`, else walk up for `node_modules/@napi-rs/canvas` +
`ttf_library`, else cwd), and invokes the bundle with
`cwd=project_root` and `NODE_PATH=<root>/node_modules` so the native canvas +
`smol-toml` resolve. If `node` or the project is missing, it raises a clear
error with install instructions (hard dependency).

### Data layer in Python

`core/model.py` mirrors `DocumentModelOps` from `settings.ts` **exactly**
(`set_range`/`clear_range`/`split_at`/`merge_adjacent`/`effective_params`/
`trim_to_text`). This is project-file data manipulation — permitted by HARNESS
("manipulate the native format directly as the data layer"). **Rendering is
never reimplemented**; every pixel comes from the real Node pipeline.

## 4. State model

- **Session** (JSON, `*.hwsess.json`): holds the `DocumentModel` dict, current
  font, output dir, seed, undo/redo history. Saved with `_locked_save_json`
  (see `guides/session-locking.md`).
- **Project file** (TOML, GUI-interoperable): written/read through the real
  `persistence` module via the backend (`serialize-toml` / `load-toml`), so a
  CLI-saved `.toml` opens in the GUI and vice-versa.
- **Auto-save**: one-shot mutations auto-save the session unless `--dry-run`
  (see `guides/auto-save-dry-run.md`). REPL never auto-saves.

## 5. CLI command groups

- **project** — `new` / `open` / `save` / `info` / `close`
- **text** — `set` / `show` / `append`
- **param** — `set` / `get` / `list` / `reset` (global render params + presets)
- **override** — `set` / `clear` / `list` / `show` (range-level, mirrors GUI
  selection overrides)
- **font** — `list` / `set`
- **render** — `run` (real PNG output) / `last` (paths of last render) /
  `open` (open output dir)
- **session** — `status` / `save` / `undo` / `redo` / `history`
- **repl** — interactive mode (default when no subcommand)

Every command supports `--json`. Output verification (PNG magic bytes
`89 50 4e 47`, page count, seed reproducibility, dimensions = `paper*rate`) is
enforced in tests, not just "exit code 0".

## 6. Hard dependencies

- **Node.js ≥ 20** + the HandWrite project checkout with `npm install` done
  (provides `@napi-rs/canvas`, `smol-toml`, and `ttf_library/*.ttf`).
- A `.ttf` font in `ttf_library/` (the GUI errors out on empty dir; the CLI
  does too).
- Python ≥ 3.11 (`tomllib` stdlib) + `click` + `prompt-toolkit`.

## 7. Rebuilding the backend bundle

```bash
npx vite build --config vite.config.cli.ts
```

Source: `agent-harness/cli_src/cli_render_entry.ts` + `electron-stub.js`.
Output: `agent-harness/cli_anything/handwrite/scripts/render_backend.mjs`
(shipped with the pip package via `package_data`).
