from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.rest import RestApiConnector, validate_connector_url
from app.models.domain import Connector, FieldMapping
from app.repositories.connector import ConnectorRepository
from app.schemas.connector import ConnectorInput, ConnectorOutput, MappingInput

SECRET_KEYS = {"token", "api_key", "header_value", "secret", "password", "webhook_secret"}
SAFE_CONFIG_KEYS = {"items_path", "header_name"}
MAPPING_TARGETS = {
    "shipment_no", "external_id", "status", "origin", "destination", "sender_name", "receiver_name",
    "planned_departure_time", "actual_departure_time", "planned_arrival_time", "actual_arrival_time",
    "latest_tracking_time", "signed_at", "driver_external_id", "vehicle_plate_no", "route_name",
}


def connector_output(item: Connector) -> ConnectorOutput:
    return ConnectorOutput(
        id=item.id, tenant_id=item.tenant_id, name=item.name, type=item.type,
        base_url=item.base_url, auth_type=item.auth_type, status=item.status,
        config={key: value for key, value in item.config.items() if key in SAFE_CONFIG_KEYS},
    )


class ConnectorService:
    def __init__(self, session: AsyncSession, tenant_id: str) -> None:
        self.session = session
        self.repo = ConnectorRepository(session, tenant_id)
        self.tenant_id = tenant_id

    async def create(self, payload: ConnectorInput) -> Connector:
        if payload.type == "rest":
            if not payload.base_url:
                raise ValueError("REST connector requires base_url")
            validate_connector_url(payload.base_url)
        if payload.type == "webhook" and not payload.config.get("webhook_secret"):
            raise ValueError("Webhook connector requires webhook_secret")
        item = Connector(tenant_id=self.tenant_id, **payload.model_dump())
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def update(self, item: Connector, payload: ConnectorInput) -> Connector:
        if payload.type == "rest":
            if not payload.base_url:
                raise ValueError("REST connector requires base_url")
            validate_connector_url(payload.base_url)
        if payload.type == "webhook" and not (payload.config.get("webhook_secret") or item.config.get("webhook_secret")):
            raise ValueError("Webhook connector requires webhook_secret")
        for key, value in payload.model_dump().items():
            if key == "config" and not value:
                continue  # Omitted secrets are preserved when editing a connector.
            setattr(item, key, value)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def delete(self, item: Connector) -> None:
        mappings = await self.repo.mappings(item.id)
        for mapping in mappings:
            await self.session.delete(mapping)
        await self.session.delete(item)
        await self.session.commit()

    async def replace_mappings(self, connector_id: str, inputs: list[MappingInput]) -> list[FieldMapping]:
        if await self.repo.get(connector_id) is None:
            raise ValueError("Connector not found")
        if len({item.source_field for item in inputs}) != len(inputs) or len({item.target_field for item in inputs}) != len(inputs):
            raise ValueError("Duplicate source or target fields")
        if any(item.target_field not in MAPPING_TARGETS for item in inputs):
            raise ValueError("Unsupported mapping target")
        if "shipment_no" not in {item.target_field for item in inputs}:
            raise ValueError("shipment_no mapping is required")
        for old in await self.repo.mappings(connector_id):
            await self.session.delete(old)
        await self.session.flush()
        result = [FieldMapping(tenant_id=self.tenant_id, connector_id=connector_id, entity_type="shipment", **item.model_dump()) for item in inputs]
        self.session.add_all(result)
        await self.session.commit()
        return result

    async def fetch(self, item: Connector, sample: bool = False) -> list[dict]:
        if item.type != "rest" or not item.base_url:
            raise ValueError("This connector does not support fetching")
        adapter = RestApiConnector(item.base_url, item.config, item.auth_type)
        return await (adapter.fetch_sample() if sample else adapter.fetch_data())
