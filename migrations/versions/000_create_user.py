"""
Create user table

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import func


revision = "000_create_user"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
        op.create_table(
                "users",
                sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
                sa.Column("username", sa.String(64), nullable=False),
                sa.Column("email", sa.String(255), nullable=False),
                sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
                sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=func.now()),
                sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=func.now()),
                sa.UniqueConstraint("username", name="uq_users_username"),
                sa.UniqueConstraint("email", name="uq_users_email")
        )

        op.create_index(
                "idx_users_is_deleted",
                "users",
                ["is_deleted"]
        )



def downgrade() -> None:
        op.drop_index("idx_users_is_deleted", table_name="users")
        op.drop_table("users")