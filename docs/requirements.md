# griver_favorites 需求与开发计划

| 字段 | 内容 |
|------|------|
| **文档类型** | 需求说明 + 可执行开发计划（文件级 / 行为级） |
| **版本** | v2.5 |
| **编制日期** | 2026-07-29（v2.2）；**终版刷新 2026-07-31** |
| **计划周期** | 2026-07-29（周三，自 B2 起）— 2026-07-31（周五）23:00 |
| **交付范围** | 9 HTTP 接口、业务规则 R1–R10、Redis Cache-Aside、RabbitMQ 操作日志、Docker Compose、全量自动化测试 |
| **当前工作项** | **交付收尾**：可选增强（health 探针、N+1 专项测、main.py MQ 优雅降级） |
| **关联文档** | [design.md](./design.md) v3.3、[api.md](./api.md) v2.1 |

---

## 1. 文档说明

### 1.1 编制目的

本文档用于明确 griver_favorites 项目的交付边界、业务规则、技术约束、当前进度与分日工作安排。开发、自测、Code Review 与最终验收均可对照本文档执行。

文档职责划分如下：

| 文档 | 职责 |
|------|------|
| **本文档** | 需求范围、进度基线、任务拆解、排期、验收清单、风险应对 |
| **design.md** | 数据模型、索引、分层架构、缓存/MQ 设计、测试用例编号 |
| **api.md** | 接口路径、请求/响应字段、HTTP 状态码、错误码字符串 |

编码时建议遵循：**业务规则以 design.md §2.3 为准**；**接口字段以 api.md 为准**；**排期与任务以本文档 §6 为准**。

### 1.2 适用读者

项目开发人员（本人）、代码评审人员、作业验收对照人员。

### 1.3 阅读说明

- 任务编号（A1、B2、F1 等）沿用以便于与历史 commit 对照；**已完成任务见 §9 附录**，正文 §6 从 **B2** 接续。
- 涉及 Repository 函数名时，**以仓库现有代码为准**（见 §3.1.1 命名对照表）。
- 文中「预期产出」「收口标准」为验收参考；「建议」「拟采用」为推荐实现路径，可在 Review 中调整，但不得削弱 §5 验收底线。

---

## 2. 项目需求

### 2.1 业务背景

运营人员需将系统中**已存在的情报**整理至不同**收藏夹**，以支持分类查看与后续管理。

本项目范围内：

- 情报表 **只读引用**，不提供情报新增、修改、删除 API；
- 须提供 **可重复执行** 的测试数据初始化脚本（用户、情报、收藏夹、收藏关系）；
- 本地 / 作业环境 **不设登录与权限**，`user_id` 由 Body 或 Query 显式传入。

### 2.2 范围界定

#### 2.2.1 纳入范围

| 类别 | 内容 |
|------|------|
| 功能 | 下文 §2.3 所列 10 项 |
| 接口 | 下文 §2.6 所列 9 个 HTTP API |
| 规则 | R1–R10（§2.4） |
| 缓存 | Redis Cache-Aside：收藏夹详情 + `item_count`（§2.8） |
| 消息 | RabbitMQ：收藏成功后异步操作日志（§2.9） |
| 编排 | Docker Compose：app + PostgreSQL + Redis + RabbitMQ |
| 测试 | 单元、集成、缓存、MQ、并发（§5、§6、design §10） |

#### 2.2.2 暂不纳入范围

登录鉴权、权限体系、前端页面、情报写接口、消息队列以外的异步任务。

### 2.3 功能需求（10 项）

| 编号 | 功能 | 详细说明 | 主要接口 / 模块 |
|------|------|----------|-----------------|
| F1 | 收藏夹 CRUD | 创建、查询、重命名、软删除 | POST/GET/PATCH/DELETE `/folders` |
| F2 | 收藏夹列表 | 分页；按 **folder.name** keyword 模糊搜索 | GET `/folders` |
| F3 | 收藏夹详情 | 返回 folder 字段 + **item_count**（未软删 item 数） | GET `/folders/{id}` |
| F4 | 加入情报 | 指定 `intelligence_id` 加入指定 folder | POST `/folders/{id}/items` |
| F5 | 移除情报 | 软删 item，**不修改** intelligence 表 | DELETE `/folders/{id}/items/{item_id}` |
| F6 | 移动情报 | 从 folder A 移至 folder B，单事务 | PUT `/items/{item_id}/move` |
| F7 | 夹内列表 | 分页展示该 folder 下有效 item | GET `/folders/{id}/items` |
| F8 | 标题筛选 | keyword 对 **intelligence.title** ILIKE | GET `/folders/{id}/items` |
| F9 | 跨夹重复 | 同一 intelligence 可存在于多个 folder | item 唯一索引为 folder 级 |
| F10 | 删夹保情报 | 删 folder 级联软删 item，intelligence 不变 | DELETE `/folders/{id}` |

### 2.4 业务规则（R1–R10）

| 编号 | 规则 | 实现要点（Service + DB） | 异常 / 错误码 |
|------|------|--------------------------|---------------|
| **R1** | 有效 folder 名称不可重复；校验前 **strip** | Service 长度校验；部分唯一索引 `(user_id, name) WHERE is_deleted=false` | `FAVORITE_FOLDER_NAME_DUPLICATE` |
| **R2** | 同一 folder 内不可重复同一情报 | 唯一索引 `(folder_id, target_type, target_id) WHERE is_deleted=false` | `FAVORITE_ITEM_ALREADY_EXISTS` |
| **R3** | 已软删 folder 不可查、改、加 item | 读写前 `find_by_id_and_user` + `is_deleted=false` | `FAVORITE_FOLDER_NOT_EXISTS` |
| **R4** | 不存在或已删情报不可加入 | `intelligence_find_by_id_not_deleted` | `INTELLIGENCE_NOT_EXISTS` |
| **R5** | 移动前来源 folder 须包含该 item | Service 查 source item 归属 | `FAVORITE_ITEM_MOVE_FAILED` |
| **R6** | 目标 folder 已有同一情报则移动失败 | `favorite_item_find_in_folder` | `FAVORITE_ITEM_ALREADY_EXISTS` |
| **R7** | 移动须 **单事务** | 来源软删 + 目标新建（或更新）同一 `commit`；失败 `rollback` | — |
| **R8** | 删 folder 级联软删 item，不动 intelligence | 同一事务内更新 folder + items | — |
| **R9** | 并发重复收藏 DB 保证唯一 | 依赖 R2 索引 + IntegrityError 映射 | R10 |
| **R10** | 不暴露 DB 原始错误 | `exception_handlers.handle_integrity_error` | 稳定 `code` + `msg` |

