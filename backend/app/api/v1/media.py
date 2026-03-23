from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import ActiveUser, DBSession
from app.core.config import settings
from app.core.exceptions import BadRequestException, NotFoundException
from app.models.media_file import MediaFile
from app.models.tweet import Tweet
from app.models.twitter_account import TwitterAccount
from app.models.twitter_user import TwitterUser
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationParams
from app.schemas.twitter import MediaFileResponse

router = APIRouter(prefix="/media", tags=["媒体文件"])


@router.get("", response_model=ApiResponse[PaginatedResponse[MediaFileResponse]])
async def list_media(
    db: DBSession,
    current_user: ActiveUser,
    pagination: PaginationParams = None,
    media_type: str | None = Query(None, description="媒体类型: photo, video, gif"),
    start_date: datetime | None = Query(None, description="开始日期"),
    end_date: datetime | None = Query(None, description="结束日期"),
    twitter_user_id: UUID | None = Query(None, description="博主ID"),
    download_status: str | None = Query(None, description="下载状态: pending, completed, failed"),
) -> ApiResponse[PaginatedResponse[MediaFileResponse]]:
    if pagination is None:
        pagination = PaginationParams()

    query = (
        select(MediaFile)
        .join(Tweet)
        .join(TwitterAccount, Tweet.twitter_account_id == TwitterAccount.id)
        .where(TwitterAccount.user_id == current_user.id)
    )

    if media_type:
        query = query.where(MediaFile.media_type == media_type)

    if download_status:
        query = query.where(MediaFile.download_status == download_status)

    if start_date:
        query = query.where(MediaFile.created_at >= start_date)

    if end_date:
        query = query.where(MediaFile.created_at <= end_date)

    if twitter_user_id:
        query = query.where(Tweet.twitter_user_id == twitter_user_id)

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


@router.get("/stats", response_model=ApiResponse[dict[str, Any]])
async def get_media_stats(
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[dict[str, Any]]:
    base_query = (
        select(MediaFile)
        .join(Tweet)
        .join(TwitterAccount, Tweet.twitter_account_id == TwitterAccount.id)
        .where(TwitterAccount.user_id == current_user.id)
    )

    total_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(total_query)
    total_count = total_result.scalar() or 0

    type_query = (
        select(
            MediaFile.media_type,
            func.count(MediaFile.id).label("count"),
            func.sum(MediaFile.file_size).label("total_size"),
        )
        .select_from(base_query.subquery())
        .group_by(MediaFile.media_type)
    )
    type_result = await db.execute(type_query)
    by_type = [
        {
            "media_type": row.media_type,
            "count": row.count,
            "total_size": row.total_size or 0,
        }
        for row in type_result.all()
    ]

    status_query = (
        select(
            MediaFile.download_status,
            func.count(MediaFile.id).label("count"),
        )
        .select_from(base_query.subquery())
        .group_by(MediaFile.download_status)
    )
    status_result = await db.execute(status_query)
    by_status = {row.download_status: row.count for row in status_result.all()}

    size_query = select(func.sum(MediaFile.file_size)).select_from(base_query.subquery())
    size_result = await db.execute(size_query)
    total_size = size_result.scalar() or 0

    return ApiResponse(
        data={
            "total_count": total_count,
            "total_size": total_size,
            "by_type": by_type,
            "by_status": by_status,
        }
    )


@router.get("/{media_id}", response_model=ApiResponse[MediaFileResponse])
async def get_media(
    media_id: UUID,
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[MediaFileResponse]:
    result = await db.execute(
        select(MediaFile)
        .join(Tweet)
        .join(TwitterAccount, Tweet.twitter_account_id == TwitterAccount.id)
        .where(
            MediaFile.id == media_id,
            TwitterAccount.user_id == current_user.id,
        )
        .options(selectinload(MediaFile.tweet).selectinload(Tweet.twitter_user))
    )
    media_file = result.scalar_one_or_none()

    if not media_file:
        raise NotFoundException(message="媒体文件不存在")

    return ApiResponse(data=MediaFileResponse.model_validate(media_file))


@router.get("/{media_id}/thumbnail")
async def get_thumbnail(
    media_id: UUID,
    db: DBSession,
    current_user: ActiveUser,
):
    result = await db.execute(
        select(MediaFile)
        .join(Tweet)
        .join(TwitterAccount, Tweet.twitter_account_id == TwitterAccount.id)
        .where(
            MediaFile.id == media_id,
            TwitterAccount.user_id == current_user.id,
        )
    )
    media_file = result.scalar_one_or_none()

    if not media_file:
        raise NotFoundException(message="媒体文件不存在")

    if not media_file.local_path:
        raise NotFoundException(message="缩略图不可用")

    file_path = Path(media_file.local_path)
    if not file_path.exists():
        raise NotFoundException(message="文件不存在")

    return FileResponse(
        path=file_path,
        media_type="image/jpeg",
    )


@router.get("/{media_id}/download")
async def download_media(
    media_id: UUID,
    db: DBSession,
    current_user: ActiveUser,
):
    result = await db.execute(
        select(MediaFile)
        .join(Tweet)
        .join(TwitterAccount, Tweet.twitter_account_id == TwitterAccount.id)
        .where(
            MediaFile.id == media_id,
            TwitterAccount.user_id == current_user.id,
        )
    )
    media_file = result.scalar_one_or_none()

    if not media_file:
        raise NotFoundException(message="媒体文件不存在")

    if not media_file.local_path or media_file.download_status != "completed":
        raise NotFoundException(message="文件尚未下载")

    file_path = Path(media_file.local_path)
    if not file_path.exists():
        raise NotFoundException(message="文件不存在")

    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type=media_file.media_type,
    )


@router.delete("/{media_id}", response_model=ApiResponse[None])
async def delete_media(
    media_id: UUID,
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[None]:
    result = await db.execute(
        select(MediaFile)
        .join(Tweet)
        .join(TwitterAccount, Tweet.twitter_account_id == TwitterAccount.id)
        .where(
            MediaFile.id == media_id,
            TwitterAccount.user_id == current_user.id,
        )
    )
    media_file = result.scalar_one_or_none()

    if not media_file:
        raise NotFoundException(message="媒体文件不存在")

    if media_file.local_path:
        file_path = Path(media_file.local_path)
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception:
                pass

    await db.delete(media_file)

    return ApiResponse(message="媒体文件已删除")
