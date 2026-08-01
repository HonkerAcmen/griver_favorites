# griver_favorites

GoldRiver 情报收藏夹（Favorite）独立服务。支持收藏夹 CRUD、情报加入/移除/移动、分页筛选，以及收藏夹详情 Redis 缓存与 RabbitMQ 操作日志。

架构：**Router → Service → Repository**，参考 [DogeX GoldRiver](https://github.com/biteying/back_dogex_griver) 分层规范。

## 当前进度

| 模块 | 状态 |
|------|------|
| 9 个 HTTP API | ✓ |
| 业务规则 R1–R10 | ✓ |
| Redis Cache-Aside（详情 + item_count） | ✓ |
| RabbitMQ 收藏事件 + Consumer 落库 | ✓ |
| 自动化测试 | **101 passed**（`pytest tests/ -q`） |

## 文档

| 文档 | 说明 |
|------|------|
| [docs/design.md](docs/design.md) | 数据模型、分层、缓存/MQ 泳道图、测试设计（v3.2） |
| [docs/api.md](docs/api.md) | API 清单，路由前缀 `/grapi/v1/favorite`（v2.1） |
| [docs/requirements.md](docs/requirements.md) | 需求、验收清单、进度（v2.5） |

## 技术栈

- Python 3.14+
- [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn
- [SQLAlchemy 2](https://docs.sqlalchemy.org/) async + [Alembic](https://alembic.sqlalchemy.org/)
- PostgreSQL（asyncpg / psycopg 3）
- Redis 5（Cache-Aside）
- RabbitMQ + [aio-pika](https://aio-pika.readthedocs.io/)（收藏操作日志）
- pytest + httpx

## 项目结构

```
griver_favorites/
├── main.py                      # FastAPI 入口（lifespan 初始化 Redis / RabbitMQ）
├── docker-compose.yml           # PostgreSQL + Redis + RabbitMQ
├── alembic.ini
├── migrations/versions/         # 000–004
├── apps/
│   ├── core/                    # config, database, redis, rabbitmq
│   └── favorite/                # routers, services, repositories, mq
├── scripts/db/                  # 种子 SQL
├── tests/                       # unit + integration
├── docs/
├── requirements.txt
└── requirements-dev.txt
```

## 快速开始

### 1. 环境要求

- Python 3.14+
- Docker（推荐，用于 PostgreSQL / Redis / RabbitMQ）
- 或自行安装上述三个服务

### 2. 启动基础设施（Docker）

```bash
docker compose up -d
docker compose ps
```

| 服务 | 端口 | 说明 |
|------|------|------|
| PostgreSQL | 5432 | 用户 `postgres` / 密码 `password`，库 `griver_favorites` |
| Redis | 6379 | 无密码 |
| RabbitMQ | 5672 / 15672 | 管理台 `guest` / `guest`，<http://localhost:15672> |

### 3. 安装 Python 依赖

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

### 4. 配置环境变量

```bash
cp .env.example .env
```

默认连接串已与 `docker-compose.yml` 对齐；若使用自建数据库，请修改 `.env` 中对应项。

### 5. 数据库迁移

`docker compose` 首次启动时会自动创建 `griver_favorites` 库，直接执行迁移即可：

```bash
alembic upgrade head
alembic current    # 期望：004_favorite_operation_log (head)
```

### 6. 种子数据（可选，测试/联调推荐）

```bash
psql "$DATABASE_URL_SYNC" -f scripts/db/002_users_seed.sql
psql "$DATABASE_URL_SYNC" -f scripts/db/003_intelligence_seed.sql
psql "$DATABASE_URL_SYNC" -f scripts/db/004_favorite_seed.sql
```

数据量：5 用户、80 情报、15 收藏夹、105 收藏项。

### 7. 启动应用

**终端 1 — HTTP 服务：**

```bash
uvicorn main:app --reload
```

- 健康检查：<http://127.0.0.1:8000/health>
- OpenAPI：<http://127.0.0.1:8000/docs>

**终端 2 — MQ Consumer（收藏操作日志）：**

```bash
python -m apps.favorite.mq.consumer
```

收藏成功后，Publisher 发消息到 `favorite.events`；Consumer 写入 `favorite_operation_log` 表。

### 8. 运行测试

```bash
pytest tests/ -q
```

MQ 集成测（`tests/integration/favorite/test_mq_favorite_add.py`）需要 RabbitMQ 运行；不可用时自动 skip。

生成可复现结果文件：

```bash
pytest tests/ --tb=short 2>&1 | tee test_results.txt
```

## 功能范围

| 功能 | 说明 |
|------|------|
| 收藏夹 CRUD | 创建 / 列表 / 搜索 / 详情 / 重命名 / 软删 |
| 收藏项 | 加入 / 移除 / 移动 / 分页列表 / 标题筛选 |
| Redis | GET 详情 Cache-Aside；写操作后失效 |
| RabbitMQ | 加入收藏 commit 后发事件；Consumer 幂等落库 |

## 数据库

### 迁移版本链

```
base → 000_create_user → 001_favorite_folder → 002_favorite_folder
     → 003_intelligence → 004_favorite_operation_log (head)
```

| 表 | 说明 |
|----|------|
| `users` | 用户 |
| `intelligence` | 情报（只读引用） |
| `griver_favorite_folder` | 收藏夹 |
| `griver_favorite_item` | 收藏关系 |
| `favorite_operation_log` | MQ 消费操作日志（`event_id` UNIQUE 幂等） |

### Alembic 常用命令

```bash
alembic upgrade head
alembic downgrade -1
alembic current
alembic history -v
```

## 排查

| 现象 | 处理 |
|------|------|
| `alembic` ImportError / `_BindParamClause` | venv 中重装官方包：`pip uninstall -y uliweb-alembic alembic && pip install 'alembic>=1.14,<2'` |
| `redis.exceptions` 找不到 | `pip install --force-reinstall 'redis>=5.2,<6'` |
| uvicorn 启动失败（连不上 RabbitMQ） | 先 `docker compose up -d`，或确保 `.env` 中 `RABBITMQ_URL` 正确 |
| MQ 集成测 skip | 本地需运行 RabbitMQ（`docker compose up -d`） |

## 开发说明

- 业务代码在 `apps/favorite/`（Router / Service / Repository / mq）
- 统一响应与错误码见 [docs/api.md](docs/api.md)
- `.env` 已加入 `.gitignore`，勿提交真实凭据

## License

内部项目，未指定开源协议。