**名称校验约定**（R1 相关）：

- 空字符串或 strip 后为空 → `FavoriteFolderNameInvalidException`
- 长度上限 **100**（`FOLDER_NAME_MAX_LEN`）
- Unicode 计长；区分大小写；「待跟进」与「待跟进 」视为不同名（strip 后比较）

### 2.5 分层与 Session 约定

```
Depends(get_db_session)     # 注意：不加括号
  → Router：解析参数、注入 Service、return success(data=...)
  → Service：业务规则、commit/rollback、缓存/MQ 编排、抛业务异常
  → Repository：select/ORM，接收 session，不 commit
```

| 层级 | 职责 | 禁止事项 |
|------|------|----------|
| Router | 参数解析、HTTP 状态码、统一响应 | 不写 SQL、不承载核心业务 |
| Service | 规则校验、事务、调 Repo、调缓存/MQ | 不 `session.query()`（1.x） |
| Repository | 数据访问 | 不创建 Session、不 commit |

### 2.6 HTTP 接口清单

前缀：`/grapi/v1/favorite`（完整路径见 api.md）

| # | 方法 | 路径 | 成功 HTTP | 主要 Query/Body |
|---|------|------|-----------|-----------------|
| 1 | POST | `/folders` | 201 | Body: `user_id`, `name` |
| 2 | GET | `/folders` | 200 | Query: `user_id`, `page`, `size`/`page_size`, `keyword` |
| 3 | GET | `/folders/{folder_id}` | 200 | Query: `user_id` |
| 4 | PATCH | `/folders/{folder_id}` | 200 | Body: `user_id`, `name` |
| 5 | DELETE | `/folders/{folder_id}` | 200 | Query: `user_id` |
| 6 | POST | `/folders/{folder_id}/items` | 201 | Body: `user_id`, `intelligence_id` |
| 7 | DELETE | `/folders/{folder_id}/items/{item_id}` | 200 | Query: `user_id` |
| 8 | PUT | `/items/{item_id}/move` | 200 | Body: `user_id`, `target_folder_id` |
| 9 | GET | `/folders/{folder_id}/items` | 200 | Query: `user_id`, `page`, `size`, `keyword`（搜 title） |

**响应 envelope**：

```json
{ "code": 0, "msg": "success", "data": { } }
```

业务失败：HTTP **200**，`code ≠ 0`，`msg` 为 api.md 字符串标识；参数错误：HTTP **422**。

### 2.7 技术栈

| 组件 | 拟采用 |
|------|--------|
| Web | FastAPI + Pydantic 2 |
| DB | PostgreSQL + SQLAlchemy 2.0 异步（asyncpg） |
| 迁移 | Alembic（`DATABASE_URL_SYNC` / psycopg） |
| 缓存 | Redis（redis-py 异步；读写客户端分离） |
| 消息 | RabbitMQ（aio-pika 或同类异步客户端） |
| 测试 | pytest + pytest-asyncio |
| 编排 | Docker Compose |

**异步约束**：业务层不使用同步阻塞的数据库、Redis、HTTP 调用。

### 2.8 Redis 设计要求（作业第七节）

| # | 要求 | 拟实现位置 |
|---|------|------------|
| 1 | 详情 + `item_count` 使用 Cache-Aside | `services/cache/folder_cache.py` |
| 2 | 读：先 Redis，未命中查 DB 并回写 | `get_folder_detail_cached` |
| 3 | 读写客户端分离 | `apps/core/redis.py` |
| 4 | 不存在 folder：短 TTL 空值缓存 | sentinel JSON `{"__null__": true}`，TTL **60s** |
| 5 | 正常条目 TTL | **300s**（写操作主动 delete，TTL 作兜底） |
| 6 | rename/delete/add/remove 后失效 | Service commit 后 `invalidate_folder_detail` |
| 7 | move 后失效来源 + 目标 | 两个 key 均 delete |
| 8 | 读失败降级查 DB + 日志 | WARNING/ERROR，不向客户端抛 Redis 异常 |
| 9 | 写/删失败不静默 | ERROR 日志或上抛（团队约定：至少 ERROR） |
| 10 | 缓存 JSON DTO，不缓存 ORM | `FolderDetailCacheDTO` |

**缓存键格式（与 design 一致）**：

```
folder:detail:{user_id}:{folder_id}
```

**读路径伪代码**：

```
1. key = folder:detail:{user_id}:{folder_id}
2. val = await redis_read.get(key)
3. if val == NULL_SENTINEL → raise FavoriteFolderNotFoundException
4. if val hits → return deserialize(DTO)
5. folder = await repo.find_by_id_and_user(...)
6. if folder is None → setex(key, 60, NULL_SENTINEL); raise NotFound
7. count = await repo.count_items(...)
8. dto = build DTO; setex(key, 300, serialize(dto)); return dto
9. on redis_read error → log; fallback to step 5–8 without cache
```

### 2.9 RabbitMQ 设计要求（作业任务 6）

#### 2.9.1 拓扑（拟采用）

| 组件 | 名称 |
|------|------|
| Exchange | `favorite.events`（topic） |
| Routing key | `favorite.item.added` |
| Queue | `favorite.operation_log` |
| DLQ | `favorite.operation_log.dlq` |
| 重试 | 消费失败 nack + requeue，**≥3 次** 进 DLQ |

#### 2.9.2 事件体（JSON）

```json
{
  "event_id": "uuid",
  "user_id": "uuid",
  "folder_id": "uuid",
  "intelligence_id": "uuid",
  "action": "favorite_add",
  "occurred_at": "2026-07-29T12:00:00+00:00"
}
```

#### 2.9.3 行为约定

| 场景 | 拟采用行为 |
|------|------------|
| add_item commit 成功 | Publisher 发消息 |
| 校验失败 / rollback | **不发**消息 |
| Broker 不可用 | HTTP 仍返回成功；`logger.error` |
| Consumer 成功 | 写 `favorite_operation_log` + **manual ack** |
| 重复 `event_id` | DB UNIQUE，不重复插入 |
| Consumer 失败 | nack；超 3 次 → DLQ |

#### 2.9.4 操作日志表（migration 004）

```text
favorite_operation_log
  id              UUID PK DEFAULT gen_random_uuid()
  event_id        UUID UNIQUE NOT NULL
  user_id         UUID NOT NULL
  folder_id       UUID NOT NULL
  intelligence_id UUID NOT NULL
  action          VARCHAR(32) NOT NULL
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
```

---

## 3. 进度基线（2026-07-31 终版）

