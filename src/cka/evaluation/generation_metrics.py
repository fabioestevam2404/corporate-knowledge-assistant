def citation_accuracy(cited_source_ids: list[str], expected_source_ids: list[str]) -> float:
    """Of the sources the answer actually cited, what fraction were correct?"""
    if not cited_source_ids:
        return 0.0
    correct = sum(1 for source_id in cited_source_ids if source_id in expected_source_ids)
    return correct / len(cited_source_ids)


def citation_completeness(cited_source_ids: list[str], expected_source_ids: list[str]) -> float:
    """Of the sources that should have been cited, what fraction were?"""
    if not expected_source_ids:
        return 1.0
    found = sum(1 for source_id in expected_source_ids if source_id in cited_source_ids)
    return found / len(expected_source_ids)


def matches_expected_behavior(grounded: bool, expected_behavior: str) -> bool:
    predicted_behavior = "answer" if grounded else "abstain"
    return predicted_behavior == expected_behavior
