from datetime import datetime
from uuid import uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

JsonType = JSON().with_variant(JSONB(), "postgresql")
EmbeddingType = Vector(1536).with_variant(JSON(), "sqlite")


class Identity:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenants.id"), nullable=False, index=True)


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Connector(Identity, Timestamped, Base):
    __tablename__ = "connectors"
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(2048))
    auth_type: Mapped[str] = mapped_column(String(30), nullable=False, default="none")
    config: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")


class FieldMapping(Identity, Timestamped, Base):
    __tablename__ = "field_mappings"
    __table_args__ = (UniqueConstraint("tenant_id", "connector_id", "entity_type", "source_field", name="uq_mapping_source"),)
    connector_id: Mapped[str] = mapped_column(String(36), ForeignKey("connectors.id"), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False, default="shipment")
    source_field: Mapped[str] = mapped_column(String(200), nullable=False)
    target_field: Mapped[str] = mapped_column(String(100), nullable=False)
    transform: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class CollectionMapping(Identity, Timestamped, Base):
    __tablename__ = "collection_mappings"
    __table_args__ = (UniqueConstraint("tenant_id", "connector_id", "target_entity", name="uq_collection_mapping_entity"),)
    connector_id: Mapped[str] = mapped_column(String(36), ForeignKey("connectors.id"), nullable=False, index=True)
    source_field: Mapped[str] = mapped_column(String(200), nullable=False)
    target_entity: Mapped[str] = mapped_column(String(40), nullable=False)
    fields: Mapped[list] = mapped_column(JsonType, nullable=False, default=list)


class SyncJob(Identity, Base):
    __tablename__ = "sync_jobs"
    __table_args__ = (
        Index("uq_sync_jobs_active_connector", "tenant_id", "connector_id", unique=True,
              postgresql_where=text("status IN ('PENDING', 'RUNNING')"),
              sqlite_where=text("status IN ('PENDING', 'RUNNING')")),
    )
    connector_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SyncIssue(Identity, Base):
    __tablename__ = "sync_issues"
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("sync_jobs.id"), nullable=False, index=True)
    connector_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    row_number: Mapped[int | None] = mapped_column(Integer)
    entity: Mapped[str] = mapped_column(String(40), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(100))
    level: Mapped[str] = mapped_column(String(10), nullable=False)
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Vehicle(Identity, Timestamped, Base):
    __tablename__ = "vehicles"
    __table_args__ = (UniqueConstraint("tenant_id", "plate_no", name="uq_vehicle_plate"),)
    external_id: Mapped[str | None] = mapped_column(String(100))
    plate_no: Mapped[str] = mapped_column(String(30), nullable=False)
    vehicle_type: Mapped[str | None] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    raw_data: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)


class Driver(Identity, Timestamped, Base):
    __tablename__ = "drivers"
    external_id: Mapped[str | None] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    raw_data: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)


class Route(Identity, Timestamped, Base):
    __tablename__ = "routes"
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    origin: Mapped[str] = mapped_column(String(200), nullable=False)
    destination: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")


class Shipment(Identity, Timestamped, Base):
    __tablename__ = "shipments"
    __table_args__ = (
        UniqueConstraint("tenant_id", "shipment_no", name="uq_shipment_no"),
        Index("uq_shipments_tenant_source", "tenant_id", "source_connector_id", "source_external_id", unique=True,
              postgresql_where=text("source_connector_id IS NOT NULL AND source_external_id IS NOT NULL"),
              sqlite_where=text("source_connector_id IS NOT NULL AND source_external_id IS NOT NULL")),
    )
    shipment_no: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(100))
    source_connector_id: Mapped[str | None] = mapped_column(String(36), index=True)
    source_external_id: Mapped[str | None] = mapped_column(String(100))
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="UNKNOWN")
    origin: Mapped[str | None] = mapped_column(String(200))
    destination: Mapped[str | None] = mapped_column(String(200))
    sender_name: Mapped[str | None] = mapped_column(String(100))
    receiver_name: Mapped[str | None] = mapped_column(String(100))
    planned_departure_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_departure_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    planned_arrival_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_arrival_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    latest_tracking_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    driver_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("drivers.id"))
    vehicle_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("vehicles.id"))
    route_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("routes.id"))
    raw_data: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)


class TrackingEvent(Identity, Base):
    __tablename__ = "tracking_events"
    __table_args__ = (Index("uq_tracking_source_event", "tenant_id", "shipment_id", "external_event_id", unique=True,
        postgresql_where=text("external_event_id IS NOT NULL"), sqlite_where=text("external_event_id IS NOT NULL")),)
    shipment_id: Mapped[str] = mapped_column(String(36), ForeignKey("shipments.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    external_event_id: Mapped[str | None] = mapped_column(String(100))
    location: Mapped[str | None] = mapped_column(String(200))
    longitude: Mapped[float | None] = mapped_column(Float)
    latitude: Mapped[float | None] = mapped_column(Float)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_data: Mapped[dict] = mapped_column(JsonType, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LogisticsException(Identity, Timestamped, Base):
    __tablename__ = "exceptions"
    __table_args__ = (UniqueConstraint("tenant_id", "shipment_id", "rule_code", name="uq_exception_rule"),)
    shipment_id: Mapped[str] = mapped_column(String(36), ForeignKey("shipments.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    rule_code: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    ai_analysis: Mapped[str | None] = mapped_column(Text)
    suggestion: Mapped[str | None] = mapped_column(Text)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AIConversation(Identity, Timestamped, Base):
    __tablename__ = "ai_conversations"
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)


class AIMessage(Identity, Base):
    __tablename__ = "ai_messages"
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("ai_conversations.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str | None] = mapped_column(String(50))
    model: Mapped[str | None] = mapped_column(String(100))
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AIUsage(Identity, Base):
    __tablename__ = "ai_usage"
    purpose: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(36))
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str | None] = mapped_column(String(100))
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class KnowledgeDocument(Identity, Timestamped, Base):
    __tablename__ = "knowledge_documents"
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(EmbeddingType)
    extra_metadata: Mapped[dict] = mapped_column("metadata", JsonType, nullable=False, default=dict)


class KnowledgeChunk(Identity, Base):
    __tablename__ = "knowledge_chunks"
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("knowledge_documents.id"), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(EmbeddingType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


Index("ix_exception_tenant_status", LogisticsException.tenant_id, LogisticsException.status)
Index("ix_shipment_tenant_status", Shipment.tenant_id, Shipment.status)