> 以下以 **git 提交 + 仓库文件 + `pytest tests/` 结果** 为准。  
> **当前 pytest：101 passed**（单元 + 集成 + MQ；见根目录 `test_results.txt`）。

### 3.1 已完成（可审查展示）

#### 3.1.1 HTTP 接口（9/9）

| # | 方法 | 路径 | 实现文件 | 测试 |
|---|------|------|----------|------|
| 1 | POST | `/folders` | `routers/folder.py` | unit + integration |
| 2 | GET | `/folders` | 同上 | 同上 |
| 3 | GET | `/folders/{id}` | 同上 | 同上 + Redis Cache-Aside |
| 4 | PATCH | `/folders/{id}` | 同上 | 同上 |
| 5 | DELETE | `/folders/{id}` | 同上 | 同上 |
| 6 | POST | `/folders/{id}/items` | `routers/item.py` | unit + integration + MQ |
| 7 | DELETE | `/folders/{id}/items/{item_id}` | 同上 | 同上 |
| 8 | PUT | `/items/{item_id}/move` | 同上 | integration + unit |
| 9 | GET | `/folders/{id}/items` | 同上 | integration（含 keyword） |

#### 3.1.2 业务层与基础设施

| 模块 | 路径 | 说明 |
|------|------|------|
| FolderService | `services/folder.py` | CRUD；详情走 Redis Cache-Aside |
| ItemService | `services/item.py` | add/remove/move/list；commit 后发 MQ；写后失效缓存 |
| folder_cache | `services/cache/folder_cache.py` | Cache-Aside 读/写/失效 |
| MQ Publisher | `mq/publisher.py` | `publish_favorite_added` |
| MQ Consumer | `mq/consumer.py` | 落库、ack、重试、DLQ；`python -m apps.favorite.mq.consumer` |
| operation_log | `repositories/operation_log.py` + migration 004 | `event_id` UNIQUE 幂等 |
| Redis / RabbitMQ | `apps/core/redis.py`、`rabbitmq.py` | lifespan 初始化；Depends 注入 |
| Docker | `docker-compose.yml` | PostgreSQL + Redis + RabbitMQ |
| 配置 | `config.py`、`.env.example` | 全量环境变量 |
| 交付 | `README.md`、`test_results.txt` | 启动说明 + 可复现测试输出 |

#### 3.1.3 测试覆盖摘要

| 文件 | 条数 | 覆盖范围 |
|------|------|----------|
| `test_repo.py` | 23 | folder + item + operation_log repo |
| `test_folder_service.py` | 14 | folder service |
| `test_item_service.py` | 14 | item service + MQ publish |
| `test_folder_cache.py` | 8 | Redis §7.2 |
| `test_mq_publisher.py` | 3 | Publisher |
| `test_mq_consumer.py` | 8 | Consumer ack/重试/DLQ |
| `test_routers.py` | 8 | Router HTTP 形态 |
| `test_folder_router.py` | 10 | folder 集成 |
| `test_item_router.py` | 8 | item 集成 + 并发 R9 |
| `test_mq_favorite_add.py` | 5 | MQ 集成 §7.3 |

**合计**：`pytest tests/ -q` → **101 passed**（2026-07-31；需 PG + RabbitMQ，MQ 测不可用时 skip）。

#### 3.1.4 常用 seed UUID（不变）

| 用途 | UUID |
|------|------|
| Alice user | `fa500001-0001-4000-8000-000000000001` |
| Alice 有效情报 | `fa700001-0001-4000-8000-000000000001` |
| Alice 已删情报（R4） | `fa700001-0001-4000-8000-000000000099` |

#### 3.1.5 已完成任务编号（对照 §6）

| 阶段 | 任务 | 状态 |
|------|------|------|
| 周三晚 | B2–C3 | ✓ |
| 周四 | A6–A8、B5–B8、C2、C4；C5 部分（`.env.example` ✓） | ✓ |
| 周五 | F1–F5（9 API + Item 全系 + 并发 R9） | ✓ |
| 周五 | G（Redis Cache-Aside） | ✓ |
| 周五 | H（RabbitMQ Publisher + Consumer + 集成测） | ✓ |
| 周五 | I（docker-compose） | ✓ |
| 周五 | J/K（README、test_results.txt） | ✓ |

#### 3.1.6 Redis 与 RabbitMQ 摘要

| 能力 | 关键路径 | 测试 |
|------|----------|------|
| Cache-Aside | `folder_cache.py` + Service 失效 | `test_folder_cache.py` ×8 |
| 发消息 | `mq/publisher.py`；`add_item` commit 后 | `test_mq_publisher.py` ×3、`test_item_service` ×2 |
| 消费落库 | `mq/consumer.py`；manual ack + DLQ | `test_mq_consumer.py` ×8、`test_mq_favorite_add.py` ×5 |

### 3.2 可选增强（非入项阻塞）

| 项 | 说明 |
|----|------|
| `main.py` MQ init try/except | 无 RabbitMQ 时 uvicorn 仍可启动 |
| `/health` 返回 redis/rabbitmq 状态 | 演示用 |
| N+1 专项测 | 列表 repo 已 JOIN，缺独立断言 |
| 移动回滚 Service 单测 | Router 层已部分覆盖 |
| `003_intelligence_seed.sql` 重复 CREATE TABLE | 低优先级清理 |

### 3.3 本地验证命令

```bash
docker compose up -d
cp .env.example .env
alembic upgrade head
pytest tests/ -q                    # 101 passed（需 PG + RabbitMQ）
python -m apps.favorite.mq.consumer   # 独立 Consumer 进程
uvicorn main:app --reload
```

### 3.4 黄金河入项验收对照（2026-07-31 终版）

> 对照入项文档 **一～十一** 节；✓ = 本仓库已满足或基本满足，△ = 部分满足，✗ = 未做。

#### 三、功能要求（10 项）

| # | 要求 | 状态 | 说明 |
|---|------|------|------|
| 1 | 收藏夹 CRUD | ✓ | 5 个 Folder API + 单/集成测 |
| 2 | 分页 + 名称搜索 | ✓ | `keyword` on folder list |
| 3 | 详情 + 情报数量 | ✓ | `item_count`；Redis Cache-Aside |
| 4 | 加入情报 | ✓ | POST items |
| 5 | 移除情报 | ✓ | DELETE item |
| 6 | 移动情报 | ✓ | PUT move |
| 7 | 收藏夹内情报分页 | ✓ | GET items list |
| 8 | 按标题筛选 | ✓ | keyword on item list |
| 9 | 同情报多收藏夹 | ✓ | 唯一约束 `(folder_id, target_type, target_id)` |
| 10 | 删收藏夹不删情报 | ✓ | 仅软删 item 关系 |

