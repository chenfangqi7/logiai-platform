from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import KnowledgeChunk, KnowledgeDocument


class KnowledgeRepository:
    def __init__(self, session: AsyncSession, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id

    async def list(self) -> list[KnowledgeDocument]:
        return list((await self.session.scalars(select(KnowledgeDocument).where(KnowledgeDocument.tenant_id == self.tenant_id).order_by(KnowledgeDocument.created_at.desc()).limit(100))).all())

    async def get(self, document_id: str) -> KnowledgeDocument | None:
        return await self.session.scalar(select(KnowledgeDocument).where(KnowledgeDocument.tenant_id == self.tenant_id, KnowledgeDocument.id == document_id))

    async def chunks(self, document_id: str) -> list[KnowledgeChunk]:
        return list((await self.session.scalars(select(KnowledgeChunk).where(KnowledgeChunk.tenant_id == self.tenant_id, KnowledgeChunk.document_id == document_id))).all())

    async def search(self, vector: list[float], limit: int) -> list[tuple[KnowledgeChunk, float]]:
        if self.session.bind and self.session.bind.dialect.name == "postgresql":
            distance = KnowledgeChunk.embedding.cosine_distance(vector)
            rows = (await self.session.execute(select(KnowledgeChunk, distance.label("distance"))
                .where(KnowledgeChunk.tenant_id == self.tenant_id).order_by(distance).limit(limit))).all()
            return [(item, 1.0 - float(distance or 0)) for item, distance in rows]
        chunks = list((await self.session.scalars(select(KnowledgeChunk).where(KnowledgeChunk.tenant_id == self.tenant_id).limit(500))).all())
        scored = [(item, sum(a * b for a, b in zip(item.embedding, vector))) for item in chunks]
        return sorted(scored, key=lambda pair: pair[1], reverse=True)[:limit]
