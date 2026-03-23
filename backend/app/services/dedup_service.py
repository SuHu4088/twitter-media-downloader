import uuid
from dataclasses import dataclass

from sqlalchemy import func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dedup_record import DedupRecord
from app.models.media_file import MediaFile


@dataclass
class DedupStats:
    total_records: int
    hash_records: int
    tweet_records: int
    url_records: int
    orphan_records: int


class DedupService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_file_hash(self, file_hash: str) -> DedupRecord | None:
        if not file_hash:
            return None
        
        query = select(DedupRecord).where(DedupRecord.file_hash == file_hash)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def check_tweet_id(self, tweet_id: str) -> DedupRecord | None:
        if not tweet_id:
            return None
        
        query = select(DedupRecord).where(DedupRecord.tweet_id == tweet_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def check_media_url(self, media_url: str) -> DedupRecord | None:
        if not media_url:
            return None
        
        query = select(DedupRecord).where(DedupRecord.media_url == media_url)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def add_file_hash(self, file_hash: str, media_id: uuid.UUID | None = None) -> DedupRecord:
        existing = await self.check_file_hash(file_hash)
        if existing:
            return existing
        
        record = DedupRecord(
            file_hash=file_hash,
            media_id=media_id,
        )
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        
        return record

    async def add_tweet_id(self, tweet_id: str) -> DedupRecord:
        existing = await self.check_tweet_id(tweet_id)
        if existing:
            return existing
        
        record = DedupRecord(tweet_id=tweet_id)
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        
        return record

    async def add_media_url(self, media_url: str, media_id: uuid.UUID | None = None) -> DedupRecord:
        existing = await self.check_media_url(media_url)
        if existing:
            return existing
        
        record = DedupRecord(
            media_url=media_url,
            media_id=media_id,
        )
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        
        return record

    async def get_duplicate_stats(self) -> DedupStats:
        total_query = select(func.count(DedupRecord.id))
        total_result = await self.db.execute(total_query)
        total_records = total_result.scalar() or 0

        hash_query = select(func.count(DedupRecord.id)).where(
            DedupRecord.file_hash.isnot(None)
        )
        hash_result = await self.db.execute(hash_query)
        hash_records = hash_result.scalar() or 0

        tweet_query = select(func.count(DedupRecord.id)).where(
            DedupRecord.tweet_id.isnot(None)
        )
        tweet_result = await self.db.execute(tweet_query)
        tweet_records = tweet_result.scalar() or 0

        url_query = select(func.count(DedupRecord.id)).where(
            DedupRecord.media_url.isnot(None)
        )
        url_result = await self.db.execute(url_query)
        url_records = url_result.scalar() or 0

        orphan_query = (
            select(func.count(DedupRecord.id))
            .where(DedupRecord.media_id.isnot(None))
            .where(
                ~DedupRecord.media_id.in_(
                    select(MediaFile.id)
                )
            )
        )
        orphan_result = await self.db.execute(orphan_query)
        orphan_records = orphan_result.scalar() or 0

        return DedupStats(
            total_records=total_records,
            hash_records=hash_records,
            tweet_records=tweet_records,
            url_records=url_records,
            orphan_records=orphan_records,
        )

    async def cleanup_orphan_records(self) -> int:
        query = (
            delete(DedupRecord)
            .where(DedupRecord.media_id.isnot(None))
            .where(
                ~DedupRecord.media_id.in_(
                    select(MediaFile.id)
                )
            )
        )
        
        result = await self.db.execute(query)
        await self.db.flush()
        
        return result.rowcount

    async def add_dedup_record(
        self,
        file_hash: str | None = None,
        tweet_id: str | None = None,
        media_url: str | None = None,
        media_id: uuid.UUID | None = None,
    ) -> DedupRecord:
        records = []
        
        if file_hash:
            record = await self.add_file_hash(file_hash, media_id)
            records.append(record)
        
        if tweet_id:
            record = await self.add_tweet_id(tweet_id)
            records.append(record)
        
        if media_url:
            record = await self.add_media_url(media_url, media_id)
            records.append(record)
        
        return records[0] if records else DedupRecord(media_id=media_id)

    async def is_duplicate(
        self,
        file_hash: str | None = None,
        tweet_id: str | None = None,
        media_url: str | None = None,
    ) -> bool:
        if file_hash and await self.check_file_hash(file_hash):
            return True
        if tweet_id and await self.check_tweet_id(tweet_id):
            return True
        if media_url and await self.check_media_url(media_url):
            return True
        return False

    async def get_duplicate_info(
        self,
        file_hash: str | None = None,
        tweet_id: str | None = None,
        media_url: str | None = None,
    ) -> dict:
        result = {
            "is_duplicate": False,
            "duplicate_type": None,
            "existing_media_id": None,
        }
        
        if file_hash:
            record = await self.check_file_hash(file_hash)
            if record:
                result["is_duplicate"] = True
                result["duplicate_type"] = "file_hash"
                result["existing_media_id"] = record.media_id
                return result
        
        if tweet_id:
            record = await self.check_tweet_id(tweet_id)
            if record:
                result["is_duplicate"] = True
                result["duplicate_type"] = "tweet_id"
                result["existing_media_id"] = record.media_id
                return result
        
        if media_url:
            record = await self.check_media_url(media_url)
            if record:
                result["is_duplicate"] = True
                result["duplicate_type"] = "media_url"
                result["existing_media_id"] = record.media_id
                return result
        
        return result

    async def remove_file_hash(self, file_hash: str) -> bool:
        query = delete(DedupRecord).where(DedupRecord.file_hash == file_hash)
        result = await self.db.execute(query)
        await self.db.flush()
        return result.rowcount > 0

    async def remove_tweet_id(self, tweet_id: str) -> bool:
        query = delete(DedupRecord).where(DedupRecord.tweet_id == tweet_id)
        result = await self.db.execute(query)
        await self.db.flush()
        return result.rowcount > 0

    async def remove_media_url(self, media_url: str) -> bool:
        query = delete(DedupRecord).where(DedupRecord.media_url == media_url)
        result = await self.db.execute(query)
        await self.db.flush()
        return result.rowcount > 0