#### 四、业务规则 R1–R10

| 规则 | 状态 |
|------|------|
| R1–R10 | ✓ 均有 Service/集成测覆盖核心路径 |

#### 引用完整性（外键策略）

| 项 | 状态 | 说明 |
|----|------|------|
| item → intelligence 逻辑引用 | ✓ | 无物理 FK；Service R4 校验 |
| user / folder 逻辑引用 + Service | ✓ | 005 删物理 FK；见 design §3.6 |
| 全逻辑外键（去掉所有 DB FK） | ✓ | migration 005 + Service 校验 |

#### 五、独立设计任务

| # | 内容 | 状态 |
|---|------|------|
| 1–10 | 需求/模型/索引/软删/分层/API/事务/N+1/Redis/测试方案 | ✓ `docs/design.md` + `docs/api.md` + 本文档 |

#### 六、强制工程规范（10 条）

| # | 规范 | 状态 |
|---|------|------|
| 1–2 | 异步 DB/Redis；无 sync 阻塞 | ✓ |
| 3–7 | DI Session、分层职责 | ✓ |
| 8 | 业务异常 + 统一响应 + 日志 | ✓（logger 写法已在 cache 层修正） |
| 9 | 无全局可变业务状态 | △ `redis_service` 单例为基础设施，与 design 一致 |
| 10 | 迁移 + seed 脚本 | ✓ 000–004 + scripts/db |

#### 七、Redis 要求（10 条）

| # | 要求 | 状态 |
|---|------|------|
| 1–10 | 全部 | ✓ 见 §3.1.6 |

#### 八、测试要求（15 条）

| # | 场景 | 状态 |
|---|------|------|
| 1–8 | CRUD / 移动 / 并发 / 分页 | ✓ |
| 9 | N+1 / 懒加载 | △ repo JOIN，无专项测 |
| 10–15 | Redis 六场景 | ✓ `test_folder_cache.py` |
| MQ 五条 | 发消息/失败不发/落库/幂等/DLQ | ✓ `test_mq_*` + 集成测 |
| — | Service + HTTP 集成 | ✓ |

#### 九、任务安排（入项 7 项）

| 任务 | 状态 | 说明 |
|------|------|------|
| 任务 1–2 | — | 入项前练习，不在本仓库 |
| 任务 3–6 | ✓ | 设计 + API + 缓存 + MQ |
| 任务 7 | ✓ | 101 测 + test_results.txt |

#### 十、交付物（10 项）

| # | 交付物 | 状态 |
|---|--------|------|
| 1 | 源码 + Git 记录 | ✓ |
| 2 | 设计文档 + API 清单 | ✓ |
| 3 | 迁移脚本 | ✓ 000–004 |
| 4 | 测试数据脚本 | ✓ |
| 5 | 单测 + 集成 + 并发 + MQ | ✓ |
| 6 | `.env.example` | ✓ |
| 7 | README | ✓ |
| 8 | Docker Compose | ✓ |
| 9 | `test_results.txt` | ✓ |
| 10 | 标准 commit | ✓ |

#### 十一、验收标准（8 条）

| # | 标准 | 状态 |
|---|------|------|
| 1–8 | 全部 | ✓（审查时演示 Consumer + `/docs`） |

**入项整体完成度（终版）**：核心功能 + Redis + MQ + 交付物 ≈ **95%**；可选增强见 §3.2。

### 3.5 历史：待完成总览（v2.3 以前）

---

## 3.x 历史进度基线（2026-07-29，已过期，仅供回溯）

<details>
<summary>点击展开 2026-07-29 旧基线（B2 进行中）</summary>

### 3.1 已完成（2026-07-29 快照）

#### 3.1.1 命名对照（避免文档与代码不一致）

| 文档 / 旧称 | **代码中实际名称** |
|-------------|-------------------|
| `favorite_folder_create` | **`favorite_create_folder`** |

（以下 2026-07-29 条目已过时：FolderService 曾为 pass、Item 未实现等，以 §3 顶部 2026-07-31 刷新为准。）

</details>

---

## 4. 工期与节奏

### 4.1 工作时段假设

| 时段 | 安排 |
|------|------|
| 08:30–12:00 | 开发 |
| 12:00–14:00 | 午休 |
| 14:00–19:00 | 开发 |
| 19:00–20:30 | 晚餐 |
| 20:30–23:00 | 开发 |
| 23:00 后 | 休息 |

Wed–Fri 有效开发约 **33 小时**。

### 4.2 历史提交节奏（2026-07-28，参考）

| 时段 | 提交数 | 时长 | 产出类型 |
|------|--------|------|----------|
| 14:32–16:37 | 5 | 2.1h | migration、Alembic |
| 18:26–19:21 | 3 | 0.9h | scaffold、database |
| 21:39–23:12 | 9 | 1.5h | TDD、seed、异常 |

**评估**：熟悉栈后，单个「Repo + Service + Router + 测试」模块约 **1.5–2h**。周五集中 Redis + MQ，时间紧，建议周四前完成 Item add/remove，为周五留缓冲。

---

## 5. 验收清单（2026-07-31 23:00）

### 5.1 核心 API 与数据

- [x] 9 接口在 `/docs` 可调用，与 api.md 一致
- [x] R1–R10 有单元或集成测试覆盖（核心路径；Redis 降级测除外）
- [x] `alembic upgrade head`：000–004（含 `004_favorite_operation_log`）
- [x] seed 002→003→004 可重复执行
- [x] 业务层无同步 Session / Redis / HTTP（Redis 客户端为 asyncio）

### 5.2 Redis

- [x] Cache-Aside 读写正常
- [x] 空值 TTL 60s 生效
- [x] rename/delete/add/remove/move 后 key 失效
- [x] move 双端失效
- [x] 读失败降级 + 日志
- [x] 写/删失败有日志
- [x] 命中时不查 DB（单测验证）

### 5.3 RabbitMQ

- [x] commit 成功后发消息
- [x] 失败/rollback 不发
- [x] Consumer 落库 + manual ack
- [x] event_id 幂等
- [x] 3 次失败进 DLQ
- [x] Broker 不可用不影响 HTTP 成功 + ERROR 日志

### 5.4 工程交付

- [x] `pytest` 全绿（当前 **101 passed**）
- [x] `.env.example`
- [x] `docker-compose.yml`
- [x] README（启动、迁移、测试、consumer、排查）
- [x] `test_results.txt` 可复现
- [ ] Git push 最终版（审查前）

