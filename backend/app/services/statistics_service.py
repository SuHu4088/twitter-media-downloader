from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.download_task import DownloadTask
from app.models.media_file import MediaFile
from app.models.tweet import Tweet
from app.models.twitter_user import TwitterUser


@dataclass
class MediaByType:
    media_type: str
    count: int
    total_size: int


@dataclass
class TopUser:
    user_id: UUID
    username: str
    name: str | None
    tweet_count: int
    followers_count: int


@dataclass
class DownloadStats:
    total_tasks: int
    pending_tasks: int
    running_tasks: int
    completed_tasks: int
    failed_tasks: int
    total_downloaded: int
    total_skipped: int


@dataclass
class StorageTrend:
    date: str
    tweets_count: int
    media_count: int
    storage_size: int


class StatisticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_total_tweets_count(self) -> int:
        query = select(func.count(Tweet.id))
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_total_media_count(self) -> int:
        query = select(func.count(MediaFile.id))
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_total_storage_size(self) -> int:
        query = select(func.sum(MediaFile.file_size)).where(
            MediaFile.file_size.isnot(None)
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_tweets_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> list[Tweet]:
        query = (
            select(Tweet)
            .where(Tweet.published_at >= start_date)
            .where(Tweet.published_at <= end_date)
            .order_by(Tweet.published_at.desc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_media_by_type(self) -> list[MediaByType]:
        query = (
            select(
                MediaFile.media_type,
                func.count(MediaFile.id).label("count"),
                func.sum(MediaFile.file_size).label("total_size"),
            )
            .group_by(MediaFile.media_type)
        )
        result = await self.db.execute(query)
        rows = result.all()

        return [
            MediaByType(
                media_type=row.media_type,
                count=row.count,
                total_size=row.total_size or 0,
            )
            for row in rows
        ]

    async def get_top_users(self, limit: int = 10) -> list[TopUser]:
        query = (
            select(
                TwitterUser.id.label("user_id"),
                TwitterUser.username,
                TwitterUser.name,
                func.count(Tweet.id).label("tweet_count"),
                TwitterUser.followers_count,
            )
            .join(Tweet, TwitterUser.id == Tweet.twitter_user_id)
            .group_by(TwitterUser.id)
            .order_by(func.count(Tweet.id).desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        rows = result.all()

        return [
            TopUser(
                user_id=row.user_id,
                username=row.username,
                name=row.name,
                tweet_count=row.tweet_count,
                followers_count=row.followers_count,
            )
            for row in rows
        ]

    async def get_download_stats(self) -> DownloadStats:
        total_query = select(func.count(DownloadTask.id))
        total_result = await self.db.execute(total_query)
        total_tasks = total_result.scalar() or 0

        status_query = (
            select(DownloadTask.status, func.count(DownloadTask.id))
            .group_by(DownloadTask.status)
        )
        status_result = await self.db.execute(status_query)
        status_counts = dict(status_result.all())

        sum_query = select(
            func.sum(DownloadTask.downloaded_count),
            func.sum(DownloadTask.skipped_count),
        )
        sum_result = await self.db.execute(sum_query)
        sums = sum_result.one()

        return DownloadStats(
            total_tasks=total_tasks,
            pending_tasks=status_counts.get("pending", 0),
            running_tasks=status_counts.get("running", 0),
            completed_tasks=status_counts.get("completed", 0),
            failed_tasks=status_counts.get("failed", 0),
            total_downloaded=sums[0] or 0,
            total_skipped=sums[1] or 0,
        )

    async def get_storage_trend(self, days: int = 30) -> list[StorageTrend]:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        tweets_query = (
            select(
                func.date(Tweet.created_at).label("date"),
                func.count(Tweet.id).label("count"),
            )
            .where(Tweet.created_at >= start_date)
            .where(Tweet.created_at <= end_date)
            .group_by(func.date(Tweet.created_at))
            .order_by(func.date(Tweet.created_at))
        )
        tweets_result = await self.db.execute(tweets_query)
        tweets_by_date = {str(row.date): row.count for row in tweets_result.all()}

        media_query = (
            select(
                func.date(MediaFile.created_at).label("date"),
                func.count(MediaFile.id).label("count"),
                func.sum(MediaFile.file_size).label("size"),
            )
            .where(MediaFile.created_at >= start_date)
            .where(MediaFile.created_at <= end_date)
            .group_by(func.date(MediaFile.created_at))
            .order_by(func.date(MediaFile.created_at))
        )
        media_result = await self.db.execute(media_query)
        media_by_date = {
            str(row.date): {"count": row.count, "size": row.size or 0}
            for row in media_result.all()
        }

        all_dates = set(tweets_by_date.keys()) | set(media_by_date.keys())

        trends = []
        for date_str in sorted(all_dates):
            trends.append(
                StorageTrend(
                    date=date_str,
                    tweets_count=tweets_by_date.get(date_str, 0),
                    media_count=media_by_date.get(date_str, {}).get("count", 0),
                    storage_size=media_by_date.get(date_str, {}).get("size", 0),
                )
            )

        return trends

    async def get_media_status_stats(self) -> dict[str, int]:
        query = (
            select(MediaFile.download_status, func.count(MediaFile.id))
            .group_by(MediaFile.download_status)
        )
        result = await self.db.execute(query)
        return dict(result.all())

    async def get_tweets_count_by_account(self, account_id: UUID) -> int:
        query = select(func.count(Tweet.id)).where(
            Tweet.twitter_account_id == account_id
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_media_count_by_account(self, account_id: UUID) -> int:
        query = (
            select(func.count(MediaFile.id))
            .join(Tweet, MediaFile.tweet_id == Tweet.id)
            .where(Tweet.twitter_account_id == account_id)
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_storage_size_by_account(self, account_id: UUID) -> int:
        query = (
            select(func.sum(MediaFile.file_size))
            .join(Tweet, MediaFile.tweet_id == Tweet.id)
            .where(Tweet.twitter_account_id == account_id)
            .where(MediaFile.file_size.isnot(None))
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_recent_tweets_count(self, hours: int = 24) -> int:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        query = select(func.count(Tweet.id)).where(Tweet.created_at >= cutoff)
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_recent_media_count(self, hours: int = 24) -> int:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        query = select(func.count(MediaFile.id)).where(MediaFile.created_at >= cutoff)
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_dashboard_summary(self) -> dict[str, Any]:
        total_tweets = await self.get_total_tweets_count()
        total_media = await self.get_total_media_count()
        total_storage = await self.get_total_storage_size()
        download_stats = await self.get_download_stats()
        media_status = await self.get_media_status_stats()

        return {
            "total_tweets": total_tweets,
            "total_media": total_media,
            "total_storage_size": total_storage,
            "download_stats": {
                "total_tasks": download_stats.total_tasks,
                "pending_tasks": download_stats.pending_tasks,
                "running_tasks": download_stats.running_tasks,
                "completed_tasks": download_stats.completed_tasks,
                "failed_tasks": download_stats.failed_tasks,
                "total_downloaded": download_stats.total_downloaded,
                "total_skipped": download_stats.total_skipped,
            },
            "media_status": media_status,
        }

    async def get_user_statistics(self, user_id: UUID) -> dict[str, Any]:
        tweets_count = await self.get_tweets_count_by_account(user_id)
        media_count = await self.get_media_count_by_account(user_id)
        storage_size = await self.get_storage_size_by_account(user_id)

        return {
            "user_id": str(user_id),
            "tweets_count": tweets_count,
            "media_count": media_count,
            "storage_size": storage_size,
        }

    async def get_hourly_download_distribution(self) -> dict[int, int]:
        query = (
            select(
                func.extract("hour", MediaFile.created_at).label("hour"),
                func.count(MediaFile.id).label("count"),
            )
            .where(MediaFile.download_status == "completed")
            .group_by(func.extract("hour", MediaFile.created_at))
        )
        result = await self.db.execute(query)
        return {int(row.hour): row.count for row in result.all()}

    async def get_daily_download_distribution(self, days: int = 7) -> dict[str, int]:
        start_date = datetime.utcnow() - timedelta(days=days)

        query = (
            select(
                func.date(MediaFile.created_at).label("date"),
                func.count(MediaFile.id).label("count"),
            )
            .where(MediaFile.download_status == "completed")
            .where(MediaFile.created_at >= start_date)
            .group_by(func.date(MediaFile.created_at))
            .order_by(func.date(MediaFile.created_at))
        )
        result = await self.db.execute(query)
        return {str(row.date): row.count for row in result.all()}
