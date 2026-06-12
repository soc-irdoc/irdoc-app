"""Switch SSO from SAML to OIDC — replace SAML columns with tenant_id/client_id/client_secret.

Revision ID: 018
Revises: 017
Create Date: 2026-06-12
"""
import sqlalchemy as sa
from alembic import op

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade():
    # Drop SAML-specific columns
    with op.batch_alter_table("sso_configs") as batch_op:
        for col in ("provider", "idp_metadata_url", "entity_id", "sso_url",
                    "certificate", "attr_email", "attr_name", "attr_groups"):
            try:
                batch_op.drop_column(col)
            except Exception:
                pass  # Column may not exist if sso_configs table is fresh

    # Add OIDC columns
    op.add_column("sso_configs", sa.Column("tenant_id", sa.Text(), nullable=True))
    op.add_column("sso_configs", sa.Column("client_id", sa.Text(), nullable=True))
    op.add_column("sso_configs", sa.Column("client_secret", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("sso_configs", "client_secret")
    op.drop_column("sso_configs", "client_id")
    op.drop_column("sso_configs", "tenant_id")

    op.add_column("sso_configs", sa.Column("provider", sa.Text(), nullable=True, server_default="saml"))
    op.add_column("sso_configs", sa.Column("idp_metadata_url", sa.Text(), nullable=True))
    op.add_column("sso_configs", sa.Column("entity_id", sa.Text(), nullable=True))
    op.add_column("sso_configs", sa.Column("sso_url", sa.Text(), nullable=True))
    op.add_column("sso_configs", sa.Column("certificate", sa.Text(), nullable=True))
    op.add_column("sso_configs", sa.Column("attr_email", sa.Text(), nullable=True))
    op.add_column("sso_configs", sa.Column("attr_name", sa.Text(), nullable=True))
    op.add_column("sso_configs", sa.Column("attr_groups", sa.Text(), nullable=True))
