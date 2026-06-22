import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config.settings import DocumentModel, GlobalParams  # noqa: E402
from fonts.font_catalog import default_font_path  # noqa: E402
from render.layout import layout_document  # noqa: E402

FONT = default_font_path()


def make_model(text, **kw):
    gp = GlobalParams(font_path=FONT, rate=1, line_spacing=70, font_size=30,
                      margin_top=10, margin_bottom=10, margin_left=10, margin_right=10,
                      line_spacing_sigma=0, font_size_sigma=0, word_spacing_sigma=0,
                      **kw)
    return DocumentModel(text=text, global_params=gp)


def count_jobs(pages):
    return sum(len(p) for p in pages)


def test_single_line_one_page():
    m = make_model("abc")
    pages, size = layout_document(m, random.Random(0))
    assert len(pages) == 1
    assert count_jobs(pages) == 3
    assert all(j.page == 0 for p in pages for j in p)
    assert size == (m.global_params.paper_w, m.global_params.paper_h)


def test_newline_advances_line():
    m = make_model("ab\ncd")
    pages, _ = layout_document(m, random.Random(0))
    assert len(pages) == 1
    jobs = pages[0]
    # 'a','b' on line 1 (lower y), 'c','d' on line 2 (higher y)
    y_ab = [j.y for j in jobs[:2]]
    y_cd = [j.y for j in jobs[2:]]
    assert max(y_ab) < min(y_cd)


def test_long_text_multi_page():
    text = "字" * 500
    m = make_model(text)
    pages, _ = layout_document(m, random.Random(0))
    assert len(pages) >= 2
    assert count_jobs(pages) == 500


def test_center_alignment_applies_offset():
    m = make_model("ab", alignment="center")
    pages, _ = layout_document(m, random.Random(0))
    jobs = pages[0]
    gp = m.global_params
    # center => first glyph x shifted right beyond left margin
    assert jobs[0].x > gp.margin_left


def test_left_alignment_no_offset():
    m = make_model("ab", alignment="left")
    pages, _ = layout_document(m, random.Random(0))
    assert abs(pages[0][0].x - m.global_params.margin_left) < 1


def test_override_changes_font_size():
    m = make_model("abc")
    m.set_range(0, 1, {"font_size": 50})
    pages, _ = layout_document(m, random.Random(0))
    jobs = pages[0]
    assert jobs[0].font_size == 50
    assert jobs[1].font_size == 30


def test_override_underline_carried():
    m = make_model("abc")
    m.set_range(1, 2, {"underline": True})
    pages, _ = layout_document(m, random.Random(0))
    jobs = pages[0]
    assert jobs[0].underline is False
    assert jobs[1].underline is True


def test_empty_text_one_blank_page():
    m = make_model("")
    pages, _ = layout_document(m, random.Random(0))
    assert pages == [[]]
