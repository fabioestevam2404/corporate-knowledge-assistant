from cka.domain.llm_provider import LLMResponse
from cka.infrastructure.llm.fake_llm_provider import FakeLLMProvider


def test_returns_configured_response() -> None:
    provider = FakeLLMProvider(LLMResponse(answer="canned", citations=["c1"]))

    response = provider.generate("system", "user")

    assert response.answer == "canned"
    assert response.citations == ["c1"]


def test_records_every_call() -> None:
    provider = FakeLLMProvider(LLMResponse(answer="a", citations=[]))

    provider.generate("sys-1", "user-1")
    provider.generate("sys-2", "user-2")

    assert provider.calls == [("sys-1", "user-1"), ("sys-2", "user-2")]
