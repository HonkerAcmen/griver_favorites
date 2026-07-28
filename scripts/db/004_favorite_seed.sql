-- =============================================================================
-- 收藏夹 + 收藏关系种子数据（可重复执行，v2.0）
-- =============================================================================
-- 前置（按顺序）：
--   1. alembic upgrade head
--   2. scripts/db/002_users_seed.sql
--   3. scripts/db/003_intelligence_seed.sql
--
-- 数据量：15 folder + 105 item（15 × 7）
-- target_type：intelligence（对齐 v2.0）
-- 约束：同一 folder 内 target 唯一；跨 folder 允许重复（alice 的 folder 101 与 102 共享情报 1~3）
-- =============================================================================

BEGIN;

DELETE FROM griver_favorite_item
WHERE id >= 'fa600000-0000-4000-8000-000000000000'::uuid
  AND id <  'fa610000-0000-4000-8000-000000000000'::uuid;

DELETE FROM griver_favorite_folder
WHERE id >= 'fa500000-0000-4000-8000-000000000000'::uuid
  AND id <  'fa510000-0000-4000-8000-000000000000'::uuid;

-- §1 收藏夹 15 条（14 有效 + 1 已软删）
INSERT INTO griver_favorite_folder (id, user_id, name, is_deleted, created_at, updated_at)
VALUES
    ('fa500001-0001-4000-8000-000000000101', 'fa500001-0001-4000-8000-000000000001', '重点情报',      false, now() - interval '30 days', now() - interval '1 day'),
    ('fa500001-0001-4000-8000-000000000102', 'fa500001-0001-4000-8000-000000000001', '待跟进',        false, now() - interval '25 days', now() - interval '2 days'),
    ('fa500001-0001-4000-8000-000000000103', 'fa500001-0001-4000-8000-000000000001', '归档参考',      false, now() - interval '20 days', now() - interval '3 hours'),
    ('fa500001-0002-4000-8000-000000000101', 'fa500001-0002-4000-8000-000000000002', 'DeFi 专题',     false, now() - interval '28 days', now() - interval '5 hours'),
    ('fa500001-0002-4000-8000-000000000102', 'fa500001-0002-4000-8000-000000000002', 'Meme 追踪',     false, now() - interval '18 days', now() - interval '1 day'),
    ('fa500001-0002-4000-8000-000000000103', 'fa500001-0002-4000-8000-000000000002', '交易所动态',    false, now() - interval '15 days', now() - interval '12 hours'),
    ('fa500001-0003-4000-8000-000000000101', 'fa500001-0003-4000-8000-000000000003', 'Research',      false, now() - interval '22 days', now() - interval '6 hours'),
    ('fa500001-0003-4000-8000-000000000102', 'fa500001-0003-4000-8000-000000000003', '基础设施',      false, now() - interval '16 days', now() - interval '2 days'),
    ('fa500001-0003-4000-8000-000000000103', 'fa500001-0003-4000-8000-000000000003', '亚洲市场',      false, now() - interval '10 days', now() - interval '1 hour'),
    ('fa500001-0004-4000-8000-000000000101', 'fa500001-0004-4000-8000-000000000004', 'Builder',       false, now() - interval '14 days', now() - interval '8 hours'),
    ('fa500001-0004-4000-8000-000000000102', 'fa500001-0004-4000-8000-000000000004', 'GameFi',        false, now() - interval '12 days', now() - interval '3 days'),
    ('fa500001-0004-4000-8000-000000000103', 'fa500001-0004-4000-8000-000000000004', '已归档收藏夹',  true,  now() - interval '60 days', now() - interval '30 days'),
    ('fa500001-0005-4000-8000-000000000101', 'fa500001-0005-4000-8000-000000000005', '宏观',          false, now() - interval '8 days',  now() - interval '30 minutes'),
    ('fa500001-0005-4000-8000-000000000102', 'fa500001-0005-4000-8000-000000000005', 'RWA',           false, now() - interval '6 days',  now() - interval '4 hours'),
    ('fa500001-0005-4000-8000-000000000105', 'fa500001-0005-4000-8000-000000000005', '全球视野',      false, now() - interval '4 days',  now() - interval '2 hours');

-- §2 收藏项 105 条
-- intel_seq：每 folder 内 7 条互不重复；跨 folder 通过 (folder_idx * 3 + slot) % 15 产生重叠
INSERT INTO griver_favorite_item (id, folder_id, user_id, target_type, target_id, is_deleted, created_at)
SELECT
    ('fa600000-0000-4000-8000-' || lpad(to_hex(rn.global_rn), 12, '0'))::uuid,
    rn.folder_id,
    rn.user_id,
    'intelligence',
    ('fa700001-000' || rn.user_idx || '-4000-8000-' || lpad(to_hex(rn.intel_seq), 12, '0'))::uuid,
    CASE WHEN rn.folder_deleted THEN true ELSE false END,
    now() - (rn.global_rn || ' hours')::interval
FROM (
    SELECT
        f.id AS folder_id,
        f.user_id,
        f.is_deleted AS folder_deleted,
        (right(f.user_id::text, 1))::int AS user_idx,
        gs.n AS slot_in_folder,
        ((row_number() OVER (PARTITION BY f.user_id ORDER BY f.id) - 1) * 3 + gs.n - 1) % 15 + 1 AS intel_seq,
        row_number() OVER (ORDER BY f.user_id, f.id, gs.n) AS global_rn
    FROM griver_favorite_folder f
    CROSS JOIN generate_series(1, 7) AS gs(n)
    WHERE f.id >= 'fa500000-0000-4000-8000-000000000000'::uuid
      AND f.id <  'fa510000-0000-4000-8000-000000000000'::uuid
) rn;

COMMIT;

-- 自检：
-- SELECT COUNT(*) FROM griver_favorite_folder WHERE id::text LIKE 'fa500%';  -- 15
-- SELECT COUNT(*) FROM griver_favorite_item   WHERE id::text LIKE 'fa600%';  -- 105
-- SELECT target_type, COUNT(*) FROM griver_favorite_item WHERE id::text LIKE 'fa600%' GROUP BY 1;  -- intelligence: 105
--
-- 跨 folder 重复（alice 情报-01 应出现在多个收藏夹）：
-- SELECT folder_id, target_id FROM griver_favorite_item
-- WHERE user_id = 'fa500001-0001-4000-8000-000000000001'
--   AND target_id = 'fa700001-0001-4000-8000-000000000000000001'
-- ORDER BY folder_id;
