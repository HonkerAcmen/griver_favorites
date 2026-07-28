# griver_favorites 需求与开发计划

> **文档类型**：需求说明 + 可执行开发计划  
> **版本**：v1.0  
> **日期**：2026-07-28  
> **计划周期**：2026-07-29（周三）08:30 — 2026-07-31（周五）23:00  
> **关联文档**：[design.md](./design.md)（技术设计 v2.0）、[api.md](./api.md)（接口清单）

---

## 1. 文档目的

本文档回答三件事：

1. **项目要交付什么**（功能、规则、验收标准）  
2. **当前已经做了什么**（以 git 与代码为准）  
3. **接下来每一天具体要做什么**（写到文件级、行为级，避免「只做 TDD」这种看不懂的简称）

编码时：**业务规则以 design.md §2.3 为准**；**接口字段以 api.md 为准**；**本文件负责排期与任务拆解**。

---

## 2. 项目需求说明（你要做成什么样）

### 2.1 业务场景

运营人员把系统中**已经存在的情报**，整理进不同**收藏夹**，方便分类查看。

- 情报数据：只读引用，**不做**情报的增删改 API。  
- 用户身份：作业/本地环境**无登录**，`user_id` 由请求 **Body 或 Query 传入**。  
- 不做：登录、权限、MQ、Redis、前端页面。

### 2.2 必须实现的 10 项功能

1. **收藏夹**：创建、查询、重命名、软删除。  
2. **收藏夹列表**：分页 + 按收藏夹**名称**搜索。  
3. **收藏夹详情**：返回收藏夹信息 + **当前有效情报条数（item_count）**。  
4. **加入情报**：把指定情报加入指定收藏夹。  
5. **移除情报**：从收藏夹移除一条收藏关系（软删 item）。  
6. **移动情报**：从收藏夹 A 移到收藏夹 B。  
7. **收藏夹内情报列表**：分页展示。  
8. **按情报标题筛选**：列表支持 keyword 模糊搜 **intelligence.title**。  
9. **同一情报可进多个收藏夹**（不同 folder 可以重复同一 intelligence_id）。  
10. **删收藏夹不删情报**：只处理收藏关系，**不修改 intelligence 表**。

### 2.3 必须遵守的 10 条业务规则

| 编号 | 规则 | 实现要点 |
|------|------|----------|
| R1 | 有效收藏夹名称不能重复；名称先 strip 再校验 | Service 校验 + DB 部分唯一索引 `(user_id, name) WHERE is_deleted=false` |
| R2 | 同一情报不能重复加入**同一**收藏夹 | 唯一索引 `(folder_id, target_type, target_id) WHERE is_deleted=false` |
| R3 | 已删收藏夹不能查、改、加情报 | 所有 folder/item 写操作先查 `is_deleted=false` |
| R4 | 不存在或已删情报不能加入 | `repositories/intelligence.py` 只读校验 |
| R5 | 移动前来源收藏夹必须包含该 item | Service 内查 source folder 的 item |
| R6 | 目标收藏夹已有同一情报则移动失败 | 查 target 是否已有 active item |
| R7 | 移动必须单事务，失败全回滚 | 一次 `commit`，异常 `rollback` |
| R8 | 删 folder 级联软删 item，不动 intelligence | `delete_favorite_folder` 同一事务 |
| R9 | 并发重复收藏 DB 层保证唯一 | 依赖 R2 索引 + IntegrityError → 业务码 |
| R10 | 禁止暴露 DB 原始错误 | `exception_handlers` 映射 IntegrityError |

### 2.4 必须交付的 9 个 HTTP 接口

路由前缀：`/grapi/v1/favorite`（详见 api.md）

| # | 方法 | 路径 | 成功 HTTP |
|---|------|------|-----------|
| 1 | POST | `/folders` | 201 |
| 2 | GET | `/folders` | 200 |
| 3 | GET | `/folders/{folder_id}` | 200 |
| 4 | PATCH | `/folders/{folder_id}` | 200 |
| 5 | DELETE | `/folders/{folder_id}` | 200 |
| 6 | POST | `/folders/{folder_id}/items` | 201 |
| 7 | DELETE | `/folders/{folder_id}/items/{item_id}` | 200 |
| 8 | PUT | `/items/{item_id}/move` | 200 |
| 9 | GET | `/folders/{folder_id}/items` | 200 |

