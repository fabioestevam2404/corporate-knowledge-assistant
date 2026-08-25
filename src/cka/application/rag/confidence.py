from cka.domain.evidence import Evidence

HIGH = "high"
MEDIUM = "medium"
LOW = "low"


def compute_confidence(
    evidences: list[Evidence],
    total_citations: int,
    valid_citations: int,
    score_threshold: float,
    high_min_evidence: int,
) -> str:
    """Rule-based confidence — deliberately not the raw retrieval similarity
    score (see ADR-008/Sprint 08):

    - LOW: no valid citation (nothing in the answer is actually grounded).
    - HIGH: every citation the model gave is valid, and at least
      `high_min_evidence` pieces of evidence scored at/above the threshold.
    - MEDIUM: everything else that still has at least one valid citation
      (single evidence, or some citations were invalid/hallucinated).
    """
    if valid_citations == 0:
        return LOW

    strong_evidence_count = sum(1 for evidence in evidences if evidence.score >= score_threshold)
    all_citations_valid = total_citations > 0 and valid_citations == total_citations

    if all_citations_valid and strong_evidence_count >= high_min_evidence:
        return HIGH

    return MEDIUM
