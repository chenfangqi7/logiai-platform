"""Encrypt credentials stored by existing connectors.

Revision ID: 0009_encrypt_connector_secrets
Revises: 0008_tracking_collections
"""

from alembic import op
import sqlalchemy as sa

from app.core.secrets import encrypt_config
from app.models.domain import Connector

revision = "0009_encrypt_connector_secrets"
down_revision = "0008_tracking_collections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    for connector_id, config in connection.execute(sa.select(Connector.id, Connector.config)):
        encrypted = encrypt_config(config or {})
        if encrypted != config:
            connection.execute(sa.update(Connector).where(Connector.id == connector_id).values(config=encrypted))


def downgrade() -> None:
    # Reverting schema must never put credentials back in plaintext.
    pass
