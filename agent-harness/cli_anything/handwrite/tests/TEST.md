# TEST.md — cli-anything-handwrite

Test plan **and** results for the `cli-anything-handwrite` CLI harness. This file
is written before implementation (Part 1) and appended with results after
execution (Part 2), per HARNESS Phase 4–6.

## Part 1 — Test Plan

### Test Inventory

| File | Scope | Est. tests |
|---|---|---|
| `test_core.py` | Unit (pure Python, no Node) | ~30 |
| `test_full_e2e.py` | Real-backend E2E + CLI subprocess | ~16 |

### Unit Test Plan (`test_core.py`)

No external dependencies. Synthetic data only. Fast + deterministic.

- **model.py**
  - `create_document_model` / `default_global_params`: every default value
    matches `src/shared/settings.ts` (paper 667×945, font_size 30, rate 4,
    perturb_theta_sigma 0.05, alignment "left", …).
  - `document_to_dict` / `document_from_dict` round-trip preserves
    text/global_params/overrides.
  - `DocumentModelOps.set_range`: basic override, gap-fill inside a cleared
    region, split across an existing segment, merge of adjacent equal params.
  - `clear_range`: removes inside, preserves outside, splits crossing segments.
  - `effective_params` / `override_at`: global + override merge at an index.
  - `trim_to_text`: shrinks overrides when text shortens, drops out-of-range.
  - Parity spot-checks against the TS test cases in `tests/layout.test.ts`
    (override changes font_size; underline carried).
- **params.py**
  - `parse_color`: named (black/red/white/blue), `#rrggbb`, `#rrggbbaa`,
    `"r,g,b"`, list/tuple.
  - `parse_background`: named (transparent/white) + hex.
  - `coerce_value`: rate accepts `x4`; underline accepts "true"; numeric
    coercion; fill → list.
  - `validate_params`: `font_size > line_spacing` raises; `paper_w<=0` raises;
    bad alignment raises; bad rate raises.
  - `normalize_key` / aliases; `apply_preset` (a4 changes paper + margins);
    unknown preset raises.
- **session.py**
  - `snapshot`/`undo`/`redo`: mutation → undo restores prior, redo replays.
  - `save_session`/`load_session` JSON round-trip (locked save) on a real
    temp path.
  - `status` / `history` report modified + depths.
- **render.py**
  - `verify_png`: valid PNG (magic bytes + IHDR width/height); rejects bad
    magic; rejects missing file.
  - `verify_render_result` on a synthetic page record.
- **cli `_parse_override_pairs`**: `font_size=50 fill=red` → correct typed dict;
  rejects non-adjustable key; rejects malformed `KEY VALUE`.

### E2E Test Plan (`test_full_e2e.py`)

**Invokes the REAL Node render pipeline** (no graceful degradation). Requires
the project checkout with `npm install` and a `.ttf` in `ttf_library/`.

- **TestRenderE2E** — create project with Chinese + ASCII text, render via real
  backend, verify:
  - PNG magic bytes `89 50 4e 47 0d 0a 1a 0a`
  - dimensions == `paper_w*rate × paper_h*rate`
  - page_count >= 1, file size > 1000
  - print artifact paths for manual inspection.
- **TestSeedReproducibility** — same seed → byte-identical PNG; different seed
  → different bytes.
- **TestOverridesRendered** — an override (`font_size=50`) on a range produces a
  page whose layout differs from the no-override baseline (byte difference),
  proving overrides reach the real renderer.
- **TestTomlRoundTrip** — `serialize-toml` then `load-toml` via the real
  persistence layer; output is GUI-native (smol-toml: `[[overrides]]` +
  `[overrides.params]`); model preserved.
- **TestParamValidationE2E** — `font_size > line_spacing` is rejected by the
  backend with the same message as `renderer.ts`.
- **TestCLISubprocess** — `_resolve_cli("cli-anything-handwrite")`:
  - `--help` exits 0.
  - `--json project new` emits valid JSON with a `project` record.
  - full workflow: `project new` → `param set` → `override set` → `render run`
    → verify PNG via subprocess, no hardcoded paths, no CWD assumption.
  - `--dry-run` does not rewrite the project TOML.
- **TestSubprocessReproducibility** — two subprocess renders with the same seed
  produce identical PNG bytes.

### Realistic Workflow Scenarios

1. **Official-form filler** — long Chinese text → multi-page render at rate 4,
   center alignment, verified PNGs. *Verified: page_count, dimensions, magic.*
2. **Selection override** — set a red larger-font override on a span → render →
   differs from baseline. *Verified: byte difference vs baseline.*
3. **Config portability** — CLI saves `.toml` → reloads → re-renders identically.
   *Verified: model equality + reproducible render.*
4. **Undo/redo stress** — set param, override, text; undo all; redo all; render
   matches the pre-undo render. *Verified: snapshot/redo semantics.*

## Part 2 — Test Results

