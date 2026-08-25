from cka.domain.llm_provider import LLMProvider, LLMResponse


class FakeLLMProvider(LLMProvider):
    """Deterministic LLMProvider double for tests — no network, no API key.

    Records every call so tests can assert on what was actually sent (e.g.
    that untrusted document content never leaks into the system prompt).
    """

    def __init__(self, response: LLMResponse) -> None:
        self._response = response
        self.calls: list[tuple[str, str]] = []

    def generate(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        self.calls.append((system_prompt, user_prompt))
        return self._response
