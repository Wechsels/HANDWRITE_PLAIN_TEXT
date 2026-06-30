"""E2E tests for cli-anything-handwrite.

Invokes the REAL Node render pipeline (no graceful degradation) and the
installed CLI via subprocess. Requires the project checkout with `npm install`
and a `.ttf` in `ttf_library/`.
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

from cli_anything.handwrite.core import model as M
from cli_anything.handwrite.core import render as R
from cli_anything.handwrite.utils import handwrite_backend as BE


def _resolve_cli(name):
    """Resolve installed CLI command; falls back to python -m for dev.

    Set env CLI_ANYTHING_FORCE_INSTALLED=1 to require the installed command.
    """
    import shutil as _shutil
    force = os.environ.get("CLI_ANYTHING_FORCE_INSTALLED", "").strip() == "1"
    path = _shutil.which(name)
    if path:
        print(f"[_resolve_cli] Using installed command: {path}")
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    module = name.replace("cli-anything-", "cli_anything.") + "." + name.split("-")[-1] + "_cli"
    print(f"[_resolve_cli] Falling back to: {sys.executable} -m {module}")
    return [sys.executable, "-m", module]


def _make_model(font_path, text="手写体生成测试\n第二行文字abc"):
    m = M.create_document_model(font_path)
    m["text"] = text
    return m


# ── real-backend render ────────────────────────────────────────────────
class TestRenderE2E:
    def test_render_real_png(self, font_path, tmp_dir, project_root):
        m = _make_model(font_path)
        outdir = os.path.join(tmp_dir, "out")
        result = R.render_model(m, outdir, seed=42, project_root=project_root)
        assert result["page_count"] >= 1
        pages = result["pages"]
        gp = m["global_params"]
        rate = gp["rate"]
        for p in pages:
            assert os.path.exists(p["path"])
            assert p["bytes"] > 1000
            assert p["width"] == gp["paper_w"] * rate
            assert p["height"] == gp["paper_h"] * rate
            v = R.verify_png(p["path"])
            assert v["ok"] is True
            assert v["width"] == p["width"] and v["height"] == p["height"]
            print(f"\n  PNG: {p['path']} ({p['bytes']:,} bytes, {p['width']}x{p['height']})")

    def test_multi_page_long_text(self, font_path, tmp_dir, project_root):
        m = _make_model(font_path, text="字" * 600)
        outdir = os.path.join(tmp_dir, "long")
        result = R.render_model(m, outdir, seed=1, project_root=project_root)
        assert result["page_count"] >= 2
        print(f"\n  pages={result['page_count']} out={outdir}")


class TestSeedReproducibility:
    def test_same_seed_identical(self, font_path, tmp_dir, project_root):
        m = _make_model(font_path)
        d1 = os.path.join(tmp_dir, "s1")
        d2 = os.path.join(tmp_dir, "s2")
        r1 = R.render_model(m, d1, seed=7, project_root=project_root)
        r2 = R.render_model(m, d2, seed=7, project_root=project_root)
        a = open(r1["outputs"][0], "rb").read()
        b = open(r2["outputs"][0], "rb").read()
        assert a == b
        print(f"\n  seed=7 bytes={len(a)} (identical)")

    def test_diff_seed_diff(self, font_path, tmp_dir, project_root):
        m = _make_model(font_path)
        d1 = os.path.join(tmp_dir, "d1")
        d2 = os.path.join(tmp_dir, "d2")
        r1 = R.render_model(m, d1, seed=7, project_root=project_root)
        r2 = R.render_model(m, d2, seed=99, project_root=project_root)
        assert open(r1["outputs"][0], "rb").read() != open(r2["outputs"][0], "rb").read()


class TestOverridesRendered:
    def test_override_changes_output(self, font_path, tmp_dir, project_root):
        """An override must reach the real renderer — output differs from baseline."""
        base = _make_model(font_path)
        over = _make_model(font_path)
        M.DocumentModelOps.set_range(over, 0, 5, {"font_size": 60, "fill": [255, 0, 0, 255]})
        rb = R.render_model(base, os.path.join(tmp_dir, "base"), seed=3, project_root=project_root)
        ro = R.render_model(over, os.path.join(tmp_dir, "over"), seed=3, project_root=project_root)
        a = open(rb["outputs"][0], "rb").read()
        b = open(ro["outputs"][0], "rb").read()
        assert a != b, "override did not change rendered output (rendering gap!)"
        print(f"\n  base={len(a)}B over={len(b)}B (override reached renderer)")


class TestTomlRoundTrip:
    def test_serialize_load_via_real_persistence(self, font_path, tmp_dir, project_root):
        m = _make_model(font_path)
        M.DocumentModelOps.set_range(m, 0, 5, {"font_size": 50})
        toml_path = os.path.join(tmp_dir, "p.toml")
        BE.serialize_toml(M.document_to_dict(m), toml_path, project_root=project_root)
        # GUI-native format: smol-toml uses [[overrides]] + [overrides.params]
        raw = open(toml_path, "r", encoding="utf-8").read()
        assert "[[overrides]]" in raw
        assert "[overrides.params]" in raw
        assert "font_size = 50" in raw
        # Round-trip via the real loadModel
        loaded = BE.load_toml(toml_path, project_root=project_root)
        assert loaded["text"] == m["text"]
        assert loaded["overrides"][0]["params"]["font_size"] == 50
        print(f"\n  TOML: {toml_path}")


class TestParamValidationE2E:
    def test_font_size_gt_line_spacing_rejected(self, font_path, tmp_dir, project_root):
        m = _make_model(font_path)
        m["global_params"]["font_size"] = 100
        m["global_params"]["line_spacing"] = 50
        with pytest.raises(Exception):
            R.render_model(m, os.path.join(tmp_dir, "bad"), seed=1, project_root=project_root)


# ── CLI subprocess ─────────────────────────────────────────────────────
class TestCLISubprocess:
    CLI_BASE = _resolve_cli("cli-anything-handwrite")

    def _run(self, args, env=None, check=True):
        return subprocess.run(
            self.CLI_BASE + args,
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", check=check, env=env,
        )

    def test_help(self):
        r = self._run(["--help"])
        assert r.returncode == 0
        assert "HandWrite" in r.stdout or "handwrite" in r.stdout.lower()

    def test_version(self):
        r = self._run(["--version"])
        assert r.returncode == 0
        assert "1.0.0" in r.stdout

    def test_project_new_json(self, tmp_dir, cli_env):
        out = os.path.join(tmp_dir, "new.toml")
        r = self._run(["--json", "project", "new", "--text", "hello", "-o", out], env=cli_env)
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["ok"] is True
        assert data["project"]["text_length"] == 5
        assert os.path.exists(out)

    def test_full_workflow(self, font_path, tmp_dir, cli_env):
        """create -> param -> override -> render -> verify PNG via subprocess."""
        proj = os.path.join(tmp_dir, "flow.toml")
        outdir = os.path.join(tmp_dir, "rendered")
        self._run(["--json", "project", "new", "--text", "公文写作测试文字",
                   "--font", font_path, "-o", proj], env=cli_env)
        self._run(["--json", "--project", proj, "param", "set", "font_size", "36"], env=cli_env)
        self._run(["--json", "--project", proj, "override", "set", "0", "4",
                   "font_size=50", "fill=red"], env=cli_env)
        r = self._run(["--json", "--project", proj, "render", "run",
                       "--seed", "11", "--output-dir", outdir], env=cli_env)
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert data["ok"] is True
        assert data["page_count"] >= 1
        assert data["verification"]["ok"] is True
        png = data["outputs"][0]
        assert os.path.exists(png)
        with open(png, "rb") as f:
            assert f.read(8) == R.PNG_MAGIC
        print(f"\n  workflow PNG: {png} ({os.path.getsize(png):,} bytes)")

    def test_dry_run_does_not_save(self, font_path, tmp_dir, cli_env):
        proj = os.path.join(tmp_dir, "dr.toml")
        self._run(["--json", "project", "new", "--text", "x", "--font", font_path,
                   "-o", proj], env=cli_env)
        before = open(proj, "r", encoding="utf-8").read()
        self._run(["--dry-run", "--project", proj, "param", "set", "font_size", "44"],
                  env=cli_env)
        after = open(proj, "r", encoding="utf-8").read()
        assert before == after, "--dry-run rewrote the project file"
        # And a non-dry-run DOES persist
        self._run(["--project", proj, "param", "set", "font_size", "44"], env=cli_env)
        persisted = open(proj, "r", encoding="utf-8").read()
        assert "font_size = 44" in persisted

    def test_subprocess_seed_reproducibility(self, font_path, tmp_dir, cli_env):
        proj = os.path.join(tmp_dir, "rep.toml")
        self._run(["--json", "project", "new", "--text", "可复现性测试",
                   "--font", font_path, "-o", proj], env=cli_env)
        d1 = os.path.join(tmp_dir, "r1")
        d2 = os.path.join(tmp_dir, "r2")
        self._run(["--json", "--project", proj, "render", "run", "--seed", "5",
                   "--output-dir", d1], env=cli_env)
        self._run(["--json", "--project", proj, "render", "run", "--seed", "5",
                   "--output-dir", d2], env=cli_env)
        a = open(os.path.join(d1, "0.png"), "rb").read()
        b = open(os.path.join(d2, "0.png"), "rb").read()
        assert a == b
        print(f"\n  reproducible subprocess render: {len(a)} bytes")


# ── workflow: undo/redo round-trip renders identically ─────────────────
class TestUndoRedoWorkflow:
    def test_undo_redo_render_parity(self, font_path, tmp_dir, project_root):
        m = _make_model(font_path, text="abcdefghij")
        # baseline render
        rb = R.render_model(m, os.path.join(tmp_dir, "base"), seed=2, project_root=project_root)
        base_bytes = open(rb["outputs"][0], "rb").read()
        # mutate via a Python session, then undo
        from cli_anything.handwrite.core.session import Session
        s = Session()
        s.set_model(m)
        s.snapshot()
        M.DocumentModelOps.set_range(s.model, 0, 3, {"font_size": 60})
        assert s.undo() is True
        # after undo, model == original -> render matches baseline
        ru = R.render_model(s.model, os.path.join(tmp_dir, "undone"), seed=2, project_root=project_root)
        undone_bytes = open(ru["outputs"][0], "rb").read()
        assert undone_bytes == base_bytes
        print(f"\n  undo restored baseline render ({len(base_bytes)} bytes)")