---

## 6. 分日开发计划（详细任务说明）

### 6.0 三日总览

| 日期 | 计划交付 | 关键里程碑 |
|------|----------|------------|
| **周三 7/29 晚** | B2–C3 | POST + GET 列表 + GET 详情 + Service 单测 |
| **周四 7/30** | A6–C5 | Folder 五接口齐；Item add/remove |
| **周五 7/31** | F–K | 移动、列表、并发、Redis、MQ、Docker、全量 pytest |

---

### 6.1 周三（2026-07-29）— 自 B2 起

> A1–A5、B1 已完成，见 §9。本节从 **B2** 执行。

**当日收口标准**：POST 创建真实写库；GET 列表与 GET 详情可用；`test_folder_service.py` 通过。

---

#### 任务 B2（15:00–16:30）— FolderService.create_folder 真写库

**背景**：Router 已 `await service.create_folder`，但 Service 为 `pass`，POST 不会落库。

**步骤 1：编写单测（Red）**

文件：`tests/unit/favorite/test_folder_service.py`

建议使用 **真实 AsyncSession + rollback**（与 `test_repo.py` 相同 fixture 模式），或 mock Repository；推荐真实 DB 以覆盖 commit。

| # | 用例名（建议） | 输入 | 预期 |
|---|----------------|------|------|
| 1 | `test_create_folder_success` | 合法 name + `SEED_ALICE_ID` | dict 含 `id`,`name`,`created_at`,`updated_at`；DB 有新行 |
| 2 | `test_create_folder_empty_name_raises` | `name=""` 或 `"   "` | `FavoriteFolderNameInvalidException` |
| 3 | `test_create_folder_name_too_long_raises` | 101 字符 | `FavoriteFolderNameInvalidException` |
| 4 | `test_create_folder_duplicate_name_raises` | 同 user 连续两次同名 | 第二次 `FavoriteFolderNameDuplicateException` 或 IntegrityError→业务码 |

**步骤 2：实现 Service（Green）**

文件：`apps/favorite/services/folder.py`

```python
async def create_folder(self, user_id: uuid.UUID, name: str) -> dict:
    cleaned = name.strip()
    if not cleaned or len(cleaned) > FOLDER_NAME_MAX_LEN:
        raise FavoriteFolderNameInvalidException()
    folder = await favorite_create_folder(self.session, user_id, cleaned)
    await self.session.commit()
    return {
        "id": folder.id,
        "name": folder.name,
        "created_at": folder.created_at,
        "updated_at": folder.updated_at,
    }
```

**重名处理（二选一，建议先做 a）**：

- a) Service 内先 `favorite_folder_count_by_name` → ≥1 则抛 Duplicate  
- b) 仅靠唯一索引，捕获 IntegrityError，由 `exception_handlers` 映射（R10）

**步骤 3：验收**

```bash
pytest tests/unit/favorite/test_folder_service.py -v
# 手动：
curl -X POST http://127.0.0.1:8000/grapi/v1/favorite/folders \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"fa500001-0001-4000-8000-000000000001","name":"测试夹"}'
# 期望 201，code=0，DB griver_favorite_folder 有新行
```

---

#### 任务 B3（16:30–17:30）— POST Router 与 Schema 对齐

**文件**：

| 文件 | 改动 |
|------|------|
| `apps/favorite/schemas/folder.py` | `user_id: UUID`（Pydantic 2）；`name: str` |
| `apps/favorite/routers/folder.py` | 已 `return success(data=folder)`，确认 HTTP 201 |

**验收**：`pytest tests/unit/favorite/test_routers.py` 仍绿；真实 POST 写库成功。

---

#### 任务 B4（17:30–19:00）— GET 分页列表 + 名称搜索

**新建 Schema**：`FavoriteFolderListQueryParams`（或 FastAPI Query 参数类）

| 参数 | 类型 | 默认 | 规则 |
|------|------|------|------|
| `user_id` | UUID | 必填 | |
| `page` | int | 1 | `<1` 当 1 |
| `size` / `page_size` | int | 10 | 1–100；**size 优先** |
| `keyword` | Optional[str] | None | 空/空白当未传 |

**Service**：`list_favorite_folders(user_id, page, page_size, keyword)`

1. 规范化 page、page_size  
2. `items, total = await favorite_folder_list_by_user(...)`  
3. 将 ORM 转为 dict 列表（含 id、name、created_at、updated_at）  
4. 返回 `{ "items": [...], "total": n, "page": p, "page_size": s }`

**Router**：`@router.get("")`

**验收**：alice + `keyword=重点` → 命中「重点情报」；空 keyword → 3 条（seed）。

---

#### 任务 C1（20:30–21:30）— GET 详情 + item_count

**Repository 新增**（`repositories/folder.py`）：

```python
async def favorite_folder_count_items(session, folder_id: uuid.UUID) -> int:
    # SELECT count(*) FROM griver_favorite_item
    # WHERE folder_id = ? AND is_deleted = false
```

**Service**：`get_favorite_folder_detail(user_id, folder_id)`

1. `folder = await favorite_folder_find_by_id_and_user(...)`  
2. 若 None → `FavoriteFolderNotFoundException`（R3）  
3. `item_count = await favorite_folder_count_items(...)`  
4. 返回 `{ id, name, item_count, created_at, updated_at }`

> **说明**：Redis 计划于周五接入；周三 C1 先直连 DB，避免阻塞列表/详情联调。

**Router**：`GET /{folder_id}?user_id=...`

**验收**：对 seed folder `...0101`（重点情报），`item_count` 与 SQL count 一致。

---

#### 任务 C2（21:30–22:15）— Folder 集成测试（前 4 能力）

**新建**：`tests/integration/favorite/test_folder_router.py`

建议使用 TestClient + 真实 DB + seed alice；每用例 rollback 或独立数据。

| # | 用例 | 断言要点 |
|---|------|----------|
| 1 | `test_create_folder_success` | 201；code=0；data 含 id |
| 2 | `test_list_folders_with_keyword` | keyword=重点；items 含「重点情报」 |
| 3 | `test_get_folder_detail_with_item_count` | data 含 item_count ≥ 0 |
| 4 | `test_create_duplicate_folder_name` | 第二次 code≠0；DUPLICATE msg |

**验收**：

```bash
pytest tests/integration/favorite/test_folder_router.py -v
```

---

#### 任务 C3（22:15–23:00）— 提交

