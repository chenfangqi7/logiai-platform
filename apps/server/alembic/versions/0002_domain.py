"""Create connector, logistics, AI and knowledge tables.

Revision ID: 0002_domain
Revises: 0001_auth
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector

revision = "0002_domain"
down_revision = "0001_auth"
branch_labels = None
depends_on = None

json_type = sa.JSON().with_variant(JSONB(), "postgresql")
embedding_type = Vector(1536).with_variant(sa.JSON(), "sqlite")


def identity() -> list[sa.Column]:
    return [
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
    ]


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def create(name: str, *columns: sa.Column | sa.Constraint, updated: bool = True) -> None:
    op.create_table(name, *identity(), *columns, *(timestamps() if updated else [sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)]))
    op.create_index(f"ix_{name}_tenant_id", name, ["tenant_id"])


def upgrade() -> None:
    create("connectors",
        sa.Column("name", sa.String(200), nullable=False), sa.Column("type", sa.String(20), nullable=False),
        sa.Column("base_url", sa.String(2048)), sa.Column("auth_type", sa.String(30), nullable=False),
        sa.Column("config", json_type, nullable=False), sa.Column("status", sa.String(20), nullable=False))
    create("field_mappings",
        sa.Column("connector_id", sa.String(36), sa.ForeignKey("connectors.id"), nullable=False),
        sa.Column("entity_type", sa.String(30), nullable=False), sa.Column("source_field", sa.String(200), nullable=False),
        sa.Column("target_field", sa.String(100), nullable=False), sa.Column("transform", json_type, nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("tenant_id", "connector_id", "entity_type", "source_field", name="uq_mapping_source"))
    op.create_index("ix_field_mappings_connector_id", "field_mappings", ["connector_id"])
    create("vehicles",
        sa.Column("external_id", sa.String(100)), sa.Column("plate_no", sa.String(30), nullable=False),
        sa.Column("vehicle_type", sa.String(60)), sa.Column("status", sa.String(30), nullable=False),
        sa.Column("raw_data", json_type, nullable=False),
        sa.UniqueConstraint("tenant_id", "plate_no", name="uq_vehicle_plate"))
    create("drivers", sa.Column("external_id", sa.String(100)), sa.Column("name", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(40)), sa.Column("status", sa.String(30), nullable=False),
        sa.Column("raw_data", json_type, nullable=False))
    create("routes", sa.Column("name", sa.String(160), nullable=False), sa.Column("origin", sa.String(200), nullable=False),
        sa.Column("destination", sa.String(200), nullable=False), sa.Column("status", sa.String(30), nullable=False))
    create("shipments",
        sa.Column("shipment_no", sa.String(100), nullable=False), sa.Column("external_id", sa.String(100)),
        sa.Column("status", sa.String(30), nullable=False), sa.Column("origin", sa.String(200)),
        sa.Column("destination", sa.String(200)), sa.Column("sender_name", sa.String(100)),
        sa.Column("receiver_name", sa.String(100)),
        sa.Column("planned_departure_time", sa.DateTime(timezone=True)),
        sa.Column("actual_departure_time", sa.DateTime(timezone=True)),
        sa.Column("planned_arrival_time", sa.DateTime(timezone=True)),
        sa.Column("actual_arrival_time", sa.DateTime(timezone=True)),
        sa.Column("latest_tracking_time", sa.DateTime(timezone=True)),
        sa.Column("signed_at", sa.DateTime(timezone=True)),
        sa.Column("driver_id", sa.String(36), sa.ForeignKey("drivers.id")),
        sa.Column("vehicle_id", sa.String(36), sa.ForeignKey("vehicles.id")),
        sa.Column("route_id", sa.String(36), sa.ForeignKey("routes.id")),
        sa.Column("raw_data", json_type, nullable=False),
        sa.UniqueConstraint("tenant_id", "shipment_no", name="uq_shipment_no"))
    op.create_index("ix_shipments_shipment_no", "shipments", ["shipment_no"])
    op.create_index("ix_shipment_tenant_status", "shipments", ["tenant_id", "status"])
    create("tracking_events",
        sa.Column("shipment_id", sa.String(36), sa.ForeignKey("shipments.id"), nullable=False),
        sa.Column("event_type", sa.String(60), nullable=False), sa.Column("location", sa.String(200)),
        sa.Column("longitude", sa.Float()), sa.Column("latitude", sa.Float()),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_data", json_type, nullable=False), updated=False)
    op.create_index("ix_tracking_events_shipment_id", "tracking_events", ["shipment_id"])
    create("exceptions",
        sa.Column("shipment_id", sa.String(36), sa.ForeignKey("shipments.id"), nullable=False),
        sa.Column("type", sa.String(40), nullable=False), sa.Column("level", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False), sa.Column("rule_code", sa.String(50), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False), sa.Column("ai_analysis", sa.Text()),
        sa.Column("suggestion", sa.Text()), sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("tenant_id", "shipment_id", "rule_code", name="uq_exception_rule"))
    op.create_index("ix_exceptions_shipment_id", "exceptions", ["shipment_id"])
    op.create_index("ix_exception_tenant_status", "exceptions", ["tenant_id", "status"])
    create("ai_conversations", sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False))
    create("ai_messages", sa.Column("conversation_id", sa.String(36), sa.ForeignKey("ai_conversations.id"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False), sa.Column("content", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(50)), sa.Column("model", sa.String(100)),
        sa.Column("input_tokens", sa.Integer(), nullable=False), sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("cost", sa.Numeric(12, 6), nullable=False), updated=False)
    op.create_index("ix_ai_messages_conversation_id", "ai_messages", ["conversation_id"])
    create("knowledge_documents", sa.Column("title", sa.String(200), nullable=False),
        sa.Column("source_type", sa.String(20), nullable=False), sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", embedding_type), sa.Column("metadata", json_type, nullable=False))


def downgrade() -> None:
    for name in (
        "knowledge_documents", "ai_messages", "ai_conversations", "exceptions", "tracking_events",
        "shipments", "routes", "drivers", "vehicles", "field_mappings", "connectors",
    ):
        op.drop_table(name)
