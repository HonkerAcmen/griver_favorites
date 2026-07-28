-- =============================================================================
-- griver_favorites 种子数据（120 条 = 15 folder + 105 item）
-- =============================================================================
-- 前置：已执行 001_favorite_schema.sql；users 表存在且含下方 5 个测试用户 id
--
-- target_type 对齐 ENTITY_TYPES：figure | project | agency
-- target_id  对齐 entity.id 占位 UUID（仅十六进制，便于与 entity 主表联调）
--
-- 重复执行：脚本内按 id 段清理后重插
-- =============================================================================

BEGIN;

-- §0 测试用户（按实际 users 表字段取消注释并修改）
-- INSERT INTO users (id, username, email, created_at, updated_at)
-- VALUES
--     ('fa500001-0001-4000-8000-000000000001', 'seed_alice', 'alice@seed.test', now(), now()),
--     ('fa500001-0002-4000-8000-000000000002', 'seed_bob',   'bob@seed.test',   now(), now()),
--     ('fa500001-0003-4000-8000-000000000003', 'seed_carol', 'carol@seed.test', now(), now()),
--     ('fa500001-0004-4000-8000-000000000004', 'seed_dave',  'dave@seed.test',  now(), now()),
--     ('fa500001-0005-4000-8000-000000000005', 'seed_eve',   'eve@seed.test',   now(), now())
-- ON CONFLICT (id) DO NOTHING;

DELETE FROM griver_favorite_item
WHERE id >= 'fa600000-0000-4000-8000-000000000000'::uuid
  AND id <  'fa610000-0000-4000-8000-000000000000'::uuid;

DELETE FROM griver_favorite_folder
WHERE id >= 'fa500000-0000-4000-8000-000000000000'::uuid
  AND id <  'fa510000-0000-4000-8000-000000000000'::uuid;

-- §1 收藏夹 15 条
INSERT INTO griver_favorite_folder (id, user_id, name, is_deleted, created_at, updated_at)
VALUES
    ('fa500001-0001-4000-8000-000000000101', 'fa500001-0001-4000-8000-000000000001', '重点 KOL',      false, now() - interval '30 days', now() - interval '1 day'),
    ('fa500001-0001-4000-8000-000000000102', 'fa500001-0001-4000-8000-000000000001', 'L1 项目观察',   false, now() - interval '25 days', now() - interval '2 days'),
    ('fa500001-0001-4000-8000-000000000103', 'fa500001-0001-4000-8000-000000000001', 'VC 机构清单',   false, now() - interval '20 days', now() - interval '3 hours'),
    ('fa500001-0002-4000-8000-000000000101', 'fa500001-0002-4000-8000-000000000002', 'DeFi 人物',     false, now() - interval '28 days', now() - interval '5 hours'),
    ('fa500001-0002-4000-8000-000000000102', 'fa500001-0002-4000-8000-000000000002', 'Meme 项目',     false, now() - interval '18 days', now() - interval '1 day'),
    ('fa500001-0002-4000-8000-000000000103', 'fa500001-0002-4000-8000-000000000002', '交易所相关',    false, now() - interval '15 days', now() - interval '12 hours'),
    ('fa500001-0003-4000-8000-000000000101', 'fa500001-0003-4000-8000-000000000003', 'Research 人物', false, now() - interval '22 days', now() - interval '6 hours'),
    ('fa500001-0003-4000-8000-000000000102', 'fa500001-0003-4000-8000-000000000003', '基础设施项目',  false, now() - interval '16 days', now() - interval '2 days'),
    ('fa500001-0003-4000-8000-000000000103', 'fa500001-0003-4000-8000-000000000003', '亚洲机构',      false, now() - interval '10 days', now() - interval '1 hour'),
    ('fa500001-0004-4000-8000-000000000101', 'fa500001-0004-4000-8000-000000000004', 'Builder 关注',  false, now() - interval '14 days', now() - interval '8 hours'),
    ('fa500001-0004-4000-8000-000000000102', 'fa500001-0004-4000-8000-000000000004', 'GameFi 项目',   false, now() - interval '12 days', now() - interval '3 days'),
    ('fa500001-0004-4000-8000-000000000103', 'fa500001-0004-4000-8000-000000000004', '已归档机构',    true,  now() - interval '60 days', now() - interval '30 days'),
    ('fa500001-0005-4000-8000-000000000101', 'fa500001-0005-4000-8000-000000000005', '宏观人物',      false, now() - interval '8 days',  now() - interval '30 minutes'),
    ('fa500001-0005-4000-8000-000000000102', 'fa500001-0005-4000-8000-000000000005', 'RWA 项目',      false, now() - interval '6 days',  now() - interval '4 hours'),
    ('fa500001-0005-4000-8000-000000000105', 'fa500001-0005-4000-8000-000000000005', '全球 agency',   false, now() - interval '4 days',  now() - interval '2 hours');

-- §2 收藏项 105 条（15 folder × 7；含 1 个软删 folder 内的历史收藏）
-- 约束：同一 user 对 (target_type, target_id) 全局唯一 → 按 user 内序号生成 entity.id
INSERT INTO griver_favorite_item (id, folder_id, user_id, target_type, target_id, is_deleted, created_at)
SELECT
    ('fa600000-0000-4000-8000-' || lpad(to_hex(rn.global_rn), 12, '0'))::uuid,
    rn.folder_id,
    rn.user_id,
    (ARRAY['figure', 'project', 'agency'])[1 + ((rn.user_seq - 1) % 3)],
    CASE (ARRAY['figure', 'project', 'agency'])[1 + ((rn.user_seq - 1) % 3)]
        WHEN 'figure'  THEN ('fa400001-0001-4000-8000-' || lpad(to_hex(rn.user_seq), 12, '0'))::uuid
        WHEN 'project' THEN ('fa400002-0001-4000-8000-' || lpad(to_hex(rn.user_seq), 12, '0'))::uuid
        ELSE                ('fa400003-0001-4000-8000-' || lpad(to_hex(rn.user_seq), 12, '0'))::uuid
    END,
    CASE WHEN rn.folder_deleted THEN true ELSE false END,
    now() - (rn.global_rn || ' hours')::interval
FROM (
    SELECT
        f.id AS folder_id,
        f.user_id,
        f.is_deleted AS folder_deleted,
        gs.n AS slot_in_folder,
        row_number() OVER (ORDER BY f.user_id, f.id, gs.n) AS global_rn,
        row_number() OVER (PARTITION BY f.user_id ORDER BY f.id, gs.n) AS user_seq
    FROM griver_favorite_folder f
    CROSS JOIN generate_series(1, 7) AS gs(n)
    WHERE f.id >= 'fa500000-0000-4000-8000-000000000000'::uuid
      AND f.id <  'fa510000-0000-4000-8000-000000000000'::uuid
) rn;

COMMIT;

-- 自检：
-- SELECT COUNT(*) FROM griver_favorite_folder WHERE id::text LIKE 'fa500%';  -- 期望 15
-- SELECT COUNT(*) FROM griver_favorite_item   WHERE id::text LIKE 'fa600%';  -- 期望 105
-- SELECT target_type, COUNT(*) FROM griver_favorite_item WHERE id::text LIKE 'fa600%' GROUP BY 1;  -- figure/project/agency 各 35
