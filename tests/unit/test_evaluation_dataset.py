from pathlib import Path

from cka.evaluation.dataset import (
    load_adversarial_cases,
    load_generation_cases,
    load_retrieval_cases,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = REPO_ROOT / "data" / "evaluation"


def test_loads_real_retrieval_cases() -> None:
    cases = load_retrieval_cases(EVAL_DIR / "retrieval.yaml")

    assert len(cases) >= 5
    assert all(case.expected_source_ids for case in cases)
    assert all(case.query for case in cases)


def test_loads_real_generation_cases() -> None:
    cases = load_generation_cases(EVAL_DIR / "generation.yaml")

    assert len(cases) >= 4
    behaviors = {case.expected_behavior for case in cases}
    assert behaviors == {"answer", "abstain"}


def test_loads_real_adversarial_cases() -> None:
    cases = load_adversarial_cases(EVAL_DIR / "adversarial.yaml")

    assert len(cases) >= 3
    categories = {case.category for case in cases}
    assert "prompt_injection" in categories
    assert "unauthorized_document" in categories


def test_adversarial_case_defaults_role_to_employee() -> None:
    cases = load_adversarial_cases(EVAL_DIR / "adversarial.yaml")
    injection_case = next(c for c in cases if c.category == "prompt_injection")

    assert injection_case.role == "employee"
