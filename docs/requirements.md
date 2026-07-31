# griver_favorites 需求与开发计划

| 字段 | 内容 |
|------|------|
| **文档类型** | 需求说明 + 可执行开发计划（文件级 / 行为级） |
| **版本** | v2.3 |
| **编制日期** | 2026-07-29（v2.2）；**进度刷新 2026-07-31** |
| **计划周期** | 2026-07-29（周三，自 B2 起）— 2026-07-31（周五）23:00 |
| **交付范围** | 9 HTTP 接口、业务规则 R1–R10、Redis Cache-Aside、RabbitMQ 操作日志、Docker Compose、全量自动化测试 |
| **当前工作项** | **G**：Redis Cache-Aside 业务接入（`folder_cache.py` + 写后失效 + 单测） |
| **关联文档** | [design.md](./design.md) v3.0、[api.md](./api.md) v2.0 |

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

## 3. 进度基线（2026-07-31 15:35 刷新）

> 以下以 **git 提交 + 仓库文件 + `pytest tests/` 结果** 为准。  
> **当前 pytest：73 passed**（单元 + 集成，含并发 R9）。

### 3.1 已完成（可审查展示）

#### 3.1.1 HTTP 接口（9/9）

| # | 方法 | 路径 | 实现文件 | 测试 |
|---|------|------|----------|------|
| 1 | POST | `/folders` | `routers/folder.py` | unit + integration |
| 2 | GET | `/folders` | 同上 | 同上 |
| 3 | GET | `/folders/{id}` | 同上 | 同上 |
| 4 | PATCH | `/folders/{id}` | 同上 | 同上 |
| 5 | DELETE | `/folders/{id}` | 同上 | 同上 |
| 6 | POST | `/folders/{id}/items` | `routers/item.py` | unit + integration |
| 7 | DELETE | `/folders/{id}/items/{item_id}` | 同上 | 同上 |
| 8 | PUT | `/items/{item_id}/move` | 同上 | integration + unit |
| 9 | GET | `/folders/{id}/items` | 同上 | integration（含 keyword） |

#### 3.1.2 业务层与规则

| 模块 | 路径 | 说明 |
|------|------|------|
| FolderService | `services/folder.py` | CRUD 全实现；A8 边界单测（分页钳制、keyword `%`、软删后 list/同名重建） |
| ItemService | `services/item.py` | add / remove / move / list；R4 情报校验已接 `intelligence_find_by_id_not_deleted` |
| Folder Repo | `repositories/folder.py` | 含 rename、soft_delete、级联 item、count_items、list |
| Item Repo | `repositories/item.py` | create / find / list / soft_delete |
| 异常 + 映射 | `exceptions.py`、`exception_handlers.py` | R10；item 唯一索引 → `FAVORITE_ITEM_ALREADY_EXISTS` |
| 配置 | `apps/core/config.py`、`.env`、`.env.example` | DB + Redis + RabbitMQ 环境变量 |
| CI | `ci.py` | 本地 lint / test 入口 |

#### 3.1.3 测试覆盖摘要

| 文件 | 条数 | 覆盖范围 |
|------|------|----------|
| `tests/unit/favorite/test_repo.py` | 21 | folder + item repo |
| `tests/unit/favorite/test_folder_service.py` | 14 | folder service（含 A8） |
| `tests/unit/favorite/test_item_service.py` | 12 | design §10.2 #19–27 |
| `tests/unit/favorite/test_routers.py` | 8 | 各 Router HTTP 形态（含 move + 列表） |
| `tests/integration/favorite/test_folder_router.py` | 10 | folder 集成 §10.1 |
| `tests/integration/favorite/test_item_router.py` | 8 | item 集成 F4 + **F5 并发 R9**（`test_concurrent_add_same_intelligence_same_folder`） |

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
| 周五 | F1–F5 | ✓ |
| 周五 | G（Redis 基建：客户端 + lifespan） | **部分** |
| 周五 | H（RabbitMQ）、I（Docker）、J/K（交付收尾） | ✗ |

### 3.2 未完成（审查前必须对齐预期）

| 项 | 现状 | 影响 |
|----|------|------|
| Redis Cache-Aside **业务层** | `apps/core/redis.py` + `main.py` lifespan 已有；**未**接 `get_favorite_folder_detail` | §5.2 未满足；详情仍直连 DB |
| Redis 写后失效 | rename/delete/add/remove/move 均未 `delete` cache key | 缓存即使接入也会脏读 |
| `test_folder_cache.py` | 未建 | §7.2 六条未覆盖 |
| RabbitMQ 全系 | 无 migration 004、无 publisher/consumer | §5.3 未满足 |
| `docker-compose.yml` | 无 | §5.4 未满足 |
| README 启动说明 | 未更新 Redis/MQ/compose | 审查第一印象 |
| `requirements.txt` 中 `redis` | 仍注释（venv 或已手动安装） | 他人 clone 后可能缺依赖 |
| `main.py` logging | 默认 WARNING，lifespan INFO 不可见 | 演示 Redis 初始化不直观 |
| `003_intelligence_seed.sql` CREATE TABLE | 仍未清理 | 低优先级 |