统一成功 body：`{"code":0,"msg":"success","data":...}`  
业务失败：HTTP **200** + `code != 0`；参数错误：HTTP **422**。

### 2.5 技术栈与架构约束

- **全链路异步**：`create_async_engine` + `AsyncSession`；Repository/Service 全部 `async def` + `await`。  
- **分层**：Router 只注入依赖、调 Service、返回 `success()`；Service 做规则与事务；Repository 只做 SQL/ORM。  
- **Migration**：Alembic 使用 `DATABASE_URL_SYNC`（psycopg）；运行时 `DATABASE_URL`（asyncpg）。  
- **测试**：Service 单元测试 mock Repository 或测真实逻辑；Router 集成测试用 TestClient + seed 数据。

---

## 3. 当前进度基线（2026-07-28 止）

以下根据 **git 提交与现有代码** 整理，作为计划起点。

### 3.1 已完成

| 类别 | 具体内容 |
|------|----------|
| 文档 | design v2.0、api v2.0、README、migrations/README.md |
| 数据库迁移 | `000_create_user`、`001_favorite_folder`（folder+item 表）、`002_favorite_folder`（item 唯一索引改为 folder 级） |
| Seed | `002_users_seed.sql`、`003_intelligence_seed.sql`、`004_favorite_seed.sql`（可重复执行） |
| 工程骨架 | `apps/favorite/` 目录、`on_init` 路由注册、`main.register_router` |
| 基础设施 | `apps/core/database.py`（async engine）、`dependencies.py`、`response.py`、`exception_handlers.py`、`exceptions.py`（folder 部分） |
| API | POST 创建收藏夹 Router 壳；Service `create_folder` 未完成写库 |
| 测试 | `tests/unit/favorite/test_routers.py` 1 条（mock Service） |

### 3.2 未完成（必须在周五 23:00 前补齐）

| 类别 | 缺口 |
|------|------|
| 迁移 | **`003_intelligence` 正式 migration**（目前 intelligence 表仅在 seed 里 `CREATE TABLE IF NOT EXISTS`） |
| 模型 | `apps/favorite/models.py`、`common/constants.py` |
| 仓储 | `repositories/folder.py`、`item.py`、`intelligence.py`（async） |
| 服务 | Folder 全 CRUD；Item 增删移查 |
| 路由 | GET 列表/详情、PATCH、DELETE；Item 四个接口；`routers/item.py` |
| 异步修复 | `dependencies` 勿 `await FolderService(...)`；删 Service 上错误 `__await__` |
| 测试 | `test_folder_service.py`；`test_item_service.py`；integration 全用例 |
| 配置 | `.env.example` |
| 日志 | Service 写操作 INFO / 业务异常 WARNING（design §9） |

---

## 4. 开发节奏与速度评估（基于 7/28 git）

### 4.1 你的作息（计划统一假设）

| 时段 | 安排 |
|------|------|
| 08:30–12:00 | 工作 |
| 12:00–14:00 | 午饭 + 午休 |
| 14:00–19:00 | 工作 |
| 19:00–20:30 | 晚饭 |
| 20:30–23:00 | 工作（提交频率通常更高） |
| 23:00 后 | 休息 |

**Wed–Fri 各 11 小时有效编码 ≈ 共 33 小时。**

### 4.2 7/28 提交频次（Mark Yang，16 次有效功能提交）

| 时段 | 提交数 | 约计时长 | 速度（次/小时） | 典型产出 |
|------|--------|----------|-----------------|----------|
| 14:32–16:37 | 5 | 2.1h | 2.4 | migration、Alembic、requirements |
| 18:26–19:21 | 3 | 0.9h | 3.3 | scaffold、database、dependencies |
| 21:39–23:12 | 9 | 1.5h | 6.0 | TDD、seed、异常、async |