Run with `CLI_ANYTHING_FORCE_INSTALLED=1` so subprocess tests exercise the real
installed command (confirmed by `_resolve_cli`):

```
[_resolve_cli] Using installed command: C:\Users\26673\AppData\Roaming\Python\Python314\Scripts\cli-anything-handwrite.EXE
```

```
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.0.0 -- C:\Python314\python.exe
rootdir: ...\agent-harness
collected 64 items

cli_anything/handwrite/tests/test_core.py::TestDefaults::test_default_global_params_match_ts PASSED [  1%]
cli_anything/handwrite/tests/test_core.py::TestDefaults::test_create_document_model PASSED [  3%]
cli_anything/handwrite/tests/test_core.py::TestDefaults::test_adjustable_keys_match_ts PASSED [  4%]
cli_anything/handwrite/tests/test_core.py::TestRoundTrip::test_to_from_dict_roundtrip PASSED [  6%]
cli_anything/handwrite/tests/test_core.py::TestRoundTrip::test_from_dict_missing_fields PASSED [  7%]
cli_anything/handwrite/tests/test_core.py::TestSetRange::test_basic_override PASSED [  9%]
cli_anything/handwrite/tests/test_core.py::TestSetRange::test_override_changes_font_size_parity PASSED [ 10%]
cli_anything/handwrite/tests/test_core.py::TestSetRange::test_override_underline_carried PASSED [ 12%]
cli_anything/handwrite/tests/test_core.py::TestSetRange::test_merge_adjacent_equal PASSED [ 14%]
cli_anything/handwrite/tests/test_core.py::TestSetRange::test_gap_fill PASSED [ 15%]
cli_anything/handwrite/tests/test_core.py::TestSetRange::test_split_crossing_segment PASSED [ 17%]
cli_anything/handwrite/tests/test_core.py::TestSetRange::test_empty_params_noop PASSED [ 18%]
cli_anything/handwrite/tests/test_core.py::TestSetRange::test_out_of_range_clamped PASSED [ 20%]
cli_anything/handwrite/tests/test_core.py::TestClearRange::test_clear_inside PASSED [ 21%]
cli_anything/handwrite/tests/test_core.py::TestClearRange::test_clear_all PASSED [ 23%]
cli_anything/handwrite/tests/test_core.py::TestTrimToText::test_keeps_and_clamps_fitting_override PASSED [ 25%]
cli_anything/handwrite/tests/test_core.py::TestTrimToText::test_drops_overlong_override PASSED [ 26%]
cli_anything/handwrite/tests/test_core.py::TestTrimToText::test_drops_fully_out_of_range PASSED [ 28%]
cli_anything/handwrite/tests/test_core.py::TestParseColor::test_named PASSED [ 29%]
cli_anything/handwrite/tests/test_core.py::TestParseColor::test_hex_6 PASSED [ 31%]
cli_anything/handwrite/tests/test_core.py::TestParseColor::test_hex_8 PASSED [ 32%]
cli_anything/handwrite/tests/test_core.py::TestParseColor::test_csv PASSED [ 34%]
cli_anything/handwrite/tests/test_core.py::TestParseColor::test_list PASSED [ 35%]
cli_anything/handwrite/tests/test_core.py::TestParseColor::test_background_named PASSED [ 37%]
cli_anything/handwrite/tests/test_core.py::TestParseColor::test_bad PASSED [ 39%]
cli_anything/handwrite/tests/test_core.py::TestCoerce::test_rate_alias PASSED [ 40%]
cli_anything/handwrite/tests/test_core.py::TestCoerce::test_underline PASSED [ 42%]
cli_anything/handwrite/tests/test_core.py::TestCoerce::test_fill_coerces_to_list PASSED [ 43%]
cli_anything/handwrite/tests/test_core.py::TestCoerce::test_numeric PASSED [ 45%]
cli_anything/handwrite/tests/test_core.py::TestValidate::test_font_size_gt_line_spacing PASSED [ 46%]
cli_anything/handwrite/tests/test_core.py::TestValidate::test_nonpositive_paper PASSED [ 48%]
cli_anything/handwrite/tests/test_core.py::TestValidate::test_bad_alignment PASSED [ 50%]
cli_anything/handwrite/tests/test_core.py::TestValidate::test_bad_rate PASSED [ 51%]
cli_anything/handwrite/tests/test_core.py::TestValidate::test_valid_ok PASSED [ 53%]
cli_anything/handwrite/tests/test_core.py::TestPresetsAndKeys::test_normalize_alias PASSED [ 54%]
cli_anything/handwrite/tests/test_core.py::TestPresetsAndKeys::test_apply_preset_a4 PASSED [ 56%]
cli_anything/handwrite/tests/test_core.py::TestPresetsAndKeys::test_unknown_preset PASSED [ 57%]
cli_anything/handwrite/tests/test_core.py::TestPresetsAndKeys::test_is_global_key PASSED [ 59%]
cli_anything/handwrite/tests/test_core.py::TestSession::test_undo_redo PASSED [ 60%]
cli_anything/handwrite/tests/test_core.py::TestSession::test_undo_empty PASSED [ 62%]
cli_anything/handwrite/tests/test_core.py::TestSession::test_save_load_roundtrip PASSED [ 64%]
cli_anything/handwrite/tests/test_core.py::TestSession::test_modified_tracking PASSED [ 65%]
cli_anything/handwrite/tests/test_core.py::TestVerifyPng::test_valid_png PASSED [ 67%]
cli_anything/handwrite/tests/test_core.py::TestVerifyPng::test_bad_magic PASSED [ 68%]
cli_anything/handwrite/tests/test_core.py::TestVerifyPng::test_missing PASSED [ 70%]
cli_anything/handwrite/tests/test_core.py::TestParseOverridePairs::test_basic PASSED [ 71%]
cli_anything/handwrite/tests/test_core.py::TestParseOverridePairs::test_alignment_and_underline PASSED [ 73%]
cli_anything/handwrite/tests/test_core.py::TestParseOverridePairs::test_float PASSED [ 75%]
cli_anything/handwrite/tests/test_core.py::TestParseOverridePairs::test_rejects_non_adjustable PASSED [ 76%]
cli_anything/handwrite/tests/test_core.py::TestParseOverridePairs::test_rejects_malformed PASSED [ 78%]
cli_anything/handwrite/tests/test_full_e2e.py::TestRenderE2E::test_render_real_png PASSED [ 79%]
cli_anything/handwrite/tests/test_full_e2e.py::TestRenderE2E::test_multi_page_long_text PASSED [ 81%]
cli_anything/handwrite/tests/test_full_e2e.py::TestSeedReproducibility::test_same_seed_identical PASSED [ 82%]
cli_anything/handwrite/tests/test_full_e2e.py::TestSeedReproducibility::test_diff_seed_diff PASSED [ 84%]
cli_anything/handwrite/tests/test_full_e2e.py::TestOverridesRendered::test_override_changes_output PASSED [ 85%]
cli_anything/handwrite/tests/test_full_e2e.py::TestTomlRoundTrip::test_serialize_load_via_real_persistence PASSED [ 87%]
cli_anything/handwrite/tests/test_full_e2e.py::TestParamValidationE2E::test_font_size_gt_line_spacing_rejected PASSED [ 89%]
cli_anything/handwrite/tests/test_full_e2e.py::TestCLISubprocess::test_help PASSED [ 90%]
cli_anything/handwrite/tests/test_full_e2e.py::TestCLISubprocess::test_version PASSED [ 92%]
cli_anything/handwrite/tests/test_full_e2e.py::TestCLISubprocess::test_project_new_json PASSED [ 93%]
cli_anything/handwrite/tests/test_full_e2e.py::TestCLISubprocess::test_full_workflow PASSED [ 95%]
cli_anything/handwrite/tests/test_full_e2e.py::TestCLISubprocess::test_dry_run_does_not_save PASSED [ 96%]
cli_anything/handwrite/tests/test_full_e2e.py::TestCLISubprocess::test_subprocess_seed_reproducibility PASSED [ 98%]
cli_anything/handwrite/tests/test_full_e2e.py::TestUndoRedoWorkflow::test_undo_redo_render_parity PASSED [100%]

============================= 64 passed in 14.82s =============================
```

