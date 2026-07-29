import sqlalchemy as sa
from alembic import op
from sqlalchemy import ForeignKey, String, Boolean
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.sql import func

revision = "003_intelligence"
down_revision = "002_favorite_folder"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "intelligence",
        sa.Column(
            "id",
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=func.gen_random_uuid(),
        ),
        sa.Column(
            "user_id",
            pg.UUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", String(255), nullable=False),
        sa.Column(
            "is_deleted", Boolean, nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )

    op.execute("""
            CREATE INDEX idx_intelligence_user_active ON intelligence (user_id, is_deleted);
        """)

    op.execute("""
            CREATE INDEX idx_intelligence_title ON intelligence(title);
        """)


def downgrade() -> None:
    op.drop_index("idx_intelligence_title", "intelligence", if_exists=True)
    op.drop_index("idx_intelligence_user_active", "intelligence", if_exists=True)
    op.drop_table("intelligence")