**结论**：熟悉栈后速度明显加快；晚饭后块可按 **1 个完整功能模块（Repo+Service+Router+测）/ 1.5–2h** 估算。本计划按该速度排满 33h，**Friday 23:00 交付全部 9 接口 + 测试**。

---

## 5. 最终交付验收清单（2026-07-31 23:00 前）

完成以下全部项方可视为「全部写完」：

- [ ] 9 个 API 在 `/docs` 可调用，行为符合 api.md  
- [ ] R1–R10 有关键单测或集成测覆盖  
- [ ] `alembic upgrade head` 含 000–**003**  
- [ ] `pytest` 全绿（unit + integration）  
- [ ] seed 002→003→004 可重复执行  
- [ ] `.env.example` 已提交  
- [ ] 无同步 `Session` 混入业务层（全 async）  
- [ ] git 最终 commit + push  

---

## 6. 分日开发计划（详细任务说明）

---

### 6.1 周三 2026-07-29 — 异步修通 + Folder 读写的 3 个接口

**当日目标**：修复 async 基础问题；intelligence 正式进 migration；Folder 的 **创建、列表、详情** 三个接口真实写库/读库可用。

---

#### 任务 A1（08:30–09:00）修复异步基础三处 Bug

**为什么要做**：当前代码表面 async，但有致命错误，会导致测试或运行时报错。

**你要改的文件**：

1. `apps/favorite/dependencies.py`  
   - 错误：`return await FolderService(session)`  
   - 正确：`return FolderService(session)`  
   - 原因：类实例化不是 awaitable。

2. `apps/favorite/services/folder.py`  
   - 删除整个 `def __await__(self): pass`  
   - 原因：不需要、且实现非法。

3. `apps/core/database.py`  
   - 推荐写法：  
     ```python
     async def get_db_session():
         async with SessionLocal() as session:
             yield session
     ```  
   - 去掉 `finally` 里多余的 `await session.close()`（`async with` 已负责关闭）。

**验收**：`uvicorn main:app --reload` 能启动；import 无报错。

---

#### 任务 A2（09:00–09:30）测试 mock 改 async + 常量文件

**`tests/unit/favorite/test_routers.py`**：

- Router 里是 `await service.create_folder(...)`，mock 必须用 **`AsyncMock`**：  
  `mock_service.create_folder = AsyncMock(return_value={...})`  
- 返回字段与 api 一致：`id, name, created_at, updated_at`（不是 `folder_id`）。  
- 期望 `msg` 为 `"success"`（与 `apps/core/response.success` 一致）。

**新建 `apps/favorite/common/constants.py`**，至少包含：

```python
TARGET_TYPE_INTELLIGENCE = "intelligence"
FOLDER_NAME_MAX_LEN = 100
PAGE_DEFAULT = 10
PAGE_MAX = 100
```

**验收**：`pytest tests/unit/favorite/test_routers.py` 通过。

---

#### 任务 A3（09:30–10:30）ORM 模型 models.py

**新建 `apps/favorite/models.py`**，使用 SQLAlchemy 2.0 声明式 `DeclarativeBase`。

**需要映射的表**（表名、字段名必须与 migration 一致）：

| 模型类 | 表名 | 关键字段 |
|--------|------|----------|
| `Intelligence` | `intelligence` | id, user_id, title, is_deleted, created_at, updated_at |
| `GriverFavoriteFolder` | `griver_favorite_folder` | id, user_id, name, is_deleted, created_at, updated_at |
| `GriverFavoriteItem` | `griver_favorite_item` | id, folder_id, user_id, target_type, target_id, is_deleted, created_at |

**注意**：migration 003 完成前，intelligence 可能只在 seed 里建表；模型先写好，003 跑通后 ORM 与 DB 一致。

**验收**：`from apps.favorite.models import GriverFavoriteFolder` 无报错。

---

#### 任务 A4（10:30–11:15）Migration 003：intelligence 表

**新建** `migrations/versions/003_intelligence.py`（revision id 自定，`down_revision = "002_favorite_folder"`）。

**upgrade 应包含**：

- `CREATE TABLE intelligence (...)`  
- 索引：`idx_intelligence_user_active`、`idx_intelligence_title`  

**downgrade**：删表/删索引。