### 3.3 待完成总览

**审查前优先顺序**：G（Redis 业务）→ I（最简 compose + README）→ H（MQ 最小可演示）→ J/K（全量验证与 push）。  
详细步骤见 **§6.4**。

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
- [ ] `alembic upgrade head`：000–003 + **004_operation_log**
- [x] seed 002→003→004 可重复执行
- [x] 业务层无同步 Session / Redis / HTTP（Redis 客户端为 asyncio）

### 5.2 Redis

- [ ] Cache-Aside 读写正常
- [ ] 空值 TTL 60s 生效
- [ ] rename/delete/add/remove/move 后 key 失效
- [ ] move 双端失效
- [ ] 读失败降级 + 日志
- [ ] 写/删失败有日志
- [ ] 命中时不查 DB（单测验证）

### 5.3 RabbitMQ

- [ ] commit 成功后发消息
- [ ] 失败/rollback 不发
- [ ] Consumer 落库 + manual ack
- [ ] event_id 幂等
- [ ] 3 次失败进 DLQ
- [ ] Broker 不可用不影响 HTTP 成功 + ERROR 日志

### 5.4 工程交付

- [x] `pytest` 全绿（当前 73 passed）
- [x] `.env.example`
- [ ] `docker-compose.yml`
- [ ] README（启动、迁移、测试、consumer、排查）
- [ ] `test_results.txt` 可复现
- [ ] Git 提交清晰（审查前需 push 最终版）

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

#### G（15:45–17:30）— Redis 全量 — **进行中（基建 ✓，业务 ✗）**

**15:45–16:15 基础设施**

| 文件 | 内容 |
|------|------|
| `apps/core/redis.py` | `RedisRead` / `RedisWrite` 异步客户端；lifespan 或 Depends |
| `apps/favorite/common/cache_keys.py` | `def folder_detail_key(user_id, folder_id): ...` |
| `apps/favorite/schemas/cache.py` | `FolderDetailCacheDTO`；`to_json` / `from_json` |
| `.env.example` | `REDIS_READ_URL`、`REDIS_WRITE_URL`（可相同） |

**16:15–17:00 Cache-Aside**

文件：`apps/favorite/services/cache/folder_cache.py`

- `get_folder_detail_cached`（§2.8 伪代码）  
- `invalidate_folder_detail(user_id, folder_id)`  
- `invalidate_folder_detail_many([...])` 供 move 使用

**17:00–17:30 接入 + 测试**

- `get_favorite_folder_detail` 改调缓存层  
- **新建** `tests/unit/favorite/test_folder_cache.py`（6 条，见 §7.2）

---

#### H（17:30–19:30）— RabbitMQ 全量

**17:30–18:00 migration 004 + Repo**

- `migrations/versions/004_favorite_operation_log.py`  
- `repositories/operation_log.py`：`operation_log_create`；`event_id` UNIQUE

**18:00–18:45 Publisher**

- `apps/favorite/mq/publisher.py`  
- 在 `add_item_to_folder` **commit 之后**调用  
- Broker 异常：log error，不抛到 HTTP

**18:45–19:15 Consumer**

- `apps/favorite/mq/consumer.py`  
- 独立进程：`python -m apps.favorite.mq.consumer`（README 说明）  
- manual ack；幂等；3 次 → DLQ

**19:15–19:30 MQ 测试**

- `tests/integration/favorite/test_mq_favorite_add.py`（5 条，见 §7.3）

**`.env.example` 追加**：

```env
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
FAVORITE_EVENT_EXCHANGE=favorite.events
FAVORITE_OPERATION_LOG_QUEUE=favorite.operation_log
```

---

#### I（19:30–20:30）— Docker + 日志 + 集成测收尾

**docker-compose.yml**：

```yaml
services:
  postgres:
    image: postgres:16
    ports: ["5432:5432"]
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
      POSTGRES_DB: griver_favorites
  redis:
    image: redis:7
    ports: ["6379:6379"]
  rabbitmq:
    image: rabbitmq:3-management
    ports: ["5672:5672", "15672:15672"]
  app:
    build: .
    depends_on: [postgres, redis, rabbitmq]
    ports: ["8000:8000"]
    env_file: .env
```

**日志**（design §9）：folder/item 写成功 INFO；业务异常 WARNING；格式建议单行 JSON。

---

#### J（20:30–22:15）— 全量验证

