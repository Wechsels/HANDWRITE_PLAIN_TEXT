# cli-anything-handwrite

Agent-usable, stateful CLI for the **HandWrite Plain Text** generator. Renders
plain text as paginated "handwritten" PNG images by driving the project's
**real Node.js render pipeline** (layout + stroke perturbation +
`@napi-rs/canvas`) — rendering is never reimplemented. Supports GUI-native TOML
project files, range-level overrides, seeded reproducible renders, and undo/redo.

This package is built per the [cli-anything](https://github.com/) methodology
(see `HARNESS.md`). Software analysis lives in `agent-harness/HANDWRITE.md`.

## Install

```bash
pip install -e .          # from agent-harness/
```

### Hard dependencies

- **Python ≥ 3.11**
- **Node.js ≥ 20** on PATH
- The **HandWrite Plain Text** project checked out with `npm install` done
  (provides `@napi-rs/canvas`, `smol-toml`, `ttf_library/*.ttf`).
- A `.ttf` font in `ttf_library/`.

Point the CLI at the project root:

```bash
export HANDWRITE_PROJECT_ROOT=/path/to/HANDWRITE_PLAIN_TEXT
# or just run from inside the project
```

## Quick start

```bash
# JSON one-shot workflow
cli-anything-handwrite --json project new --text "手写测试" -o p.toml
cli-anything-handwrite --json --project p.toml font set 0
cli-anything-handwrite --json --project p.toml render run --seed 42 --output-dir out

# Interactive REPL (default)
cli-anything-handwrite
```

See `SKILL.md` for the full command reference and agent guidance.

## How rendering works (no reimplementation)

The CLI does **not** render in Python. It bundles the project's real render
pipeline headlessly into `scripts/render_backend.mjs` (built by
`vite.config.cli.ts` from `agent-harness/cli_src/cli_render_entry.ts`), then
invokes it via `node` as a subprocess. `@napi-rs/canvas` and `smol-toml` are
resolved from the project's `node_modules` at runtime (via `NODE_PATH`).

To rebuild the bundle after editing the render pipeline:

```bash
cd /path/to/HANDWRITE_PLAIN_TEXT
npx vite build --config vite.config.cli.ts
```

## Tests

```bash
# from agent-harness/
python -m pytest cli_anything/handwrite/tests/ -v -s

# force-installed mode (tests the real installed command, not the module fallback):
CLI_ANYTHING_FORCE_INSTALLED=1 python -m pytest cli_anything/handwrite/tests/ -v -s
```

Tests invoke the **real** Node backend and verify PNG outputs (magic bytes,
dimensions, page count, seed reproducibility). See `tests/TEST.md`.

## Layout

```
cli_anything/handwrite/
├── __init__.py / __main__.py
├── handwrite_cli.py          # Click CLI + REPL
├── core/
│   ├── model.py              # DocumentModel ops (port of settings.ts)
│   ├── params.py             # global params, validation, presets, colors
│   ├── project.py            # new/open/save/info
│   ├── session.py            # stateful session, undo/redo, locked saves
│   └── render.py             # real-backend render + output verification
├── utils/
│   ├── handwrite_backend.py  # subprocess driver for the real Node pipeline
│   └── repl_skin.py          # unified REPL skin (from cli-anything-plugin)
├── scripts/render_backend.mjs # bundled real render entry
├── skills/SKILL.md           # packaged skill copy
└── tests/                    # test_core.py + test_full_e2e.py + TEST.md
```

## License

WNCPL v1.0 (Wechsels Non-Commercial License). The vendored `handright` stroke
perturbation remains BSD-3-Clause.
