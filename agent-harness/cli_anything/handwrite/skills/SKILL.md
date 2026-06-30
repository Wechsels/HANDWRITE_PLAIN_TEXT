---
name: cli-anything-handwrite
description: Agent-usable CLI for the HandWrite Plain Text generator. Renders plain text as multi-page handwritten PNG images by driving the project's real Node.js render pipeline (layout + stroke perturbation + @napi-rs/canvas), with stateful projects, range-level overrides, and GUI-native TOML config. Use for batch-generating handwritten-looking documents (official forms, pledge letters, reports) without a display.
---

# cli-anything-handwrite

Agent-usable, stateful CLI for the **HandWrite Plain Text** generator. It renders
plain text as paginated "handwritten" PNG images by invoking the project's
**real Node.js render pipeline** (layout engine + vendored `handright` stroke
perturbation + `@napi-rs/canvas` font rasterization) — it never reimplements
rendering. Supports GUI-native TOML project files (round-trippable with the
Electron app), range-level selection overrides, seeded reproducible renders, and
undo/redo.

## Installation

```bash
pip install cli-anything-handwrite
```

**Prerequisites (hard dependencies):**

- **Python ≥ 3.11** (`tomllib` stdlib)
- **Node.js ≥ 20** on PATH
- The **HandWrite Plain Text project** checked out with `npm install` run (this
  provides `@napi-rs/canvas`, `smol-toml`, and `ttf_library/*.ttf`). Point the
  CLI at it with `HANDWRITE_PROJECT_ROOT` or run from inside it.
- At least one `.ttf` font in `ttf_library/` (the GUI errors on an empty dir;
  the CLI does too). Generate fonts with
  [HANDWRITE_TTF_FONTBUILDER](https://github.com/Wechsels/HANDWRITE_TTF_FONTBUILDER).

## Usage

```bash
# Help
cli-anything-handwrite --help

# Interactive REPL (default with no subcommand)
cli-anything-handwrite

# One-shot with JSON output (for agents)
cli-anything-handwrite --json project new --text "hello" -o proj.toml
```

## Command Groups

### project
Project (DocumentModel) lifecycle — TOML files are GUI-native.

| Command | Description |
|---------|-------------|
| `project new [--font P] [--text T] [-o out.toml]` | Create a fresh project |
| `project open <toml>` | Open a GUI-native .toml |
| `project save [toml]` | Save as .toml via the real persistence layer |
| `project info` | Show text/override/param summary |
| `project close` | Close the current project |

### text
| Command | Description |
|---------|-------------|
| `text set [CONTENT] [--file F]` | Set document text |
| `text append <CONTENT>` | Append text |
| `text show [--head N]` | Print document text |

### param (global render parameters)
| Command | Description |
|---------|-------------|
| `param set <KEY> <VALUE>` | Set a global param (e.g. `font_size 40`, `fill #ff0000`, `rate x4`) |
| `param get <KEY>` | Read a param |
| `param list` | List all params |
| `param reset [KEY]` | Reset one or all params to defaults |
| `param preset <name>` | Apply a paper preset: `default`/`a4`/`b5`/`letter` |

Global param keys: `paper_w paper_h font_path font_size line_spacing word_spacing
margin_{top,bottom,left,right} fill background rate {line_spacing,font_size,word_spacing}_sigma
perturb_{x,y,theta}_sigma alignment underline`.

### override (range-level, mirrors GUI selection overrides)
Adjustable keys: `font_size word_spacing perturb_{x,y,theta}_sigma fill alignment underline`.

| Command | Description |
|---------|-------------|
| `override set <start> <end> KEY=VALUE...` | Override `[start,end)` (e.g. `override set 0 5 font_size=50 fill=red`) |
| `override clear <start> <end>` | Clear overrides on a range |
| `override list` | List all override ranges |
| `override show <index>` | Effective params at a character index |

### font
| Command | Description |
|---------|-------------|
| `font list` | List `.ttf` fonts in `ttf_library/` |
| `font set <name|index>` | Set the active font |

### render
| Command | Description |
|---------|-------------|
| `render run [--seed N] [--output-dir D] [--verify]` | Render to PNGs via the real Node pipeline; verifies output |
| `render last` | Print paths from the last render |
| `render open` | Open the output folder (GUI-equivalent button) |

### session
| Command | Description |
|---------|-------------|
| `session status` | Current session state |
| `session save [path]` / `session load <path>` | Persist/load a `.hwsess.json` |
| `session undo` / `session redo` / `session history` | Undo/redo (up to 50 levels) |

### repl
Interactive mode with history + completion (default when no subcommand).

## Examples

### Render a multi-page handwritten document
```bash
cli-anything-handwrite --json project new --text "思想汇报正文..." --font ttf_library/hry手写体.ttf -o report.toml
cli-anything-handwrite --json --project report.toml param set rate x4
cli-anything-handwrite --json --project report.toml render run --seed 42 --output-dir outputs
```

### Selection override (red, larger font on a span)
```bash
cli-anything-handwrite --json --project p.toml override set 0 6 font_size=50 fill=red
cli-anything-handwrite --json --project p.toml render run --seed 7
```

### Seeded reproducibility (same seed → identical PNG bytes)
```bash
cli-anything-handwrite --json --project p.toml render run --seed 7 --output-dir a
cli-anything-handwrite --json --project p.toml render run --seed 7 --output-dir b
# a/0.png and b/0.png are byte-identical
```

## State Management

- **Session** (`.hwsess.json`): holds the model, font, output dir, seed,
  undo/redo history. Saved with locked JSON writes.
- **Project** (`.toml`): GUI-native format; written/read through the real
  `smol-toml` persistence module, so files open in the Electron GUI.
- **Auto-save**: one-shot mutations persist to the project/session unless
  `--dry-run` is passed. The REPL never auto-saves.

## Output Formats

All commands support `--json` for machine-readable output. Errors are reported
as `{"ok": false, "error": "..."}` with a non-zero exit code.

## For AI Agents

1. **Always use `--json`** for parseable output.
2. **Set `HANDWRITE_PROJECT_ROOT`** (or run from the repo) so the backend finds
   `node_modules` + `ttf_library/`.
3. **Pick a font first** with `font list` / `font set`, or pass `--font`.
4. **Verify renders**: `render run` returns a `verification` block (PNG magic
   bytes + dimensions = `paper × rate`). Treat `verification.ok == false` as a
   hard failure — the render may not have produced valid output.
5. **Use a fixed `--seed`** for reproducible output across runs.
6. **Use `--dry-run`** to preview a mutation without persisting it.
7. **Check return codes**: 0 = success, non-zero = error (see stderr / JSON).

## More Information

- Full docs: `README.md` in the package
- Test coverage: `TEST.md` in the package
- Software analysis: `agent-harness/HANDWRITE.md`
- Methodology: `HARNESS.md` in the cli-anything-plugin

## Version

1.0.0
