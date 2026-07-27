import numpy as np

from repath_evaluation.algorithms.vista import UPSTREAM_COMMIT, VistaMatcher
from repath_evaluation.domain.models import BoundingBox, DomNode


def make(index, area_box):
    return DomNode(index, index, index, -1, 2, "div", "", "", {}, (), True, area_box)


def test_vista_is_pinned_to_original_author_repository_commit():
    assert UPSTREAM_COMMIT == "7bf2a588897637e0e1c9a2cc33e4d372a62bcaf0"


def test_smallest_containing_node_preserves_reference_rule():
    nodes = [
        make(0, BoundingBox(0, 0, 100, 100)),
        make(1, BoundingBox(10, 10, 40, 40)),
        make(2, BoundingBox(20, 20, 10, 10)),
    ]
    assert VistaMatcher._smallest_containing_node((25, 25), nodes).node_id == 2


def test_feature_gate_runs_both_detectors(monkeypatch):
    calls = []

    def sift(cls, template, scene):
        calls.append("sift")
        return True

    def fast(cls, template, scene):
        calls.append("fast")
        return False

    monkeypatch.setattr(VistaMatcher, "_sift_gate", classmethod(sift))
    monkeypatch.setattr(VistaMatcher, "_fast_gate", classmethod(fast))
    image = np.zeros((10, 10, 3), dtype="uint8")
    assert VistaMatcher._feature_gate(image, image)
    assert calls == ["sift", "fast"]
