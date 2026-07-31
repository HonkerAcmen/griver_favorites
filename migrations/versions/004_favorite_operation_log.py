import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.sql import func

revision = "004_favorite_operation_log"
down_revision = "003_intelligence"

branch_labels = None
depends_on = None


"""
favorite_operation_log
  id              UUID PK  DEFAULT gen_random_uuid()
  event_id        UUID UNIQUE NOT NULL    ← 幂等键，对应消息体 event_id
  user_id         UUID NOT NULL
  folder_id       UUID NOT NULL
  intelligence_id UUID NOT NULL
  action          VARCHAR(32) NOT NULL   ← 如 "favorite_add"
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()

"""


def upgrade() -> None:
    from sqlalchemy import String

    op.create_table(
        "favorite_operation_log",
        sa.Column(
            "id",
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=func.gen_random_uuid(),
        ),
        sa.Column("event_id", pg.UUID, nullable=False),
        sa.Column("user_id", pg.UUID, nullable=False),
        sa.Column("folder_id", pg.UUID, nullable=False),
        sa.Column("intelligence_id", pg.UUID, nullable=False),
        sa.Column("action", String(32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )
    op.create_index(
        "uq_favorite_operation_log_event_id",
        "favorite_operation_log",
        ["event_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_favorite_operation_log_event_id", "favorite_operation_log")
    op.drop_table("favorite_operation_log")