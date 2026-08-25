import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cka.evaluation.evaluator import (
    AdversarialEvalResult,
    GenerationEvalResult,
    RetrievalEvalResult,
)


def build_report_dict(
    retrieval: RetrievalEvalResult,
    generation: GenerationEvalResult,
    adversarial: AdversarialEvalResult,
    real_llm_used: bool,
) -> dict[str, Any]:
    return {
        "dataset": "golden-v1-block3",
        "generated_at": datetime.now(UTC).isoformat(),
        "real_llm_used": real_llm_used,
        "retrieval": asdict(retrieval),
        "generation": asdict(generation),
        "adversarial": asdict(adversarial),
    }


def write_json_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")


def write_markdown_report(report: dict[str, Any], path: Path) -> None:
    retrieval = report["retrieval"]
    generation = report["generation"]
    adversarial = report["adversarial"]

    lines = [
        "# RAG Evaluation Report",
        "",
        f"Generated: {report['generated_at']}",
        f"Real LLM used: {report['real_llm_used']}",
        "",
        "## Retrieval",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Cases | {retrieval['case_count']} |",
        f"| Recall@5 | {retrieval['recall_at_5']:.3f} |",
        f"| Precision@5 | {retrieval['precision_at_5']:.3f} |",
        f"| MRR | {retrieval['mrr']:.3f} |",
        f"| NDCG@5 | {retrieval['ndcg_at_5']:.3f} |",
        "",
        "## Generation",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Cases | {generation['case_count']} |",
        f"| Citation Accuracy | {generation['citation_accuracy']:.3f} |",
        f"| Citation Completeness | {generation['citation_completeness']:.3f} |",
        f"| Abstention Accuracy | {generation['abstention_accuracy']:.3f} |",
        f"| Faithfulness | {generation['faithfulness']} (n={generation['judged_case_count']}) |",
        f"| Answer Relevance | {generation['answer_relevance']} "
        f"(n={generation['judged_case_count']}) |",
        "",
        "## Adversarial",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Cases | {adversarial['case_count']} |",
        f"| Resistance Rate (prompt injection) | {adversarial['resistance_rate']:.3f} |",
        f"| Abstention Accuracy (unauthorized/out-of-domain) | "
        f"{adversarial['abstention_accuracy']:.3f} |",
        f"| Failures | {adversarial['failures'] or 'none'} |",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
