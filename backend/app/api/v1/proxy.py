from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import ActiveUser, DBSession
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.proxy import (
    ProxyConfigCreate,
    ProxyConfigResponse,
    ProxyConfigUpdate,
    ProxyTestRequest,
    ProxyTestResponse,
)
from app.services.proxy_service import ProxyService

router = APIRouter(prefix="/proxy", tags=["代理配置"])


@router.post("", response_model=ApiResponse[ProxyConfigResponse], status_code=status.HTTP_201_CREATED)
async def create_proxy_config(
    config_in: ProxyConfigCreate,
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[ProxyConfigResponse]:
    service = ProxyService(db)
    config = await service.create_proxy_config(config_in)
    return ApiResponse(
        message="代理配置创建成功",
        data=ProxyConfigResponse.from_model(config),
    )


@router.get("", response_model=ApiResponse[PaginatedResponse[ProxyConfigResponse]])
async def list_proxy_configs(
    db: DBSession,
    current_user: ActiveUser,
    page: int = 1,
    page_size: int = 20,
    is_active: bool | None = None,
) -> ApiResponse[PaginatedResponse[ProxyConfigResponse]]:
    service = ProxyService(db)
    configs, total = await service.get_proxy_configs(
        page=page,
        page_size=page_size,
        is_active=is_active,
    )

    return ApiResponse(
        data=PaginatedResponse.create(
            items=[ProxyConfigResponse.from_model(c) for c in configs],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/{config_id}", response_model=ApiResponse[ProxyConfigResponse])
async def get_proxy_config(
    config_id: UUID,
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[ProxyConfigResponse]:
    service = ProxyService(db)
    config = await service.get_proxy_config(config_id)
    return ApiResponse(data=ProxyConfigResponse.from_model(config))


@router.put("/{config_id}", response_model=ApiResponse[ProxyConfigResponse])
async def update_proxy_config(
    config_id: UUID,
    config_in: ProxyConfigUpdate,
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[ProxyConfigResponse]:
    service = ProxyService(db)
    config = await service.update_proxy_config(config_id, config_in)
    return ApiResponse(
        message="代理配置更新成功",
        data=ProxyConfigResponse.from_model(config),
    )


@router.delete("/{config_id}", response_model=ApiResponse[None])
async def delete_proxy_config(
    config_id: UUID,
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[None]:
    service = ProxyService(db)
    await service.delete_proxy_config(config_id)
    return ApiResponse(message="代理配置删除成功")


@router.post("/{config_id}/test", response_model=ApiResponse[ProxyTestResponse])
async def test_proxy_connection(
    config_id: UUID,
    test_request: ProxyTestRequest,
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[ProxyTestResponse]:
    service = ProxyService(db)
    result = await service.test_proxy_connection(config_id, test_request)
    return ApiResponse(
        message="代理测试完成" if result.success else "代理测试失败",
        data=result,
    )


@router.post("/{config_id}/set-default", response_model=ApiResponse[ProxyConfigResponse])
async def set_default_proxy(
    config_id: UUID,
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[ProxyConfigResponse]:
    service = ProxyService(db)
    config = await service.set_default_proxy(config_id)
    return ApiResponse(
        message="已设置为默认代理",
        data=ProxyConfigResponse.from_model(config),
    )