**同步修改** `scripts/db/003_intelligence_seed.sql`：**删除**其中的 `CREATE TABLE IF NOT EXISTS intelligence` 及建索引语句，**只保留** DELETE + INSERT（表由 migration 创建）。

**验收**：

```bash
alembic upgrade head
alembic current   # 应显示 003_xxx (head)
```

---

#### 任务 A5（11:15–12:00）Repository：folder.py（异步读写的核心）

**新建 `apps/favorite/repositories/folder.py`**，所有函数 **`async def`**，接收 `AsyncSession`，**不 commit**。

**至少实现**：

| 函数名 | 做什么 |
|--------|--------|
| `favorite_folder_create(session, user_id, name)` | 构造 ORM 对象，`session.add`，`await session.flush()` 拿到 id |
| `favorite_folder_find_by_id_and_user(session, folder_id, user_id)` | 查 `is_deleted=false` 且 id、user_id 匹配；无则 None |
| `favorite_folder_count_by_name(session, user_id, name)` | 同 user 未删同名计数（可选，也可只靠唯一索引） |
| `favorite_folder_list_by_user(session, user_id, page, page_size, keyword)` | 分页列表；keyword 空/空白不过滤；ILIKE 时对 `%` `_` 转义；排序 `updated_at DESC`；返回 `(items, total)` |

**写法示例**：`result = await session.execute(select(GriverFavoriteFolder).where(...))`  
**禁止**：`session.query(...)`（1.x 风格）。

---

#### 任务 B1（14:00–15:00）Repository：intelligence.py（只读）

**新建 `apps/favorite/repositories/intelligence.py`**。

| 函数名 | 做什么 |
|--------|--------|
| `intelligence_find_by_id_not_deleted(session, intelligence_id)` | 查 intelligence 存在且 `is_deleted=false`；否则 None |

后续 **POST 加入情报** 时，Service 调此函数满足 **R4**。

---

#### 任务 B2（15:00–16:30）TDD：FolderService.create_folder 真写库

**新建 `tests/unit/favorite/test_folder_service.py`**（先用 pytest-asyncio 或 anyio）。

**先写测试（Red）**：

1. 合法 name + seed 里 user_id → 返回 dict 含 id、name、created_at、updated_at。  
2. `name=""` 或全空格 → `FavoriteFolderNameInvalidException`。  
3. name 长度 101 → Invalid。  
4. 同一 user 连续创建同名 → 第二次 `FavoriteFolderNameDuplicateException`（或 IntegrityError 被上层映射）。

**再实现 `FolderService.create_folder`（Green）**：

1. `cleaned = name.strip()`  
2. 长度校验，非法抛 `FavoriteFolderNameInvalidException`  
3. `await favorite_folder_create(...)`  
4. `await self.session.commit()`  
5. 返回 folder 字段 dict（勿包 code/msg）

**验收**：单元测试绿；手动 POST 后 DB `griver_favorite_folder` 有新行。

---

#### 任务 B3（16:30–17:30）Router：POST 创建对齐规范

**改 `apps/favorite/routers/folder.py`**：

- 已有 `await service.create_folder`  
- 返回 `return success(data=folder)`，`success` 来自 `apps.core.response`  
- HTTP 201 保持不变  

**改 `apps/favorite/schemas/folder.py`**：

- `FavoriteFolderCreateInSchema`：`user_id: UUID`、`name: str`（建议 UUID 类型）

**验收**：

```bash
curl -X POST http://127.0.0.1:8000/grapi/v1/favorite/folders \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"fa500001-0001-4000-8000-000000000001","name":"测试夹"}'
```

返回 201，`code=0`，DB 有记录。

---

#### 任务 B4（17:30–19:00）GET 收藏夹分页列表 + 名称搜索

**Schema**：`FavoriteFolderListQueryParams`（FastAPI Query）

- `user_id: UUID`（必填）  
- `page: int = 1`（小于 1 当 1）  
- `size` / `page_size`（默认 10，最大 100，**size 优先**）  
- `keyword: Optional[str]`（空/空白当未传）

**Service**：`async def list_favorite_folders(...)` → 调 repo list，返回 `{items, total, page, page_size}`。

