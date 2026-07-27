from __future__ import annotations

import math


def levenshtein_distance(left: str, right: str) -> int:
    if len(left) < len(right):
        left, right = right, left
    costs = list(range(len(right) + 1))
    for i, left_char in enumerate(left, start=1):
        previous_diagonal = costs[0]
        costs[0] = i
        for j, right_char in enumerate(right, start=1):
            old_cost = costs[j]
            substitution = 0 if left_char == right_char else 1
            costs[j] = min(costs[j] + 1, costs[j - 1] + 1, previous_diagonal + substitution)
            previous_diagonal = old_cost
    return costs[-1]


def normalized_edit_similarity(left: str, right: str, max_length: int | None = None) -> float:
    left = "" if left is None else str(left)
    right = "" if right is None else str(right)
    if max_length is not None:
        left = left[:max_length]
        right = right[:max_length]
    if not left or not right:
        return 0.0
    left = left.casefold()
    right = right.casefold()
    if left == right:
        return 1.0
    maximum = max(len(left), len(right))
    if maximum == 0:
        return 1.0
    return max(0.0, (maximum - levenshtein_distance(left, right)) / maximum)


def euclidean(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.hypot(x1 - x2, y1 - y2)
