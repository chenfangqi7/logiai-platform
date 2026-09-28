"""Persist connector sync jobs and history.

Revision ID: 0006_sync_jobs
Revises: 0005_shipment_source
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0006_sync_jobs"
down_revision = "0005_shipment_source"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("sync_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("connector_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("total_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("result", sa.JSON().with_variant(JSONB(), "postgresql"), nullable=False),
        sa.Column("error_message", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_sync_jobs_tenant_id", "sync_jobs", ["tenant_id"])
    op.create_index("ix_sync_jobs_connector_id", "sync_jobs", ["connector_id"])
    op.create_index("uq_sync_jobs_active_connector", "sync_jobs", ["tenant_id", "connector_id"], unique=True,
        postgresql_where=sa.text("status IN ('PENDING', 'RUNNING')"),
        sqlite_where=sa.text("status IN ('PENDING', 'RUNNING')"))


def downgrade() -> None:
    op.drop_index("uq_sync_jobs_active_connector", table_name="sync_jobs")
    op.drop_index("ix_sync_jobs_connector_id", table_name="sync_jobs")
    op.drop_index("ix_sync_jobs_tenant_id", table_name="sync_jobs")
    op.drop_table("sync_jobs")