**Router**：`@router.get("")`，Query 注入， `return success(data=...)`。

**验收**：对 seed 用户 alice 搜 `keyword=重点` 能命中「重点情报」收藏夹。

---

#### 任务 C1（20:30–21:30）GET 收藏夹详情 + item_count

**Repository 新增**：`favorite_folder_count_items(session, folder_id)` — 统计该 folder 下 `is_deleted=false` 的 item 数。

**Service**：`async def get_favorite_folder_detail(user_id, folder_id)`  

- 调 `find_by_id_and_user`  
- 不存在 / 已软删 / user 不匹配 → `FavoriteFolderNotFoundException`（**R3**）  
- 返回 folder 字段 + **`item_count`**

**Router**：`GET /{folder_id}?user_id=...`

**验收**：详情 JSON 含 `item_count`，与 DB count 一致。

---

#### 任务 C2（21:30–22:15）集成测试（Folder 前 4 个能力）

**新建/扩充 `tests/integration/favorite/test_folder_router.py`**：

至少 4 条（可连真实 DB，先用 seed user）：

1. `test_create_folder_success`  
2. `test_list_folders_with_keyword`  
3. `test_get_folder_detail_with_item_count`  
4. `test_create_duplicate_folder_name` → 200 + DUPLICATE 码

**验收**：`pytest tests/integration/favorite/` 通过。

---

#### 任务 C3（22:15–23:00）提交

```bash
git add ...
git commit -m "feat(favorite): async folder create, list, detail with tests"
git push
```

**周三结束标准**：POST + GET 列表 + GET 详情 真实可用；003 migration 已建；async 基础 bug 已清。

---

### 6.2 周四 2026-07-30 — Folder 收尾 + Item 加入/移除

**当日目标**：Folder **5 接口全部完成** + Item **加入、移除** + Folder 集成测试 18 条 + `.env.example`。

---

#### 任务 A6（08:30–09:45）PATCH 重命名收藏夹

**Repository**：`favorite_folder_update_name(session, folder, new_name)` — 更新 name、updated_at。

**Schema**：`FavoriteFolderUpdateInSchema`（body：`user_id`, `name`）。

**Service**：`rename_favorite_folder`  

- 先 `find_by_id_and_user`，无则 NotFound  
- strip + 长度校验  
- 新名与当前名相同 → **仍算成功**，更新 updated_at（幂等）  
- 与他人未删 folder 重名 → Duplicate  

**Router**：`PATCH /{folder_id}`，返回**完整 folder 对象**（HTTP 200）。

---

#### 任务 A7（09:45–11:00）DELETE 软删收藏夹 + 级联 item

**Repository**：

- `favorite_folder_soft_delete(session, folder)` — folder `is_deleted=true`  
- `favorite_item_soft_delete_by_folder_id(session, folder_id)` — 该 folder 下所有 active item 软删  

**Service**：`delete_favorite_folder` — **同一事务**内先级联 item 再删 folder，**一次 commit**（**R8**）。**禁止** UPDATE intelligence。

**Router**：`DELETE /{folder_id}?user_id=...`，成功 `success(data={})`。

**验收**：删后 GET 详情 NotFound；item 表对应行 is_deleted=true；intelligence 不变。

---

#### 任务 A8（11:00–12:00）Folder Service 单测补全（design §10.1）

在 `test_folder_service.py` 补用例，覆盖例如：

- keyword 含 `%` 不误匹配  
- page=0 → 当 page=1  
- page_size=200 → 钳制 100  
- 软删后列表不可见  
- 软删后同名可新建  

**验收**：§10.1 表格 18 条在 unit 或 integration 中有对应测试且通过。

---

#### 任务 B5（14:00–15:00）Item 相关异常 + IntegrityError 扩展

**扩充 `apps/favorite/exceptions.py`**：

| 异常类 | msg 字符串 |
|--------|------------|
| `FavoriteItemNotFoundException` | FAVORITE_ITEM_NOT_EXISTS |
| `FavoriteItemAlreadyExistsException` | FAVORITE_ITEM_ALREADY_EXISTS |
| `IntelligenceNotFoundException` | INTELLIGENCE_NOT_EXISTS |
| `FavoriteItemMoveFailedException` | FAVORITE_ITEM_MOVE_FAILED |

