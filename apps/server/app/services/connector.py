from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.rest import RestApiConnector
from app.core.secrets import contains_secret, decrypt_config, encrypt_config, merge_config, redact_config
from app.models.domain import CollectionMapping, Connector, FieldMapping
from app.repositories.connector import ConnectorRepository
from app.schemas.connector import ConnectorInput, ConnectorOutput, MappingInput, TrackingMappingInput
from app.services.mapping import validate_transform

SECRET_KEYS = {"token", "api_key", "header_value", "secret", "password", "webhook_secret"}
SAFE_CONFIG_KEYS = {"items_path", "header_name", "method", "timeout_seconds", "query_params", "request_body", "pagination", "sync_mode", "incremental_field", "incremental_param", "incremental_location", "last_sync_value"}
MAPPING_TARGETS = {
    "shipment_no", "external_id", "status", "origin", "destination", "sender_name", "receiver_name",
    "planned_departure_time", "actual_departure_time", "planned_arrival_time", "actual_arrival_time",
    "latest_tracking_time", "signed_at", "driver_external_id", "vehicle_plate_no", "route_name",
}


def connector_output(item: Connector) -> ConnectorOutput:
    public_config = redact_config({key: value for key, value in item.config.items() if key in SAFE_CONFIG_KEYS})
    return ConnectorOutput(
        id=item.id, tenant_id=item.tenant_id, name=item.name, type=item.type,
        base_url=item.base_url, auth_type=item.auth_type, status=item.status,
        config=public_config, credential_configured=contains_secret(item.config),
        capabilities={"read": ["shipment", "tracking"], "write": []},
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
            RestApiConnector(payload.base_url, payload.config, payload.auth_type)._headers()
        if payload.type == "webhook" and not payload.config.get("webhook_secret"):
            raise ValueError("Webhook connector requires webhook_secret")
        item = Connector(tenant_id=self.tenant_id, **(payload.model_dump() | {"config": encrypt_config(payload.config)}))
        self.session.add(item)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def update(self, item: Connector, payload: ConnectorInput) -> Connector:
        config = merge_config(decrypt_config(item.config), payload.config)
        if payload.type == "rest":
            if not payload.base_url:
                raise ValueError("REST connector requires base_url")
            RestApiConnector(payload.base_url, config, payload.auth_type)._headers()
        if payload.type == "webhook" and not config.get("webhook_secret"):
            raise ValueError("Webhook connector requires webhook_secret")
        for key, value in payload.model_dump().items():
            setattr(item, key, encrypt_config(config) if key == "config" else value)
        await self.session.commit()
        await self.session.refresh(item)
        return item

    async def delete(self, item: Connector) -> None:
        mappings = await self.repo.mappings(item.id)
        for mapping in mappings:
            await self.session.delete(mapping)
        tracking_mapping = await self.repo.tracking_mapping(item.id)
        if tracking_mapping:
            await self.session.delete(tracking_mapping)
        await self.session.delete(item)
        await self.session.commit()

    @staticmethod
    def validate_mappings(inputs: list[MappingInput]) -> None:
        if len({item.source_field for item in inputs}) != len(inputs) or len({item.target_field for item in inputs}) != len(inputs):
            raise ValueError("Duplicate source or target fields")
        if any(item.target_field not in MAPPING_TARGETS for item in inputs):
            raise ValueError("Unsupported mapping target")
        if "shipment_no" not in {item.target_field for item in inputs}:
            raise ValueError("shipment_no mapping is required")
        for item in inputs:
            if item.target_field == "shipment_no" and not item.required:
                raise ValueError("shipment_no mapping must be required")
            validate_transform(item.target_field, item.transform)

    async def replace_mappings(self, connector_id: str, inputs: list[MappingInput]) -> list[FieldMapping]:
        if await self.repo.get(connector_id) is None:
            raise ValueError("Connector not found")
        self.validate_mappings(inputs)
        for old in await self.repo.mappings(connector_id):
            await self.session.delete(old)
        await self.session.flush()
        result = [FieldMapping(tenant_id=self.tenant_id, connector_id=connector_id, entity_type="shipment", **item.model_dump()) for item in inputs]
        self.session.add_all(result)
        await self.session.commit()
        return result

    async def replace_tracking_mapping(self, connector_id: str, payload: TrackingMappingInput) -> CollectionMapping:
        if await self.repo.get(connector_id) is None:
            raise ValueError("Connector not found")
        if len({item.source_field for item in payload.fields}) != len(payload.fields) or len({item.target_field for item in payload.fields}) != len(payload.fields):
            raise ValueError("Duplicate tracking source or target fields")
        event_time = next((item for item in payload.fields if item.target_field == "event_time"), None)
        if event_time is None or not event_time.required:
            raise ValueError("event_time mapping must be required")
        for item in payload.fields:
            validate_transform(item.target_field, item.transform)
        mapping = await self.repo.tracking_mapping(connector_id)
        if mapping is None:
            mapping = CollectionMapping(tenant_id=self.tenant_id, connector_id=connector_id, target_entity="tracking_event")
            self.session.add(mapping)
        mapping.source_field = payload.source_field
        mapping.fields = [item.model_dump() for item in payload.fields]
        await self.session.commit()
        await self.session.refresh(mapping)
        return mapping

    async def fetch(self, item: Connector, sample: bool = False) -> list[dict]:
        if item.type != "rest" or not item.base_url:
            raise ValueError("This connector does not support fetching")
        adapter = RestApiConnector(item.base_url, decrypt_config(item.config), item.auth_type)
        return await (adapter.fetch_sample() if sample else adapter.fetch_data())

    async def test(self, item: Connector) -> dict:
        if item.type != "rest" or not item.base_url:
            raise ValueError("This connector does not support connection tests")
        adapter = RestApiConnector(item.base_url, decrypt_config(item.config), item.auth_type)
        await adapter.fetch_sample()
        return {"ok": True, "success": True, **adapter.last_response_meta}
