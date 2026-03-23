from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import ActiveUser, DBSession
from app.schemas.common import ApiResponse, PaginatedResponse
from app.schemas.telegram import (
    TelegramBatchUploadCreate,
    TelegramBatchUploadResult,
    TelegramConfigCreate,
    TelegramConfigResponse,
    TelegramTestResponse,
    TelegramUploadCreate,
    TelegramUploadDetailResponse,
    TelegramUploadResponse,
    TelegramUploadResult,
)
from app.services.telegram_service import TelegramService
from app.services.tdl_service import TDLService

router = APIRouter(prefix="/telegram", tags=["Telegram上传"])


@router.post(
    "/config",
    response_model=ApiResponse[TelegramConfigResponse],
    status_code=status.HTTP_201_CREATED,
)
async def configure_telegram(
    config_in: TelegramConfigCreate,
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[TelegramConfigResponse]:
    tdl_service = TDLService()
    service = TelegramService(db, tdl_service)
    
    config_data = {
        "api_id": config_in.api_id,
        "api_hash": config_in.api_hash,
        "phone": config_in.phone,
    }
    
    result = await service.configure_telegram(config_data)
    
    return ApiResponse(
        message="Telegram配置成功",
        data=TelegramConfigResponse(
            api_id=config_in.api_id,
            phone=config_in.phone,
            has_api_hash=True,
        ),
    )


@router.get("/config", response_model=ApiResponse[TelegramConfigResponse])
async def get_telegram_config(
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[TelegramConfigResponse]:
    tdl_service = TDLService()
    service = TelegramService(db, tdl_service)
    
    status_result = await tdl_service.check_login_status()
    
    return ApiResponse(
        data=TelegramConfigResponse(
            api_id=0,
            phone="",
            has_api_hash=False,
        )
    )


@router.post("/test", response_model=ApiResponse[TelegramTestResponse])
async def test_telegram_connection(
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[TelegramTestResponse]:
    tdl_service = TDLService()
    service = TelegramService(db, tdl_service)
    
    result = await service.test_connection()
    
    return ApiResponse(
        message=result.get("message", "测试完成"),
        data=TelegramTestResponse(
            success=result.get("success", False),
            message=result.get("message", ""),
            user=result.get("user"),
            need_login=result.get("need_login", False),
        ),
    )


@router.post("/login", response_model=ApiResponse[dict])
async def login_telegram(
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[dict]:
    tdl_service = TDLService()
    result = await tdl_service.login()
    
    return ApiResponse(
        message="登录流程已启动" if result.get("success") else "登录失败",
        data=result,
    )


@router.post(
    "/upload",
    response_model=ApiResponse[TelegramUploadResponse],
    status_code=status.HTTP_201_CREATED,
)
async def upload_media(
    upload_in: TelegramUploadCreate,
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[TelegramUploadResponse]:
    tdl_service = TDLService()
    service = TelegramService(db, tdl_service)
    
    upload_record = await service.upload_media(
        media_id=upload_in.media_id,
        chat_id=upload_in.chat_id,
        caption=upload_in.caption,
    )
    
    from app.tasks.telegram_tasks import upload_media_task
    upload_media_task.delay(str(upload_record.id))
    
    return ApiResponse(
        message="上传任务已创建",
        data=TelegramUploadResponse.from_model(upload_record),
    )


@router.post(
    "/upload/batch",
    response_model=ApiResponse[TelegramBatchUploadResult],
    status_code=status.HTTP_201_CREATED,
)
async def batch_upload_media(
    upload_in: TelegramBatchUploadCreate,
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[TelegramBatchUploadResult]:
    tdl_service = TDLService()
    service = TelegramService(db, tdl_service)
    
    upload_records = await service.upload_media_batch(
        media_ids=upload_in.media_ids,
        chat_id=upload_in.chat_id,
    )
    
    upload_ids = [record.id for record in upload_records]
    
    from app.tasks.telegram_tasks import batch_upload_task
    batch_upload_task.delay([str(uid) for uid in upload_ids])
    
    return ApiResponse(
        message=f"批量上传任务已创建: {len(upload_records)}个",
        data=TelegramBatchUploadResult(
            total=len(upload_in.media_ids),
            success_count=len(upload_records),
            failed_count=len(upload_in.media_ids) - len(upload_records),
            upload_ids=upload_ids,
        ),
    )


@router.get("/uploads", response_model=ApiResponse[PaginatedResponse[TelegramUploadResponse]])
async def list_uploads(
    db: DBSession,
    current_user: ActiveUser,
    page: int = 1,
    page_size: int = 50,
    status_filter: str | None = None,
    chat_id: str | None = None,
) -> ApiResponse[PaginatedResponse[TelegramUploadResponse]]:
    tdl_service = TDLService()
    service = TelegramService(db, tdl_service)
    
    uploads, total = await service.get_upload_history(
        page=page,
        page_size=page_size,
        status=status_filter,
        chat_id=chat_id,
    )
    
    return ApiResponse(
        data=PaginatedResponse.create(
            items=[TelegramUploadResponse.from_model(u) for u in uploads],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/uploads/{upload_id}", response_model=ApiResponse[TelegramUploadDetailResponse])
async def get_upload_detail(
    upload_id: UUID,
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[TelegramUploadDetailResponse]:
    from sqlalchemy import select
    from app.models.media_file import MediaFile
    
    tdl_service = TDLService()
    service = TelegramService(db, tdl_service)
    
    upload_record = await service.get_upload_status(upload_id)
    
    result = await db.execute(
        select(MediaFile).where(MediaFile.id == upload_record.media_file_id)
    )
    media_file = result.scalar_one_or_none()
    
    return ApiResponse(
        data=TelegramUploadDetailResponse.from_model_with_media(upload_record, media_file),
    )


@router.post("/uploads/{upload_id}/retry", response_model=ApiResponse[TelegramUploadResult])
async def retry_upload(
    upload_id: UUID,
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[TelegramUploadResult]:
    tdl_service = TDLService()
    service = TelegramService(db, tdl_service)
    
    result = await service.retry_failed_upload(upload_id)
    
    return ApiResponse(
        message="重试成功" if result.get("success") else "重试失败",
        data=TelegramUploadResult(
            success=result.get("success", False),
            message=result.get("message", ""),
            upload_id=upload_id,
            retry_count=result.get("retry_count"),
        ),
    )


@router.delete("/uploads/{upload_id}", response_model=ApiResponse[None])
async def cancel_upload(
    upload_id: UUID,
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[None]:
    tdl_service = TDLService()
    service = TelegramService(db, tdl_service)
    
    await service.cancel_upload(upload_id)
    
    return ApiResponse(message="上传任务已取消")


@router.get("/chats", response_model=ApiResponse[list])
async def list_chats(
    db: DBSession,
    current_user: ActiveUser,
    limit: int = 50,
) -> ApiResponse[list]:
    tdl_service = TDLService()
    
    result = await tdl_service.get_chats(limit=limit)
    
    return ApiResponse(
        data=result.get("chats", []),
    )


@router.get("/chats/{chat_id}", response_model=ApiResponse[dict])
async def get_chat_info(
    chat_id: str,
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[dict]:
    tdl_service = TDLService()
    
    result = await tdl_service.get_chat_info(chat_id)
    
    return ApiResponse(
        data=result,
    )
