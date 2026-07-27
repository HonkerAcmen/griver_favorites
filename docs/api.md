# 收藏夹模块 API 清单

> 项目：`griver_favorites`  
> 路由前缀：`/grapi/v1/favorite`  
> 设计文档：[design.md](./design.md)

---

## 通用说明

### 鉴权

读写均 `Depends(request_init(verify=True))`。  
`user_id` 从 `request.user_id` 获取，请求体不传用户 ID。

### 响应格式

```json
{
  "code": 0,
  "msg": "success",
  "data": {}
}
```

业务错误：HTTP 200，`code` 非 0。

---

## 接口列表

| # | 方法 | 路径 | 说明 |
|---|------|------|------|
| 1 | POST | `/grapi/v1/favorite/folders` | 创建收藏夹 |
| 2 | GET | `/grapi/v1/favorite/folders` | 分页列表 + 关键词搜索 |
| 3 | GET | `/grapi/v1/favorite/folders/{folder_id}` | 收藏夹详情 |
| 4 | PATCH | `/grapi/v1/favorite/folders/{folder_id}` | 重命名 |
| 5 | DELETE | `/grapi/v1/favorite/folders/{folder_id}` | 软删除 |

---

## 1. 创建收藏夹

**POST** `/grapi/v1/favorite/folders`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 1~100 字符，trim 后非空 |

**错误码**：`NAME_DUPLICATE` / `NAME_INVALID`

---

## 2. 分页列表 + 搜索

**GET** `/grapi/v1/favorite/folders`

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `page` | int | 1 | 页码 |
| `size` / `page_size` | int | 10 | 每页条数 |
| `keyword` | string | - | name 模糊搜索 |

---

## 3. 收藏夹详情

**GET** `/grapi/v1/favorite/folders/{folder_id}`

**错误码**：`FOLDER_NOT_EXISTS`

---

## 4. 重命名

**PATCH** `/grapi/v1/favorite/folders/{folder_id}`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 1~100 字符 |

---

## 5. 软删除

**DELETE** `/grapi/v1/favorite/folders/{folder_id}`

---

## 预留接口（本期不实现）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/folders/{folder_id}/items` | 添加收藏 |
| DELETE | `/items/{item_id}` | 移除收藏 |
| PUT | `/items/{item_id}/move` | 移动 |
