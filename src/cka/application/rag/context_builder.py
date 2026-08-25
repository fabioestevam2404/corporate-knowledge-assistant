import tiktoken

from cka.domain.evidence import Evidence

BLOCK_SEPARATOR = "\n---\n"


class ContextBuilder:
    """Builds structured, citable context blocks from evidence, staying under
    a token budget (never truncating a block mid-chunk — see ADR-008).
    """

    def __init__(self, max_context_tokens: int = 6000) -> None:
        self._max_context_tokens = max_context_tokens
        self._encoding = tiktoken.get_encoding("cl100k_base")

    def build(self, evidences: list[Evidence]) -> tuple[str, list[Evidence]]:
        blocks: list[str] = []
        included: list[Evidence] = []
        total_tokens = 0

        for evidence in evidences:
            block = self._format_block(evidence)
            block_tokens = len(self._encoding.encode(block))

            if included and total_tokens + block_tokens > self._max_context_tokens:
                break

            blocks.append(block)
            included.append(evidence)
            total_tokens += block_tokens

        return BLOCK_SEPARATOR.join(blocks), included

    @staticmethod
    def _format_block(evidence: Evidence) -> str:
        page = evidence.page_number if evidence.page_number is not None else "N/A"
        return (
            f"SOURCE_ID: {evidence.source_id}\n"
            f"DOCUMENT_ID: {evidence.document_id}\n"
            f"PAGE: {page}\n"
            f"CHUNK_ID: {evidence.chunk_id}\n\n"
            f"CONTENT:\n{evidence.content}"
        )
