import pytest

from cka.core.config import get_settings
from cka.infrastructure.llm.anthropic_provider import AnthropicProvider

pytestmark = pytest.mark.skipif(
    not get_settings().anthropic_api_key,
    reason="ANTHROPIC_API_KEY not set in .env — real-generation test skipped, not faked",
)


def test_anthropic_provider_returns_structured_grounded_answer() -> None:
    settings = get_settings()
    provider = AnthropicProvider(
        api_key=settings.anthropic_api_key,  # type: ignore[arg-type]
        model=settings.anthropic_model,
        max_tokens=settings.llm_max_tokens,
    )
    system_prompt = (
        "You are a test assistant. Answer only from the evidence below, and always "
        "call provide_answer citing the CHUNK_ID you used."
    )
    user_prompt = (
        "<UNTRUSTED_DOCUMENTS>\n"
        "SOURCE_ID: SRC-TEST\nDOCUMENT_ID: doc-test\nPAGE: N/A\nCHUNK_ID: chunk-test\n\n"
        "CONTENT:\nThe test policy allows remote work up to three days per week.\n"
        "</UNTRUSTED_DOCUMENTS>\n\n"
        "<USER_QUERY>\nHow many days per week can I work remotely?\n</USER_QUERY>"
    )

    response = provider.generate(system_prompt, user_prompt)

    assert "three" in response.answer.lower() or "3" in response.answer
    assert "chunk-test" in response.citations


def test_anthropic_provider_abstains_style_response_when_asked_out_of_scope() -> None:
    settings = get_settings()
    provider = AnthropicProvider(
        api_key=settings.anthropic_api_key,  # type: ignore[arg-type]
        model=settings.anthropic_model,
        max_tokens=settings.llm_max_tokens,
    )
    system_prompt = (
        "You are a test assistant. Answer only from the evidence below. If the "
        "evidence does not answer the question, say so explicitly and cite nothing. "
        "Always call provide_answer."
    )
    user_prompt = (
        "<UNTRUSTED_DOCUMENTS>\n"
        "SOURCE_ID: SRC-TEST\nDOCUMENT_ID: doc-test\nPAGE: N/A\nCHUNK_ID: chunk-test\n\n"
        "CONTENT:\nThe test policy allows remote work up to three days per week.\n"
        "</UNTRUSTED_DOCUMENTS>\n\n"
        "<USER_QUERY>\nWhat was the company's revenue in 1999?\n</USER_QUERY>"
    )

    response = provider.generate(system_prompt, user_prompt)

    assert response.citations == []
