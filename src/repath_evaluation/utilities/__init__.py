"""Shared algorithm-independent utilities."""

from .similarity import levenshtein_distance, normalized_edit_similarity

__all__ = ["levenshtein_distance", "normalized_edit_similarity"]
