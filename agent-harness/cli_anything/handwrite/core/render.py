"""Render pipeline: hands the model to the REAL Node backend, verifies output.

Never reimplements rendering — every PNG is produced by the actual
layout/perturb/fontCache/renderer pipeline. This module also provides
programmatic output verification (PNG magic bytes, page count, dimensions,
seed reproducibility) so "it ran without errors" is never the only signal.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils import handwrite_backend
from .model import document_to_dict
from .params import validate_params

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def render_model(model: Dict[str, Any], outdir: str, seed: Optional[int] = None,
                 project_root: Optional[Path] = None) -> Dict[str, Any]:
    """Render via the real backend. Validates params first (mirrors renderer.ts)."""
    validate_params(model["global_params"])
    os.makedirs(outdir, exist_ok=True)
    return handwrite_backend.render(document_to_dict(model), outdir, seed=seed,
                                    project_root=project_root)


def verify_png(path: str) -> Dict[str, Any]:
    """Programmatic verification of a rendered PNG (HARNESS: don't trust exit codes)."""
    p = Path(path)
    if not p.exists():
        return {"ok": False, "path": path, "error": "file does not exist"}
    size = p.stat().st_size
    with open(p, "rb") as f:
        head = f.read(24)  # magic(8) + IHDR length(4) + type(4) + width(4) + height(4)
    if head[:8] != PNG_MAGIC:
        return {"ok": False, "path": path, "bytes": size, "error": "not a PNG (bad magic bytes)"}
    # Minimal IHDR parse for width/height.
    chunk_type = head[12:16]
    length = int.from_bytes(head[8:12], "big")
    if chunk_type == b"IHDR" and length >= 8 and len(head) >= 24:
        width = int.from_bytes(head[16:20], "big")
        height = int.from_bytes(head[20:24], "big")
    else:
        width = height = None
    return {"ok": True, "path": str(p), "bytes": size, "width": width, "height": height}


def verify_render_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Verify every page PNG produced by render_model."""
    pages = result.get("pages", [])
    checks = []
    for pg in pages:
        v = verify_png(pg["path"])
        v["index"] = pg.get("index")
        v["expected_size"] = (pg.get("width"), pg.get("height"))
        v["size_matches"] = (
            v["width"] == pg.get("width") and v["height"] == pg.get("height")
            if v.get("width") else None
        )
        checks.append(v)
    all_ok = all(c["ok"] for c in checks) and len(checks) > 0
    return {"ok": all_ok, "page_count": len(checks), "pages": checks,
            "outputs": result.get("outputs", []), "seed": result.get("seed")}


def open_output_dir(outdir: str) -> Dict[str, Any]:
    """Cross-platform 'open the output folder' (mirrors the GUI button)."""
    outdir = os.path.abspath(outdir)
    if not os.path.isdir(outdir):
        return {"ok": False, "error": f"not a directory: {outdir}"}
    try:
        if sys.platform == "win32":
            os.startfile(outdir)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", outdir], check=False)
        else:
            subprocess.run(["xdg-open", outdir], check=False)
        return {"ok": True, "opened": outdir}
    except Exception as e:
        return {"ok": False, "error": str(e), "path": outdir}
