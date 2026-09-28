from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import Connector, FieldMapping


class ConnectorRepository:
    def __init__(self, session: AsyncSession, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id

    async def list(self) -> list[Connector]:
        return list((await self.session.scalars(select(Connector).where(Connector.tenant_id == self.tenant_id).order_by(Connector.created_at.desc()))).all())

    async def get(self, connector_id: str) -> Connector | None:
        return await self.session.scalar(select(Connector).where(Connector.tenant_id == self.tenant_id, Connector.id == connector_id))

    async def mappings(self, connector_id: str) -> list[FieldMapping]:
        return list((await self.session.scalars(select(FieldMapping).where(FieldMapping.tenant_id == self.tenant_id, FieldMapping.connector_id == connector_id, FieldMapping.entity_type == "shipment").order_by(FieldMapping.created_at))).all())