```bash
docker compose up -d
alembic upgrade head
psql $DATABASE_URL_SYNC -f scripts/db/002_users_seed.sql
psql $DATABASE_URL_SYNC -f scripts/db/003_intelligence_seed.sql
psql $DATABASE_URL_SYNC -f scripts/db/004_favorite_seed.sql
pytest --tb=short 2>&1 | tee test_results.txt
```

**走查**：

- [ ] `/docs` 9 接口逐一点试  
- [ ] `rg 'session\.query' apps/` 无结果  
- [ ] `Depends(get_folder_service)` 无多括号

---

#### K（22:15–23:00）— 最终提交与验收

```bash
git commit -m "feat: complete favorite APIs with redis cache and rabbitmq logging"
git push
```

对照 **§5** 逐项打勾。

---

### 6.4 审查前剩余任务（2026-07-31 下午 → 明早，按优先级执行）

> **背景**：核心 9 API + 73 条 pytest 已绿；审查重点将转向 **Redis 缓存、MQ、工程化交付**。  
> 下列任务按 **必须 → 建议 → 可选** 排序；每项含：做什么、改哪些文件、怎么验收。

---

#### 任务 P0-G1：Redis Cache-Aside 业务接入（约 2h，最高优先级）

**目标**：GET `/folders/{id}` 详情走缓存；写操作后失效；满足 §5.2 核心四项。

**步骤 1 — 缓存键与 DTO（约 20min）**

| 文件 | 内容 |
|------|------|
| `apps/favorite/common/cache_keys.py` | `folder_detail_key(user_id, folder_id) -> str`，格式见 design §6.4：`folder:detail:{user_id}:{folder_id}` |
| `apps/favorite/schemas/cache.py` | `FolderDetailCacheDTO`：字段 `id, name, item_count, created_at, updated_at`；提供 `to_json()` / `from_json()` |

**步骤 2 — 缓存服务（约 40min）**

新建 `apps/favorite/services/cache/folder_cache.py`：

| 函数 | 行为 |
|------|------|
| `get_folder_detail_cached(session, redis_read, redis_write, user_id, folder_id)` | 先 `GET` key；命中 return；未命中查 DB 组装 DTO → `SETEX` 300s；NotFound 写空值 sentinel `{"__null__":true}` TTL 60s |
| `invalidate_folder_detail(redis_write, user_id, folder_id)` | `DELETE` 单 key |
| `invalidate_folder_detail_many(redis_write, keys)` | move 时删来源+目标 |

**读失败**：`try/except` 包住 redis_read，打 WARNING，降级直查 DB（design §6.4）。

**步骤 3 — 接入 FolderService（约 30min）**

| 写操作 | 失效时机 |
|--------|----------|
| `rename_favorite_folder` | commit 后 invalidate 该 folder |
| `delete_favorite_folder` | 同上 |
| `ItemService.add_item_to_folder` / `remove_item_from_folder` | commit 后 invalidate 该 folder |
| `ItemService.move_item` | commit 后 invalidate **来源 + 目标** |

`get_favorite_folder_detail` 改为调用 `get_folder_detail_cached`（Redis 客户端经 Depends 或构造注入）。

**步骤 4 — 单测（约 30min）**

新建 `tests/unit/favorite/test_folder_cache.py`，覆盖 §7.2 六条（mock redis + mock repo）：

1. 命中不查 repo  
2. 未命中查 DB 并 setex  
3. 空值缓存 60s  
4. rename 后 delete key  
5. move 后双 key delete  
6. redis_read 异常降级  

**验收命令**：

```bash
pytest tests/unit/favorite/test_folder_cache.py -v
pytest tests/ -q   # 全量仍绿
# 手动：连 redis，连续 GET 同一详情，第二次起 DB query 应减少（可用日志或断点）
```

---

#### 任务 P0-ENG1：工程小修（约 20min，审查演示用）

| 项 | 文件 | 改动 |
|----|------|------|
| 启动可见 Redis 日志 | `main.py` | 文件顶部 `logging.basicConfig(level=logging.INFO, format="...")` |
| 依赖声明 | `requirements.txt` | 取消注释 `redis>=5.2.0,<6` |
| 健康检查（可选） | `main.py` 或 `/health` | 返回 `{"status":"ok","redis": true/false}` 便于演示 |

---

#### 任务 P1-I1：Docker Compose 最简版（约 45min）

**目标**：审查时可说「一条命令起 PG + Redis + RabbitMQ」；app 仍可本地 `uvicorn` 连接。

新建 `docker-compose.yml`（可先不含 app  build，降低今晚工作量）：

- `postgres:16` → 5432  
- `redis:7` → 6379  
- `rabbitmq:3-management` → 5672 / 15672  

**验收**：

```bash
docker compose up -d
docker compose ps   # 三服务 healthy / running
redis-cli ping      # PONG
```

---

