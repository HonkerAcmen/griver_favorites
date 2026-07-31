import importlib
import logging
import pkgutil
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from apps.core.exception_handlers import register_exception_handlers
from apps.core.rabbitmq import rabbitmq_service
from apps.core.redis import redis_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    await redis_service.init_redis()
    await rabbitmq_service.init_rabbitmq()   # 新增
    yield
    await rabbitmq_service.close()
    await redis_service.close()


logging.basicConfig(level=logging.INFO)
app = FastAPI(lifespan=lifespan)
register_exception_handlers(app)

def register_router(application: FastAPI):
    apps_dir = Path(__file__).parent / "apps"
    for module_info in pkgutil.iter_modules([str(apps_dir)]):
        module = importlib.import_module(f"apps.{module_info.name}")
        router = getattr(module, "on_init", None)

        if router is not None:
            application.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok"}


register_router(app)
