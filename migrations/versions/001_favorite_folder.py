
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import func

revision = "001_favorite_folder"
down_revision = None
branch_labels = None
depends_on = None

def upgrade()->None:
        op.create_table(
                "griver_favorite_folder",
                sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
                sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
                sa.Column("name", sa.String(100), nullable=False),
                sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.text("false")),
                sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=func.now()),
                sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=func.now()),
                sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE")
        )

        op.execute(
                """
                        CREATE UNIQUE INDEX IF NOT EXISTS uq_griver_favorite_folder_user_name_active
                                ON griver_favorite_folder (user_id, name)
                                WHERE is_deleted = false;
                """
        )

        op.execute(
                """
                        CREATE INDEX IF NOT EXISTS idx_griver_favorite_folder_user_list
                                ON griver_favorite_folder (user_id, is_deleted, updated_at DESC);

                """
        )

        op.create_table(
                "griver_favorite_item",
                sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,server_default=sa.text("gen_random_uuid()")),
                sa.Column("folder_id", postgresql.UUID(as_uuid=True), nullable=False),
                sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
                sa.Column("target_type", sa.String(50), nullable=False),
                sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
                sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.text("false")),
                sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default= func.now()),
                sa.ForeignKeyConstraint(["folder_id"], ["griver_favorite_folder.id"]),
                sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE")
        )




        op.execute(
                """
                        CREATE UNIQUE INDEX IF NOT EXISTS uq_griver_favorite_item_user_target_active
                            ON griver_favorite_item (user_id, target_type, target_id)
                            WHERE is_deleted = false;

                """
        )

        op.execute(
                """
                        CREATE INDEX IF NOT EXISTS idx_griver_favorite_item_folder
                                ON griver_favorite_item (folder_id, is_deleted);
                """
        )


def downgrade():
        op.execute(
                "DROP INDEX IF EXISTS idx_griver_favorite_item_folder"
        )

        op.execute(
                "DROP INDEX IF EXISTS uq_griver_favorite_item_user_target_active"
        )

        op.drop_table("griver_favorite_item")

        op.execute(
                "DROP INDEX IF EXISTS idx_griver_favorite_folder_user_list"
        )

        op.execute(
                "DROP INDEX IF EXISTS uq_griver_favorite_folder_user_name_active"
        )

        op.drop_table("griver_favorite_folder")