#### 任务 P1-H1：RabbitMQ 最小可演示链路（约 2–2.5h，时间紧可做「发消息 + 落库」简化版）

**完整版见 §6.3 H**；审查**最低线**：

1. **migration 004**：`favorite_operation_log` 表，`event_id` UNIQUE  
2. **`apps/favorite/mq/publisher.py`**：`publish_favorite_added(...)`，在 `add_item_to_folder` **commit 成功后**调用  
3. **Consumer 简化**：`python -m apps.favorite.mq.consumer` 消费一条写 `operation_log`；manual ack  
4. **集成测 1 条**：add 成功 → 等待 → log 表有记录  

Broker 不可用：publisher `except` 打 ERROR，**HTTP 仍 201**（§5.3 最后一条）。

若时间不够：**审查口述** design §6.5 设计 + 展示 `.env` 中 MQ 变量 + publisher 空壳，明晚补 consumer。

---

#### 任务 P1-README：README 审查版（约 30min）

更新 `README.md` 章节：

1. **当前进度**：9 API ✓、73 tests ✓、Redis/MQ 状态  
2. **环境要求**：Python 3.14、PostgreSQL、Redis、RabbitMQ  
3. **快速开始**：venv → pip → `.env` → alembic → seed → uvicorn  
4. **测试**：`pytest tests/ -q`  
5. **Docker**：`docker compose up -d`  
6. **MQ Consumer**（若已实现）：启动命令  

---

#### 任务 P2-J1：审查前全量验证（约 30min，明早执行）

```bash
pytest tests/ --tb=short 2>&1 | tee test_results.txt
uvicorn main:app --reload
# 浏览器打开 /docs，9 接口各点一次
```

走查清单：

- [ ] `test_results.txt` 与 CI 输出一致（全绿）  
- [ ] `/docs` 9 接口可调用  
- [ ] `rg 'session\.query' apps/` 无结果  

---

#### 任务 P2-K1：Git 收尾（审查前）

```bash
git add ...
git commit -m "feat(favorite): redis cache-aside and delivery docs"  # 按实际改动
git push
```

---

#### 建议时间分配（今晚 ~4h 可用时）

| 顺序 | 任务 | 时长 |
|------|------|------|
| 1 | P0-ENG1 工程小修 | 20min |
| 2 | P0-G1 Redis 业务 + 单测 | 2h |
| 3 | P1-I1 docker-compose | 45min |
| 4 | P1-README | 30min |
| 5 | P1-H1 MQ（能写多少写多少） | 剩余时间 |
| 明早 | P2-J1 + P2-K1 | 1h |

**若只能做一件事**：优先 **P0-G1**，审查时最有说服力。

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

### 7.2 Redis 单测（6 条）

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

## 8. 关键文件清单（B2 起）

| 路径 | 动作 | 计划节点 |
|------|------|----------|
| `apps/favorite/services/folder.py` | 补全 CRUD + 调缓存 | 周三–周五 |
| `apps/favorite/services/item.py` | **新建** | 周四–周五 |
| `apps/favorite/services/cache/folder_cache.py` | **新建** | 周五 17:30 前 |
| `apps/core/redis.py` | **新建** | 周五 16:15 前 |
| `apps/favorite/repositories/folder.py` | +count_items, update, soft_delete | 周三–周四 |
| `apps/favorite/repositories/item.py` | **新建** | 周四 |
| `apps/favorite/repositories/operation_log.py` | **新建** | 周五 |
| `apps/favorite/mq/publisher.py` | **新建** | 周五 |
| `apps/favorite/mq/consumer.py` | **新建** | 周五 |
| `apps/favorite/routers/item.py` | **新建** | 周四 |
| `migrations/versions/004_*.py` | **新建** | 周五 |
| `docker-compose.yml` | **新建** | 周五 |
| `tests/unit/favorite/test_folder_service.py` | B2 起编写 | 周三 |
| `tests/unit/favorite/test_item_service.py` | **新建** | 周五 |
| `tests/unit/favorite/test_folder_cache.py` | **新建** | 周五 |
| `tests/integration/favorite/test_folder_router.py` | **新建/补全** | 周三–周四 |
| `tests/integration/favorite/test_item_router.py` | **新建** | 周五 |
| `tests/integration/favorite/test_concurrency.py` | **新建** | 周五 |
| `tests/integration/favorite/test_mq_favorite_add.py` | **新建** | 周五 |
| `.env.example` | **新建/扩充** | 周四–周五 |

---

## 9. 风险与应对

### 9.1 进度风险

| 时间点 | 若滞后 | 建议保留最小集 |
|--------|--------|----------------|
| 周五 17:00 Redis 未完成 | Cache-Aside 读 + 写失效 + 1 条降级测 |
| 周五 20:00 MQ 未完成 | publish + consumer + 幂等 + DLQ 代码路径 |

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
