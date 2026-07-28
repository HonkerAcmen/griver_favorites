# 收藏夹模块 API 清单

> 项目：griver_favorites  
> 路由前缀：/grapi/v1/favorite  
> 设计文档：[design.md](./design.md)（v1.2）  
> 错误码定义以 design.md §8 为准；异步消息见 design.md §13

---

## 通用说明

### 鉴权

读写均 Depends(request_init(verify=True))。  
user_id 从 request.user_id 获取，请求体不传用户 ID。

| 场景 | HTTP |
|------|------|
| 未登录 / token 无效 | 401 |
| 参数格式错误（如 UUID 非法） | 422 |
| 业务错误（不存在、重名等） | 200，code 非 0 |

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

说明：numeric code 实现阶段向 GoldRiver 错误码段申请；字符串 msg 为稳定契约。

### 错误码一览

| 字符串标识 | 场景 |
|------------|------|
| FAVORITE_FOLDER_NOT_EXISTS | 收藏夹不存在、已软删或非本人 |
| FAVORITE_FOLDER_NAME_DUPLICATE | 创建或重命名时名称重复 |
| FAVORITE_FOLDER_NAME_INVALID | 空名或超过 100 字符 |

---

## 接口列表

| # | 方法 | 路径 | 说明 | 成功 HTTP |
|---|------|------|------|-----------|
| 1 | POST | /grapi/v1/favorite/folders | 创建收藏夹 | 201 |
| 2 | GET | /grapi/v1/favorite/folders | 分页列表 + 关键词搜索 | 200 |
| 3 | GET | /grapi/v1/favorite/folders/{folder_id} | 收藏夹详情 | 200 |
| 4 | PATCH | /grapi/v1/favorite/folders/{folder_id} | 重命名 | 200 |
| 5 | DELETE | /grapi/v1/favorite/folders/{folder_id} | 软删除 | 200 |

---

## 1. 创建收藏夹

POST /grapi/v1/favorite/folders

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | strip 后 1~100 Unicode 字符；区分大小写重名 |

响应 data：folder 对象（id, name, created_at, updated_at）

错误：FAVORITE_FOLDER_NAME_DUPLICATE / FAVORITE_FOLDER_NAME_INVALID

---

## 2. 分页列表 + 搜索

GET /grapi/v1/favorite/folders

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| page | int | 1 | 小于 1 按 1 处理 |
| size / page_size | int | 10 | 1~100；size 优先于 page_size |
| keyword | string | - | name 模糊搜索；空或空白视为未传 |

排序：updated_at DESC。不含 item_count。

---

## 3. 收藏夹详情

GET /grapi/v1/favorite/folders/{folder_id}

folder_id 须为合法 UUID，否则 422。

错误：FAVORITE_FOLDER_NOT_EXISTS（不区分不存在 / 非本人 / 已软删）

---

## 4. 重命名

PATCH /grapi/v1/favorite/folders/{folder_id}

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 同创建；改为原名视为成功 |

响应：更新后的完整 folder 对象。

错误：FAVORITE_FOLDER_NAME_DUPLICATE / FAVORITE_FOLDER_NAME_INVALID / FAVORITE_FOLDER_NOT_EXISTS

---

## 5. 软删除

DELETE /grapi/v1/favorite/folders/{folder_id}

响应 data 为空对象。软删后同名可新建。

错误：FAVORITE_FOLDER_NOT_EXISTS

---

## 预留接口（本期不实现）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /folders/{folder_id}/items | 添加收藏 |
| DELETE | /items/{item_id} | 移除收藏 |
| PUT | /items/{item_id}/move | 移动 |

跨模块职责见 design.md §11.2。
