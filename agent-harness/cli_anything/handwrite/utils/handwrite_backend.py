"""Backend wrapper: invokes the REAL Node.js render pipeline.

Per HARNESS rule #1, the CLI must call the actual software for rendering — not
reimplement it. Here the "actual software" is the project's own render engine
(layout → perturb → fontCache → renderer) and persistence layer (smol-toml),
bundled headlessly into ``scripts/render_backend.mjs`` (built by
``vite.config.cli.ts`` from ``agent-harness/cli_src/cli_render_entry.ts``).

This module finds ``node``, the bundled entry, and the project root (where
``node_modules/`` + ``ttf_library/`` live), then drives the bundle via
subprocess. The project checkout with ``npm install`` is a HARD dependency.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Subcommand names mirror cli_render_entry.ts.
RENDER = "render"
SERIALIZE_TOML = "serialize-toml"
LOAD_TOML = "load-toml"
LIST_FONTS = "list-fonts"
PROBE = "probe"


class BackendError(RuntimeError):
    """Raised when the Node backend is missing, misconfigured, or reports failure."""


def find_node() -> str:
    node = shutil.which("node") or shutil.which("node.exe")
    if node:
        return node
    raise BackendError(
        "Node.js is not installed or not on PATH. Install Node.js >= 20:\n"
        "  https://nodejs.org/  (or: winget install OpenJS.NodeJS / brew install node)\n"
        "The render backend requires Node to run the real @napi-rs/canvas pipeline."
    )


def bundle_path() -> Path:
    """Absolute path to the bundled render_backend.mjs (shipped in the package)."""
    return Path(__file__).resolve().parent.parent / "scripts" / "render_backend.mjs"


def find_project_root(start: Optional[str] = None) -> Path:
    """Locate the HandWrite project root (has node_modules/@napi-rs/canvas + ttf_library).

    Resolution order: $HANDWRITE_PROJECT_ROOT, then walk up from `start`/cwd.
    """
    env = os.environ.get("HANDWRITE_PROJECT_ROOT")
    if env and Path(env).is_dir():
        return Path(env).resolve()

    def looks_like_root(p: Path) -> bool:
        return (p / "ttf_library").is_dir() or (
            (p / "node_modules" / "@napi-rs" / "canvas").is_dir()
        )

    p = Path(start or os.getcwd()).resolve()
    for _ in range(15):
        if looks_like_root(p):
            return p
        parent = p.parent
        if parent == p:
            break
        p = parent
    # Fallback: cwd (backend will surface a clear error if fonts/canvas missing).
    return Path(start or os.getcwd()).resolve()


def _run(subcmd: str, args: List[str], project_root: Optional[Path] = None,
         capture: bool = True) -> Dict[str, Any]:
    """Invoke the bundle and parse its JSON stdout. Raises BackendError on failure."""
    node = find_node()
    bundle = bundle_path()
    if not bundle.exists():
        raise BackendError(
            f"Render backend bundle not found: {bundle}\n"
            "Rebuild with:  npx vite build --config vite.config.cli.ts"
        )
    root = (project_root or find_project_root()).resolve()
    node_path = str(root / "node_modules")
    env = dict(os.environ)
    # Let the bundle resolve @napi-rs/canvas + smol-toml from the project's node_modules
    # regardless of where the bundle file itself lives (e.g. site-packages).
    env["NODE_PATH"] = node_path + (os.pathsep + env["NODE_PATH"]) if env.get("NODE_PATH") else node_path

    cmd = [node, str(bundle), subcmd, *args]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            env=env,
            capture_output=capture,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except FileNotFoundError as e:
        raise BackendError(f"Failed to launch node: {e}") from e

    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "")[-2000:]
        raise BackendError(
            f"Node backend '{subcmd}' exited {proc.returncode}.\n{tail}"
        )

    out = proc.stdout.strip()
    if not out:
        raise BackendError(f"Node backend '{subcmd}' produced no output.\n{proc.stderr}")
    try:
        data = json.loads(out)
    except json.JSONDecodeError as e:
        raise BackendError(
            f"Node backend '{subcmd}' returned non-JSON: {e}\n--- stdout ---\n{out[:1000]}"
        ) from e
    if not data.get("ok", False):
        raise BackendError(data.get("error", f"backend '{subcmd}' failed"))
    return data


# ── high-level operations ──────────────────────────────────────────────

def probe() -> Dict[str, Any]:
    return _run(PROBE, [])


def list_fonts(project_root: Optional[Path] = None) -> List[Dict[str, str]]:
    data = _run(LIST_FONTS, ["-"], project_root=project_root)
    return data.get("fonts", [])


def load_toml(toml_path: str, project_root: Optional[Path] = None) -> Dict[str, Any]:
    data = _run(LOAD_TOML, [str(toml_path), "-"], project_root=project_root)
    return data["model"]


def serialize_toml(model: Dict[str, Any], toml_path: str,
                   project_root: Optional[Path] = None) -> str:
    """Write a GUI-interoperable .toml via the REAL persistence module (smol-toml)."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(model, f)
        model_json = f.name
    try:
        data = _run(SERIALIZE_TOML, [model_json, str(toml_path)], project_root=project_root)
        return data["path"]
    finally:
        try:
            os.unlink(model_json)
        except OSError:
            pass


def render(model: Dict[str, Any], outdir: str, seed: Optional[int] = None,
           project_root: Optional[Path] = None) -> Dict[str, Any]:
    """Render the model to PNGs via the REAL pipeline. Returns dict with pages/paths."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(model, f)
        model_json = f.name
    try:
        args = [model_json, str(outdir)]
        if seed is not None:
            args.append(str(seed))
        data = _run(RENDER, args, project_root=project_root)
        return {
            "seed": data.get("seed"),
            "pages": data.get("pages", []),
            "page_count": data.get("page_count", 0),
            "outputs": [p["path"] for p in data.get("pages", [])],
            "model": data.get("model", model),
        }
    finally:
        try:
            os.unlink(model_json)
        except OSError:
            pass


def resolve_cli_base() -> Tuple[str, ...]:
    """Return the argv prefix to run the backend directly (for diagnostics)."""
    return (find_node(), str(bundle_path()))