```bash
git add apps/favorite/services/folder.py \
        apps/favorite/schemas/folder.py \
        apps/favorite/repositories/folder.py \
        apps/favorite/routers/folder.py \
        tests/unit/favorite/test_folder_service.py \
        tests/integration/favorite/test_folder_router.py
git commit -m "feat(favorite): implement folder create, list, detail with service and integration tests"
```

---

### 6.2 周四（2026-07-30）— Folder 收尾 + Item 加入/移除

**当日收口标准**：Folder 五个接口全部可用；Item POST/DELETE 可用；`.env.example` 初稿提交。

---

#### 任务 A6（08:30–09:45）— PATCH 重命名

**Repository 新增**：

```python
async def favorite_folder_update_name(
    session, folder: GriverFavoriteFolder, new_name: str
) -> GriverFavoriteFolder:
    folder.name = new_name
    # updated_at 由 DB onupdate 或手动设置
    await session.flush()
    return folder
```

**Schema**：`FavoriteFolderUpdateInSchema` — Body: `user_id`, `name`

**Service**：`rename_favorite_folder(user_id, folder_id, name)`

| 步骤 | 说明 |
|------|------|
| 1 | `find_by_id_and_user` → 无则 NotFound |
| 2 | strip + 长度校验 |
| 3 | 新名与当前名相同 → **仍成功**，刷新 updated_at（幂等） |
| 4 | 与他人 active folder 重名 → Duplicate |
| 5 | commit |

**Router**：`PATCH /{folder_id}` → 返回完整 folder 对象，HTTP 200

---

#### 任务 A7（09:45–11:00）— DELETE 软删 + 级联 item

**Repository 新增**：

| 函数 | 说明 |
|------|------|
| `favorite_folder_soft_delete(session, folder)` | `folder.is_deleted = True` |
| `favorite_item_soft_delete_by_folder_id(session, folder_id)` | 该 folder 下所有 `is_deleted=false` 的 item 置 true |

**Service**：`delete_favorite_folder(user_id, folder_id)`

- **同一事务**：先软删 items，再软删 folder  
- **禁止** UPDATE intelligence（R8）  
- commit

**Router**：`DELETE /{folder_id}?user_id=...` → `success(data={})`

**验收**：

- 删后 GET 详情 → NotFound  
- item 表对应行 `is_deleted=true`  
- intelligence 行不变

---

#### 任务 A8（11:00–12:00）— Folder Service 单测补全

在 `test_folder_service.py` 补充（可与集成测试分工）：

| 用例 | 预期 |
|------|------|
| keyword 含 `%` 不误匹配全表 | list total 精确 |
| page=0 → 当 1 | items 正常 |
| page_size=200 → 钳制 100 | len(items)≤100 |
| 软删后 list 不可见 | total 减少 |
| 软删后同名可新建 | create 成功 |

**目标**：design §10.1 中 folder 相关用例（1–18）在 unit 或 integration 中有对应且通过。

---

#### 任务 B5（14:00–15:00）— Item 异常 + IntegrityError

**扩充** `apps/favorite/exceptions.py`：

| 异常类 | msg |
|--------|-----|
| `FavoriteItemNotFoundException` | FAVORITE_ITEM_NOT_EXISTS |
| `FavoriteItemAlreadyExistsException` | FAVORITE_ITEM_ALREADY_EXISTS |
| `IntelligenceNotFoundException` | INTELLIGENCE_NOT_EXISTS |
| `FavoriteItemMoveFailedException` | FAVORITE_ITEM_MOVE_FAILED |

**修改** `apps/core/exception_handlers.py`：

- 在 `handle_integrity_error` 中识别 `uq_griver_favorite_item_folder_target_active` → `FAVORITE_ITEM_ALREADY_EXISTS`

---

#### 任务 B6（15:00–16:30）— Repository：item.py

**新建** `apps/favorite/repositories/item.py`（全 async，不 commit）：

| 函数 | 说明 |
|------|------|
| `favorite_item_create(session, folder_id, user_id, target_type, target_id)` | add + flush；`target_type=TARGET_TYPE_INTELLIGENCE` |
| `favorite_item_find_by_id_and_user(session, item_id, user_id)` | active item |
| `favorite_item_find_in_folder(session, folder_id, target_type, target_id)` | 是否已有（R2/R6） |
| `favorite_item_soft_delete(session, item)` | 单条软删 |
| `favorite_item_list_by_folder(session, folder_id, page, page_size, keyword)` | join intelligence；title ILIKE；返回 `(rows, total)` |

**list 响应行建议字段**：`item_id`, `intelligence_id`, `title`, `created_at`

---

#### 任务 B7（16:30–18:00）— POST 加入情报

**Schema**：`FavoriteItemCreateInSchema` — `user_id`, `intelligence_id`

**Service**：`add_item_to_folder(user_id, folder_id, intelligence_id)`

| 步骤 | 规则 |
|------|------|
| 1 | folder active（R3） |
| 2 | `intelligence_find_by_id_not_deleted`（R4） |
| 3 | `find_in_folder` 无重复（R2） |
| 4 | create + commit |
| 5 | 并发靠索引 + R9/R10 |

**Router**：`POST /folders/{folder_id}/items`，HTTP 201

**新建** `apps/favorite/routers/item.py`；在 `routers/__init__.py` `include_router`

> MQ Publisher 计划于周五接入；周四仅 commit，不发消息。

---

#### 任务 B8（18:00–19:00）— DELETE 移除情报

**Service**：`remove_item_from_folder(user_id, folder_id, item_id)`

- 校验 item 归属 folder + user  
- soft delete  
- commit

**Router**：`DELETE /folders/{folder_id}/items/{item_id}?user_id=...`

**验收**：移除后 GET items 无该条；intelligence 不变。

---

#### 任务 C4（20:30–22:00）— Folder 集成测试补全

在 `test_folder_router.py` 补全 design §10.1 剩余用例：

- NotFound（错误 folder_id）  
- 422 非法 UUID  
- PATCH 重命名成功 / 重名  
- DELETE 后详情 NotFound  
- 软删后 item 不可见（若已有 item seed）

---

#### 任务 C5（22:00–23:00）— `.env.example` + 提交

**新建** `.env.example`：

```env
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/griver_favorites
DATABASE_URL_SYNC=postgresql+psycopg://postgres:password@localhost:5432/griver_favorites
```

```bash
git commit -m "feat(favorite): complete folder CRUD and item add/remove"
```

**可选（低优先级）**：清理 `003_intelligence_seed.sql` 内 `CREATE TABLE`，仅保留 DELETE + INSERT。

---

### 6.3 周五（2026-07-31）— Item 收尾、Redis、MQ、Docker、交付

