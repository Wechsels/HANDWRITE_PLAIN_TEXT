from __future__ import annotations

import random
from dataclasses import dataclass

from config.settings import DocumentModel
from render.font_cache import get_font

# 提前换行：这些字符不宜出现在行尾
START_CHARS = "“（[<"
# 禁止行首：这些字符不宜出现在行首
END_CHARS = "，。》？；：’”】｝、！％）,.>?;:]}!%)′″℃℉"


@dataclass
class GlyphJob:
    char: str
    page: int
    x: float
    y: float
    font_size: int
    perturb_x_sigma: float
    perturb_y_sigma: float
    perturb_theta_sigma: float
    fill: tuple
    underline: bool


def _gauss(rand: random.Random, mu: float, sigma: float) -> float:
    if sigma == 0:
        return mu
    return rand.gauss(mu, sigma)


def _line_alignment(model: DocumentModel, line_buffer) -> str:
    if line_buffer:
        return model.effective_params(line_buffer[0][0])["alignment"]
    return model.global_params.alignment


def layout_document(model: DocumentModel, rand: random.Random):
    """Return (pages, page_size). pages: list[list[GlyphJob]]. page_size: (w,h) scaled px."""
    gp = model.global_params
    rate = gp.rate
    pw = gp.paper_w * rate
    ph = gp.paper_h * rate
    lm = gp.margin_left * rate
    rm = gp.margin_right * rate
    tm = gp.margin_top * rate
    bm = gp.margin_bottom * rate
    line_spacing = gp.line_spacing * rate
    lss = gp.line_spacing_sigma * rate
    fss = gp.font_size_sigma * rate
    wss = gp.word_spacing_sigma * rate
    base_font_size_px = gp.font_size * rate

    text = model.text.replace("\r\n", "\n").replace("\r", "\n")
    n = len(text)

    pages: list[list[GlyphJob]] = []
    current_jobs: list[GlyphJob] = []
    line_buffer: list = []
    page_index = 0

    def flush_line(alignment: str) -> None:
        if not line_buffer:
            return
        first_x = line_buffer[0][4]
        last = line_buffer[-1]
        line_width = (last[4] + last[6]) - first_x
        avail = pw - lm - rm
        offset_x = max(0.0, (avail - line_width) / 2) if alignment == "center" else 0.0
        for ci, ch, _font, fs, xp, yp, _adv, fill, ul, sigmas in line_buffer:
            current_jobs.append(GlyphJob(
                char=ch, page=page_index, x=xp + offset_x, y=yp, font_size=fs,
                perturb_x_sigma=sigmas[0], perturb_y_sigma=sigmas[1],
                perturb_theta_sigma=sigmas[2], fill=fill, underline=ul,
            ))
        line_buffer.clear()

    def next_line() -> None:
        nonlocal y, x
        flush_line(_line_alignment(model, line_buffer))
        y += line_spacing
        x = lm

    def new_page() -> None:
        nonlocal current_jobs, page_index, y
        flush_line(_line_alignment(model, line_buffer))
        if current_jobs:
            pages.append(current_jobs)
        current_jobs = []
        page_index = len(pages)
        y = tm + line_spacing - base_font_size_px

    x = lm
    y = tm + line_spacing - base_font_size_px
    i = 0
    while i < n:
        ch = text[i]
        if ch == "\n":
            next_line()
            if y > ph - bm - base_font_size_px:
                new_page()
            i += 1
            continue

        eff = model.effective_params(i)
        fs_nominal = eff["font_size"] * rate
        fs_actual = max(round(_gauss(rand, fs_nominal, fss)), 1)
        font = get_font(gp.font_path, fs_actual)
        l, _t, r, _b = font.getbbox(ch)
        advance = r - l

        need_wrap = (
            (x > pw - rm - 2 * fs_actual and ch in START_CHARS)
            or (x > pw - rm - fs_actual and ch not in END_CHARS)
        )
        if need_wrap:
            next_line()
            if y > ph - bm - base_font_size_px:
                new_page()
            continue  # reprocess ch on the new line

        y_jit = _gauss(rand, y, lss)
        sigmas = (eff["perturb_x_sigma"], eff["perturb_y_sigma"], eff["perturb_theta_sigma"])
        line_buffer.append((i, ch, font, fs_actual, x, y_jit, advance,
                            eff["fill"], eff["underline"], sigmas))
        x += _gauss(rand, eff["word_spacing"] * rate + advance, wss)
        i += 1

    flush_line(_line_alignment(model, line_buffer))
    if current_jobs:
        pages.append(current_jobs)
    if not pages:
        pages = [[]]
    return pages, (pw, ph)
