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


def _page_pair(tmp_path):
    from pathlib import Path

    from repath_evaluation.domain.models import PagePair, PageSnapshot

    old_node = make(0, BoundingBox(10, 10, 20, 20))
    initial_node = make(10, BoundingBox(-1, -1, 200, 200))
    new_node = make(1, BoundingBox(0, 0, 100, 100))
    old_page = PageSnapshot(
        "site",
        "old",
        tmp_path,
        [old_node],
        [],
        Path(tmp_path) / "old.png",
        None,
    )
    new_page = PageSnapshot(
        "site",
        "new",
        tmp_path,
        [initial_node, new_node],
        [],
        Path(tmp_path) / "new.png",
        None,
    )
    return PagePair("site", tmp_path, old_page, new_page, {0: 1}, [], [])


def test_prepare_loads_page_screenshots_once_for_reused_queries(monkeypatch, tmp_path):
    pair = _page_pair(tmp_path)
    old_image = np.zeros((100, 100, 3), dtype="uint8")
    new_image = np.zeros((100, 100, 3), dtype="uint8")
    reads = []

    def imread(path, mode):
        reads.append((path, mode))
        return old_image if path.endswith("old.png") else new_image

    monkeypatch.setattr("cv2.imread", imread)
    monkeypatch.setattr(
        VistaMatcher,
        "_sift_scene_descriptors",
        staticmethod(lambda gray: np.ones((2, 128), dtype="float32")),
    )
    monkeypatch.setattr(
        VistaMatcher,
        "_fast_scene_descriptors",
        staticmethod(lambda gray: np.ones((2, 128), dtype="float32")),
    )
    monkeypatch.setattr(VistaMatcher, "_feature_gate_from_cache", lambda self, template: True)
    monkeypatch.setattr(
        VistaMatcher,
        "_template_center",
        staticmethod(lambda template, scene: (50.0, 50.0)),
    )

    matcher = VistaMatcher()
    matcher.prepare(pair)
    first = matcher.match(0)
    second = matcher.match(0)

    assert first.top1 == 1
    assert second.top1 == 1
    assert len(reads) == 2
    assert reads[0][0].endswith("old.png")
    assert reads[1][0].endswith("new.png")


def test_cached_feature_gate_runs_both_detectors_with_cached_scene_descriptors(monkeypatch):
    matcher = VistaMatcher()
    matcher._new_gray = np.zeros((10, 10), dtype="uint8")
    matcher._scene_sift_descriptors = np.full((2, 128), 1.0, dtype="float32")
    matcher._scene_fast_descriptors = np.full((2, 128), 2.0, dtype="float32")
    calls = []

    def sift(cls, template_gray, descriptors):
        calls.append(("sift", descriptors))
        return True

    def fast(cls, template_gray, descriptors):
        calls.append(("fast", descriptors))
        return False

    monkeypatch.setattr(VistaMatcher, "_sift_gate_cached", classmethod(sift))
    monkeypatch.setattr(VistaMatcher, "_fast_gate_cached", classmethod(fast))

    template = np.zeros((5, 5, 3), dtype="uint8")
    assert matcher._feature_gate_from_cache(template) is True
    assert [name for name, _ in calls] == ["sift", "fast"]
    assert calls[0][1] is matcher._scene_sift_descriptors
    assert calls[1][1] is matcher._scene_fast_descriptors


def test_close_discards_vista_page_cache():
    matcher = VistaMatcher()
    matcher._old_image = np.zeros((1, 1, 3), dtype="uint8")
    matcher._new_image = np.zeros((1, 1, 3), dtype="uint8")
    matcher._new_gray = np.zeros((1, 1), dtype="uint8")
    matcher._scene_sift_descriptors = np.ones((1, 128), dtype="float32")
    matcher._scene_fast_descriptors = np.ones((1, 128), dtype="float32")

    matcher.close()

    assert matcher._old_image is None
    assert matcher._new_image is None
    assert matcher._new_gray is None
    assert matcher._scene_sift_descriptors is None
    assert matcher._scene_fast_descriptors is None