**当日收口标准**：§5 验收清单全部勾选；**23:00 前** push；**不安排周末顺延**。

---

#### F1（08:30–10:00）— PUT 移动情报 ✓ **已完成**

**Schema**：`FavoriteItemMoveInSchema` — `user_id`, `target_folder_id`

**Service**：`move_item(user_id, item_id, target_folder_id)`

| 步骤 | 规则 |
|------|------|
| 1 | 查 item 存在且属 user |
| 2 | R5：来源 folder 含该 item |
| 3 | target folder active；R6 目标无重复 |
| 4 | R7 单事务：来源 soft delete + 目标 create |
| 5 | commit；异常 rollback |

**Router**：`PUT /items/{item_id}/move`

**验收**：移动后来源列表无、目标有；注入异常时两边不变。

---

#### F2（10:00–11:30）— GET 收藏夹内情报列表 ✓ **已完成**

**Service**：`list_items_in_folder` → `favorite_item_list_by_folder`

**Query**：`user_id`, `page`, `size`/`page_size`, `keyword`（**intelligence.title**）

**Router**：`GET /folders/{folder_id}/items`

---

#### F3（11:30–12:00）— Item Service 单测 ✓ **已完成**

**新建** `tests/unit/favorite/test_item_service.py`

覆盖 design §10.2 核心：19–27（加入、重复、跨 folder、intel 不存在、移除、移动失败等）

---

#### F4（14:00–15:00）— Item 集成测试 ✓ **已完成**

**新建** `tests/integration/favorite/test_item_router.py`

| 场景 | 规则 |
|------|------|
| add 成功 | 201 |
| 同 folder 重复 | ALREADY_EXISTS |
| 不同 folder 同一 intel | 均成功（F9） |
| intel 已删 | INTELLIGENCE_NOT_EXISTS |
| folder 已删后 add | FOLDER_NOT_EXISTS |
| move 成功 | R7 |
| list keyword | 命中/未命中 title |

---

#### F5（15:00–15:45）— 并发重复收藏（R9）✓ **已完成**

**实现位置**：`tests/integration/favorite/test_item_router.py::test_concurrent_add_same_intelligence_same_folder`  
（原计划的独立文件 `test_concurrency.py` 可不再新建，除非希望目录拆分。）

- 同 folder 并发 N 次 POST add 同一 intelligence  
- 预期：最终仅 **1** 条 active item；其余 DUPLICATE

---

#### G（15:45–17:30）— Redis 全量 ✓ **已完成**

<details>
<summary>展开查看原步骤（供回溯）</summary>

**15:45–16:15 基础设施** ✓：`redis.py`、`cache_keys.py`、`schemas/cache.py`、`.env.example`

**16:15–17:00 Cache-Aside** ✓：`folder_cache.py`（get / invalidate / invalidate_many）

**17:00–17:30 接入 + 测试** ✓：Service 接入 + `test_folder_cache.py` **8 条**

验收：`pytest tests/unit/favorite/test_folder_cache.py -v` + `pytest tests/ -q`（101 passed）

</details>

---

#### H（17:30–19:30）— RabbitMQ 全量 ✓ **已完成**

<details>
<summary>展开查看原步骤（供回溯）</summary>

- migration 004 + `operation_log` repo ✓  
- `mq/publisher.py`；`add_item_to_folder` commit 后调用 ✓  
- `mq/consumer.py`；manual ack + 重试 + DLQ ✓  
- `test_mq_publisher.py` ×3、`test_mq_consumer.py` ×8、`test_mq_favorite_add.py` ×5 ✓  

</details>

---

#### I（19:30–20:30）— Docker + 日志 + 集成测收尾 ✓ **已完成**

**docker-compose.yml**（**仅基础设施**，app 本机 `uvicorn`）：

```yaml
services:
  postgres:    # 5432
  redis:       # 6379
  rabbitmq:    # 5672 / 15672
```

**日志**（design §9）：folder/item 写成功 INFO；业务异常 WARNING。

---

#### J（20:30–22:15）— 全量验证 ✓ **已完成**

```bash
docker compose up -d
alembic upgrade head
pytest tests/ --tb=short 2>&1 | tee test_results.txt   # 101 passed
```

走查：

- [x] `/docs` 9 接口可调用  
- [x] `rg 'session\.query' apps/` 无结果  
- [x] `Depends(get_folder_service)` 无多括号  

---

#### K（22:15–23:00）— 最终提交与验收 ✓ **基本完成**

对照 **§5** 逐项打勾；审查前可选 `git push` 最终版。

---

### 6.4 审查前剩余任务 — **已全部完成（2026-07-31 终版）**

> **背景**：9 API + Redis + MQ + Docker + 交付物均已完成；**101 passed**。  
> 下列任务保留供回溯；仅剩 **可选增强** 见 §3.2。

---

#### 任务 P0-G1：Redis Cache-Aside 业务接入 — **已完成 ✓**

<details>
<summary>展开查看原步骤（供回溯）</summary>

**步骤 1 — 缓存键与 DTO** ✓  
**步骤 2 — 缓存服务 `folder_cache.py`** ✓  
**步骤 3 — 接入 FolderService / ItemService** ✓  
**步骤 4 — `test_folder_cache.py` 8 条** ✓  

验收：`pytest tests/unit/favorite/test_folder_cache.py -v` + `pytest tests/ -q`（**101 passed**）

</details>

---

#### 任务 P0-ENG1：工程小修 — **已完成 ✓**（健康检查仍为可选）

| 项 | 文件 | 改动 | 状态 |
|----|------|------|------|
| 启动可见 Redis 日志 | `main.py` | `logging.basicConfig(level=logging.INFO)` | ✓ |
| 依赖声明 | `requirements.txt` | `redis>=5.2.0,<6`、`aio-pika>=9.5,<10` | ✓ |
| 健康检查（可选） | `main.py` 或 `/health` | 返回 `{"status":"ok","redis": true/false}` | △ 未做，见 §3.2 |

---

#### 任务 P1-I1：Docker Compose — **已完成 ✓**

`docker-compose.yml` 已落地（postgres:16、redis:7、rabbitmq:3-management；**不含 app 容器**）。

**验收**：

```bash
docker compose up -d
docker compose ps   # 三服务 healthy / running
redis-cli ping      # PONG
```

---

#### 任务 P1-H1：RabbitMQ 全链路 — **已完成 ✓**

完整版见 §6.3 H；已实现：

1. migration 004 + `operation_log` repo  
2. `publisher.py` + `add_item` commit 后发消息  
3. `consumer.py` manual ack + 重试 + DLQ  
4. 集成测 5 条 + 单元测 11 条（publisher 3 + consumer 8）

