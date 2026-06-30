"""Unit tests for cli-anything-handwrite core modules.

Pure Python, synthetic data, no Node backend. Fast + deterministic.
Mirrors src/shared/settings.ts and palette.ts semantics; parity spot-checks
against tests/layout.test.ts.
"""
import json
import os

import pytest

from cli_anything.handwrite.core import model as M
from cli_anything.handwrite.core import params as P
from cli_anything.handwrite.core import session as S
from cli_anything.handwrite.core import render as R
from cli_anything.handwrite.handwrite_cli import _parse_override_pairs


# ── model: defaults ────────────────────────────────────────────────────
class TestDefaults:
    def test_default_global_params_match_ts(self):
        gp = M.default_global_params("f.ttf")
        assert gp["paper_w"] == 667
        assert gp["paper_h"] == 945
        assert gp["font_path"] == "f.ttf"
        assert gp["font_size"] == 30
        assert gp["line_spacing"] == 70
        assert gp["word_spacing"] == 1
        assert gp["margin_top"] == 10
        assert gp["rate"] == 4
        assert gp["line_spacing_sigma"] == 1.0
        assert gp["font_size_sigma"] == 1.0
        assert gp["word_spacing_sigma"] == 1.0
        assert gp["perturb_x_sigma"] == 1.0
        assert gp["perturb_y_sigma"] == 1.0
        assert gp["perturb_theta_sigma"] == 0.05
        assert gp["alignment"] == "left"
        assert gp["underline"] is False
        assert gp["fill"] == [0, 0, 0, 255]
        assert gp["background"] == [255, 255, 255, 255]

    def test_create_document_model(self):
        m = M.create_document_model("x.ttf")
        assert m["text"] == ""
        assert m["overrides"] == []
        assert m["global_params"]["font_path"] == "x.ttf"

    def test_adjustable_keys_match_ts(self):
        assert set(M.ADJUSTABLE_KEYS) == {
            "font_size", "word_spacing", "perturb_x_sigma", "perturb_y_sigma",
            "perturb_theta_sigma", "fill", "alignment", "underline",
        }


# ── model: dict round-trip ─────────────────────────────────────────────
class TestRoundTrip:
    def test_to_from_dict_roundtrip(self):
        m = M.create_document_model("f.ttf")
        m["text"] = "abc"
        M.DocumentModelOps.set_range(m, 0, 2, {"font_size": 50})
        d = M.document_to_dict(m)
        m2 = M.document_from_dict(d)
        assert m2["text"] == "abc"
        assert m2["overrides"] == m["overrides"]
        assert m2["global_params"] == m["global_params"]

    def test_from_dict_missing_fields(self):
        m = M.document_from_dict({"text": "x"})
        assert m["text"] == "x"
        assert m["overrides"] == []
        assert m["global_params"]["font_size"] == 30  # defaults fill in


# ── model: DocumentModelOps (parity with settings.ts) ──────────────────
class TestSetRange:
    def make(self, text="abc"):
        m = M.create_document_model("f.ttf")
        m["text"] = text
        return m

    def test_basic_override(self):
        m = self.make("abc")
        M.DocumentModelOps.set_range(m, 0, 1, {"font_size": 50})
        assert len(m["overrides"]) == 1
        seg = m["overrides"][0]
        assert seg["start"] == 0 and seg["end"] == 1
        assert seg["params"]["font_size"] == 50

    def test_override_changes_font_size_parity(self):
        # Mirrors tests/layout.test.ts 'override changes font size'
        m = self.make("abc")
        M.DocumentModelOps.set_range(m, 0, 1, {"font_size": 50})
        eff0 = M.DocumentModelOps.effective_params(m, 0)
        eff1 = M.DocumentModelOps.effective_params(m, 1)
        assert eff0["font_size"] == 50
        assert eff1["font_size"] == 30

    def test_override_underline_carried(self):
        # Mirrors tests/layout.test.ts 'override underline carried'
        m = self.make("abc")
        M.DocumentModelOps.set_range(m, 1, 2, {"underline": True})
        assert M.DocumentModelOps.effective_params(m, 0)["underline"] is False
        assert M.DocumentModelOps.effective_params(m, 1)["underline"] is True

    def test_merge_adjacent_equal(self):
        m = self.make("abcde")
        M.DocumentModelOps.set_range(m, 0, 2, {"font_size": 50})
        M.DocumentModelOps.set_range(m, 2, 4, {"font_size": 50})
        # adjacent + equal params -> merged into one segment
        assert len(m["overrides"]) == 1
        assert m["overrides"][0]["start"] == 0 and m["overrides"][0]["end"] == 4

    def test_gap_fill(self):
        m = self.make("abcde")
        M.DocumentModelOps.set_range(m, 0, 1, {"font_size": 50})
        M.DocumentModelOps.set_range(m, 4, 5, {"font_size": 50})
        # setting [0,5) fills the gap between the two single-char overrides
        M.DocumentModelOps.set_range(m, 0, 5, {"font_size": 50})
        assert len(m["overrides"]) == 1
        assert m["overrides"][0]["end"] == 5

    def test_split_crossing_segment(self):
        m = self.make("abcde")
        M.DocumentModelOps.set_range(m, 0, 4, {"font_size": 50})
        # override [2,3) splits the existing [0,4) segment
        M.DocumentModelOps.set_range(m, 2, 3, {"font_size": 80})
        sizes = [M.DocumentModelOps.effective_params(m, i)["font_size"] for i in range(4)]
        assert sizes == [50, 50, 80, 50]

    def test_empty_params_noop(self):
        m = self.make("abc")
        M.DocumentModelOps.set_range(m, 0, 2, {})
        assert m["overrides"] == []

    def test_out_of_range_clamped(self):
        m = self.make("ab")
        M.DocumentModelOps.set_range(m, 0, 99, {"font_size": 50})
        assert m["overrides"][0]["end"] == 2


