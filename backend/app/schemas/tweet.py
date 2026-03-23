from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class MediaUrl(BaseModel):
    media_key: str | None = None
    media_type: str
    url: str
    preview_url: str | None = None
    width: int | None = None
    height: int | None = None
    duration_ms: int | None = None


class TweetBase(BaseModel):
    twitter_id: str
    text: str | None = None
    lang: str | None = None


class TweetCreate(TweetBase):
    author_id: str | None = None
    retweet_count: int = 0
    like_count: int = 0
    reply_count: int = 0
    quote_count: int = 0
    is_retweet: bool = False
    is_quote: bool = False
    is_liked_by_me: bool = False
    is_bookmarked: bool = False
    published_at: datetime | None = None
    media: list[MediaUrl] = []


class TweetInDB(TweetBase):
    id: UUID
    twitter_user_id: UUID
    twitter_account_id: UUID | None = None
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
    updated_at: datetime

    class Config:
        from_attributes = True


class TwitterUserBase(BaseModel):
    twitter_id: str
    username: str


class TwitterUserCreate(TwitterUserBase):
    name: str | None = None
    profile_image_url: str | None = None
    description: str | None = None
    followers_count: int = 0
    friends_count: int = 0
    statuses_count: int = 0


class TwitterUserInDB(TwitterUserBase):
    id: UUID
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


class TweetWithMedia(TweetInDB):
    twitter_user: TwitterUserInDB | None = None
    media_files: list[Any] = []


class TweetSyncResult(BaseModel):
    account_id: str
    tweets_count: int = 0
    media_count: int = 0
    pages_fetched: int = 0
    errors: list[str] = []


class TweetFetchParams(BaseModel):
    max_results: int = Field(default=100, ge=10, le=100)
    max_pages: int = Field(default=10, ge=1, le=50)
    since_tweet_id: str | None = None
