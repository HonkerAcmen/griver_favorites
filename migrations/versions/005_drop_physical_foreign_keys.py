"""Drop physical foreign keys; reference integrity enforced in Service layer."""

from alembic import op

revision = "005_drop_physical_foreign_keys"
down_revision = "004_favorite_operation_log"
branch_labels = None
depends_on = None

_FK_DROPS = (
    ("griver_favorite_folder", "griver_favorite_folder_user_id_fkey"),
    ("griver_favorite_item", "griver_favorite_item_folder_id_fkey"),
    ("griver_favorite_item", "griver_favorite_item_user_id_fkey"),
    ("intelligence", "intelligence_user_id_fkey"),
)


def upgrade() -> None:
    for table, constraint in _FK_DROPS:
        op.execute(
            f'ALTER TABLE {table} DROP CONSTRAINT IF EXISTS "{constraint}"'
        )


def downgrade() -> None:
    op.create_foreign_key(
        "intelligence_user_id_fkey",
        "intelligence",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "griver_favorite_item_user_id_fkey",
        "griver_favorite_item",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "griver_favorite_item_folder_id_fkey",
        "griver_favorite_item",
        "griver_favorite_folder",
        ["folder_id"],
        ["id"],
    )
    op.create_foreign_key(
        "griver_favorite_folder_user_id_fkey",
        "griver_favorite_folder",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
