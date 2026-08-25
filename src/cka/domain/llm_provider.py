from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMResponse:
    answer: str
    citations: list[str]


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> LLMResponse: ...
