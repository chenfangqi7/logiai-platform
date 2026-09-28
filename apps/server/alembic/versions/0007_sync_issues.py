"""Persist structured sync warnings and errors.

Revision ID: 0007_sync_issues
Revises: 0006_sync_jobs
"""

from alembic import op
import sqlalchemy as sa

revision = "0007_sync_issues"
down_revision = "0006_sync_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("sync_issues",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("sync_jobs.id"), nullable=False),
        sa.Column("connector_id", sa.String(36), nullable=False),
        sa.Column("row_number", sa.Integer()),
        sa.Column("entity", sa.String(40), nullable=False),
        sa.Column("external_id", sa.String(100)),
        sa.Column("level", sa.String(10), nullable=False),
        sa.Column("code", sa.String(60), nullable=False),
        sa.Column("message", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_sync_issues_tenant_id", "sync_issues", ["tenant_id"])
    op.create_index("ix_sync_issues_job_id", "sync_issues", ["job_id"])
    op.create_index("ix_sync_issues_connector_id", "sync_issues", ["connector_id"])


def downgrade() -> None:
    op.drop_index("ix_sync_issues_connector_id", table_name="sync_issues")
    op.drop_index("ix_sync_issues_job_id", table_name="sync_issues")
    op.drop_index("ix_sync_issues_tenant_id", table_name="sync_issues")
    op.drop_table("sync_issues")
