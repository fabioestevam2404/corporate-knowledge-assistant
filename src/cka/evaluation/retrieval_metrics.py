"""Pure retrieval-quality metrics (ADR-006/Sprint 06-07).

Deliberately lightweight for now: no Golden Dataset runner or CI gate yet
(that's Block 3 / Sprint 10) — just the metric functions, so retrieval
quality is measurable and unit-testable from day one.
"""

import math


def hit_rate_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    return 1.0 if set(retrieved[:k]) & relevant else 0.0


def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    return len(set(retrieved[:k]) & relevant) / len(relevant)


def precision_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if k <= 0:
        return 0.0
    return len(set(retrieved[:k]) & relevant) / k


def reciprocal_rank(retrieved: list[str], relevant: set[str]) -> float:
    for index, item_id in enumerate(retrieved, start=1):
        if item_id in relevant:
            return 1.0 / index
    return 0.0


def ndcg_at_k(retrieved: list[str], relevance: dict[str, float], k: int) -> float:
    """Normalized Discounted Cumulative Gain with graded relevance (Sprint 07)."""

    def _dcg(item_ids: list[str]) -> float:
        return sum(
            relevance.get(item_id, 0.0) / math.log2(index + 2)
            for index, item_id in enumerate(item_ids)
        )

    actual = _dcg(retrieved[:k])
    ideal_order = sorted(relevance, key=lambda item_id: relevance[item_id], reverse=True)[:k]
    ideal = _dcg(ideal_order)

    return actual / ideal if ideal > 0 else 0.0