**改 `apps/core/exception_handlers.py`**：  
在 `handle_integrity_error` 中增加对 `uq_griver_favorite_item_folder_target_active` 的判断 → 映射 **ALREADY_EXISTS**。

---

#### 任务 B6（15:00–16:30）Repository：item.py

**新建 `apps/favorite/repositories/item.py`**（全 async）：

| 函数 | 说明 |
|------|------|
| `favorite_item_create` | 创建 item，target_type 用 constants 里 `intelligence` |
| `favorite_item_find_by_id_and_user` | 按 item_id + user 查 active |
| `favorite_item_find_in_folder` | folder 内是否已有 target_id（R2/R6） |
| `favorite_item_soft_delete` | 单条软删 |
| `favorite_item_list_by_folder` | 分页 + join intelligence 按 title keyword 过滤 |

---

#### 任务 B7（16:30–18:00）POST 加入情报

**Schema**：`FavoriteItemCreateInSchema` — `user_id`, `intelligence_id`。

**Service**：`add_item_to_folder(user_id, folder_id, intelligence_id)`  

1. folder 须 active（R3）  
2. intelligence 须 active（R4）  
3. folder 内尚无同一 intelligence（R2）  
4. create + commit  
5. 并发重复靠唯一索引 + R9/R10  

**Router**：`POST /folders/{folder_id}/items`，HTTP **201**。

**新建 `apps/favorite/routers/item.py`**，并在 `routers/__init__.py` 里 `include_router(item_router)`。

---

#### 任务 B8（18:00–19:00）DELETE 从收藏夹移除情报

**Service**：`remove_item_from_folder(user_id, folder_id, item_id)` — 校验归属后 soft delete item。

**Router**：`DELETE /folders/{folder_id}/items/{item_id}?user_id=...`

**验收**：移除后 GET items 列表无该条；intelligence 行不变。

---

#### 任务 C4（20:30–22:00）Folder 集成测试 18 条补齐

在 `test_folder_router.py` 补全 design §10.1 剩余用例（NotFound、422 非法 UUID、重命名、软删等）。

**验收**：folder 相关集成测试完整绿。

---

#### 任务 C5（22:00–23:00）`.env.example` + commit

**新建 `.env.example`**：

```env
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/griver_favorites
DATABASE_URL_SYNC=postgresql+psycopg://postgres:password@localhost:5432/griver_favorites
```

**commit**：`feat(favorite): complete folder CRUD; item add/remove`

**周四结束标准**：Folder 全完成；Item 加入/移除可用。

---

### 6.3 周五 2026-07-31 — Item 移动/列表 + 全量测试 + 交付

**当日目标**：剩余 **移动、item 列表**；item 单测/集成测；日志；全项目 pytest 绿；文档与最终 commit。

---

#### 任务 F1（08:30–10:00）PUT 移动情报（最难，整块时间）

**Schema**：`FavoriteItemMoveInSchema` — `user_id`, `target_folder_id`。

**Service**：`move_item(user_id, item_id, target_folder_id)`  

1. 查 item 存在且属于 user  
2. **R5**：当前 item 的 folder_id 即来源（或校验仍在来源 folder）  
3. target folder 须 active，且 **R6** target 内无同一 intelligence  
4. **R7 单事务**：  
   - 方案 A：来源 item 软删 + 在 target 新建 item  
   - 方案 B：更新 item.folder_id（若业务允许）  
   - 任一步失败 `await session.rollback()`  
5. commit  

**Router**：`PUT /items/{item_id}/move`

**验收**：移动后来源列表无、目标列表有；中途异常时两边不变。

---

#### 任务 F2（10:00–11:30）GET 收藏夹内情报列表

**Schema**：Query — `user_id`, `page`, `size`/`page_size`, `keyword`（搜 **intelligence.title**）。

**Service**：`list_items_in_folder` — 调 repo 分页 join intelligence。

**Router**：`GET /folders/{folder_id}/items`

