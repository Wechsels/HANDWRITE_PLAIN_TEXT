# Vendored from handright (https://github.com/Gsllchb/Handright), BSD-3-Clause.
# Copyright (c) 2017-2023, Chenghui LI (Gsllchb). Adapted for per-glyph
# stroke-level perturbation. See LICENSE-handright.txt for full notice.
#
# 改动点：原库在整页"1"位图上一次性提取笔画并按页级 Template sigma 扰动；
# 此处改为逐字形提取笔画，接受逐字形 sigma 与目标画布偏移，写入 RGBA 画布。
import array
import collections.abc
import math
import random
from typing import Tuple

_UNSIGNED_INT32_TYPECODE = "L"
_MAX_INT16_VALUE = 0xFFFF
_STROKE_END = 0xFFFFFFFF


class NumericOrderedSet(collections.abc.Collection):
    __slots__ = ("_typecode", "_privileged", "_array", "_set")

    def __init__(self, typecode: str, privileged=None) -> None:
        self._typecode = typecode
        self._privileged = privileged
        self._array = array.array(typecode)
        self._set = set()

    def add(self, item) -> bool:
        if item != self._privileged and item in self._set:
            return False
        self._set.add(item)
        self._array.append(item)
        return True

    def add_privileged(self) -> None:
        self._set.add(self._privileged)
        self._array.append(self._privileged)

    def __contains__(self, item) -> bool:
        return item in self._set

    def __iter__(self):
        return iter(self._array)

    def clear(self) -> None:
        self._set.clear()
        self._array = array.array(self._typecode)

    def __len__(self) -> int:
        return len(self._array)


def _gauss(rand: random.Random, mu: float, sigma: float) -> float:
    if sigma == 0:
        return mu
    return rand.gauss(mu, sigma)


def _xy(x: int, y: int) -> int:
    return (x << 16) | y


def _x_y(xy: int) -> Tuple[int, int]:
    return xy >> 16, xy & 0xFFFF


def _extract_strokes(bitmap, bbox: Tuple[int, int, int, int]):
    left, upper, right, lower = bbox
    assert left >= 0 and upper >= 0
    if right >= _MAX_INT16_VALUE or lower >= _MAX_INT16_VALUE:
        raise ValueError("glyph bitmap too large for stroke extraction")
    strokes = NumericOrderedSet(_UNSIGNED_INT32_TYPECODE, privileged=_STROKE_END)
    for y in range(upper, lower):
        for x in range(left, right):
            if bitmap[x, y] and strokes.add(_xy(x, y)):
                _extract_stroke(bitmap, (x, y), strokes, bbox)
                strokes.add_privileged()
    return strokes


def _extract_stroke(bitmap, start, strokes, bbox) -> None:
    left, upper, right, lower = bbox
    stack = [start]
    while stack:
        x, y = stack.pop()
        if y - 1 >= upper and bitmap[x, y - 1] and strokes.add(_xy(x, y - 1)):
            stack.append((x, y - 1))
        if y + 1 < lower and bitmap[x, y + 1] and strokes.add(_xy(x, y + 1)):
            stack.append((x, y + 1))
        if x - 1 >= left and bitmap[x - 1, y] and strokes.add(_xy(x - 1, y)):
            stack.append((x - 1, y))
        if x + 1 < right and bitmap[x + 1, y] and strokes.add(_xy(x + 1, y)):
            stack.append((x + 1, y))


def _rotate(center, x, y, theta):
    if theta == 0:
        return x, y
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    dx = x - center[0]
    dy = y - center[1]
    return (dx * cos_t + dy * sin_t + center[0],
            dy * cos_t - dx * sin_t + center[1])


def _draw_strokes(canvas_load, strokes, offset, sigmas, fill, canvas_size, rand) -> None:
    sx, sy, st = sigmas
    cw, ch = canvas_size
    ox, oy = offset
    stroke = []
    min_x = _MAX_INT16_VALUE
    min_y = _MAX_INT16_VALUE
    max_x = 0
    max_y = 0
    for xy in strokes:
        if xy == _STROKE_END:
            if stroke:
                center = ((min_x + max_x) / 2, (min_y + max_y) / 2)
                dx = _gauss(rand, 0, sx)
                dy = _gauss(rand, 0, sy)
                theta = _gauss(rand, 0, st)
                for lx, ly in stroke:
                    nx, ny = _rotate(center, lx, ly, theta)
                    tx = round(nx + ox + dx)
                    ty = round(ny + oy + dy)
                    if 0 <= tx < cw and 0 <= ty < ch:
                        canvas_load[tx, ty] = fill
            min_x = _MAX_INT16_VALUE
            min_y = _MAX_INT16_VALUE
            max_x = 0
            max_y = 0
            stroke.clear()
            continue
        x, y = _x_y(xy)
        min_x = min(x, min_x)
        max_x = max(x, max_x)
        min_y = min(y, min_y)
        max_y = max(y, max_y)
        stroke.append((x, y))


def perturb_glyph(scratch_img, ink_bbox, canvas, offset, sigma_x, sigma_y,
                  sigma_theta, fill, rand) -> None:
    """Extract strokes from `scratch_img` ("1" mode) over `ink_bbox` and write
    perturbed `fill` pixels into `canvas` (RGBA) at `offset`."""
    strokes = _extract_strokes(scratch_img.load(), ink_bbox)
    _draw_strokes(
        canvas.load(), strokes, offset,
        (sigma_x, sigma_y, sigma_theta), fill, canvas.size, rand,
    )
