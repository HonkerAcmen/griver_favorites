-- =============================================================================
-- 情报测试数据（可重复执行）
-- =============================================================================
-- 前置：alembic upgrade head；建议先执行 002_users_seed.sql
-- 执行：psql -d griver_favorites -f scripts/db/003_intelligence_seed.sql
--
-- ID 段：fa700000-0000-4000-8000-*
-- 每用户 15 条有效情报 + 1 条已软删（用于 R4 测试）
-- =============================================================================

BEGIN;

CREATE TABLE intelligence (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title      VARCHAR(255) NOT NULL,
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_intelligence_user_active
    ON intelligence (user_id, is_deleted);

CREATE INDEX IF NOT EXISTS idx_intelligence_title
    ON intelligence (title);

DELETE FROM intelligence
WHERE id >= 'fa700000-0000-4000-8000-000000000000'::uuid
  AND id <  'fa710000-0000-4000-8000-000000000000'::uuid;

-- 5 用户 × 15 条有效情报
INSERT INTO intelligence (id, user_id, title, is_deleted, created_at, updated_at)
SELECT
    ('fa700001-000' || u.n || '-4000-8000-' || lpad(to_hex(s.n), 12, '0'))::uuid,
    ('fa500001-000' || u.n || '-4000-8000-00000000000' || u.n)::uuid,
    '情报-' || u.name || '-' || lpad(s.n::text, 2, '0'),
    false,
    now() - ((u.n * 20 + s.n) || ' days')::interval,
    now() - ((u.n + s.n) || ' hours')::interval
FROM (VALUES
    (1, 'alice'),
    (2, 'bob'),
    (3, 'carol'),
    (4, 'dave'),
    (5, 'eve')
) AS u(n, name)
CROSS JOIN generate_series(1, 15) AS s(n);

-- 每用户 1 条已软删情报（R4：不可加入收藏夹）
INSERT INTO intelligence (id, user_id, title, is_deleted, created_at, updated_at)
VALUES
    ('fa700001-0001-4000-8000-000000000099', 'fa500001-0001-4000-8000-000000000001', '情报-alice-已删除', true, now() - interval '90 days', now() - interval '60 days'),
    ('fa700001-0002-4000-8000-000000000099', 'fa500001-0002-4000-8000-000000000002', '情报-bob-已删除',   true, now() - interval '90 days', now() - interval '60 days'),
    ('fa700001-0003-4000-8000-000000000099', 'fa500001-0003-4000-8000-000000000003', '情报-carol-已删除', true, now() - interval '90 days', now() - interval '60 days'),
    ('fa700001-0004-4000-8000-000000000099', 'fa500001-0004-4000-8000-000000000004', '情报-dave-已删除',  true, now() - interval '90 days', now() - interval '60 days'),
    ('fa700001-0005-4000-8000-000000000099', 'fa500001-0005-4000-8000-000000000005', '情报-eve-已删除',   true, now() - interval '90 days', now() - interval '60 days');

COMMIT;

-- 自检：
-- SELECT COUNT(*) FROM intelligence WHERE id::text LIKE 'fa700%';                    -- 期望 80
-- SELECT COUNT(*) FROM intelligence WHERE id::text LIKE 'fa700%' AND is_deleted;     -- 期望 5
-- SELECT title FROM intelligence WHERE user_id = 'fa500001-0001-4000-8000-000000000001' AND NOT is_deleted LIMIT 3;