### Summary

| Metric | Value |
|---|---|
| Total tests | 64 |
| Passed | 64 |
| Failed | 0 |
| Pass rate | 100% |
| Duration | ~15s |
| Unit (`test_core.py`) | 50 |
| E2E (`test_full_e2e.py`) | 14 |
| Backend | Real Node pipeline (`render_backend.mjs` → `renderPages`) |
| CLI under test | Installed `cli-anything-handwrite.EXE` (force-installed) |

### Coverage Notes

- **Real-software verification**: every E2E render invokes the actual Node
  render pipeline and verifies PNG magic bytes, dimensions (`paper × rate`),
  page count, and byte-level seed reproducibility.
- **Rendering-gap guard**: `TestOverridesRendered` proves overrides reach the
  real renderer (output differs from baseline) — not silently dropped.
- **GUI interoperability**: `TestTomlRoundTrip` confirms CLI-written `.toml`
  uses the GUI-native `smol-toml` format (`[[overrides]]` + `[overrides.params]`).
- **Auto-save / `--dry-run`**: `TestCLISubprocess::test_dry_run_does_not_save`
  verifies `--dry-run` suppresses persistence while normal one-shots persist.
- **Subprocess tests** use `_resolve_cli()` with `CLI_ANYTHING_FORCE_INSTALLED=1`,
  no hardcoded paths, no CWD assumption.
- **Gaps**: no pixel-level ink-coverage assertion (format/reproducibility/override
  verification is sufficient and robust against font changes); premium/stub
  `AIFontEdgeEnhancer` path is a no-op by design and not rendered.

