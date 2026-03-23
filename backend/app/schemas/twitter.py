from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TwitterAccountBase(BaseModel):
    twitter_username: str = Field(..., min_length=1, max_length=100)


class TwitterAccountCreate(TwitterAccountBase):
    pass


class TwitterAccountUpdate(BaseModel):
    is_active: bool | None = None


class TwitterAccountResponse(BaseModel):
    id: UUID
    twitter_user_id: str
    twitter_username: str
    is_active: bool
    last_sync_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TwitterOAuthCallback(BaseModel):
    code: str
    state: str


class TwitterUserInfo(BaseModel):
    id: str | None = None
    name: str | None = None
    username: str | None = None
    profile_image_url: str | None = None


class TwitterAccountStatus(BaseModel):
    account_id: str
    twitter_username: str
    is_active: bool
    token_valid: bool
    token_expires_at: datetime | None = None
    last_sync_at: datetime | None = None
    can_refresh: bool = False
    twitter_user_info: TwitterUserInfo | None = None
    error: str | None = None

    class Config:
        from_attributes = True


class TwitterUserResponse(BaseModel):
    id: UUID
    twitter_id: str
    username: str
    name: str | None
    profile_image_url: str | None
    description: str | None
    followers_count: int
    friends_count: int
    statuses_count: int
    is_following: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TweetResponse(BaseModel):
    id: UUID
    twitter_id: str
    text: str | None
    lang: str | None
    retweet_count: int
    like_count: int
    reply_count: int
    quote_count: int
    is_retweet: bool
    is_quote: bool
    is_liked_by_me: bool
    is_bookmarked: bool
    published_at: datetime | None
    created_at: datetime
    twitter_user: TwitterUserResponse | None = None
    media_files: list["MediaFileResponse"] = []

    class Config:
        from_attributes = True


class MediaFileResponse(BaseModel):
    id: UUID
    media_type: str
    url: str
    local_path: str | None
    file_size: int | None
    width: int | None
    height: int | None
    duration_ms: int | None
    is_downloaded: bool
    created_at: datetime

    class Config:
        from_attributes = True


TweetResponse.model_rebuild()
