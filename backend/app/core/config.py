from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    DEBUG: bool = False

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/social_media"

    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    TWITTER_CLIENT_ID: str = ""
    TWITTER_CLIENT_SECRET: str = ""
    TWITTER_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/twitter/callback"

    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    TELEGRAM_API_ID: int | None = None
    TELEGRAM_API_HASH: str = ""

    REDIS_URL: str = "redis://localhost:6379/0"

    DOWNLOAD_DIR: str = "./downloads"
    MAX_DOWNLOAD_WORKERS: int = 3
    TDL_PATH: str = "./tdl"

    PROXY_HTTP: str | None = None
    PROXY_HTTPS: str | None = None

    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if v == "your-secret-key-change-in-production":
            import warnings
            warnings.warn(
                "使用默认 SECRET_KEY 不安全，请在生产环境中设置自定义密钥",
                UserWarning,
                stacklevel=2,
            )
        if len(v) < 32:
            raise ValueError("SECRET_KEY 长度必须至少为 32 个字符")
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v.startswith(("postgresql+asyncpg://", "postgresql://")):
            raise ValueError("DATABASE_URL 必须是 PostgreSQL 连接字符串")
        return v

    @property
    def proxy_dict(self) -> dict[str, str] | None:
        proxies = {}
        if self.PROXY_HTTP:
            proxies["http"] = self.PROXY_HTTP
        if self.PROXY_HTTPS:
            proxies["https"] = self.PROXY_HTTPS
        return proxies if proxies else None

    @property
    def is_production(self) -> bool:
        return not self.DEBUG


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
