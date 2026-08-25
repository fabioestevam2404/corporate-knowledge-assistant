import pytest

from cka.infrastructure.processing.chunker import TextChunker


def test_short_text_returns_single_chunk() -> None:
    chunker = TextChunker(chunk_size=1200, overlap=200)

    chunks = chunker.chunk("This is a short document about remote work policy.")

    assert len(chunks) == 1
    assert chunks[0].content == "This is a short document about remote work policy."
    assert chunks[0].token_count > 0


def test_long_text_is_split_into_multiple_chunks() -> None:
    chunker = TextChunker(chunk_size=200, overlap=50)
    paragraph = "Paragraph about corporate policy details. " * 20  # ~860 chars

    chunks = chunker.chunk(paragraph)

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.content) <= 200 + 50  # soft bound: chunk_size + overlap carry-over


def test_consecutive_chunks_share_overlap_content() -> None:
    chunker = TextChunker(chunk_size=200, overlap=50)
    paragraph = "Sentence number filler text to force multiple chunks. " * 15

    chunks = chunker.chunk(paragraph)

    assert len(chunks) > 1
    tail_of_first = chunks[0].content[-50:]
    assert tail_of_first[:20] in chunks[1].content


def test_empty_text_returns_no_chunks() -> None:
    chunker = TextChunker()

    assert chunker.chunk("") == []


def test_overlap_must_be_smaller_than_chunk_size() -> None:
    with pytest.raises(ValueError, match="overlap must be smaller than chunk_size"):
        TextChunker(chunk_size=100, overlap=100)


def test_single_unbreakable_word_falls_back_to_hard_character_split() -> None:
    # No spaces/newlines/periods to split on (e.g. a long token/URL/hash) —
    # forces the hard character-split fallback once separators are exhausted.
    chunker = TextChunker(chunk_size=50, overlap=10, separators=["\n\n", "\n", ". ", " "])

    chunks = chunker.chunk("x" * 130)

    assert len(chunks) > 1
    assert all(
        len(chunk.content) <= 50 + 10 for chunk in chunks
    )  # soft bound: chunk_size + overlap
