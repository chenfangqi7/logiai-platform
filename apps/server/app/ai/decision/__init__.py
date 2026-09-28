from typing import Protocol


class DecisionProvider(Protocol):
    async def evaluate(self, input_data: dict, schema: dict) -> dict: ...


class RuleDecisionProvider:
    async def evaluate(self, input_data: dict, schema: dict) -> dict:
        return {"provider": "rules", "requires_human": input_data.get("level") in {"HIGH", "CRITICAL"}}


class LLMDecisionProvider:
    def __init__(self, llm) -> None:
        self.llm = llm

    async def evaluate(self, input_data: dict, schema: dict) -> dict:
        import json

        response = await self.llm.generate("Return only JSON matching the supplied schema.", json.dumps({"input": input_data, "schema": schema}, ensure_ascii=False))
        return json.loads(response.text)


class JevDecisionProvider:
    async def evaluate(self, input_data: dict, schema: dict) -> dict:
        raise NotImplementedError("Jev provider is reserved for a later integration")
