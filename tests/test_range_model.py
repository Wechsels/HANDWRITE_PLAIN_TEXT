import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config.settings import DocumentModel, GlobalParams, RangeOverride  # noqa: E402


def make_model(text: str = "abcdefghij") -> DocumentModel:
    return DocumentModel(text=text, global_params=GlobalParams(font_path="x.ttf"))


def test_set_range_creates_override():
    m = make_model()
    m.set_range(2, 5, {"perturb_x_sigma": 3.0})
    assert m.ranges_for_marking() == [(2, 5)]
    assert m.effective_params(0)["perturb_x_sigma"] == 1.0
    assert m.effective_params(3)["perturb_x_sigma"] == 3.0
    assert m.effective_params(5)["perturb_x_sigma"] == 1.0


def test_set_range_partial_overlap_splits():
    m = make_model()
    m.set_range(2, 6, {"font_size": 40})
    m.set_range(4, 8, {"perturb_y_sigma": 5.0})
    # original [2,6) split into [2,4) font_size=40 and [4,6) merged
    assert m.effective_params(3)["font_size"] == 40
    assert m.effective_params(3)["perturb_y_sigma"] == 1.0
    assert m.effective_params(5)["font_size"] == 40
    assert m.effective_params(5)["perturb_y_sigma"] == 5.0
    # gap [6,8) gets only the new param
    assert m.effective_params(7)["font_size"] == 30
    assert m.effective_params(7)["perturb_y_sigma"] == 5.0
    assert m.effective_params(8)["perturb_y_sigma"] == 1.0


def test_merge_semantics_preserves_prior_keys():
    m = make_model()
    m.set_range(0, 4, {"font_size": 50})
    m.set_range(1, 3, {"perturb_x_sigma": 2.0})
    assert m.effective_params(2)["font_size"] == 50
    assert m.effective_params(2)["perturb_x_sigma"] == 2.0


def test_clear_range_keeps_outside():
    m = make_model()
    m.set_range(2, 8, {"font_size": 40})
    m.clear_range(4, 6)
    assert m.effective_params(3)["font_size"] == 40
    assert m.effective_params(5)["font_size"] == 30
    assert m.effective_params(7)["font_size"] == 40
    assert m.ranges_for_marking() == [(2, 4), (6, 8)]


def test_override_at_and_reselect_shows_adjusted():
    m = make_model()
    m.set_range(3, 6, {"perturb_theta_sigma": 0.2, "font_size": 35})
    seg = m.override_at(4)
    assert seg is not None
    assert seg.params["perturb_theta_sigma"] == 0.2
    assert m.effective_params(4)["font_size"] == 35


def test_adjacent_same_params_merge():
    m = make_model()
    m.set_range(0, 3, {"font_size": 40})
    m.set_range(3, 6, {"font_size": 40})
    assert m.ranges_for_marking() == [(0, 6)]


def test_clamp_and_empty_noop():
    m = make_model()
    m.set_range(-5, 100, {"font_size": 40})
    assert m.ranges_for_marking() == [(0, 10)]
    m.set_range(2, 2, {"font_size": 99})
    assert len(m.overrides) == 1
    m.set_range(1, 3, {})
    assert len(m.overrides) == 1


def test_persistence_roundtrip(tmp_path):
    m = make_model("hello world")
    m.set_range(0, 5, {"font_size": 44, "underline": True})
    from config import persistence as pers  # noqa: E402
    path = tmp_path / "cfg.toml"
    pers.save_model(m, str(path))
    loaded = pers.load_model(str(path))
    assert loaded.text == "hello world"
    assert loaded.global_params.font_path == "x.ttf"
    assert loaded.ranges_for_marking() == [(0, 5)]
    assert loaded.effective_params(2)["font_size"] == 44
    assert loaded.effective_params(2)["underline"] is True


def test_range_override_to_from_dict():
    o = RangeOverride(1, 3, {"font_size": 40})
    o2 = RangeOverride.from_dict(o.to_dict())
    assert o2.start == 1 and o2.end == 3 and o2.params == {"font_size": 40}
