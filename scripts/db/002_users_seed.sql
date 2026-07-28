-- =============================================================================
-- 测试用户（可重复执行）
-- =============================================================================
-- 前置：alembic upgrade head
-- 执行：psql -d griver_favorites -f scripts/db/002_users_seed.sql
-- =============================================================================

BEGIN;

DELETE FROM users
WHERE id >= 'fa500001-0000-4000-8000-000000000000'::uuid
  AND id <  'fa500010-0000-4000-8000-000000000000'::uuid;

INSERT INTO users (id, username, email, is_deleted, created_at, updated_at)
VALUES
    ('fa500001-0001-4000-8000-000000000001', 'seed_alice', 'alice@seed.test', false, now(), now()),
    ('fa500001-0002-4000-8000-000000000002', 'seed_bob',   'bob@seed.test',   false, now(), now()),
    ('fa500001-0003-4000-8000-000000000003', 'seed_carol', 'carol@seed.test', false, now(), now()),
    ('fa500001-0004-4000-8000-000000000004', 'seed_dave',  'dave@seed.test',  false, now(), now()),
    ('fa500001-0005-4000-8000-000000000005', 'seed_eve',   'eve@seed.test',   false, now(), now())
ON CONFLICT (id) DO UPDATE SET
    username = EXCLUDED.username,
    email = EXCLUDED.email,
    is_deleted = EXCLUDED.is_deleted,
    updated_at = now();

COMMIT;
