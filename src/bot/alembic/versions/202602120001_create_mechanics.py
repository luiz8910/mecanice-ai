"""create mechanics

Revision ID: 202602120001
Revises: 
Create Date: 2026-02-12

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "202602120001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
	# Replicates: workshop_id bigserial NULL
	workshop_id_seq = sa.Sequence("mechanics_workshop_id_seq")
	op.execute(sa.schema.CreateSequence(workshop_id_seq))

	op.create_table(
		"mechanics",
		sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
		sa.Column("name", sa.Text(), nullable=False),
		sa.Column("whatsapp_phone_e164", sa.Text(), nullable=False),
		sa.Column("city", sa.Text(), nullable=False),
		sa.Column("state_uf", sa.CHAR(length=2), nullable=False),
		sa.Column(
			"status",
			sa.Text(),
			nullable=False,
			server_default=sa.text("'active'"),
		),
		sa.Column("address", sa.Text(), nullable=True),
		sa.Column("email", sa.Text(), nullable=True),
		sa.Column(
			"workshop_id",
			sa.BigInteger(),
			nullable=True,
			server_default=sa.text("nextval('mechanics_workshop_id_seq'::regclass)"),
		),
		sa.Column(
			"categories",
			postgresql.ARRAY(sa.Text()),
			nullable=False,
			server_default=sa.text("'{}'::text[]"),
		),
		sa.Column("notes", sa.Text(), nullable=True),
		sa.Column(
			"created_at",
			sa.DateTime(timezone=True),
			nullable=False,
			server_default=sa.text("now()"),
		),
		sa.Column(
			"updated_at",
			sa.DateTime(timezone=True),
			nullable=False,
			server_default=sa.text("now()"),
		),
		sa.CheckConstraint("status IN ('active', 'blocked')", name="mechanics_status_check"),
		sa.UniqueConstraint("whatsapp_phone_e164", name="mechanics_whatsapp_phone_e164_key"),
	)

	op.create_index("mechanics_status_idx", "mechanics", ["status"], unique=False)
	op.create_index(
		"mechanics_city_uf_idx",
		"mechanics",
		["city", "state_uf"],
		unique=False,
	)


def downgrade() -> None:
	op.drop_index("mechanics_city_uf_idx", table_name="mechanics")
	op.drop_index("mechanics_status_idx", table_name="mechanics")
	op.drop_table("mechanics")
	op.execute(sa.schema.DropSequence(sa.Sequence("mechanics_workshop_id_seq")))
