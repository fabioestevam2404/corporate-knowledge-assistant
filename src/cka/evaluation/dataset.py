from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class RetrievalCase:
    id: str
    query: str
    expected_source_ids: list[str]


@dataclass(frozen=True)
class GenerationCase:
    id: str
    query: str
    expected_sources: list[str]
    expected_behavior: str  # "answer" | "abstain"


@dataclass(frozen=True)
class AdversarialCase:
    id: str
    category: str
    query: str
    expected_sources: list[str]
    expected_behavior: str  # "abstain" | "resist"
    role: str = "employee"


def load_retrieval_cases(path: Path) -> list[RetrievalCase]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [
        RetrievalCase(
            id=case["id"],
            query=case["query"],
            expected_source_ids=case["expected_source_ids"],
        )
        for case in raw["cases"]
    ]


def load_generation_cases(path: Path) -> list[GenerationCase]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [
        GenerationCase(
            id=case["id"],
            query=case["query"],
            expected_sources=case["expected_sources"],
            expected_behavior=case["expected_behavior"],
        )
        for case in raw["cases"]
    ]


def load_adversarial_cases(path: Path) -> list[AdversarialCase]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [
        AdversarialCase(
            id=case["id"],
            category=case["category"],
            query=case["query"],
            expected_sources=case["expected_sources"],
            expected_behavior=case["expected_behavior"],
            role=case.get("role", "employee"),
        )
        for case in raw["cases"]
    ]
