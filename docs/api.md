# 收藏夹模块 API 清单

> 项目：griver_favorites  
> 路由前缀：`/grapi/v1/favorite`  
> 设计文档：[design.md](./design.md)（v3.1）  
> **版本**：v2.1（2026-07-31）  
> **实现状态**：9 个接口均已实现；**101 passed**  
> **本期无登录**：`user_id` 由 Body 或 Query 显式传入

---

## 实现说明

| 项 | 说明 |
|----|------|
| HTTP 层 | FastAPI Router → Service → Repository |
| 缓存 | **仅** GET `/folders/{folder_id}` 走 Redis Cache-Aside（TTL 300s / 空值 60s） |
| 写后失效 | PATCH/DELETE folder、POST/DELETE items、PUT move → 对应 folder 详情 key 删除 |
| MQ | **仅** POST `/folders/{folder_id}/items` 成功 commit 后发送 `favorite.item.added` |
| MQ 不可用 | HTTP 仍返回 201；Publisher 打 ERROR 日志，不影响收藏结果 |

Consumer 独立进程：`python -m apps.favorite.mq.consumer`，将消息写入 `favorite_operation_log`（`event_id` 幂等）。

---

## 通用说明

### 用户标识

本项目不实现登录与权限。需要用户隔离的接口须传 `user_id`（UUID）：

| 传递方式 | 适用 |
|----------|------|
| JSON Body | POST、PATCH、PUT |
| Query | GET、DELETE |

### 响应格式

成功：

```json
{
  "code": 0,
  "msg": "success",
  "data": {}
}
```

业务失败（HTTP 仍为 200）：

```json
{
  "code": 404001,
  "msg": "FAVORITE_FOLDER_NOT_EXISTS",
  "data": {}
}
```

| 场景 | HTTP |
|------|------|
| 参数格式错误（UUID 非法等） | 422 |
| 业务错误 | 200，code 非 0 |

### 错误码一览

| 字符串标识 | 场景 |
|------------|------|
| FAVORITE_FOLDER_NOT_EXISTS | 收藏夹不存在、已软删或非本人 |
| FAVORITE_FOLDER_NAME_DUPLICATE | 创建或重命名时名称重复 |
| FAVORITE_FOLDER_NAME_INVALID | 空名或超过 100 字符 |
| FAVORITE_ITEM_NOT_EXISTS | 收藏关系不存在或已软删 |
| FAVORITE_ITEM_ALREADY_EXISTS | 同收藏夹重复加入，或移动时目标已存在 |
| INTELLIGENCE_NOT_EXISTS | 情报不存在或已删除 |
| FAVORITE_ITEM_MOVE_FAILED | 移动时来源收藏夹不包含该情报 |

---

## 接口列表

| # | 方法 | 路径 | 说明 | 成功 HTTP | 副作用 |
|---|------|------|------|-----------|--------|
| 1 | POST | /grapi/v1/favorite/folders | 创建收藏夹 | 201 | — |
| 2 | GET | /grapi/v1/favorite/folders | 分页列表 + 名称搜索 | 200 | — |
| 3 | GET | /grapi/v1/favorite/folders/{folder_id} | 详情 + item_count | 200 | 读 Redis 缓存 |
| 4 | PATCH | /grapi/v1/favorite/folders/{folder_id} | 重命名 | 200 | 失效 folder 详情缓存 |
| 5 | DELETE | /grapi/v1/favorite/folders/{folder_id} | 软删除 | 200 | 级联软删 item；失效缓存 |
| 6 | POST | /grapi/v1/favorite/folders/{folder_id}/items | 加入情报 | 201 | 失效缓存；发 MQ |
| 7 | DELETE | /grapi/v1/favorite/folders/{folder_id}/items/{item_id} | 移除情报 | 200 | 失效缓存 |
| 8 | PUT | /grapi/v1/favorite/items/{item_id}/move | 移动情报 | 200 | 失效来源+目标缓存 |
| 9 | GET | /grapi/v1/favorite/folders/{folder_id}/items | 分页列表 + 标题筛选 | 200 | — |

---

## 1. 创建收藏夹

POST /grapi/v1/favorite/folders

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | UUID | 是 | 用户标识 |
| name | string | 是 | strip 后 1~100 字符；区分大小写重名 |

响应 data：`id, name, created_at, updated_at`

---

## 2. 分页列表 + 搜索

GET /grapi/v1/favorite/folders

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| user_id | UUID | 必填 | |
| page | int | 1 | 小于 1 按 1 |
| size / page_size | int | 10 | 1~100；size 优先 |
| keyword | string | - | folder.name 模糊搜索 |

---

## 3. 收藏夹详情

GET /grapi/v1/favorite/folders/{folder_id}

| 参数 | 类型 | 必填 |
|------|------|------|
| user_id | UUID | 是 |

响应 data：`id, name, item_count, created_at, updated_at`

**缓存**：优先读 Redis key `folder:detail:{user_id}:{folder_id}`；未命中查 DB 并回写。folder 不存在时写空值缓存（60s）。

---

## 4. 重命名

PATCH /grapi/v1/favorite/folders/{folder_id}

| 字段 | 类型 | 必填 |
|------|------|------|
| user_id | UUID | 是 |
| name | string | 是 |

写成功后失效该 folder 的 Redis 详情缓存。

---

## 5. 软删除

DELETE /grapi/v1/favorite/folders/{folder_id}?user_id=

级联软删收藏关系，不删除情报。

---

## 6. 加入情报

POST /grapi/v1/favorite/folders/{folder_id}/items

| 字段 | 类型 | 必填 |
|------|------|------|
| user_id | UUID | 是 |
| intelligence_id | UUID | 是 |

成功时：收藏关系入库 → **commit 后**发布 RabbitMQ 消息（`event_id` UUID、`action: favorite_add`）。DB 失败或 rollback 时不发消息。

---

## 7. 移除情报

DELETE /grapi/v1/favorite/folders/{folder_id}/items/{item_id}?user_id=

---

## 8. 移动情报

PUT /grapi/v1/favorite/items/{item_id}/move

| 字段 | 类型 | 必填 |
|------|------|------|
| user_id | UUID | 是 |
| target_folder_id | UUID | 是 |

同一事务完成；来源须包含、目标不能已有。

---

## 9. 收藏夹内情报列表

GET /grapi/v1/favorite/folders/{folder_id}/items

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| user_id | UUID | 必填 | |
| page | int | 1 | |
| size / page_size | int | 10 | |
| keyword | string | - | intelligence.title 模糊搜索 |

响应 items：`item_id, intelligence_id, title, created_at`

---

## 文档变更记录

| 版本 | 日期 | 变更摘要 |
|------|------|----------|
| v2.1 | 2026-07-31 | 实现状态；接口副作用列；Redis/MQ 说明；对齐 design v3.1 |
| v2.0 | 2026-07-28 | 9 接口字段与错误码定稿 |