class TestClearRange:
    def make(self, text="abcde"):
        m = M.create_document_model("f.ttf")
        m["text"] = text
        return m

    def test_clear_inside(self):
        m = self.make("abcde")
        M.DocumentModelOps.set_range(m, 0, 5, {"font_size": 50})
        M.DocumentModelOps.clear_range(m, 1, 3)
        # clears [1,3), leaving [0,1) and [3,5)
        assert len(m["overrides"]) == 2
        assert m["overrides"][0] == {"start": 0, "end": 1, "params": {"font_size": 50}}
        assert m["overrides"][1] == {"start": 3, "end": 5, "params": {"font_size": 50}}

    def test_clear_all(self):
        m = self.make("abcde")
        M.DocumentModelOps.set_range(m, 0, 5, {"font_size": 50})
        M.DocumentModelOps.clear_range(m, 0, 5)
        assert m["overrides"] == []


class TestTrimToText:
    def test_keeps_and_clamps_fitting_override(self):
        # Mirrors settings.ts trimToText: an override with end <= n is kept and clamped.
        m = M.create_document_model("f.ttf")
        m["text"] = "abcde"
        M.DocumentModelOps.set_range(m, 0, 2, {"font_size": 50})
        m["text"] = "ab"  # shorten; [0,2) still fits (end==n)
        M.DocumentModelOps.trim_to_text(m)
        assert len(m["overrides"]) == 1
        assert m["overrides"][0]["start"] == 0
        assert m["overrides"][0]["end"] == 2

    def test_drops_overlong_override(self):
        # Mirrors settings.ts: override [0,5) is dropped when text shrinks to n=2
        # (filter keeps only o.start < n && o.end <= n; no clamping of overlong end).
        m = M.create_document_model("f.ttf")
        m["text"] = "abcde"
        M.DocumentModelOps.set_range(m, 0, 5, {"font_size": 50})
        m["text"] = "ab"
        M.DocumentModelOps.trim_to_text(m)
        assert m["overrides"] == []

    def test_drops_fully_out_of_range(self):
        m = M.create_document_model("f.ttf")
        m["text"] = "abcde"
        M.DocumentModelOps.set_range(m, 3, 5, {"font_size": 50})
        m["text"] = "ab"
        M.DocumentModelOps.trim_to_text(m)
        assert m["overrides"] == []


# ── params ─────────────────────────────────────────────────────────────
class TestParseColor:
    def test_named(self):
        assert P.parse_color("black") == (0, 0, 0, 255)
        assert P.parse_color("red") == (255, 0, 0, 255)
        assert P.parse_color("white") == (255, 255, 255, 255)
        assert P.parse_color("blue") == (0, 0, 255, 255)

    def test_hex_6(self):
        assert P.parse_color("#ff0000") == (255, 0, 0, 255)

    def test_hex_8(self):
        assert P.parse_color("#ff000088") == (255, 0, 0, 136)

    def test_csv(self):
        assert P.parse_color("1,2,3") == (1, 2, 3, 255)

    def test_list(self):
        assert P.parse_color([10, 20, 30]) == (10, 20, 30, 255)
        assert P.parse_color([10, 20, 30, 40]) == (10, 20, 30, 40)

    def test_background_named(self):
        assert P.parse_background("transparent") == (0, 0, 0, 0)
        assert P.parse_background("white") == (255, 255, 255, 255)

    def test_bad(self):
        with pytest.raises(ValueError):
            P.parse_color("notacolor")


class TestCoerce:
    def test_rate_alias(self):
        assert P.coerce_value("rate", "x4") == 4
        assert P.coerce_value("rate", "8") == 8

    def test_underline(self):
        assert P.coerce_value("underline", "true") is True
        assert P.coerce_value("underline", "no") is False

    def test_fill_coerces_to_list(self):
        v = P.coerce_value("fill", "red")
        assert v == [255, 0, 0, 255]

    def test_numeric(self):
        assert P.coerce_value("font_size", "40") == 40
        assert P.coerce_value("perturb_theta_sigma", "0.1") == 0.1