---

#### 任务 P1-README：README 审查版 — **已完成 ✓**

`README.md` 已包含：进度（101 passed）、Docker、迁移、测试、Consumer 启动、排查。

---

#### 任务 P2-J1：审查前全量验证 — **已完成 ✓**

- [x] `test_results.txt` 与 pytest 输出一致（101 passed）  
- [x] `/docs` 9 接口可调用  
- [x] `rg 'session\.query' apps/` 无结果  

---

#### 任务 P2-K1：Git 收尾 — **待审查前 push**

---

#### 任务完成时间线（归档）

| 顺序 | 任务 | 状态 |
|------|------|------|
| 1 | P0-ENG1 工程小修 | ✓ |
| 2 | P0-G1 Redis 业务 + 单测 | ✓ |
| 3 | P1-I1 docker-compose | ✓ |
| 4 | P1-README | ✓ |
| 5 | P1-H1 MQ 全链路 | ✓ |
| 6 | P2-J1 全量验证 | ✓ |
| 审查前 | P2-K1 git push | 待执行 |

---

## 7. 测试矩阵

### 7.1 Folder（design §10.1，18 条方向）

| # | 场景 | 预期 |
|---|------|------|
| 1–4 | create 合法/空名/超长/重名 | 201 或 DUPLICATE |
| 5–8 | list 分页/keyword/空 keyword/% 转义 | 200；total 正确 |
| 9–12 | detail 存在/NotFound/item_count | 200 或 NOT_EXISTS |
| 13–15 | PATCH 成功/重名/幂等同名 | 200 |
| 16–18 | DELETE 级联/列表不可见/同名可新建 | 200；item 软删 |

### 7.2 Redis 单测（8 条，已实现）

| # | 场景 |
|---|------|
| 1 | 命中不查 repo |
| 2 | 未命中查 DB 并 setex |
| 3 | 空值缓存 60s |
| 4 | rename 后 delete key |
| 5 | move 后双 key delete |
| 6 | redis_read 异常降级 |

### 7.3 MQ 集成（5 条）

| # | 场景 |
|---|------|
| 1 | 收藏成功发消息 |
| 2 | DB 失败不发 |
| 3 | 消费落库 |
| 4 | 重复 event_id |
| 5 | 3 次失败进 DLQ |

---

## 8. 关键文件清单（B2 起，均已落地）

| 路径 | 状态 | 计划节点 |
|------|------|----------|
| `apps/favorite/services/folder.py` | ✓ | 周三–周五 |
| `apps/favorite/services/item.py` | ✓ | 周四–周五 |
| `apps/favorite/services/cache/folder_cache.py` | ✓ | 周五 |
| `apps/core/redis.py` | ✓ | 周五 |
| `apps/favorite/repositories/folder.py` | ✓ | 周三–周四 |
| `apps/favorite/repositories/item.py` | ✓ | 周四 |
| `apps/favorite/repositories/operation_log.py` | ✓ | 周五 |
| `apps/favorite/mq/publisher.py` | ✓ | 周五 |
| `apps/favorite/mq/consumer.py` | ✓ | 周五 |
| `apps/favorite/routers/item.py` | ✓ | 周四 |
| `migrations/versions/004_*.py` | ✓ | 周五 |
| `docker-compose.yml` | ✓ | 周五 |
| `tests/unit/favorite/test_folder_service.py` | ✓ | 周三 |
| `tests/unit/favorite/test_item_service.py` | ✓ | 周五 |
| `tests/unit/favorite/test_folder_cache.py` | ✓ | 周五 |
| `tests/integration/favorite/test_folder_router.py` | ✓ | 周三–周四 |
| `tests/integration/favorite/test_item_router.py` | ✓ | 周五（含 R9 并发） |
| `tests/integration/favorite/test_mq_favorite_add.py` | ✓ | 周五 |
| `.env.example` | ✓ | 周四–周五 |

> 原计划 `test_concurrency.py` 未单独新建；R9 并发测位于 `test_item_router.py`。

---

## 9. 风险与应对

### 9.1 进度风险（已化解，归档）

| 时间点 | 原风险 | 实际结果 |
|--------|--------|----------|
| 周五 17:00 Redis | 可能未完成 | ✓ Cache-Aside + 8 条单测 |
| 周五 20:00 MQ | 可能未完成 | ✓ 全链路 + 16 条 MQ 相关测 |

### 9.2 交付底线（不建议裁剪）

- 9 API + R1–R10  
- Redis 详情 Cache-Aside + 写后失效  
- RabbitMQ 收藏事件 + 幂等  
- docker-compose（PG + Redis + RabbitMQ）  
- pytest 全绿 + test_results.txt  

---

## 10. 附录：已完成任务（A1–A5、B1）

供回溯，**无需重复执行**。

### A1 异步基础修正 ✓

| 文件 | 修正内容 |
|------|----------|
| `dependencies.py` | `return FolderService(session)`，去掉 `await` |
| `services/folder.py` | 删除错误 `__await__` |
| `database.py` | `get_db_session` 使用 `async with` |

### A2 测试 mock + 常量 ✓

- `test_routers.py`：`AsyncMock`  
- `constants.py`：TARGET_TYPE、PAGE_*、FOLDER_NAME_MAX_LEN  

### A3 models.py ✓

四表 ORM 与 migration 字段一致。

### A4 migration 003 ✓

`003_intelligence.py` 已建；seed 内 CREATE TABLE **待清理**。

### A5 folder Repository ✓

四函数 + `test_repo.py` 8 条 folder 用例。

### B1 intelligence Repository ✓

`intelligence_find_by_id_not_deleted` → `Intelligence | None`；单测含软删 seed。

---

## 11. 文档变更记录

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2026-07-28 | 初版 |
| v2.0 | 2026-07-29 | 纳入 Redis/MQ；周五 23:00 截止 |
| v2.1 | 2026-07-29 | 语气优化（过简，已废止） |
| v2.2 | 2026-07-29 | **全文重写**：恢复文件级/行为级细节；周四/周五任务完整展开；测试矩阵、伪代码、验收命令 |
| v2.3 | 2026-07-31 | **进度刷新**：§3 基线更新为 73 passed；F1–F5 标记完成；G 部分完成；新增 **§6.4 审查前剩余任务**；§5 验收清单打勾 |
| v2.4 | 2026-07-31 | G 完成；§3.4 入项对照 |
| v2.5 | 2026-07-31 | **终版进度**：H/I/J/K 完成；101 passed；MQ 集成测；docker-compose / README / test_results.txt |
