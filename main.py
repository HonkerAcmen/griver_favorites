import importlib
import logging
import pkgutil
from pathlib import Path

from fastapi import FastAPI
from starlette import status

app = FastAPI()


def register_router(application: FastAPI):
    apps_dir = Path(__file__).parent / "apps"
    for module_info in pkgutil.iter_modules([str(apps_dir)]):
        module = importlib.import_module(f"apps.{module_info.name}")
        router = getattr(module, "on_init", None)

        if router is not None:
            application.include_router(router)




@app.get("/health")
async  def health():
    return {
        "status": "ok"
    }

register_router(app)