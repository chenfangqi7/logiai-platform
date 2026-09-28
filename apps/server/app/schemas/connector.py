from typing import Literal

from pydantic import BaseModel, Field


class ConnectorInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type: Literal["rest", "webhook", "file"]
    base_url: str | None = None
    auth_type: Literal["none", "header", "bearer"] = "none"
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


class ImportResult(BaseModel):
    imported: int
    updated: int
    rejected: int
    errors: list[str]
    exception_ids: list[str] = Field(default_factory=list)
