from cka.domain.evidence import Evidence


def validate_citations(citations: list[str], evidences: list[Evidence]) -> list[str]:
    """Drops any citation the LLM invented that doesn't correspond to a real
    evidence chunk — citations are never trusted blindly (ADR-008).
    """
    valid_ids = {evidence.chunk_id for evidence in evidences}
    return [citation for citation in citations if citation in valid_ids]
