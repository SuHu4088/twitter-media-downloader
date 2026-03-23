from enum import Enum

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class ProxyType(str, Enum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"


class ProxyConfig(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "proxy_configs"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    proxy_type: Mapped[str] = mapped_column(String(20), nullable=False, default=ProxyType.HTTP.value)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:
        return f"<ProxyConfig {self.name}>"

    def get_proxy_url(self) -> str:
        if self.username and self.password:
            return f"{self.proxy_type}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.proxy_type}://{self.host}:{self.port}"
