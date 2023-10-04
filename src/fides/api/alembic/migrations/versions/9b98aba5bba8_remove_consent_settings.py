"""remove_consent_settings

Revision ID: 9b98aba5bba8
Revises: 4cb3b5af4160
Create Date: 2023-10-03 20:26:12.492657

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "9b98aba5bba8"
down_revision = "4cb3b5af4160"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index("ix_consentsettings_id", table_name="consentsettings")
    op.drop_table("consentsettings")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "consentsettings",
        sa.Column("id", sa.VARCHAR(length=255), autoincrement=False, nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("tcf_enabled", sa.BOOLEAN(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint("id", name="consentsettings_pkey"),
    )
    op.create_index("ix_consentsettings_id", "consentsettings", ["id"], unique=False)
    # ### end Alembic commands ###
