from cka.evaluation.retrieval_metrics import (
    hit_rate_at_k,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)


def test_hit_rate_at_k_hit() -> None:
    assert hit_rate_at_k(["a", "b", "c"], {"b"}, k=3) == 1.0


def test_hit_rate_at_k_miss_outside_k() -> None:
    assert hit_rate_at_k(["a", "b", "c"], {"c"}, k=2) == 0.0


def test_recall_at_k() -> None:
    assert recall_at_k(["a", "b", "c"], {"a", "b", "x"}, k=3) == 2 / 3


def test_recall_at_k_no_relevant_items() -> None:
    assert recall_at_k(["a"], set(), k=1) == 0.0


def test_precision_at_k() -> None:
    assert precision_at_k(["a", "b", "c"], {"a"}, k=3) == 1 / 3


def test_precision_at_k_zero_k() -> None:
    assert precision_at_k(["a"], {"a"}, k=0) == 0.0


def test_reciprocal_rank_first_hit_at_position_two() -> None:
    assert reciprocal_rank(["a", "b", "c"], {"b"}) == 0.5


def test_reciprocal_rank_no_hit() -> None:
    assert reciprocal_rank(["a", "b"], {"z"}) == 0.0


def test_ndcg_perfect_ranking_is_one() -> None:
    relevance = {"a": 3.0, "b": 2.0, "c": 1.0}
    assert ndcg_at_k(["a", "b", "c"], relevance, k=3) == 1.0


def test_ndcg_reversed_ranking_is_less_than_one() -> None:
    relevance = {"a": 3.0, "b": 2.0, "c": 1.0}
    score = ndcg_at_k(["c", "b", "a"], relevance, k=3)
    assert 0.0 < score < 1.0


def test_ndcg_no_relevance_data_is_zero() -> None:
    assert ndcg_at_k(["a", "b"], {}, k=2) == 0.0
