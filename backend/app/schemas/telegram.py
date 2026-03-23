from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class UploadStatus(str, Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"


class TelegramConfigBase(BaseModel):
    api_id: int = Field(..., description="Telegram API ID")
    api_hash: str = Field(..., min_length=32, max_length=64, description="Telegram API Hash")
    phone: str = Field(..., min_length=10, max_length=20, description="手机号码")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return v.strip().replace(" ", "").replace("-", "")


class TelegramConfigCreate(TelegramConfigBase):
    pass


class TelegramConfigResponse(BaseModel):
    api_id: int
    phone: str
    has_api_hash: bool = Field(..., description="是否设置了API Hash")
    configured_at: datetime | None = Field(default=None, description="配置时间")

    class Config:
        from_attributes = True


class TelegramUploadCreate(BaseModel):
    media_id: UUID = Field(..., description="媒体文件ID")
    chat_id: str = Field(..., min_length=1, max_length=50, description="目标聊天ID")
    caption: str | None = Field(default=None, max_length=4096, description="文件说明")


class TelegramBatchUploadCreate(BaseModel):
    media_ids: list[UUID] = Field(..., min_length=1, max_length=20, description="媒体文件ID列表")
    chat_id: str = Field(..., min_length=1, max_length=50, description="目标聊天ID")


class TelegramUploadResponse(BaseModel):
    id: UUID
    media_file_id: UUID
    chat_id: str
    message_id: str | None
    status: UploadStatus
    error_message: str | None
    retry_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_model(cls, model) -> "TelegramUploadResponse":
        return cls(
            id=model.id,
            media_file_id=model.media_file_id,
            chat_id=model.chat_id,
            message_id=model.message_id,
            status=UploadStatus(model.status),
            error_message=model.error_message,
            retry_count=model.retry_count,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class TelegramChatInfo(BaseModel):
    id: str
    title: str | None = None
    username: str | None = None
    type: str
    members_count: int | None = None

    class Config:
        from_attributes = True


class TelegramTestResponse(BaseModel):
    success: bool
    message: str
    user: dict | None = None
    need_login: bool = False


class TelegramUploadResult(BaseModel):
    success: bool
    message: str
    upload_id: UUID | None = None
    retry_count: int | None = None


class TelegramBatchUploadResult(BaseModel):
    total: int
    success_count: int
    failed_count: int
    upload_ids: list[UUID]


class TelegramUploadDetailResponse(TelegramUploadResponse):
    media_type: str | None = None
    media_url: str | None = None
    local_path: str | None = None
    file_size: int | None = None

    @classmethod
    def from_model_with_media(cls, model, media_file) -> "TelegramUploadDetailResponse":
        return cls(
            id=model.id,
            media_file_id=model.media_file_id,
            chat_id=model.chat_id,
            message_id=model.message_id,
            status=UploadStatus(model.status),
            error_message=model.error_message,
            retry_count=model.retry_count,
            created_at=model.created_at,
            updated_at=model.updated_at,
            media_type=media_file.media_type if media_file else None,
            media_url=media_file.url if media_file else None,
            local_path=media_file.local_path if media_file else None,
            file_size=media_file.file_size if media_file else None,
        )