class TestValidate:
    def test_font_size_gt_line_spacing(self):
        with pytest.raises(ValueError):
            P.validate_params({"font_size": 70, "line_spacing": 50, "paper_w": 100,
                               "paper_h": 100, "alignment": "left", "rate": 4})

    def test_nonpositive_paper(self):
        with pytest.raises(ValueError):
            P.validate_params({"font_size": 10, "line_spacing": 20, "paper_w": 0,
                               "paper_h": 100, "alignment": "left", "rate": 4})

    def test_bad_alignment(self):
        with pytest.raises(ValueError):
            P.validate_params({"font_size": 10, "line_spacing": 20, "paper_w": 100,
                               "paper_h": 100, "alignment": "right", "rate": 4})

    def test_bad_rate(self):
        with pytest.raises(ValueError):
            P.validate_params({"font_size": 10, "line_spacing": 20, "paper_w": 100,
                               "paper_h": 100, "alignment": "left", "rate": 3})

    def test_valid_ok(self):
        P.validate_params({"font_size": 30, "line_spacing": 70, "paper_w": 667,
                           "paper_h": 945, "alignment": "left", "rate": 4})


class TestPresetsAndKeys:
    def test_normalize_alias(self):
        assert P.normalize_key("font-size") == "font_size"
        assert P.normalize_key("fontsize") == "font_size"
        assert P.normalize_key("perturbx") == "perturb_x_sigma"

    def test_apply_preset_a4(self):
        gp = M.default_global_params()
        gp = P.apply_preset(gp, "a4")
        assert gp["paper_w"] == 595
        assert gp["paper_h"] == 842
        assert gp["margin_top"] == 56

    def test_unknown_preset(self):
        with pytest.raises(ValueError):
            P.apply_preset(M.default_global_params(), "foo")

    def test_is_global_key(self):
        assert P.is_global_key("font_size")
        assert P.is_global_key("font-size")
        assert not P.is_global_key("nope")


# ── session ────────────────────────────────────────────────────────────
class TestSession:
    def test_undo_redo(self, tmp_dir):
        s = S.Session()
        s.set_model(M.create_document_model("f.ttf"))
        s.model["text"] = "hello"
        s.snapshot()
        s.model["text"] = "world"
        assert s.undo() is True
        assert s.model["text"] == "hello"
        assert s.redo() is True
        assert s.model["text"] == "world"

    def test_undo_empty(self):
        s = S.Session()
        assert s.undo() is False
        assert s.redo() is False

    def test_save_load_roundtrip(self, tmp_dir):
        path = os.path.join(tmp_dir, "s.hwsess.json")
        s = S.Session()
        s.set_model(M.create_document_model("f.ttf"))
        s.model["text"] = "persist me"
        M.DocumentModelOps.set_range(s.model, 0, 3, {"font_size": 50})
        s.output_dir = os.path.join(tmp_dir, "out")
        s.save_session(path)
        s2 = S.Session.load_session(path)
        assert s2.model["text"] == "persist me"
        assert s2.model["overrides"] == s.model["overrides"]
        assert s2.output_dir == s.output_dir

    def test_modified_tracking(self):
        s = S.Session()
        assert s._modified is False
        s.set_model(M.create_document_model())
        assert s._modified is True


# ── render verification ────────────────────────────────────────────────
PNG_FIXTURE = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\x0dIHDR\x00\x00\x00\x02\x00\x00\x00\x02\x08\x02\x00\x00\x00"
    b"\xfd\x4f\x33\x65"
    # minimal IDAT + IEND
    b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x00\x03\x00\x01\x5b\x62\x95"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


class TestVerifyPng:
    def test_valid_png(self, tmp_dir):
        p = os.path.join(tmp_dir, "ok.png")
        with open(p, "wb") as f:
            f.write(PNG_FIXTURE)
        v = R.verify_png(p)
        assert v["ok"] is True
        assert v["width"] == 2 and v["height"] == 2
        assert v["bytes"] > 0

    def test_bad_magic(self, tmp_dir):
        p = os.path.join(tmp_dir, "bad.png")
        with open(p, "wb") as f:
            f.write(b"NOTAPNG" + b"\x00" * 20)
        v = R.verify_png(p)
        assert v["ok"] is False
        assert "magic" in v["error"]

    def test_missing(self):
        v = R.verify_png("/no/such/file.png")
        assert v["ok"] is False


# ── cli override-pair parsing ──────────────────────────────────────────
class TestParseOverridePairs:
    def test_basic(self):
        d = _parse_override_pairs(["font_size=50", "fill=red"])
        assert d["font_size"] == 50
        assert d["fill"] == [255, 0, 0, 255]

    def test_alignment_and_underline(self):
        d = _parse_override_pairs(["alignment=center", "underline=true"])
        assert d["alignment"] == "center"
        assert d["underline"] is True

    def test_float(self):
        d = _parse_override_pairs(["perturb_theta_sigma=0.1"])
        assert d["perturb_theta_sigma"] == 0.1

    def test_rejects_non_adjustable(self):
        with pytest.raises(ValueError):
            _parse_override_pairs(["paper_w=100"])

    def test_rejects_malformed(self):
        with pytest.raises(ValueError):
            _parse_override_pairs(["font_size 50"])
