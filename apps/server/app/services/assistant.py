import json
import re
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm.openai_compatible import OpenAICompatibleProvider
from app.ai.tools.logistics import LogisticsTools
from app.core.config import get_settings
from app.models.domain import AIConversation, AIMessage, AIUsage
from app.repositories.conversations import ConversationRepository
from app.services.common import serialize_model
from app.services.knowledge import KnowledgeService


class AssistantService:
    def __init__(self, session: AsyncSession, tenant_id: str, user_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.repo = ConversationRepository(session, tenant_id, user_id)
        self.tools = LogisticsTools(session, tenant_id)

    async def evidence(self, question: str) -> tuple[str, dict, str]:
        shipment_number = re.search(r"(?<![A-Za-z0-9])(?:DEMO|MOCK|YD)[A-Za-z0-9-]{3,}", question, re.IGNORECASE)
        if shipment_number:
            matches = await self.tools.search_shipments(shipment_number.group(), 5)
            if not matches["items"]:
                return "shipment", matches, "未找到该运单，现有数据不足以分析。"
            detail = await self.tools.get_shipment(matches["items"][0]["id"])
            if detail is None:
                return "shipment", matches, "未找到该运单，现有数据不足以分析。"
            evidence = {"shipment_no": detail["shipment_no"], "status": detail["status"],
                "origin": detail["origin"], "destination": detail["destination"],
                "tracking_events": detail["tracking_events"][-5:], "exceptions": detail["exceptions"]}
            text = f"运单 {detail['shipment_no']} 当前状态为 {detail['status']}，从 {detail['origin']} 发往 {detail['destination']}。"
            if detail["exceptions"]:
                text += f" 检测到 {len(detail['exceptions'])} 条异常：" + "；".join(item["reason"] for item in detail["exceptions"][:3])
            return "shipment", evidence, text
        if "线路" in question or "路线" in question:
            ranking = await self.tools.dashboard.route_ranking()
            destination = next((entry["route_name"].split("→")[-1] for entry in ranking if entry["route_name"].split("→")[-1] in question), "")
            if not destination:
                return "route", {"ranking": ranking}, "请提供具体线路或终点；现有问题不足以定位一条线路。"
            evidence = await self.tools.get_route_exception_statistics(destination)
            if evidence is None:
                return "route", {}, "该线路目前没有可分析的异常数据。"
            types = "、".join(f"{item['type']} {item['count']} 条" for item in evidence["today_types"])
            text = f"{evidence['route_name']} 当前有 {evidence['exception_count']} 条未处理异常。今日类型分布：{types or '暂无今日异常'}。建议先核实高频异常的原因。"
            return "route", evidence, text
        if "高风险" in question or "优先" in question or "人工" in question:
            evidence = await self.tools.get_exceptions(level="HIGH", today="今天" in question, limit=10)
            text = f"共找到 {evidence['total']} 条高风险异常。" + (" 优先处理：" + "；".join(item["reason"] for item in evidence["items"][:5]) if evidence["items"] else " 当前无高风险异常。")
            return "priority", evidence, text
        stats = await self.tools.get_exception_statistics(today=True)
        evidence = {"statistics": stats, "high_risk": await self.tools.get_exceptions(level="HIGH", today=True, limit=5)}
        if stats["exception_count"] == 0:
            return "today", evidence, "今天尚未检测到异常运单。"
        text = f"今天有 {stats['shipment_count']} 票异常运单，共 {stats['exception_count']} 条异常，其中 {stats['high_risk_count']} 条高风险。"
        if "分析" in question:
            text += " 建议优先处理高风险异常，并核查延误和轨迹更新。"
        return "today", evidence, text

    async def chat(self, question: str, conversation_id: str | None = None) -> dict:
        conversation = await self.repo.get(conversation_id) if conversation_id else None
        if conversation_id and conversation is None:
            raise ValueError("Conversation not found")
        if conversation is None:
            conversation = AIConversation(tenant_id=self.tenant_id, user_id=self.user_id, title=question[:80])
            self.session.add(conversation)
            await self.session.flush()
        kind, grounding, answer = await self.evidence(question)
        knowledge = [item for item in await KnowledgeService(self.session, self.tenant_id).search(question) if item["score"] >= 0.15]
        if knowledge:
            grounding["knowledge"] = knowledge
            if any(word in question for word in ("怎么处理", "如何处理", "SOP", "建议")):
                answer += f" 参考知识库：{knowledge[0]['content'][:180]}"
        provider_name, model, input_tokens, output_tokens, cost = "rules", None, 0, 0, 0.0
        settings = get_settings()
        if settings.llm_api_key and settings.llm_model and grounding:
            try:
                generated = await OpenAICompatibleProvider().generate(
                    "你是物流运营助手。只允许依据给出的结构化数据回答；缺少证据时明确说明数据不足。不要编造运单、时间或原因。",
                    json.dumps({"question": question, "evidence": grounding}, ensure_ascii=False, default=str),
                )
                answer = generated.text
                provider_name, model = generated.provider, generated.model
                input_tokens, output_tokens, cost = generated.input_tokens, generated.output_tokens, generated.cost
            except (httpx.HTTPError, ValueError, KeyError, IndexError):
                pass  # The grounded deterministic answer remains available.
        message_time = datetime.now(timezone.utc)
        self.session.add_all([
            AIMessage(tenant_id=self.tenant_id, conversation_id=conversation.id, role="user", content=question,
                input_tokens=0, output_tokens=0, cost=0, created_at=message_time),
            AIMessage(tenant_id=self.tenant_id, conversation_id=conversation.id, role="assistant", content=answer,
                provider=provider_name, model=model, input_tokens=input_tokens, output_tokens=output_tokens, cost=cost,
                created_at=message_time + timedelta(microseconds=1)),
        ])
        self.session.add(AIUsage(tenant_id=self.tenant_id, purpose="chat", entity_id=conversation.id,
            provider=provider_name, model=model, input_tokens=input_tokens, output_tokens=output_tokens, cost=cost))
        await self.session.commit()
        return {"conversation_id": conversation.id, "answer": answer, "provider": provider_name, "grounding": grounding}

    async def conversations(self) -> list[dict]:
        return [serialize_model(item) for item in await self.repo.list()]

    async def conversation(self, conversation_id: str) -> dict | None:
        item = await self.repo.get(conversation_id)
        if item is None:
            return None
        return {**serialize_model(item), "messages": [serialize_model(message) for message in await self.repo.messages(conversation_id)]}
