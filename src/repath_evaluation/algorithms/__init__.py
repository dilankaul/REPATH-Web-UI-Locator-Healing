from .base import ElementMatcher
from .water import WaterMatcher
from .vista import VistaMatcher
from .sftm import SftmMatcher
from .webevo import WebEvoMatcher
from .similo import SimiloMatcher

__all__ = [
    "ElementMatcher",
    "RepathMatcher",
    "WaterMatcher",
    "VistaMatcher",
    "SftmMatcher",
    "WebEvoMatcher",
    "SimiloMatcher",
]


def __getattr__(name: str):
    # Avoid loading LightGBM/SentenceTransformer when only a lightweight
    # baseline module is imported, for example during SFTM unit tests.
    if name == "RepathMatcher":
        from .repath import RepathMatcher

        return RepathMatcher
    raise AttributeError(name)
