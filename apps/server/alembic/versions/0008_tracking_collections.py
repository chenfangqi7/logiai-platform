"""Configure tracking collections and retain source event identity.

Revision ID: 0008_tracking_collections
Revises: 0007_sync_issues
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0008_tracking_collections"
down_revision = "0007_sync_issues"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("collection_mappings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("connector_id", sa.String(36), sa.ForeignKey("connectors.id"), nullable=False),
        sa.Column("source_field", sa.String(200), nullable=False),
        sa.Column("target_entity", sa.String(40), nullable=False),
        sa.Column("fields", sa.JSON().with_variant(JSONB(), "postgresql"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("tenant_id", "connector_id", "target_entity", name="uq_collection_mapping_entity"))
    op.create_index("ix_collection_mappings_tenant_id", "collection_mappings", ["tenant_id"])
    op.create_index("ix_collection_mappings_connector_id", "collection_mappings", ["connector_id"])
    op.add_column("tracking_events", sa.Column("external_event_id", sa.String(100)))
    op.create_index("uq_tracking_source_event", "tracking_events", ["tenant_id", "shipment_id", "external_event_id"], unique=True,
        postgresql_where=sa.text("external_event_id IS NOT NULL"), sqlite_where=sa.text("external_event_id IS NOT NULL"))


def downgrade() -> None:
    op.drop_index("uq_tracking_source_event", table_name="tracking_events")
    op.drop_column("tracking_events", "external_event_id")
    op.drop_index("ix_collection_mappings_connector_id", table_name="collection_mappings")
    op.drop_index("ix_collection_mappings_tenant_id", table_name="collection_mappings")
    op.drop_table("collection_mappings")
