from typing import TYPE_CHECKING, Any

from cka.domain.llm_provider import LLMProvider, LLMResponse

if TYPE_CHECKING:
    from anthropic import Anthropic

ANSWER_TOOL: dict[str, Any] = {
    "name": "provide_answer",
    "description": (
        "Provide the grounded answer, citing exactly the evidence chunk_ids "
        "that support it. Call this even to report that no answer is possible."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "answer": {
                "type": "string",
                "description": "The answer, grounded only in the provided evidence.",
            },
            "citations": {
                "type": "array",
                "items": {"type": "string"},
                "description": "chunk_id values (from the evidence blocks) supporting the answer.",
            },
        },
        "required": ["answer", "citations"],
    },
}


class AnthropicProviderError(Exception):
    pass


class AnthropicProvider(LLMProvider):
    """Real LLMProvider backed by the Anthropic Messages API.

    Uses forced tool-use (not freeform-text JSON parsing) to get a reliably
    structured {answer, citations} response — see ADR-008: citations are
    validated against the evidence set downstream, never trusted blindly.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        max_tokens: int = 1000,
    ) -> None:
        # Note: the installed `anthropic` SDK (1.0.0, Claude 5 family) no
        # longer exposes `temperature` as a Messages API parameter — the
        # roadmap's LLM_TEMPERATURE=0 baseline isn't expressible here. Kept
        # as a Settings field (unused by this provider) rather than removed,
        # documented here as a deliberate spec deviation, not an oversight.
        self._api_key = api_key
        self._model = model
        self._max_tokens = max_tokens
        self._client: Anthropic | None = None

    def _get_client(self) -> "Anthropic":
        if self._client is None:
            from anthropic import Anthropic

            self._client = Anthropic(api_key=self._api_key)
        return self._client

    def generate(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        # The SDK's overloaded, TypedDict-heavy signature for `tools`/`messages`
        # doesn't structurally match plain dict literals under strict mypy,
        # even though this payload shape is correct and works against the
        # real API (verified in tests/integration/test_anthropic_provider.py).
        response = self._get_client().messages.create(  # type: ignore[call-overload]
            model=self._model,
            max_tokens=self._max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            tools=[ANSWER_TOOL],
            tool_choice={"type": "tool", "name": "provide_answer"},
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "provide_answer":
                tool_input = block.input
                assert isinstance(tool_input, dict)
                citations = tool_input.get("citations", [])
                return LLMResponse(
                    answer=str(tool_input["answer"]),
                    citations=[str(c) for c in citations],
                )

        raise AnthropicProviderError("model did not return the expected provide_answer tool call")
