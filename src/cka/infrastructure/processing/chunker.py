from dataclasses import dataclass

import tiktoken

DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " "]


@dataclass(frozen=True)
class ChunkedText:
    content: str
    token_count: int


class TextChunker:
    """Recursive character chunking with overlap.

    Tries to split on paragraph breaks first, then lines, then sentences,
    then words, falling back to a hard character split only if a piece still
    doesn't fit chunk_size. Consecutive chunks share `overlap` characters of
    context, per ADR-006/Sprint 05 (chunk_size=1200, overlap=200 baseline).
    """

    def __init__(
        self,
        chunk_size: int = 1200,
        overlap: int = 200,
        separators: list[str] | None = None,
    ) -> None:
        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.separators = separators or DEFAULT_SEPARATORS
        self._encoding = tiktoken.get_encoding("cl100k_base")

    def chunk(self, text: str) -> list[ChunkedText]:
        pieces = self._split_recursive(text, self.separators)
        return self._merge_with_overlap(pieces)

    def _split_recursive(self, text: str, separators: list[str]) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text] if text else []

        if not separators:
            return [text[i : i + self.chunk_size] for i in range(0, len(text), self.chunk_size)]

        separator, *rest = separators
        parts = text.split(separator)

        pieces: list[str] = []
        for index, part in enumerate(parts):
            piece = part if index == len(parts) - 1 else part + separator
            if not piece:
                continue
            if len(piece) <= self.chunk_size:
                pieces.append(piece)
            else:
                pieces.extend(self._split_recursive(piece, rest))
        return pieces

    def _merge_with_overlap(self, pieces: list[str]) -> list[ChunkedText]:
        chunks: list[str] = []
        current = ""

        for piece in pieces:
            if current and len(current) + len(piece) > self.chunk_size:
                chunks.append(current)
                overlap_tail = current[-self.overlap :] if self.overlap else ""
                current = overlap_tail + piece
            else:
                current += piece

        if current.strip():
            chunks.append(current)

        return [self._to_chunked_text(chunk) for chunk in chunks]

    def _to_chunked_text(self, content: str) -> ChunkedText:
        content = content.strip()
        token_count = len(self._encoding.encode(content))
        return ChunkedText(content=content, token_count=token_count)
