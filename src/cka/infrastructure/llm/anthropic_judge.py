from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from anthropic import Anthropic

JUDGE_TOOL: dict[str, Any] = {
    "name": "provide_judgment",
    "description": (
        "Score how faithful and relevant an answer is, given the evidence it was grounded in."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "faithfulness": {
                "type": "number",
                "description": (
                    "0.0-1.0: does the answer only state things supported by the evidence?"
                ),
            },
            "answer_relevance": {
                "type": "number",
                "description": "0.0-1.0: does the answer actually address the question asked?",
            },
            "reason": {"type": "string", "description": "One sentence explaining the scores."},
        },
        "required": ["faithfulness", "answer_relevance", "reason"],
    },
}

JUDGE_SYSTEM_PROMPT = """You are an impartial evaluator for a RAG system. Given a question,
an answer, and the evidence the answer was supposed to be grounded in, score:

1. faithfulness (0.0-1.0): does the answer state only things actually supported by the
   evidence, without inventing anything?
2. answer_relevance (0.0-1.0): does the answer actually address the question asked?

Always respond by calling provide_judgment."""


@dataclass(frozen=True)
class JudgeResult:
    faithfulness: float
    answer_relevance: float
    reason: str


class AnthropicLLMJudge:
    """LLM-as-a-Judge (ADR-010) — never treated as ground truth, only as a
    qualitative signal alongside the deterministic metrics (citation
    accuracy, abstention accuracy) computed without any LLM call.
    """

    def __init__(self, api_key: str, model: str, max_tokens: int = 300) -> None:
        self._api_key = api_key
        self._model = model
        self._max_tokens = max_tokens
        self._client: Anthropic | None = None

    def _get_client(self) -> "Anthropic":
        if self._client is None:
            from anthropic import Anthropic

            self._client = Anthropic(api_key=self._api_key)
        return self._client

    def judge(self, question: str, answer: str, evidence: str) -> JudgeResult:
        user_prompt = (
            f"QUESTION:\n{question}\n\nEVIDENCE:\n{evidence}\n\nANSWER TO EVALUATE:\n{answer}"
        )
        response = self._get_client().messages.create(  # type: ignore[call-overload]
            model=self._model,
            max_tokens=self._max_tokens,
            system=JUDGE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
            tools=[JUDGE_TOOL],
            tool_choice={"type": "tool", "name": "provide_judgment"},
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "provide_judgment":
                tool_input = block.input
                assert isinstance(tool_input, dict)
                return JudgeResult(
                    faithfulness=float(tool_input["faithfulness"]),
                    answer_relevance=float(tool_input["answer_relevance"]),
                    reason=str(tool_input["reason"]),
                )

        raise RuntimeError("AnthropicLLMJudge: model did not return the expected tool call")
