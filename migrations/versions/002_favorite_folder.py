
from alembic import op

revision = "002_favorite_folder"
down_revision = "001_favorite_folder"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "DROP INDEX IF EXISTS uq_griver_favorite_item_user_target_active"
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_griver_favorite_item_folder_target_active
            ON griver_favorite_item (folder_id, target_type, target_id)
            WHERE is_deleted = false
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP INDEX IF EXISTS uq_griver_favorite_item_folder_target_active"
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_griver_favorite_item_user_target_active
            ON griver_favorite_item (user_id, target_type, target_id)
            WHERE is_deleted = false
        """
    )
