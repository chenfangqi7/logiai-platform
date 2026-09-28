"""Track the connector and source record for imported shipments.

Revision ID: 0005_shipment_source
Revises: 0004_ai_usage
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_shipment_source"
down_revision = "0004_ai_usage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("shipments", sa.Column("source_connector_id", sa.String(36)))
    op.add_column("shipments", sa.Column("source_external_id", sa.String(100)))
    op.add_column("shipments", sa.Column("source_updated_at", sa.DateTime(timezone=True)))
    op.add_column("shipments", sa.Column("last_synced_at", sa.DateTime(timezone=True)))
    op.create_index("ix_shipments_source_connector_id", "shipments", ["source_connector_id"])
    op.create_index("uq_shipments_tenant_source", "shipments", ["tenant_id", "source_connector_id", "source_external_id"], unique=True,
        postgresql_where=sa.text("source_connector_id IS NOT NULL AND source_external_id IS NOT NULL"),
        sqlite_where=sa.text("source_connector_id IS NOT NULL AND source_external_id IS NOT NULL"))


def downgrade() -> None:
    op.drop_index("uq_shipments_tenant_source", table_name="shipments")
    op.drop_index("ix_shipments_source_connector_id", table_name="shipments")
    op.drop_column("shipments", "last_synced_at")
    op.drop_column("shipments", "source_updated_at")
    op.drop_column("shipments", "source_external_id")
    op.drop_column("shipments", "source_connector_id")
