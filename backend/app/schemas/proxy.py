from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ProxyType(str, Enum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"


class ProxyConfigBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="配置名称")
    proxy_type: ProxyType = Field(default=ProxyType.HTTP, description="代理类型")
    host: str = Field(..., min_length=1, max_length=255, description="代理主机")
    port: int = Field(..., ge=1, le=65535, description="代理端口")
    username: str | None = Field(default=None, max_length=100, description="用户名")
    password: str | None = Field(default=None, max_length=255, description="密码")
    is_active: bool = Field(default=True, description="是否激活")

    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        return v.strip()


class ProxyConfigCreate(ProxyConfigBase):
    is_default: bool = Field(default=False, description="是否默认代理")


class ProxyConfigUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100, description="配置名称")
    proxy_type: ProxyType | None = Field(default=None, description="代理类型")
    host: str | None = Field(default=None, min_length=1, max_length=255, description="代理主机")
    port: int | None = Field(default=None, ge=1, le=65535, description="代理端口")
    username: str | None = Field(default=None, max_length=100, description="用户名")
    password: str | None = Field(default=None, max_length=255, description="密码")
    is_active: bool | None = Field(default=None, description="是否激活")
    is_default: bool | None = Field(default=None, description="是否默认代理")


class ProxyConfigResponse(BaseModel):
    id: UUID
    name: str
    proxy_type: str
    host: str
    port: int
    username: str | None
    has_password: bool = Field(..., description="是否设置了密码")
    is_active: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_model(cls, model) -> "ProxyConfigResponse":
        return cls(
            id=model.id,
            name=model.name,
            proxy_type=model.proxy_type,
            host=model.host,
            port=model.port,
            username=model.username,
            has_password=model.password is not None,
            is_active=model.is_active,
            is_default=model.is_default,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class ProxyTestRequest(BaseModel):
    test_url: str = Field(
        default="https://api.ipify.org?format=json",
        description="测试URL"
    )
    timeout: int = Field(default=10, ge=1, le=60, description="超时时间(秒)")


class ProxyTestResponse(BaseModel):
    success: bool
    message: str
    response_time: float | None = Field(default=None, description="响应时间(秒)")
    ip_address: str | None = Field(default=None, description="代理IP地址")
    error: str | None = Field(default=None, description="错误信息")
