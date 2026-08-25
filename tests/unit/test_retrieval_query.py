import pytest

from cka.domain.retrieval import RetrievalQuery


def test_top_k_within_bounds_is_accepted() -> None:
    query = RetrievalQuery(text="q", top_k=20)

    assert query.top_k == 20


@pytest.mark.parametrize("top_k", [0, -1, 21])
def test_top_k_out_of_bounds_raises(top_k: int) -> None:
    with pytest.raises(ValueError, match="top_k must be between 1 and 20"):
        RetrievalQuery(text="q", top_k=top_k)
