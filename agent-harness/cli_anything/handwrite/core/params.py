"""Global render-parameter helpers: defaults, validation, presets, color parsing.

Mirrors src/shared/palette.ts (FONT_COLOR_DICT, BACKGROUND_COLOR_DICT, RATE_DICT,
ALIGNMENT_OPTIONS) and src/shared/settings.ts (GlobalParams). Pure data — no
rendering.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from .model import (
    ALIGNMENT_OPTIONS,
    DEFAULT_BACKGROUND,
    DEFAULT_FILL,
    GLOBAL_PARAM_KEYS,
    default_global_params,
)

# Named color palettes (mirror palette.ts).
FONT_COLOR_DICT: Dict[str, Tuple[int, int, int, int]] = {
    "black": (0, 0, 0, 255),
    "white": (255, 255, 255, 255),
    "red": (255, 0, 0, 255),
    "blue": (0, 0, 255, 255),
}

BACKGROUND_COLOR_DICT: Dict[str, Tuple[int, int, int, int]] = {
    "transparent": (0, 0, 0, 0),
    "white": (255, 255, 255, 255),
}

RATE_DICT: Dict[str, int] = {
    "x1": 1, "x2": 2, "x4": 4, "x8": 8, "x16": 16, "x32": 32, "x64": 64,
}

# Paper presets (margin + size). Convenient for agents.
PAPER_PRESETS: Dict[str, Dict[str, int]] = {
    "default": {"paper_w": 667, "paper_h": 945, "margin_top": 10, "margin_bottom": 10,
                "margin_left": 10, "margin_right": 10},
    "a4": {"paper_w": 595, "paper_h": 842, "margin_top": 56, "margin_bottom": 56,
           "margin_left": 56, "margin_right": 56},
    "b5": {"paper_w": 499, "paper_h": 709, "margin_top": 40, "margin_bottom": 40,
           "margin_left": 40, "margin_right": 40},
    "letter": {"paper_w": 612, "paper_h": 792, "margin_top": 50, "margin_bottom": 50,
               "margin_left": 50, "margin_right": 50},
}

# Human-friendly aliases for param keys.
PARAM_ALIASES: Dict[str, str] = {
    "fontsize": "font_size",
    "linespacing": "line_spacing",
    "wordspacing": "word_spacing",
    "margintop": "margin_top",
    "marginbottom": "margin_bottom",
    "marginleft": "margin_left",
    "marginright": "margin_right",
    "perturbx": "perturb_x_sigma",
    "perturby": "perturb_y_sigma",
    "perturbtheta": "perturb_theta_sigma",
    "linespacingsigma": "line_spacing_sigma",
    "fontsizesigma": "font_size_sigma",
    "wordspacingsigma": "word_spacing_sigma",
}


def parse_color(value: Any) -> Tuple[int, int, int, int]:
    """Accept a named color, '#rrggbb'/'#rrggbbaa' hex, or [r,g,b(,a)] list."""
    if isinstance(value, (list, tuple)):
        nums = [int(x) for x in value]
        if len(nums) == 3:
            return (nums[0], nums[1], nums[2], 255)
        if len(nums) == 4:
            return (nums[0], nums[1], nums[2], nums[3])
        raise ValueError(f"color list must have 3 or 4 components: {value}")
    if isinstance(value, str):
        v = value.strip().lower()
        if v in FONT_COLOR_DICT:
            return FONT_COLOR_DICT[v]
        if v.startswith("#"):
            hexpart = v[1:]
            if len(hexpart) == 6:
                r, g, b = int(hexpart[0:2], 16), int(hexpart[2:4], 16), int(hexpart[4:6], 16)
                return (r, g, b, 255)
            if len(hexpart) == 8:
                r, g, b, a = (int(hexpart[i:i + 2], 16) for i in range(0, 8, 2))
                return (r, g, b, a)
            raise ValueError(f"hex color must be #rrggbb or #rrggbbaa: {value}")
        # comma-separated "r,g,b[,a]"
        if "," in v:
            return parse_color([x.strip() for x in v.split(",")])
    raise ValueError(f"cannot parse color: {value!r}")


def parse_background(value: Any) -> Tuple[int, int, int, int]:
    if isinstance(value, str):
        v = value.strip().lower()
        if v in BACKGROUND_COLOR_DICT:
            return BACKGROUND_COLOR_DICT[v]
    return parse_color(value)


def coerce_value(key: str, value: Any) -> Any:
    """Coerce a CLI string/value into the correct Python type for a global param."""
    if key in ("fill", "background"):
        return list(parse_color(value)) if key == "fill" else list(parse_background(value))
    if key in ("alignment", "font_path"):
        return str(value)
    if key == "underline":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ("1", "true", "yes", "on")
    if key == "rate":
        # accept 'x4' alias or int
        if isinstance(value, str) and value.strip().lower() in RATE_DICT:
            return RATE_DICT[value.strip().lower()]
        return int(value)
    # numeric params
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    s = str(value).strip()
    # int-valued params vs float-valued
    int_keys = {"paper_w", "paper_h", "font_size", "line_spacing", "word_spacing",
                "margin_top", "margin_bottom", "margin_left", "margin_right"}
    if key in int_keys:
        return int(float(s))
    return float(s)


def validate_params(gp: Dict[str, Any]) -> None:
    """Mirror renderer.ts renderPages preconditions. Raises ValueError on bad input."""
    if gp.get("font_size", 0) > gp.get("line_spacing", 0):
        raise ValueError("font_size must be <= line_spacing")
    if gp.get("paper_w", 0) <= 0 or gp.get("paper_h", 0) <= 0:
        raise ValueError("paper_w and paper_h must be positive")
    if gp.get("alignment", "left") not in ALIGNMENT_OPTIONS:
        raise ValueError(f"alignment must be one of {ALIGNMENT_OPTIONS}")
    if int(gp.get("rate", 4)) not in RATE_DICT.values():
        raise ValueError(f"rate must be one of {sorted(RATE_DICT.values())}")
    if gp.get("font_size", 0) <= 0:
        raise ValueError("font_size must be positive")


def normalize_key(key: str) -> str:
    k = key.strip().lower().replace("-", "_")
    return PARAM_ALIASES.get(k, k)


def is_global_key(key: str) -> bool:
    return normalize_key(key) in GLOBAL_PARAM_KEYS


def apply_preset(gp: Dict[str, Any], preset_name: str) -> Dict[str, Any]:
    name = preset_name.strip().lower()
    if name not in PAPER_PRESETS:
        raise ValueError(f"unknown paper preset '{preset_name}'. options: {sorted(PAPER_PRESETS)}")
    out = dict(gp)
    out.update(PAPER_PRESETS[name])
    return out
