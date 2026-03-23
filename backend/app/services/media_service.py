import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media_file import MediaFile
from app.models.tweet import Tweet


@dataclass
class MediaStatistics:
    total_count: int
    pending_count: int
    downloading_count: int
    completed_count: int
    failed_count: int
    total_size: int
    by_type: dict[str, int]


class MediaService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_media_record(
        self,
        tweet_id: uuid.UUID,
        media_data: dict[str, Any],
    ) -> MediaFile:
        media = MediaFile(
            tweet_id=tweet_id,
            media_type=media_data.get("media_type", "unknown"),
            url=media_data.get("url", ""),
            local_path=media_data.get("local_path"),
            file_hash=media_data.get("file_hash"),
            file_size=media_data.get("file_size"),
            width=media_data.get("width"),
            height=media_data.get("height"),
            duration_ms=media_data.get("duration_ms"),
            download_status=media_data.get("download_status", "pending"),
            error_message=media_data.get("error_message"),
        )
        
        self.db.add(media)
        await self.db.flush()
        await self.db.refresh(media)
        
        return media

    async def create_media_records_batch(
        self,
        tweet_id: uuid.UUID,
        media_list: list[dict[str, Any]],
    ) -> list[MediaFile]:
        media_records = []
        
        for media_data in media_list:
            media = await self.create_media_record(tweet_id, media_data)
            media_records.append(media)
        
        return media_records

    async def update_media_status(
        self,
        media_id: uuid.UUID,
        status: str,
        error: str | None = None,
        local_path: str | None = None,
        file_hash: str | None = None,
        file_size: int | None = None,
    ) -> MediaFile | None:
        media = await self.db.get(MediaFile, media_id)
        
        if not media:
            return None
        
        media.download_status = status
        media.error_message = error
        
        if local_path:
            media.local_path = local_path
        if file_hash:
            media.file_hash = file_hash
        if file_size is not None:
            media.file_size = file_size
        
        await self.db.flush()
        await self.db.refresh(media)
        
        return media

    async def get_pending_media(self, limit: int = 100) -> list[MediaFile]:
        query = (
            select(MediaFile)
            .where(MediaFile.download_status == "pending")
            .order_by(MediaFile.created_at)
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_media_by_tweet(self, tweet_id: uuid.UUID) -> list[MediaFile]:
        query = (
            select(MediaFile)
            .where(MediaFile.tweet_id == tweet_id)
            .order_by(MediaFile.created_at)
        )
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_media_by_id(self, media_id: uuid.UUID) -> MediaFile | None:
        return await self.db.get(MediaFile, media_id)

    async def get_media_by_hash(self, file_hash: str) -> MediaFile | None:
        query = select(MediaFile).where(MediaFile.file_hash == file_hash)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def delete_media(self, media_id: uuid.UUID) -> bool:
        media = await self.db.get(MediaFile, media_id)
        
        if not media:
            return False
        
        await self.db.delete(media)
        await self.db.flush()
        
        return True

    async def delete_media_by_tweet(self, tweet_id: uuid.UUID) -> int:
        query = select(MediaFile).where(MediaFile.tweet_id == tweet_id)
        result = await self.db.execute(query)
        media_files = result.scalars().all()
        
        count = 0
        for media in media_files:
            await self.db.delete(media)
            count += 1
        
        await self.db.flush()
        return count

    async def get_media_statistics(self) -> MediaStatistics:
        total_query = select(func.count(MediaFile.id))
        total_result = await self.db.execute(total_query)
        total_count = total_result.scalar() or 0

        status_query = (
            select(MediaFile.download_status, func.count(MediaFile.id))
            .group_by(MediaFile.download_status)
        )
        status_result = await self.db.execute(status_query)
        status_counts = dict(status_result.all())

        size_query = select(func.sum(MediaFile.file_size)).where(
            MediaFile.file_size.isnot(None)
        )
        size_result = await self.db.execute(size_query)
        total_size = size_result.scalar() or 0

        type_query = (
            select(MediaFile.media_type, func.count(MediaFile.id))
            .group_by(MediaFile.media_type)
        )
        type_result = await self.db.execute(type_query)
        by_type = dict(type_result.all())

        return MediaStatistics(
            total_count=total_count,
            pending_count=status_counts.get("pending", 0),
            downloading_count=status_counts.get("downloading", 0),
            completed_count=status_counts.get("completed", 0),
            failed_count=status_counts.get("failed", 0),
            total_size=total_size,
            by_type=by_type,
        )

    async def get_downloaded_media(
        self,
        skip: int = 0,
        limit: int = 50,
        media_type: str | None = None,
    ) -> list[MediaFile]:
        query = select(MediaFile).where(MediaFile.download_status == "completed")
        
        if media_type:
            query = query.where(MediaFile.media_type == media_type)
        
        query = query.order_by(MediaFile.created_at.desc()).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_failed_media(self, limit: int = 100) -> list[MediaFile]:
        query = (
            select(MediaFile)
            .where(MediaFile.download_status == "failed")
            .order_by(MediaFile.updated_at.desc())
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def retry_failed_media(self, media_id: uuid.UUID) -> bool:
        media = await self.db.get(MediaFile, media_id)
        
        if not media or media.download_status != "failed":
            return False
        
        media.download_status = "pending"
        media.error_message = None
        
        await self.db.flush()
        return True

    async def retry_all_failed_media(self) -> int:
        query = (
            update(MediaFile)
            .where(MediaFile.download_status == "failed")
            .values(download_status="pending", error_message=None)
        )
        
        result = await self.db.execute(query)
        await self.db.flush()
        
        return result.rowcount

    async def check_duplicate_by_hash(self, file_hash: str) -> MediaFile | None:
        query = (
            select(MediaFile)
            .where(MediaFile.file_hash == file_hash)
            .where(MediaFile.download_status == "completed")
            .limit(1)
        )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def mark_as_downloading(self, media_id: uuid.UUID) -> bool:
        media = await self.db.get(MediaFile, media_id)
        
        if not media:
            return False
        
        if media.download_status != "pending":
            return False
        
        media.download_status = "downloading"
        await self.db.flush()
        
        return True

    async def get_media_count_by_status(self, status: str) -> int:
        query = select(func.count(MediaFile.id)).where(
            MediaFile.download_status == status
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_recent_media(
        self,
        hours: int = 24,
        limit: int = 100,
    ) -> list[MediaFile]:
        from datetime import timedelta
        
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        query = (
            select(MediaFile)
            .where(MediaFile.created_at >= cutoff)
            .order_by(MediaFile.created_at.desc())
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_media_with_tweet_info(
        self,
        media_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        media = await self.db.get(MediaFile, media_id)
        
        if not media:
            return None
        
        tweet = await self.db.get(Tweet, media.tweet_id)
        
        return {
            "media": media,
            "tweet": tweet,
        }

    async def bulk_update_status(
        self,
        media_ids: list[uuid.UUID],
        status: str,
        error: str | None = None,
    ) -> int:
        query = (
            update(MediaFile)
            .where(MediaFile.id.in_(media_ids))
            .values(download_status=status, error_message=error)
        )
        
        result = await self.db.execute(query)
        await self.db.flush()
        
        return result.rowcount
