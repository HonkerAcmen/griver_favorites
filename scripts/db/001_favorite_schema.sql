CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS griver_favorite_folder (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name       VARCHAR(100) NOT NULL,
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_griver_favorite_folder_user_name_active
    ON griver_favorite_folder (user_id, name)
    WHERE is_deleted = false;

CREATE INDEX IF NOT EXISTS idx_griver_favorite_folder_user_list
    ON griver_favorite_folder (user_id, is_deleted, updated_at DESC);


-- item表
CREATE TABLE IF NOT EXISTS griver_favorite_item (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    folder_id   UUID NOT NULL REFERENCES griver_favorite_folder(id),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    target_type VARCHAR(50) NOT NULL,
    target_id   UUID NOT NULL,
    is_deleted  BOOLEAN NOT NULL DEFAULT false,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_griver_favorite_item_user_target_active
    ON griver_favorite_item (user_id, target_type, target_id)
    WHERE is_deleted = false;

CREATE INDEX IF NOT EXISTS idx_griver_favorite_item_folder
    ON griver_favorite_item (folder_id, is_deleted);