from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DownloadTaskBase(BaseModel):
    task_type: str = Field(..., pattern="^(bookmarks|likes|user_tweets)$")
    target_user_id: UUID | None = None


class DownloadTaskCreate(DownloadTaskBase):
    twitter_account_id: UUID


class DownloadTaskUpdate(BaseModel):
    status: str | None = Field(default=None, pattern="^(pending|running|completed|failed|cancelled)$")


class DownloadTaskResponse(BaseModel):
    id: UUID
    user_id: UUID
    twitter_account_id: UUID
    task_type: str
    target_user_id: UUID | None
    status: str
    total_count: int
    downloaded_count: int
    skipped_count: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    twitter_account: "TwitterAccountBrief | None" = None

    class Config:
        from_attributes = True


class TwitterAccountBrief(BaseModel):
    id: UUID
    twitter_username: str

    class Config:
        from_attributes = True


class TelegramUploadResponse(BaseModel):
    id: UUID
    media_file_id: UUID
    telegram_message_id: int
    telegram_chat_id: str
    uploaded_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class TaskProgress(BaseModel):
    task_id: UUID
    status: str
    progress: float
    current: int
    total: int
    message: str | None = None


DownloadTaskResponse.model_rebuild()
