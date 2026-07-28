# griver_favorites

GoldRiver 收藏夹（Favorite）独立模块。用户可创建、搜索、重命名与软删除收藏夹；收藏项（`favorite_item`）表结构已预留，添加/移除/移动等能力在后续迭代实现。

架构参考 DogeX GoldRiver 分层规范：**Router → Service → Repository**。

## 文档

| 文档 | 说明 |
|------|------|
| [docs/design.md](docs/design.md) | 设计文档 v1.2（数据模型、分层、错误码、RabbitMQ 预留） |
| [docs/api.md](docs/api.md) | API 清单，路由前缀 `/grapi/v1/favorite` |

## 技术栈

- Python 3.14+
- [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn
- [SQLAlchemy 2](https://docs.sqlalchemy.org/) + [Alembic](https://alembic.sqlalchemy.org/)
- PostgreSQL（驱动：psycopg 3）
- pytest + httpx（测试）

## 项目结构

```
griver_favorites/
├── main.py                 # FastAPI 入口（当前为占位 health 接口）
├── test_main.py            # 基础 API 测试
├── alembic.ini             # Alembic 配置
├── migrations/             # 数据库迁移
│   ├── env.py              # 从 .env 读取 DATABASE_URL_SYNC
│   └── versions/
│       ├── 000_create_user.py
│       └── 001_favorite_folder.py
├── scripts/db/             # 参考 SQL（schema 快照、种子数据）
│   ├── 001_favorite_schema.sql
│   ├── 002_users_seed.sql
│   ├── 003_intelligence_seed.sql
│   └── 004_favorite_seed.sql
├── docs/                   # 设计与 API 文档
├── requirements.txt
└── requirements-dev.txt
```

## 快速开始

### 1. 环境要求

- Python 3.14+
- 本地 PostgreSQL（默认 `localhost:5432`）

### 2. 安装依赖

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

### 3. 配置环境变量

在项目根目录创建 `.env`：

```env
DATABASE_URL_SYNC=postgresql+psycopg://postgres:postgres@localhost:5432/griver_favorites
```

按实际 PostgreSQL 账号、密码、主机修改连接串。

### 4. 创建数据库

Alembic 不会自动建库，需先创建目标数据库：

```bash
# 方式一：psql
psql -h localhost -U postgres -d postgres -c "CREATE DATABASE griver_favorites;"

# 方式二：Python（需已配置 .env）
python -c "
from dotenv import load_dotenv; load_dotenv()
import os
from sqlalchemy import create_engine, text
url = os.environ['DATABASE_URL_SYNC'].rsplit('/', 1)[0] + '/postgres'
with create_engine(url, isolation_level='AUTOCOMMIT').connect() as c:
    if not c.execute(text(\"SELECT 1 FROM pg_database WHERE datname='griver_favorites'\")).scalar():
        c.execute(text('CREATE DATABASE griver_favorites'))
        print('created')
"
```

### 5. 执行迁移

**必须在项目根目录运行**（不要在 `migrations/` 子目录下）：

```bash
alembic upgrade head
alembic current   # 期望输出：001_favorite_folder (head)
```

迁移完成后将存在表：`users`、`griver_favorite_folder`、`griver_favorite_item`。

### 6. 启动服务

```bash
uvicorn main:app --reload
```

- 健康检查：<http://127.0.0.1:8000/health>
- OpenAPI 文档：<http://127.0.0.1:8000/docs>

### 7. 运行测试

```bash
pytest
```

## 数据库

### 迁移版本链

```
base → 000_create_user → 001_favorite_folder (head)
```

| 表 | 说明 |
|----|------|
| `users` | 用户表（本地开发 / 联调） |
| `griver_favorite_folder` | 收藏夹；`(user_id, name)` 在未删除记录上部分唯一 |
| `griver_favorite_item` | 收藏项（表已建，业务 API 后续实现） |

### Alembic 常用命令

```bash
alembic upgrade head          # 升级到最新
alembic upgrade +1            # 升级一个版本
alembic downgrade -1          # 回退一个版本
alembic current               # 查看当前版本
alembic history -v            # 查看迁移历史
alembic revision -m "描述"    # 新建空 migration
```

当前 `migrations/env.py` 中 `target_metadata = None`，未启用 `--autogenerate`；迁移文件以手写为主。

### 种子数据（可选）

按顺序执行 seed（可重复运行）：

```bash
# 需先 alembic upgrade head；将连接串换成你的 DATABASE_URL_SYNC
psql "$DATABASE_URL_SYNC" -f scripts/db/002_users_seed.sql
psql "$DATABASE_URL_SYNC" -f scripts/db/003_intelligence_seed.sql
psql "$DATABASE_URL_SYNC" -f scripts/db/004_favorite_seed.sql
```

数据量：5 用户、80 情报、15 收藏夹、105 收藏项。`target_type` 均为 `intelligence`；同一情报可出现在不同收藏夹。

## 本期功能范围

| 功能 | 状态 |
|------|------|
| 收藏夹 CRUD（创建 / 列表 / 搜索 / 详情 / 重命名 / 软删） | 设计中，待实现 |
| 收藏项添加 / 移除 / 移动 | 否，表结构已预留 |
| Redis 缓存 | 否 |
| RabbitMQ 事件 | 否，见 design.md §13 |

## 开发说明

- 业务代码将放在 `apps/favorite/`（Router / Service / Repository），与 GoldRiver 宿主对齐后接入鉴权 `request_init(verify=True)`。
- API 错误码与响应格式见 [docs/api.md](docs/api.md)；数值 `code` 实现阶段向 GoldRiver 错误码段申请。
- `.env` 已加入 `.gitignore`，勿提交真实凭据。

## License

内部项目，未指定开源协议。
