from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.deps import ActiveUser, DBSession
from app.models.download_task import DownloadTask
from app.models.media_file import MediaFile
from app.models.tweet import Tweet
from app.models.twitter_account import TwitterAccount
from app.models.twitter_user import TwitterUser
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/statistics", tags=["统计数据"])


@router.get("/dashboard", response_model=ApiResponse[dict[str, Any]])
async def get_dashboard(
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[dict[str, Any]]:
    account_ids_query = select(TwitterAccount.id).where(
        TwitterAccount.user_id == current_user.id
    )
    account_ids_result = await db.execute(account_ids_query)
    account_ids = [row[0] for row in account_ids_result.all()]

    if not account_ids:
        return ApiResponse(
            data={
                "total_tweets": 0,
                "total_media": 0,
                "total_storage_size": 0,
                "total_users": 0,
                "recent_tweets_24h": 0,
                "recent_media_24h": 0,
                "download_stats": {
                    "total_tasks": 0,
                    "pending_tasks": 0,
                    "running_tasks": 0,
                    "completed_tasks": 0,
                    "failed_tasks": 0,
                },
                "media_by_type": [],
                "top_users": [],
            }
        )

    tweets_count_query = select(func.count(Tweet.id)).where(
        Tweet.twitter_account_id.in_(account_ids)
    )
    tweets_result = await db.execute(tweets_count_query)
    total_tweets = tweets_result.scalar() or 0

    media_count_query = (
        select(func.count(MediaFile.id))
        .join(Tweet, MediaFile.tweet_id == Tweet.id)
        .where(Tweet.twitter_account_id.in_(account_ids))
    )
    media_result = await db.execute(media_count_query)
    total_media = media_result.scalar() or 0

    storage_size_query = (
        select(func.sum(MediaFile.file_size))
        .join(Tweet, MediaFile.tweet_id == Tweet.id)
        .where(
            Tweet.twitter_account_id.in_(account_ids),
            MediaFile.file_size.isnot(None),
        )
    )
    storage_result = await db.execute(storage_size_query)
    total_storage_size = storage_result.scalar() or 0

    users_count_query = (
        select(func.count(func.distinct(Tweet.twitter_user_id)))
        .where(Tweet.twitter_account_id.in_(account_ids))
    )
    users_result = await db.execute(users_count_query)
    total_users = users_result.scalar() or 0

    cutoff_24h = datetime.utcnow() - timedelta(hours=24)
    recent_tweets_query = select(func.count(Tweet.id)).where(
        Tweet.twitter_account_id.in_(account_ids),
        Tweet.created_at >= cutoff_24h,
    )
    recent_tweets_result = await db.execute(recent_tweets_query)
    recent_tweets_24h = recent_tweets_result.scalar() or 0

    recent_media_query = (
        select(func.count(MediaFile.id))
        .join(Tweet, MediaFile.tweet_id == Tweet.id)
        .where(
            Tweet.twitter_account_id.in_(account_ids),
            MediaFile.created_at >= cutoff_24h,
        )
    )
    recent_media_result = await db.execute(recent_media_query)
    recent_media_24h = recent_media_result.scalar() or 0

    total_tasks_query = select(func.count(DownloadTask.id)).where(
        DownloadTask.user_id == current_user.id
    )
    total_tasks_result = await db.execute(total_tasks_query)
    total_tasks = total_tasks_result.scalar() or 0

    status_query = (
        select(DownloadTask.status, func.count(DownloadTask.id))
        .where(DownloadTask.user_id == current_user.id)
        .group_by(DownloadTask.status)
    )
    status_result = await db.execute(status_query)
    status_counts = dict(status_result.all())

    media_by_type_query = (
        select(
            MediaFile.media_type,
            func.count(MediaFile.id).label("count"),
            func.sum(MediaFile.file_size).label("total_size"),
        )
        .join(Tweet, MediaFile.tweet_id == Tweet.id)
        .where(Tweet.twitter_account_id.in_(account_ids))
        .group_by(MediaFile.media_type)
    )
    media_by_type_result = await db.execute(media_by_type_query)
    media_by_type = [
        {
            "media_type": row.media_type,
            "count": row.count,
            "total_size": row.total_size or 0,
        }
        for row in media_by_type_result.all()
    ]

    top_users_query = (
        select(
            TwitterUser.id,
            TwitterUser.username,
            TwitterUser.name,
            TwitterUser.profile_image_url,
            func.count(Tweet.id).label("tweet_count"),
        )
        .join(Tweet, TwitterUser.id == Tweet.twitter_user_id)
        .where(Tweet.twitter_account_id.in_(account_ids))
        .group_by(TwitterUser.id)
        .order_by(func.count(Tweet.id).desc())
        .limit(10)
    )
    top_users_result = await db.execute(top_users_query)
    top_users = [
        {
            "user_id": str(row.id),
            "username": row.username,
            "name": row.name,
            "profile_image_url": row.profile_image_url,
            "tweet_count": row.tweet_count,
        }
        for row in top_users_result.all()
    ]

    return ApiResponse(
        data={
            "total_tweets": total_tweets,
            "total_media": total_media,
            "total_storage_size": total_storage_size,
            "total_users": total_users,
            "recent_tweets_24h": recent_tweets_24h,
            "recent_media_24h": recent_media_24h,
            "download_stats": {
                "total_tasks": total_tasks,
                "pending_tasks": status_counts.get("pending", 0),
                "running_tasks": status_counts.get("running", 0),
                "completed_tasks": status_counts.get("completed", 0),
                "failed_tasks": status_counts.get("failed", 0),
            },
            "media_by_type": media_by_type,
            "top_users": top_users,
        }
    )


@router.get("/storage", response_model=ApiResponse[dict[str, Any]])
async def get_storage_stats(
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[dict[str, Any]]:
    account_ids_query = select(TwitterAccount.id).where(
        TwitterAccount.user_id == current_user.id
    )
    account_ids_result = await db.execute(account_ids_query)
    account_ids = [row[0] for row in account_ids_result.all()]

    if not account_ids:
        return ApiResponse(
            data={
                "total_size": 0,
                "by_type": [],
                "by_status": {},
                "largest_files": [],
            }
        )

    total_size_query = (
        select(func.sum(MediaFile.file_size))
        .join(Tweet, MediaFile.tweet_id == Tweet.id)
        .where(
            Tweet.twitter_account_id.in_(account_ids),
            MediaFile.file_size.isnot(None),
        )
    )
    total_size_result = await db.execute(total_size_query)
    total_size = total_size_result.scalar() or 0

    by_type_query = (
        select(
            MediaFile.media_type,
            func.count(MediaFile.id).label("count"),
            func.sum(MediaFile.file_size).label("total_size"),
        )
        .join(Tweet, MediaFile.tweet_id == Tweet.id)
        .where(Tweet.twitter_account_id.in_(account_ids))
        .group_by(MediaFile.media_type)
    )
    by_type_result = await db.execute(by_type_query)
    by_type = [
        {
            "media_type": row.media_type,
            "count": row.count,
            "total_size": row.total_size or 0,
        }
        for row in by_type_result.all()
    ]

    by_status_query = (
        select(
            MediaFile.download_status,
            func.count(MediaFile.id).label("count"),
            func.sum(MediaFile.file_size).label("total_size"),
        )
        .join(Tweet, MediaFile.tweet_id == Tweet.id)
        .where(Tweet.twitter_account_id.in_(account_ids))
        .group_by(MediaFile.download_status)
    )
    by_status_result = await db.execute(by_status_query)
    by_status = {
        row.download_status: {
            "count": row.count,
            "total_size": row.total_size or 0,
        }
        for row in by_status_result.all()
    }

    largest_files_query = (
        select(MediaFile)
        .join(Tweet, MediaFile.tweet_id == Tweet.id)
        .where(
            Tweet.twitter_account_id.in_(account_ids),
            MediaFile.file_size.isnot(None),
        )
        .order_by(MediaFile.file_size.desc())
        .limit(10)
    )
    largest_files_result = await db.execute(largest_files_query)
    largest_files = [
        {
            "id": str(mf.id),
            "media_type": mf.media_type,
            "file_size": mf.file_size,
            "created_at": mf.created_at.isoformat(),
        }
        for mf in largest_files_result.scalars().all()
    ]

    return ApiResponse(
        data={
            "total_size": total_size,
            "by_type": by_type,
            "by_status": by_status,
            "largest_files": largest_files,
        }
    )


@router.get("/download", response_model=ApiResponse[dict[str, Any]])
async def get_download_stats(
    db: DBSession,
    current_user: ActiveUser,
    days: int = Query(default=7, ge=1, le=30, description="统计天数"),
) -> ApiResponse[dict[str, Any]]:
    total_tasks_query = select(func.count(DownloadTask.id)).where(
        DownloadTask.user_id == current_user.id
    )
    total_tasks_result = await db.execute(total_tasks_query)
    total_tasks = total_tasks_result.scalar() or 0

    status_query = (
        select(DownloadTask.status, func.count(DownloadTask.id))
        .where(DownloadTask.user_id == current_user.id)
        .group_by(DownloadTask.status)
    )
    status_result = await db.execute(status_query)
    status_counts = dict(status_result.all())

    sum_query = (
        select(
            func.sum(DownloadTask.downloaded_count),
            func.sum(DownloadTask.skipped_count),
        )
        .where(DownloadTask.user_id == current_user.id)
    )
    sum_result = await db.execute(sum_query)
    sums = sum_result.one()

    type_query = (
        select(
            DownloadTask.task_type,
            func.count(DownloadTask.id).label("count"),
        )
        .where(DownloadTask.user_id == current_user.id)
        .group_by(DownloadTask.task_type)
    )
    type_result = await db.execute(type_query)
    by_type = {row.task_type: row.count for row in type_result.all()}

    start_date = datetime.utcnow() - timedelta(days=days)

    daily_query = (
        select(
            func.date(MediaFile.created_at).label("date"),
            func.count(MediaFile.id).label("count"),
            func.sum(MediaFile.file_size).label("size"),
        )
        .join(Tweet, MediaFile.tweet_id == Tweet.id)
        .join(TwitterAccount, Tweet.twitter_account_id == TwitterAccount.id)
        .where(
            TwitterAccount.user_id == current_user.id,
            MediaFile.created_at >= start_date,
            MediaFile.download_status == "completed",
        )
        .group_by(func.date(MediaFile.created_at))
        .order_by(func.date(MediaFile.created_at))
    )
    daily_result = await db.execute(daily_query)
    daily_stats = [
        {
            "date": str(row.date),
            "count": row.count,
            "size": row.size or 0,
        }
        for row in daily_result.all()
    ]

    hourly_query = (
        select(
            func.extract("hour", MediaFile.created_at).label("hour"),
            func.count(MediaFile.id).label("count"),
        )
        .join(Tweet, MediaFile.tweet_id == Tweet.id)
        .join(TwitterAccount, Tweet.twitter_account_id == TwitterAccount.id)
        .where(
            TwitterAccount.user_id == current_user.id,
            MediaFile.download_status == "completed",
        )
        .group_by(func.extract("hour", MediaFile.created_at))
    )
    hourly_result = await db.execute(hourly_query)
    hourly_stats = {int(row.hour): row.count for row in hourly_result.all()}

    return ApiResponse(
        data={
            "total_tasks": total_tasks,
            "by_status": status_counts,
            "by_type": by_type,
            "total_downloaded": sums[0] or 0,
            "total_skipped": sums[1] or 0,
            "daily_stats": daily_stats,
            "hourly_distribution": hourly_stats,
        }
    )


@router.get("/trend", response_model=ApiResponse[dict[str, Any]])
async def get_trend_stats(
    db: DBSession,
    current_user: ActiveUser,
    days: int = Query(default=30, ge=1, le=90, description="统计天数"),
) -> ApiResponse[dict[str, Any]]:
    account_ids_query = select(TwitterAccount.id).where(
        TwitterAccount.user_id == current_user.id
    )
    account_ids_result = await db.execute(account_ids_query)
    account_ids = [row[0] for row in account_ids_result.all()]

    if not account_ids:
        return ApiResponse(
            data={
                "tweets_trend": [],
                "media_trend": [],
                "storage_trend": [],
            }
        )

    start_date = datetime.utcnow() - timedelta(days=days)

    tweets_trend_query = (
        select(
            func.date(Tweet.created_at).label("date"),
            func.count(Tweet.id).label("count"),
        )
        .where(
            Tweet.twitter_account_id.in_(account_ids),
            Tweet.created_at >= start_date,
        )
        .group_by(func.date(Tweet.created_at))
        .order_by(func.date(Tweet.created_at))
    )
    tweets_trend_result = await db.execute(tweets_trend_query)
    tweets_trend = [
        {
            "date": str(row.date),
            "count": row.count,
        }
        for row in tweets_trend_result.all()
    ]

    media_trend_query = (
        select(
            func.date(MediaFile.created_at).label("date"),
            func.count(MediaFile.id).label("count"),
        )
        .join(Tweet, MediaFile.tweet_id == Tweet.id)
        .where(
            Tweet.twitter_account_id.in_(account_ids),
            MediaFile.created_at >= start_date,
        )
        .group_by(func.date(MediaFile.created_at))
        .order_by(func.date(MediaFile.created_at))
    )
    media_trend_result = await db.execute(media_trend_query)
    media_trend = [
        {
            "date": str(row.date),
            "count": row.count,
        }
        for row in media_trend_result.all()
    ]

    storage_trend_query = (
        select(
            func.date(MediaFile.created_at).label("date"),
            func.sum(MediaFile.file_size).label("size"),
        )
        .join(Tweet, MediaFile.tweet_id == Tweet.id)
        .where(
            Tweet.twitter_account_id.in_(account_ids),
            MediaFile.created_at >= start_date,
            MediaFile.file_size.isnot(None),
        )
        .group_by(func.date(MediaFile.created_at))
        .order_by(func.date(MediaFile.created_at))
    )
    storage_trend_result = await db.execute(storage_trend_query)
    storage_trend = [
        {
            "date": str(row.date),
            "size": row.size or 0,
        }
        for row in storage_trend_result.all()
    ]

    return ApiResponse(
        data={
            "tweets_trend": tweets_trend,
            "media_trend": media_trend,
            "storage_trend": storage_trend,
        }
    )
