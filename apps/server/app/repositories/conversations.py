from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import AIConversation, AIMessage


class ConversationRepository:
    def __init__(self, session: AsyncSession, tenant_id: str, user_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.user_id = user_id

    async def list(self) -> list[AIConversation]:
        return list((await self.session.scalars(select(AIConversation).where(AIConversation.tenant_id == self.tenant_id, AIConversation.user_id == self.user_id).order_by(AIConversation.updated_at.desc()).limit(50))).all())

    async def get(self, conversation_id: str) -> AIConversation | None:
        return await self.session.scalar(select(AIConversation).where(AIConversation.id == conversation_id, AIConversation.tenant_id == self.tenant_id, AIConversation.user_id == self.user_id))

    async def messages(self, conversation_id: str) -> list[AIMessage]:
        return list((await self.session.scalars(select(AIMessage).where(AIMessage.conversation_id == conversation_id, AIMessage.tenant_id == self.tenant_id).order_by(AIMessage.created_at, AIMessage.id))).all())
