"""Document model + range-override ops (mirrors src/shared/settings.ts exactly).

This is the DATA LAYER — project-file manipulation, permitted by HARNESS
("manipulate the native format directly as the data layer"). Rendering is never
reimplemented here; every pixel comes from the real Node pipeline.

The logic below is a line-by-line port of ``DocumentModelOps`` /
``defaultGlobalParams`` in ``src/shared/settings.ts`` so the CLI's range
semantics match the GUI. Tests assert parity.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

RGBA = Tuple[int, int, int, int]

ADJUSTABLE_KEYS: Tuple[str, ...] = (
    "font_size",
    "word_spacing",
    "perturb_x_sigma",
    "perturb_y_sigma",
    "perturb_theta_sigma",
    "fill",
    "alignment",
    "underline",
)

DEFAULT_FILL: RGBA = (0, 0, 0, 255)
DEFAULT_BACKGROUND: RGBA = (255, 255, 255, 255)

ALIGNMENT_OPTIONS: Tuple[str, ...] = ("left", "center")

# Allowed global-param keys (mirrors GlobalParams interface).
GLOBAL_PARAM_KEYS: Tuple[str, ...] = (
    "paper_w", "paper_h", "font_path", "font_size", "line_spacing",
    "word_spacing", "margin_top", "margin_bottom", "margin_left",
    "margin_right", "fill", "background", "rate", "line_spacing_sigma",
    "font_size_sigma", "word_spacing_sigma", "perturb_x_sigma",
    "perturb_y_sigma", "perturb_theta_sigma", "alignment", "underline",
)


def default_global_params(font_path: str = "") -> Dict[str, Any]:
    return {
        "paper_w": 667,
        "paper_h": 945,
        "font_path": font_path,
        "font_size": 30,
        "line_spacing": 70,
        "word_spacing": 1,
        "margin_top": 10,
        "margin_bottom": 10,
        "margin_left": 10,
        "margin_right": 10,
        "fill": list(DEFAULT_FILL),
        "background": list(DEFAULT_BACKGROUND),
        "rate": 4,
        "line_spacing_sigma": 1.0,
        "font_size_sigma": 1.0,
        "word_spacing_sigma": 1.0,
        "perturb_x_sigma": 1.0,
        "perturb_y_sigma": 1.0,
        "perturb_theta_sigma": 0.05,
        "alignment": "left",
        "underline": False,
    }


def create_document_model(font_path: str = "") -> Dict[str, Any]:
    return {
        "text": "",
        "global_params": default_global_params(font_path),
        "overrides": [],
    }


def global_params_from_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    out = default_global_params()
    for k in GLOBAL_PARAM_KEYS:
        if k in d and d[k] is not None:
            out[k] = d[k]
    return out


def document_from_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    gp = global_params_from_dict(d.get("global_params") or {})
    overrides = []
    for o in d.get("overrides") or []:
        overrides.append({
            "start": int(o["start"]),
            "end": int(o["end"]),
            "params": dict(o.get("params") or {}),
        })
    return {
        "text": d.get("text") or "",
        "global_params": gp,
        "overrides": overrides,
    }


def document_to_dict(model: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "text": model["text"],
        "global_params": dict(model["global_params"]),
        "overrides": [
            {"start": o["start"], "end": o["end"], "params": dict(o["params"])}
            for o in model["overrides"]
        ],
    }


def _clean_params(params: Dict[str, Any]) -> Dict[str, Any]:
    cleaned: Dict[str, Any] = {}
    for k in ADJUSTABLE_KEYS:
        v = params.get(k)
        if v is not None:
            cleaned[k] = v
    return cleaned


def _clamp_range(n: int, start: int, end: int) -> Tuple[int, int]:
    start = max(0, min(start, n))
    end = max(start, min(end, n))
    return start, end


def _params_equal(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    if a.keys() != b.keys():  # order-insensitive, length-aware
        return False
    for k in a:
        if a[k] != b[k]:
            return False
    return True


class DocumentModelOps:
    """In-place ops on a DocumentModel dict. Mirrors settings.ts DocumentModelOps."""

    @staticmethod
    def set_range(model: Dict[str, Any], start: int, end: int,
                  new_params: Dict[str, Any]) -> None:
        n = len(model["text"])
        start, end = _clamp_range(n, start, end)
        cleaned = _clean_params(new_params)
        if start >= end or not cleaned:
            return

        DocumentModelOps.split_at(model, start)
        DocumentModelOps.split_at(model, end)

        inside = [s for s in model["overrides"] if s["start"] >= start and s["end"] <= end]
        for seg in inside:
            seg["params"].update(cleaned)

        covered = sorted(inside, key=lambda s: s["start"])
        gaps: List[Dict[str, Any]] = []
        cursor = start
        for seg in covered:
            if seg["start"] > cursor:
                gaps.append({"start": cursor, "end": seg["start"], "params": dict(cleaned)})
            cursor = seg["end"]
        if cursor < end:
            gaps.append({"start": cursor, "end": end, "params": dict(cleaned)})

        model["overrides"].extend(gaps)
        model["overrides"].sort(key=lambda s: s["start"])
        DocumentModelOps.merge_adjacent(model)

    @staticmethod
    def clear_range(model: Dict[str, Any], start: int, end: int) -> None:
        n = len(model["text"])
        start, end = _clamp_range(n, start, end)
        if start >= end:
            return
        DocumentModelOps.split_at(model, start)
        DocumentModelOps.split_at(model, end)
        model["overrides"] = [
            s for s in model["overrides"]
            if not (s["start"] >= start and s["end"] <= end)
        ]

    @staticmethod
    def split_at(model: Dict[str, Any], point: int) -> None:
        if point <= 0 or point >= len(model["text"]):
            return
        new_list: List[Dict[str, Any]] = []
        for seg in model["overrides"]:
            if seg["start"] < point < seg["end"]:
                new_list.append({"start": seg["start"], "end": point, "params": dict(seg["params"])})
                new_list.append({"start": point, "end": seg["end"], "params": dict(seg["params"])})
            else:
                new_list.append(seg)
        model["overrides"] = new_list

    @staticmethod
    def merge_adjacent(model: Dict[str, Any]) -> None:
        if not model["overrides"]:
            return
        merged: List[Dict[str, Any]] = [dict(model["overrides"][0], params=dict(model["overrides"][0]["params"]))]
        for seg in model["overrides"][1:]:
            last = merged[-1]
            if last["end"] == seg["start"] and _params_equal(last["params"], seg["params"]):
                last["end"] = seg["end"]
            else:
                merged.append(dict(seg, params=dict(seg["params"])))
        model["overrides"] = merged

    @staticmethod
    def override_at(model: Dict[str, Any], index: int) -> Optional[Dict[str, Any]]:
        for seg in model["overrides"]:
            if seg["start"] <= index < seg["end"]:
                return seg
        return None

    @staticmethod
    def effective_params(model: Dict[str, Any], index: int) -> Dict[str, Any]:
        base = dict(model["global_params"])
        seg = DocumentModelOps.override_at(model, index)
        if seg:
            base.update(seg["params"])
        return base

    @staticmethod
    def ranges_for_marking(model: Dict[str, Any]) -> List[Tuple[int, int]]:
        return [(s["start"], s["end"]) for s in model["overrides"]]

    @staticmethod
    def trim_to_text(model: Dict[str, Any]) -> None:
        n = len(model["text"])
        kept = [o for o in model["overrides"] if o["start"] < n and o["end"] <= n]
        for o in kept:
            o["start"] = max(0, o["start"])
            o["end"] = min(o["end"], n)
        model["overrides"] = kept
