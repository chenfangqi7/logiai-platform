from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Generation:
    text: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0


class LLMProvider(Protocol):
    async def generate(self, system: str, user: str) -> Generation: ...
