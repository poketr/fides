"""create privacy declarations table

Revision ID: 48d9caacebd4
Revises: 8342453518cc
Create Date: 2023-04-20 20:35:05.377471

"""
import json
import uuid
from collections import defaultdict

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "48d9caacebd4"
down_revision = "8342453518cc"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "privacydeclaration",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("egress", sa.JSON(), nullable=True),
        sa.Column("ingress", sa.JSON(), nullable=True),
        sa.Column("data_use", sa.String(), nullable=False),
        sa.Column("data_categories", sa.ARRAY(sa.String()), nullable=True),
        sa.Column("data_qualifier", sa.String(), nullable=True),
        sa.Column("data_subjects", sa.ARRAY(sa.String()), nullable=True),
        sa.Column("dataset_references", sa.ARRAY(sa.String()), nullable=True),
        sa.Column("system_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["system_id"],
            ["ctl_systems.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_privacydeclaration_data_use"),
        "privacydeclaration",
        ["data_use"],
        unique=False,
    )
    op.create_index(
        op.f("ix_privacydeclaration_id"), "privacydeclaration", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_privacydeclaration_name"), "privacydeclaration", ["name"], unique=False
    )
    op.create_index(
        op.f("ix_privacydeclaration_system_id"),
        "privacydeclaration",
        ["system_id"],
        unique=False,
    )

    # Data migration

    bind = op.get_bind()
    existing_declarations = bind.execute(
        text("SELECT id, privacy_declarations FROM ctl_systems;")
    )
    for row in existing_declarations:
        system_id = row["id"]
        old_privacy_declarations = row["privacy_declarations"]
        for privacy_declaration in old_privacy_declarations:
            new_privacy_declaration_id: str = "pri_" + str(uuid.uuid4())
            new_data = {
                **privacy_declaration,
                "system_id": system_id,
                "id": new_privacy_declaration_id,
            }

            insert_privacy_declarations_query = text(
                "INSERT INTO privacydeclaration (id, name, data_categories, data_qualifier, data_subjects, dataset_references, egress, ingress, system_id, data_use) "
                "VALUES (:id, :name, :data_categories, :data_qualifier, :data_subjects, :dataset_references, :egress, :ingress, :system_id, :data_use)"
            )

            bind.execute(
                insert_privacy_declarations_query,
                new_data,
            )

    op.drop_column("ctl_systems", "privacy_declarations")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "ctl_systems",
        sa.Column(
            "privacy_declarations",
            postgresql.JSON(astext_type=sa.Text()),
            autoincrement=False,
            nullable=True,
        ),
    )

    # Data migration

    bind = op.get_bind()
    existing_declarations = bind.execute(
        text(
            "SELECT id, name, data_categories, data_qualifier, data_subjects, dataset_references, egress, ingress, system_id, data_use FROM privacydeclaration;"
        )
    )
    pds_by_system = defaultdict(list)
    for row in existing_declarations:
        system_id = row["system_id"]
        privacy_declaration = {
            "name": row["name"],
            "data_categories": row["data_categories"],
            "data_qualifier": row["data_qualifier"],
            "data_subjects": row["data_subjects"],
            "dataset_references": row["dataset_references"],
            "egress": row["egress"],
            "ingress": row["ingress"],
            "data_use": row["data_use"],
        }
        pds_by_system[system_id].append(privacy_declaration)

    for system_id, pds in pds_by_system.items():
        privacy_declarations = json.dumps(pds)
        update_systems_query = text(
            "update ctl_systems set privacy_declarations = :privacy_declarations where id = :system_id;"
        )

        bind.execute(
            update_systems_query,
            {"system_id": system_id, "privacy_declarations": privacy_declarations},
        )

    op.drop_index(
        op.f("ix_privacydeclaration_system_id"), table_name="privacydeclaration"
    )
    op.drop_index(op.f("ix_privacydeclaration_name"), table_name="privacydeclaration")
    op.drop_index(op.f("ix_privacydeclaration_id"), table_name="privacydeclaration")
    op.drop_index(
        op.f("ix_privacydeclaration_data_use"), table_name="privacydeclaration"
    )
    op.drop_table("privacydeclaration")
    # ### end Alembic commands ###
