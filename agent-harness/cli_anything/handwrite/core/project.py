"""Project (DocumentModel) lifecycle: new / open / save / info.

Project files are TOML — the GUI's native format. Reads/writes go through the
REAL persistence layer (smol-toml + documentFromDict/documentToDict) via the
Node backend, so a CLI-saved .toml opens in the GUI and vice-versa.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from ..utils import handwrite_backend
from .model import create_document_model, document_from_dict, document_to_dict


def new_project(font_path: str = "", text: str = "") -> Dict[str, Any]:
    model = create_document_model(font_path)
    if text:
        model["text"] = text
    return model


def open_project(toml_path: str) -> Dict[str, Any]:
    """Load a .toml project file via the real persistence module."""
    model = handwrite_backend.load_toml(toml_path)
    # Normalize through our port for in-memory consistency.
    return document_from_dict(model)


def save_project(model: Dict[str, Any], toml_path: str) -> str:
    """Write a GUI-interoperable .toml via the real persistence module."""
    return handwrite_backend.serialize_toml(document_to_dict(model), toml_path)


def project_info(model: Dict[str, Any], toml_path: Optional[str] = None) -> Dict[str, Any]:
    gp = model["global_params"]
    return {
        "text_length": len(model["text"]),
        "text_lines": model["text"].count("\n") + (1 if model["text"] else 0),
        "overrides": len(model["overrides"]),
        "override_ranges": [[o["start"], o["end"]] for o in model["overrides"]],
        "font_path": gp.get("font_path", ""),
        "paper": [gp.get("paper_w"), gp.get("paper_h")],
        "font_size": gp.get("font_size"),
        "line_spacing": gp.get("line_spacing"),
        "alignment": gp.get("alignment"),
        "rate": gp.get("rate"),
        "underline": gp.get("underline"),
        "project_file": toml_path,
    }
