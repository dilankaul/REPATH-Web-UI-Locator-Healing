from __future__ import annotations

import hashlib
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np

from repath_evaluation.algorithms.repath.features import (
    ALL_MODEL_FEATURES,
    RepathFeaturePipeline,
)
from repath_evaluation.domain.models import (
    BoundingBox,
    DomNode,
    PagePair,
    PageSnapshot,
)


class FakeSemanticModel:
    def encode(
        self,
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
    ):
        vectors = []
        for text in texts:
            digest = hashlib.sha256(str(text).encode("utf-8")).digest()
            vector = np.asarray(
                [digest[0] + 1.0, digest[1] + 1.0, digest[2] + 1.0],
                dtype=np.float32,
            )
            if normalize_embeddings:
                vector = vector / np.linalg.norm(vector)
            vectors.append(vector)
        return np.stack(vectors)


def raw_node(
    *,
    index: int,
    tag: str,
    text: str,
    xpath: str,
    parent: int | None,
    attrs: dict[str, str] | None = None,
):
    return {
        "nodeId": index,
        "elementId": index,
        "elementType": 0,
        "tagName": tag,
        "text": text,
        "xpath": xpath,
        "parentIndex": parent,
        "attributes": attrs or {},
        "isDisplayed": True,
        "isEnabled": True,
        "isLeaf": True,
        "x": 10 + index * 5,
        "y": 20 + index * 5,
        "width": 100,
        "height": 30,
    }


def dom_node(index: int, raw: dict) -> DomNode:
    return DomNode(
        list_index=index,
        node_id=index,
        element_id=index,
        parent_id=raw.get("parentIndex"),
        element_type=0,
        tag=raw["tagName"],
        text=raw["text"],
        xpath=raw["xpath"],
        attributes=raw["attributes"],
        displayed=True,
        bbox=BoundingBox(
            x=raw["x"],
            y=raw["y"],
            width=raw["width"],
            height=raw["height"],
        ),
        raw=raw,
    )


def test_config_feature_order_matches_notebook_schema():
    project_root = Path(__file__).resolve().parents[2]
    config = joblib.load(project_root / "models" / "config_base.pkl")
    booster = lgb.Booster(model_file=str(project_root / "models" / "lgb_ranker.txt"))

    assert config["ALL_FEATURES"] == ALL_MODEL_FEATURES
    assert booster.feature_name() == ALL_MODEL_FEATURES
    assert len(ALL_MODEL_FEATURES) == 50


def test_calibrated_config_matches_bundled_operating_point():
    project_root = Path(__file__).resolve().parents[2]
    base = joblib.load(project_root / "models" / "config_base.pkl")
    calibrated = joblib.load(project_root / "models" / "config.pkl")

    assert calibrated["ALL_FEATURES"] == base["ALL_FEATURES"]
    assert calibrated["tau_margin"] == 0.40
    assert calibrated["target_precision"] == 0.99
    assert calibrated["minimum_end_to_end_coverage"] == 0.80


def test_direct_repath_feature_pipeline_builds_50_features(tmp_path):
    old_raw = [
        raw_node(
            index=0,
            tag="button",
            text="Sign in",
            xpath="/html/body/button[1]",
            parent=None,
            attrs={"id": "sign-in", "role": "button"},
        )
    ]
    new_raw = [
        raw_node(
            index=0,
            tag="button",
            text="Log in",
            xpath="/html/body/button[1]",
            parent=None,
            attrs={"id": "login", "role": "button"},
        ),
        raw_node(
            index=1,
            tag="button",
            text="Sign in",
            xpath="/html/body/button[2]",
            parent=None,
            attrs={"id": "sign-in", "role": "button"},
        ),
    ]

    old_page = PageSnapshot(
        site="synthetic",
        version="old",
        root=tmp_path / "old",
        nodes=[dom_node(0, old_raw[0])],
        pre_nodes=[],
        full_screen_path=None,
        html_path=None,
    )
    new_page = PageSnapshot(
        site="synthetic",
        version="new",
        root=tmp_path / "new",
        nodes=[
            dom_node(0, new_raw[0]),
            dom_node(1, new_raw[1]),
        ],
        pre_nodes=[],
        full_screen_path=None,
        html_path=None,
    )
    pair = PagePair(
        site="synthetic",
        root=tmp_path,
        old_page=old_page,
        new_page=new_page,
        match_map={0: 1},
        add_list=[],
        delete_list=[],
    )

    pipeline = RepathFeaturePipeline(
        semantic_model=FakeSemanticModel(),
        feature_names=list(ALL_MODEL_FEATURES),
        config={},
    )
    pipeline.prepare(pair)
    candidate_ids, matrix = pipeline.build_query(0)

    assert candidate_ids == [0, 1]
    assert matrix.shape == (2, 50)
    assert np.isfinite(matrix).all()

    id_feature = ALL_MODEL_FEATURES.index("id_seqsim")
    assert matrix[1, id_feature] > matrix[0, id_feature]