**响应 items 元素**：`item_id`, `intelligence_id`, `title`, `created_at`（见 api.md §9）。

---

#### 任务 F3（11:30–12:00）Item Service 单测

**新建 `tests/unit/favorite/test_item_service.py`**：覆盖 §10.2 中 19–27 的核心（加入、重复、跨 folder 重复、intel 不存在、移除、移动失败等）。

---

#### 任务 F4（14:00–16:00）Item 集成测试

**新建 `tests/integration/favorite/test_item_router.py`**：  
对 seed 数据测 add、duplicate in folder、add same intel to two folders（**规则 9**）、move、list keyword、delete folder 后 item 不可见等。

---

#### 任务 F5（16:00–17:00）Service 层日志

在 folder/item 写成功路径打 INFO（user_id, folder_id, item_id 等）；捕获业务异常前打 WARNING。  
格式可参考 design §9 一行 JSON。

**若时间紧**：至少 create/delete/move 三条 INFO。

---

#### 任务 F6（17:00–18:00）全局走查

- `/docs` 9 个接口逐个点试  
- grep 项目：无 `session.query`、业务层无同步 `Session`  
- `Depends(get_db_session)` 无括号错误  

---

#### 任务 F7（18:00–19:00）从零验证

```bash
alembic downgrade base && alembic upgrade head
psql ... -f scripts/db/002_users_seed.sql
psql ... -f scripts/db/003_intelligence_seed.sql
psql ... -f scripts/db/004_favorite_seed.sql
pytest
```

---

#### 任务 F8（20:30–21:30）文档对齐

核对 `api.md`、`README.md` 中 seed 顺序、接口说明与实现一致。

---

#### 任务 F9（21:30–22:15）修红测 + async 遗留

Fix 所有 pytest failure；integration 里 async mock 问题。

---

#### 任务 F10（22:15–22:45）最终提交

```bash
git commit -m "feat(favorite): complete async folder and item APIs with full TDD tests"
git push
```

---

#### 任务 F11（22:45–23:00）对照 §5 交付清单逐项打勾

---

## 7. 文件清单速查（你要创建/改动的路径）

| 路径 | 动作 |
|------|------|
| `apps/core/database.py` | 修 session 依赖 |
| `apps/core/response.py` | 已有，使用 `success()` |
| `apps/core/exception_handlers.py` | 扩展 item 索引映射 |
| `apps/favorite/common/constants.py` | **新建** |
| `apps/favorite/models.py` | **新建** |
| `apps/favorite/exceptions.py` | 补 item 异常 |
| `apps/favorite/schemas/folder.py` | 补 List/Update Query |
| `apps/favorite/schemas/item.py` | **新建** |
| `apps/favorite/repositories/folder.py` | **新建** |
| `apps/favorite/repositories/item.py` | **新建** |
| `apps/favorite/repositories/intelligence.py` | **新建** |
| `apps/favorite/services/folder.py` | **补全 CRUD** |
| `apps/favorite/services/item.py` | **新建** |
| `apps/favorite/routers/folder.py` | **补 GET/PATCH/DELETE** |
| `apps/favorite/routers/item.py` | **新建** |
| `apps/favorite/routers/__init__.py` | include item router |
| `apps/favorite/dependencies.py` | 修 + 可选 `get_item_service` |
| `migrations/versions/003_*.py` | **新建** intelligence |
| `tests/unit/favorite/test_folder_service.py` | **新建** |
| `tests/unit/favorite/test_item_service.py` | **新建** |
| `tests/integration/favorite/test_folder_router.py` | **新建/补全** |
| `tests/integration/favorite/test_item_router.py` | **新建** |
| `.env.example` | **新建** |

---

## 8. 风险与降级（仅当超时）

若周五 20:00 仍落后，按顺序砍：

1. F5 日志简化为 1 条  
2. F8 只更新 api.md 表格，README 不改  
3. 集成测先保 **主路径**（create/list/add/move），边界用例后补  

**不可砍**：移动单事务 R7、folder 级唯一索引 R2/R9、9 接口主流程。

---

## 9. 文档变更记录

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2026-07-28 | 初版：需求说明 + Wed–Fri 33h 详细开发计划 |
