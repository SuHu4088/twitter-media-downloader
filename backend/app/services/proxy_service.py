import time
import uuid
from uuid import UUID

import httpx
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.core.security import decrypt_token, encrypt_token
from app.models.proxy_config import ProxyConfig
from app.schemas.proxy import (
    ProxyConfigCreate,
    ProxyConfigResponse,
    ProxyConfigUpdate,
    ProxyTestRequest,
    ProxyTestResponse,
)


class ProxyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_proxy_config(self, config_in: ProxyConfigCreate) -> ProxyConfig:
        result = await self.db.execute(
            select(ProxyConfig).where(ProxyConfig.name == config_in.name)
        )
        if result.scalar_one_or_none():
            raise BadRequestException(message="代理配置名称已存在")

        encrypted_password = None
        if config_in.password:
            encrypted_password = encrypt_token(config_in.password)

        if config_in.is_default:
            await self.db.execute(
                update(ProxyConfig)
                .where(ProxyConfig.is_default == True)
                .values(is_default=False)
            )

        config = ProxyConfig(
            name=config_in.name,
            proxy_type=config_in.proxy_type.value,
            host=config_in.host,
            port=config_in.port,
            username=config_in.username,
            password=encrypted_password,
            is_active=config_in.is_active,
            is_default=config_in.is_default,
        )

        self.db.add(config)
        await self.db.flush()
        await self.db.refresh(config)

        return config

    async def update_proxy_config(
        self, config_id: UUID, config_in: ProxyConfigUpdate
    ) -> ProxyConfig:
        config = await self.get_proxy_config(config_id)

        update_data = config_in.model_dump(exclude_unset=True)

        if "name" in update_data:
            result = await self.db.execute(
                select(ProxyConfig).where(
                    ProxyConfig.name == update_data["name"],
                    ProxyConfig.id != config_id,
                )
            )
            if result.scalar_one_or_none():
                raise BadRequestException(message="代理配置名称已存在")

        if "password" in update_data and update_data["password"]:
            update_data["password"] = encrypt_token(update_data["password"])

        if update_data.get("is_default") == True:
            await self.db.execute(
                update(ProxyConfig)
                .where(ProxyConfig.is_default == True)
                .values(is_default=False)
            )

        for key, value in update_data.items():
            setattr(config, key, value)

        await self.db.flush()
        await self.db.refresh(config)

        return config

    async def delete_proxy_config(self, config_id: UUID) -> None:
        config = await self.get_proxy_config(config_id)
        await self.db.delete(config)

    async def get_proxy_config(self, config_id: UUID) -> ProxyConfig:
        result = await self.db.execute(
            select(ProxyConfig).where(ProxyConfig.id == config_id)
        )
        config = result.scalar_one_or_none()

        if not config:
            raise NotFoundException(message="代理配置不存在")

        return config

    async def get_proxy_configs(
        self,
        page: int = 1,
        page_size: int = 20,
        is_active: bool | None = None,
    ) -> tuple[list[ProxyConfig], int]:
        query = select(ProxyConfig)

        if is_active is not None:
            query = query.where(ProxyConfig.is_active == is_active)

        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        result = await self.db.execute(
            query.order_by(ProxyConfig.is_default.desc(), ProxyConfig.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        configs = result.scalars().all()

        return list(configs), total

    async def get_active_proxy(self) -> ProxyConfig | None:
        result = await self.db.execute(
            select(ProxyConfig).where(
                ProxyConfig.is_active == True,
                ProxyConfig.is_default == True,
            )
        )
        config = result.scalar_one_or_none()

        if not config:
            result = await self.db.execute(
                select(ProxyConfig).where(ProxyConfig.is_active == True)
            )
            config = result.scalar_one_or_none()

        return config

    async def test_proxy_connection(
        self, config_id: UUID, test_request: ProxyTestRequest
    ) -> ProxyTestResponse:
        config = await self.get_proxy_config(config_id)

        password = None
        if config.password:
            try:
                password = decrypt_token(config.password)
            except Exception:
                password = config.password

        if config.username and password:
            proxy_url = f"{config.proxy_type}://{config.username}:{password}@{config.host}:{config.port}"
        else:
            proxy_url = f"{config.proxy_type}://{config.host}:{config.port}"

        proxies = {
            "http://": proxy_url,
            "https://": proxy_url,
        }

        start_time = time.time()

        try:
            async with httpx.AsyncClient(
                proxies=proxies,
                timeout=test_request.timeout,
                follow_redirects=True,
            ) as client:
                response = await client.get(test_request.test_url)
                response_time = time.time() - start_time

                ip_address = None
                try:
                    data = response.json()
                    ip_address = data.get("ip")
                except Exception:
                    pass

                return ProxyTestResponse(
                    success=True,
                    message="代理连接成功",
                    response_time=round(response_time, 3),
                    ip_address=ip_address,
                )

        except httpx.TimeoutException:
            return ProxyTestResponse(
                success=False,
                message="代理连接超时",
                error="连接超时",
            )
        except httpx.ProxyError as e:
            return ProxyTestResponse(
                success=False,
                message="代理连接失败",
                error=str(e),
            )
        except Exception as e:
            return ProxyTestResponse(
                success=False,
                message="代理测试失败",
                error=str(e),
            )

    async def set_default_proxy(self, config_id: UUID) -> ProxyConfig:
        config = await self.get_proxy_config(config_id)

        if not config.is_active:
            raise BadRequestException(message="无法将未激活的代理设置为默认代理")

        await self.db.execute(
            update(ProxyConfig)
            .where(ProxyConfig.is_default == True)
            .values(is_default=False)
        )

        config.is_default = True
        await self.db.flush()
        await self.db.refresh(config)

        return config

    @staticmethod
    def get_proxy_url(config: ProxyConfig) -> str | None:
        if not config or not config.is_active:
            return None

        password = None
        if config.password:
            try:
                password = decrypt_token(config.password)
            except Exception:
                password = config.password

        if config.username and password:
            return f"{config.proxy_type}://{config.username}:{password}@{config.host}:{config.port}"
        return f"{config.proxy_type}://{config.host}:{config.port}"

    @staticmethod
    def get_proxy_dict(config: ProxyConfig) -> dict[str, str] | None:
        proxy_url = ProxyService.get_proxy_url(config)
        if not proxy_url:
            return None

        return {
            "http://": proxy_url,
            "https://": proxy_url,
        }
