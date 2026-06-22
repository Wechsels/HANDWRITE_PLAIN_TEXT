from __future__ import annotations

import random

from PIL import Image, ImageDraw

from config.paths import OUTPUTS_DIR
from config.settings import DocumentModel
from premium.interfaces import registry
from render.font_cache import get_font
from render.layout import layout_document
from render.perturb import perturb_glyph


class RenderError(Exception):
    pass


def render_pages(model: DocumentModel, seed=None, save: bool = True) -> list[Image.Image]:
    gp = model.global_params
    if gp.font_size > gp.line_spacing:
        raise RenderError("font_size 必须 <= line_spacing")
    if gp.paper_w <= 0 or gp.paper_h <= 0:
        raise RenderError("纸张宽高必须为正")

    rand = random.Random(seed)
    pages, (cw, ch) = layout_document(model, rand)
    bg = tuple(gp.background)
    result: list[Image.Image] = []

    for page_jobs in pages:
        canvas = Image.new("RGBA", (cw, ch), bg)
        draw = ImageDraw.Draw(canvas)
        for job in page_jobs:
            _render_glyph(canvas, draw, job, gp.font_path, rand)
        result.append(registry.enhance_image(canvas, {"font_path": gp.font_path}))

    if save:
        _save_outputs(result)
    return result


def _render_glyph(canvas, draw, job, font_path, rand) -> None:
    font = get_font(font_path, job.font_size)
    l, t, r, b = font.getbbox(job.char)
    pad = max(job.font_size, 1)
    scratch = Image.new("1", (3 * pad, 3 * pad), 0)
    ImageDraw.Draw(scratch).text((pad, pad), job.char, fill=1, font=font)
    ink_bbox = (max(pad + l, 0), max(pad + t, 0), pad + r, pad + b)
    offset = (job.x - pad, job.y - pad)
    perturb_glyph(
        scratch, ink_bbox, canvas, offset,
        job.perturb_x_sigma, job.perturb_y_sigma, job.perturb_theta_sigma,
        tuple(job.fill), rand,
    )
    if job.underline:
        uy = int(job.y + job.font_size)
        thickness = max(1, max(job.font_size, 1) // 10)
        draw.rectangle([job.x, uy, job.x + (r - l), uy + thickness], fill=tuple(job.fill))


def _save_outputs(images: list[Image.Image]) -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    for f in OUTPUTS_DIR.iterdir():
        if f.suffix == ".png":
            try:
                f.unlink()
            except OSError:
                pass
    for i, im in enumerate(images):
        im.save(OUTPUTS_DIR / f"{i}.png")
