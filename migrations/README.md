# 数据库迁移（Alembic）

本目录存放 `griver_favorites` 的 Alembic 迁移脚本。表结构以 **migration 为准**；`scripts/db/001_favorite_schema.sql` 仅为对照参考。

设计说明见 [docs/design.md](../docs/design.md) v2.0。

---

## 前置条件

1. 本地 PostgreSQL 已启动。
2. 项目根目录已配置 `.env`：

```env
DATABASE_URL_SYNC=postgresql+psycopg://postgres:postgres@localhost:5432/griver_favorites
```

3. **目标库须先创建**（Alembic 不会自动建库）：

```bash
psql -h localhost -U postgres -d postgres -c "CREATE DATABASE griver_favorites;"
```

4. 虚拟环境已安装依赖，并在**项目根目录**执行命令：

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
```

---

## 常用命令

在仓库根目录 `/griver_favorites` 下执行（不要在 `migrations/` 子目录里跑）：

```bash
# 升级到最新
alembic upgrade head

# 查看当前版本
alembic current

# 查看迁移历史
alembic history -v

# 回退一个版本
alembic downgrade -1

# 回退到初始状态
alembic downgrade base

# 新建空 migration（手写 upgrade/downgrade）
alembic revision -m "描述"
```

---

## 版本链

```
base
  → 000_create_user
  → 001_favorite_folder
  → 002_favorite_folder (head)
```

| Revision | 文件 | 内容 |
|----------|------|------|
| `000_create_user` | `versions/000_create_user.py` | `users` 表 + 索引 |
| `001_favorite_folder` | `versions/001_favorite_folder.py` | `griver_favorite_folder`、`griver_favorite_item` 表及索引 |
| `002_favorite_folder` | `versions/002_favorite_folder.py` | 修正 item 唯一索引：由 user 级改为 **folder 级** `(folder_id, target_type, target_id)` |

### 001 创建的表

- **griver_favorite_folder**：收藏夹；`(user_id, name)` 部分唯一（`is_deleted = false`）
- **griver_favorite_item**：收藏关系；`target_type` + `target_id` 指向情报等业务对象

### 002 索引变更（v2.0 业务规则）

| 变更前 | 变更后 |
|--------|--------|
| `uq_griver_favorite_item_user_target_active` | `uq_griver_favorite_item_folder_target_active` |
| `(user_id, target_type, target_id)` | `(folder_id, target_type, target_id)` |

允许**同一情报出现在不同收藏夹**；同一收藏夹内仍不可重复。

---

## 配置说明

| 文件 | 作用 |
|------|------|
| `../alembic.ini` | `script_location = migrations`；数据库 URL 占位 |
| `env.py` | 启动时 `load_dotenv`，用 `DATABASE_URL_SYNC` 覆盖 `sqlalchemy.url` |
| `script.py.mako` | 新建 revision 的模板 |

当前 `target_metadata = None`，**未启用** `alembic revision --autogenerate`；迁移文件一律手写。

---

## 迁移后导入测试数据

Migration 只建表，不插业务数据。Seed 脚本在 `scripts/db/`，须**按顺序**执行：

```bash
psql "$DATABASE_URL_SYNC" -f scripts/db/002_users_seed.sql
psql "$DATABASE_URL_SYNC" -f scripts/db/003_intelligence_seed.sql
psql "$DATABASE_URL_SYNC" -f scripts/db/004_favorite_seed.sql
```

说明：

- `intelligence` 表目前由 `003_intelligence_seed.sql` 内 `CREATE TABLE IF NOT EXISTS` 创建；后续可补独立 migration `003_intelligence` 再移除 seed 中的建表语句。
- Seed 使用固定 UUID 段，可重复执行。

---

## 新建 migration 约定

1. 在 `versions/` 下新增文件，`down_revision` 指向当前 head。
2. 必须同时实现 `upgrade()` 与 `downgrade()`。
3. 索引/约束变更优先用 `op.execute("DROP/CREATE INDEX ...")`，与 001、002 风格一致。
4. 已 push 或他人已执行的 revision **不要改内容**；修正应新建 revision。
5. revision id 建议语义化，例如 `003_intelligence`，避免与功能无关的重复命名。

---

## 常见问题

### `database "griver_favorites" does not exist`

先创建数据库（见「前置条件」），再 `alembic upgrade head`。

### `No 'script_location' key found`

当前工作目录不对。请 `cd` 到含 `alembic.ini` 的项目根目录。

### `No module named 'asyncpg'`

`.env` 中 URL 使用了 `postgresql+asyncpg://`，但未安装 asyncpg。本项目迁移与运行时推荐：

```env
DATABASE_URL_SYNC=postgresql+psycopg://...
```

### `relation "uq_griver_favorite_item_..." already exists`

通常是 002 中先 CREATE 后 DROP，或 DROP 了错误索引名。002 正确顺序：

1. `DROP INDEX uq_griver_favorite_item_user_target_active`
2. `CREATE INDEX uq_griver_favorite_item_folder_target_active`

### 本地库从零重来

```bash
alembic downgrade base
alembic upgrade head
# 再跑 seed 脚本
```

生产环境慎用 `downgrade base`，会删表。

---

## 相关文档

- [docs/design.md](../docs/design.md) — 数据模型与业务规则
- [docs/api.md](../docs/api.md) — API 清单
- [README.md](../README.md) — 项目快速开始
