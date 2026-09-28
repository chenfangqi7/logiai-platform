from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ConnectorInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type: Literal["rest", "webhook", "file"]
    base_url: str | None = None
    auth_type: Literal["none", "header", "bearer", "basic", "api_key_header", "custom_headers"] = "none"
    config: dict = Field(default_factory=dict)
    status: Literal["active", "disabled"] = "active"


class ConnectorOutput(BaseModel):
    id: str
    tenant_id: str
    name: str
    type: str
    base_url: str | None
    auth_type: str
    status: str
    config: dict
    credential_configured: bool = False
    capabilities: dict[str, list[str]] = Field(default_factory=lambda: {"read": ["shipment", "tracking"], "write": []})


class MappingInput(BaseModel):
    source_field: str = Field(min_length=1, max_length=200)
    target_field: str = Field(min_length=1, max_length=100)
    transform: dict = Field(default_factory=dict)
    required: bool = False


class MappingOutput(MappingInput):
    id: str
    connector_id: str
    entity_type: str


class MappingReplace(BaseModel):
    mappings: list[MappingInput] = Field(min_length=1, max_length=100)


class MappingPreviewInput(BaseModel):
    sample: dict
    mappings: list[MappingInput] = Field(min_length=1, max_length=100)


class CollectionFieldInput(BaseModel):
    source_field: str = Field(min_length=1, max_length=200)
    target_field: Literal["external_event_id", "event_type", "location", "event_time", "longitude", "latitude"]
    transform: dict = Field(default_factory=dict)
    required: bool = False


class TrackingMappingInput(BaseModel):
    source_field: str = Field(min_length=1, max_length=200)
    fields: list[CollectionFieldInput] = Field(min_length=1, max_length=20)


class TrackingMappingOutput(TrackingMappingInput):
    id: str
    connector_id: str
    target_entity: str


class ImportResult(BaseModel):
    imported: int
    updated: int
    rejected: int
    errors: list[str]
    exception_ids: list[str] = Field(default_factory=list)
    total: int = 0
    success: int = 0
    failed: int = 0
    drivers_created: int = 0
    vehicles_created: int = 0
    routes_created: int = 0
    tracking_events_created: int = 0
    warnings: list[str] = Field(default_factory=list)
    issues: list[dict] = Field(default_factory=list)
    checkpoint: str | None = None


class SyncJobOutput(BaseModel):
    id: str
    connector_id: str
    status: str
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    total_count: int
    success_count: int
    failed_count: int
    result: dict
    error_message: str | None


class SyncIssueOutput(BaseModel):
    id: str
    job_id: str
    row_number: int | None
    entity: str
    external_id: str | None
    level: str
    code: str
    message: str
    created_at: datetime
