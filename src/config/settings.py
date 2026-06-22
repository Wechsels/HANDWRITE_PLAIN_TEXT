from __future__ import annotations

from dataclasses import dataclass, field, asdict

from fonts.font_catalog import default_font_path

ADJUSTABLE_KEYS = (
    "font_size",
    "word_spacing",
    "perturb_x_sigma",
    "perturb_y_sigma",
    "perturb_theta_sigma",
    "fill",
    "alignment",
    "underline",
)

DEFAULT_FILL = (0, 0, 0, 255)
DEFAULT_BACKGROUND = (255, 255, 255, 255)


@dataclass
class GlobalParams:
    paper_w: int = 667
    paper_h: int = 945
    font_path: str = ""
    font_size: int = 30
    line_spacing: int = 70
    word_spacing: int = 1
    margin_top: int = 10
    margin_bottom: int = 10
    margin_left: int = 10
    margin_right: int = 10
    fill: tuple = DEFAULT_FILL
    background: tuple = DEFAULT_BACKGROUND
    rate: int = 4
    line_spacing_sigma: float = 1.0
    font_size_sigma: float = 1.0
    word_spacing_sigma: float = 1.0
    perturb_x_sigma: float = 1.0
    perturb_y_sigma: float = 1.0
    perturb_theta_sigma: float = 0.05
    alignment: str = "left"
    underline: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "GlobalParams":
        valid = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**valid)


def default_global_params() -> GlobalParams:
    return GlobalParams(font_path=default_font_path())


@dataclass
class RangeOverride:
    start: int
    end: int
    params: dict

    def to_dict(self) -> dict:
        return {"start": self.start, "end": self.end, "params": dict(self.params)}

    @classmethod
    def from_dict(cls, d: dict) -> "RangeOverride":
        return cls(start=int(d["start"]), end=int(d["end"]), params=dict(d.get("params", {})))


@dataclass
class DocumentModel:
    text: str = ""
    global_params: GlobalParams = field(default_factory=default_global_params)
    overrides: list[RangeOverride] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "global_params": self.global_params.to_dict(),
            "overrides": [o.to_dict() for o in self.overrides],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DocumentModel":
        gp = GlobalParams.from_dict(d.get("global_params", {}))
        overrides = [RangeOverride.from_dict(o) for o in d.get("overrides", [])]
        return cls(text=d.get("text", ""), global_params=gp, overrides=overrides)

    def _clamp_range(self, start: int, end: int) -> tuple[int, int]:
        n = len(self.text)
        start = max(0, min(start, n))
        end = max(start, min(end, n))
        return start, end

    def _split_at(self, point: int) -> None:
        """Split any segment straddling `point` into two."""
        if point <= 0 or point >= len(self.text):
            return
        new_list = []
        for seg in self.overrides:
            if seg.start < point < seg.end:
                new_list.append(RangeOverride(seg.start, point, dict(seg.params)))
                new_list.append(RangeOverride(point, seg.end, dict(seg.params)))
            else:
                new_list.append(seg)
        self.overrides = new_list

    def set_range(self, start: int, end: int, new_params: dict) -> None:
        """Merge new_params into [start, end). Splits/trims existing segments;
        gap areas inside [start, end) get a fresh override."""
        start, end = self._clamp_range(start, end)
        new_params = {k: v for k, v in new_params.items() if k in ADJUSTABLE_KEYS and v is not None}
        if start >= end or not new_params:
            return

        self._split_at(start)
        self._split_at(end)

        inside = [s for s in self.overrides if s.start >= start and s.end <= end]
        for seg in inside:
            seg.params.update(new_params)

        covered = sorted([s for s in inside], key=lambda s: s.start)
        gaps = []
        cursor = start
        for seg in covered:
            if seg.start > cursor:
                gaps.append(RangeOverride(cursor, seg.start, dict(new_params)))
            cursor = seg.end
        if cursor < end:
            gaps.append(RangeOverride(cursor, end, dict(new_params)))

        self.overrides.extend(gaps)
        self.overrides.sort(key=lambda s: s.start)
        self._merge_adjacent()

    def _merge_adjacent(self) -> None:
        """Merge touching segments with identical params."""
        if not self.overrides:
            return
        merged = [self.overrides[0]]
        for seg in self.overrides[1:]:
            last = merged[-1]
            if last.end == seg.start and last.params == seg.params:
                last.end = seg.end
            else:
                merged.append(seg)
        self.overrides = merged

    def clear_range(self, start: int, end: int) -> None:
        """Remove all overrides inside [start, end), keeping outside parts."""
        start, end = self._clamp_range(start, end)
        if start >= end:
            return
        self._split_at(start)
        self._split_at(end)
        self.overrides = [
            s for s in self.overrides if not (s.start >= start and s.end <= end)
        ]

    def override_at(self, index: int) -> RangeOverride | None:
        for seg in self.overrides:
            if seg.start <= index < seg.end:
                return seg
        return None

    def effective_params(self, index: int) -> dict:
        """Global params overlaid with the override covering `index`."""
        base = self.global_params.to_dict()
        seg = self.override_at(index)
        if seg:
            base.update(seg.params)
        return base

    def ranges_for_marking(self) -> list[tuple[int, int]]:
        return [(s.start, s.end) for s in self.overrides]
