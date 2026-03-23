from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.v1 import (
    auth_router,
    media_router,
    proxy_router,
    statistics_router,
    tasks_router,
    telegram_router,
    twitter_oauth_router,
    twitter_router,
    users_router,
)
from app.core.config import settings
from app.core.database import close_db, init_db
from app.core.middleware import setup_middlewares
from app.schemas.common import ApiResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    Path(settings.DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)
    yield
    await close_db()


app = FastAPI(
    title="Social Media Downloader API",
    description="Twitter 媒体下载与 Telegram 上传服务",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

setup_middlewares(app)

api_v1_router = FastAPI()
api_v1_router.include_router(auth_router)
api_v1_router.include_router(twitter_router)
api_v1_router.include_router(twitter_oauth_router)
api_v1_router.include_router(tasks_router)
api_v1_router.include_router(media_router)
api_v1_router.include_router(telegram_router)
api_v1_router.include_router(proxy_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(statistics_router)

app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health", tags=["健康检查"])
async def health_check():
    return ApiResponse(
        message="服务运行正常",
        data={
            "status": "healthy",
            "version": "1.0.0",
            "debug": settings.DEBUG,
        },
    )


@app.get("/", tags=["根路径"])
async def root():
    return ApiResponse(
        message="Social Media Downloader API",
        data={
            "docs": "/docs" if settings.DEBUG else "disabled",
            "health": "/health",
        },
    )


downloads_path = Path(settings.DOWNLOAD_DIR)
if downloads_path.exists():
    app.mount("/downloads", StaticFiles(directory=str(downloads_path)), name="downloads")
