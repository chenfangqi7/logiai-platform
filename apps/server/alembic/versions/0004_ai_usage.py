"""Track AI usage for exception analysis and chat.

Revision ID: 0004_ai_usage
Revises: 0003_knowledge_chunks
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_ai_usage"
down_revision = "0003_knowledge_chunks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("ai_usage",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("purpose", sa.String(50), nullable=False), sa.Column("entity_id", sa.String(36)),
        sa.Column("provider", sa.String(50), nullable=False), sa.Column("model", sa.String(100)),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("cost", sa.Numeric(12, 6), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_ai_usage_tenant_id", "ai_usage", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("ai_usage")
