from app.api.v1.auth import router as auth_router
from app.api.v1.media import router as media_router
from app.api.v1.proxy import router as proxy_router
from app.api.v1.statistics import router as statistics_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.telegram import router as telegram_router
from app.api.v1.twitter import router as twitter_router
from app.api.v1.twitter_oauth import router as twitter_oauth_router
from app.api.v1.users import router as users_router

__all__ = [
    "auth_router",
    "media_router",
    "proxy_router",
    "statistics_router",
    "tasks_router",
    "telegram_router",
    "twitter_router",
    "twitter_oauth_router",
    "users_router",
]
