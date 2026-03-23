from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import ActiveUser, DBSession
from app.core.exceptions import NotFoundException
from app.models.media_file import MediaFile
from app.models.tweet import Tweet
from app.models.twitter_account import TwitterAccount
from app.models.twitter_user import TwitterUser
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationParams
from app.schemas.twitter import MediaFileResponse, TweetResponse, TwitterUserResponse

router = APIRouter(prefix="/users", tags=["博主管理"])


@router.get("", response_model=ApiResponse[PaginatedResponse[TwitterUserResponse]])
async def list_users(
    db: DBSession,
    current_user: ActiveUser,
    pagination: PaginationParams = None,
    search: str | None = Query(None, description="搜索用户名或名称"),
    is_following: bool | None = Query(None, description="是否关注"),
) -> ApiResponse[PaginatedResponse[TwitterUserResponse]]:
    if pagination is None:
        pagination = PaginationParams()

    query = (
        select(TwitterUser)
        .join(Tweet, TwitterUser.id == Tweet.twitter_user_id)
        .join(TwitterAccount, Tweet.twitter_account_id == TwitterAccount.id)
        .where(TwitterAccount.user_id == current_user.id)
        .distinct()
    )

    if search:
        query = query.where(
            (TwitterUser.username.ilike(f"%{search}%"))
            | (TwitterUser.name.ilike(f"%{search}%"))
        )

    if is_following is not None:
        query = query.where(TwitterUser.is_following == is_following)

    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    result = await db.execute(
        query
        .order_by(TwitterUser.followers_count.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    )
    users = result.scalars().all()

    return ApiResponse(
        data=PaginatedResponse.create(
            items=[TwitterUserResponse.model_validate(u) for u in users],
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )
    )


@router.get("/{user_id}", response_model=ApiResponse[TwitterUserResponse])
async def get_user(
    user_id: UUID,
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[TwitterUserResponse]:
    result = await db.execute(
        select(TwitterUser)
        .join(Tweet, TwitterUser.id == Tweet.twitter_user_id)
        .join(TwitterAccount, Tweet.twitter_account_id == TwitterAccount.id)
        .where(
            TwitterUser.id == user_id,
            TwitterAccount.user_id == current_user.id,
        )
        .distinct()
    )
    user = result.scalar_one_or_none()

    if not user:
        raise NotFoundException(message="博主不存在")

    return ApiResponse(data=TwitterUserResponse.model_validate(user))


@router.get("/{user_id}/tweets", response_model=ApiResponse[PaginatedResponse[TweetResponse]])
async def get_user_tweets(
    user_id: UUID,
    db: DBSession,
    current_user: ActiveUser,
    pagination: PaginationParams = None,
) -> ApiResponse[PaginatedResponse[TweetResponse]]:
    if pagination is None:
        pagination = PaginationParams()

    user_check = await db.execute(
        select(TwitterUser)
        .join(Tweet, TwitterUser.id == Tweet.twitter_user_id)
        .join(TwitterAccount, Tweet.twitter_account_id == TwitterAccount.id)
        .where(
            TwitterUser.id == user_id,
            TwitterAccount.user_id == current_user.id,
        )
        .distinct()
    )
    if not user_check.scalar_one_or_none():
        raise NotFoundException(message="博主不存在")

    query = (
        select(Tweet)
        .join(TwitterAccount, Tweet.twitter_account_id == TwitterAccount.id)
        .where(
            Tweet.twitter_user_id == user_id,
            TwitterAccount.user_id == current_user.id,
        )
    )

    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    result = await db.execute(
        query
        .options(
            selectinload(Tweet.twitter_user),
            selectinload(Tweet.media_files),
        )
        .order_by(Tweet.published_at.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    )
    tweets = result.scalars().all()

    return ApiResponse(
        data=PaginatedResponse.create(
            items=[TweetResponse.model_validate(t) for t in tweets],
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )
    )


@router.get("/{user_id}/media", response_model=ApiResponse[PaginatedResponse[MediaFileResponse]])
async def get_user_media(
    user_id: UUID,
    db: DBSession,
    current_user: ActiveUser,
    pagination: PaginationParams = None,
    media_type: str | None = Query(None, description="媒体类型: photo, video, gif"),
) -> ApiResponse[PaginatedResponse[MediaFileResponse]]:
    if pagination is None:
        pagination = PaginationParams()

    user_check = await db.execute(
        select(TwitterUser)
        .join(Tweet, TwitterUser.id == Tweet.twitter_user_id)
        .join(TwitterAccount, Tweet.twitter_account_id == TwitterAccount.id)
        .where(
            TwitterUser.id == user_id,
            TwitterAccount.user_id == current_user.id,
        )
        .distinct()
    )
    if not user_check.scalar_one_or_none():
        raise NotFoundException(message="博主不存在")

    query = (
        select(MediaFile)
        .join(Tweet, MediaFile.tweet_id == Tweet.id)
        .join(TwitterAccount, Tweet.twitter_account_id == TwitterAccount.id)
        .where(
            Tweet.twitter_user_id == user_id,
            TwitterAccount.user_id == current_user.id,
        )
    )

    if media_type:
        query = query.where(MediaFile.media_type == media_type)

    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    result = await db.execute(
        query
        .options(selectinload(MediaFile.tweet).selectinload(Tweet.twitter_user))
        .order_by(MediaFile.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    )
    media_files = result.scalars().all()

    return ApiResponse(
        data=PaginatedResponse.create(
            items=[MediaFileResponse.model_validate(m) for m in media_files],
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )
    )


@router.get("/{user_id}/stats", response_model=ApiResponse[dict[str, Any]])
async def get_user_stats(
    user_id: UUID,
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[dict[str, Any]]:
    user_check = await db.execute(
        select(TwitterUser)
        .join(Tweet, TwitterUser.id == Tweet.twitter_user_id)
        .join(TwitterAccount, Tweet.twitter_account_id == TwitterAccount.id)
        .where(
            TwitterUser.id == user_id,
            TwitterAccount.user_id == current_user.id,
        )
        .distinct()
    )
    user = user_check.scalar_one_or_none()
    if not user:
        raise NotFoundException(message="博主不存在")

    tweets_count_query = (
        select(func.count(Tweet.id))
        .join(TwitterAccount, Tweet.twitter_account_id == TwitterAccount.id)
        .where(
            Tweet.twitter_user_id == user_id,
            TwitterAccount.user_id == current_user.id,
        )
    )
    tweets_result = await db.execute(tweets_count_query)
    tweets_count = tweets_result.scalar() or 0

    media_count_query = (
        select(func.count(MediaFile.id))
        .join(Tweet, MediaFile.tweet_id == Tweet.id)
        .join(TwitterAccount, Tweet.twitter_account_id == TwitterAccount.id)
        .where(
            Tweet.twitter_user_id == user_id,
            TwitterAccount.user_id == current_user.id,
        )
    )
    media_result = await db.execute(media_count_query)
    media_count = media_result.scalar() or 0

    storage_size_query = (
        select(func.sum(MediaFile.file_size))
        .join(Tweet, MediaFile.tweet_id == Tweet.id)
        .join(TwitterAccount, Tweet.twitter_account_id == TwitterAccount.id)
        .where(
            Tweet.twitter_user_id == user_id,
            TwitterAccount.user_id == current_user.id,
            MediaFile.file_size.isnot(None),
        )
    )
    storage_result = await db.execute(storage_size_query)
    storage_size = storage_result.scalar() or 0

    media_type_query = (
        select(
            MediaFile.media_type,
            func.count(MediaFile.id).label("count"),
            func.sum(MediaFile.file_size).label("total_size"),
        )
        .join(Tweet, MediaFile.tweet_id == Tweet.id)
        .join(TwitterAccount, Tweet.twitter_account_id == TwitterAccount.id)
        .where(
            Tweet.twitter_user_id == user_id,
            TwitterAccount.user_id == current_user.id,
        )
        .group_by(MediaFile.media_type)
    )
    type_result = await db.execute(media_type_query)
    by_type = [
        {
            "media_type": row.media_type,
            "count": row.count,
            "total_size": row.total_size or 0,
        }
        for row in type_result.all()
    ]

    return ApiResponse(
        data={
            "user_id": str(user_id),
            "username": user.username,
            "name": user.name,
            "tweets_count": tweets_count,
            "media_count": media_count,
            "storage_size": storage_size,
            "by_type": by_type,
        }
    )
