"""adds UserRegistration table

Revision ID: 8f1a19465239
Revises: 6b9885e68cbb
Create Date: 2022-10-29 00:11:51.449359

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8f1a19465239'
down_revision = '6b9885e68cbb'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('userregistration',
    sa.Column('id', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('user_email', sa.String(), nullable=True),
    sa.Column('user_organization', sa.String(), nullable=True),
    sa.Column('analytics_id', sa.String(), nullable=False),
    sa.Column('opt_in', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('analytics_id')
    )
    op.create_index(op.f('ix_userregistration_id'), 'userregistration', ['id'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_userregistration_id'), table_name='userregistration')
    op.drop_table('userregistration')
    # ### end Alembic commands ###
