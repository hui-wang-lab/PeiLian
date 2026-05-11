"""FastAPI app 工厂 + 静态文件挂载。"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .routes import chat, personas, report, scenarios, session

_STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app() -> FastAPI:
    app = FastAPI(
        title="PeiLian 陪练系统",
        description="寿险代理人文本陪练 — Web UI + 可视化报告",
        version="0.1.0",
    )

    app.include_router(personas.router)
    app.include_router(scenarios.router)
    app.include_router(session.router)
    app.include_router(chat.router)
    app.include_router(report.router)

    if _STATIC_DIR.is_dir():
        app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")

    return app
