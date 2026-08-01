-- =============================================================================
-- griver_favorites 表结构参考（与 Alembic migration 对齐，v2.0）
-- =============================================================================
-- 说明：正式环境以 alembic upgrade head 为准；本文件供本地对照与手工建库参考。
-- item 唯一约束：folder 级 (folder_id, target_type, target_id)，允许跨收藏夹重复同一情报。
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- users 由 migration 000_create_user 创建，此处仅作参考
-- CREATE TABLE IF NOT EXISTS users (...);

CREATE TABLE IF NOT EXISTS intelligence (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL,
    title      VARCHAR(255) NOT NULL,
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_intelligence_user_active
    ON intelligence (user_id, is_deleted);

CREATE INDEX IF NOT EXISTS idx_intelligence_title
    ON intelligence (title);

CREATE TABLE IF NOT EXISTS griver_favorite_folder (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL,
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

CREATE TABLE IF NOT EXISTS griver_favorite_item (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    folder_id   UUID NOT NULL,
    user_id     UUID NOT NULL,
    target_type VARCHAR(50) NOT NULL,
    target_id   UUID NOT NULL,
    is_deleted  BOOLEAN NOT NULL DEFAULT false,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- v2.0：同一收藏夹内不可重复；跨收藏夹允许同一情报
CREATE UNIQUE INDEX IF NOT EXISTS uq_griver_favorite_item_folder_target_active
    ON griver_favorite_item (folder_id, target_type, target_id)
    WHERE is_deleted = false;

CREATE INDEX IF NOT EXISTS idx_griver_favorite_item_folder
    ON griver_favorite_item (folder_id, is_deleted);
