import uuid
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dedup_record import DedupRecord
from app.models.media_file import MediaFile
from app.services.dedup_service import DedupService, DedupStats


class TestDedupService:
    @pytest.fixture
    def dedup_service(self, db_session: AsyncSession) -> DedupService:
        return DedupService(db_session)

    @pytest.mark.asyncio
    async def test_check_file_hash_found(
        self,
        dedup_service: DedupService,
        test_dedup_record: DedupRecord,
    ) -> None:
        result = await dedup_service.check_file_hash(test_dedup_record.file_hash)

        assert result is not None
        assert result.file_hash == test_dedup_record.file_hash

    @pytest.mark.asyncio
    async def test_check_file_hash_not_found(
        self,
        dedup_service: DedupService,
    ) -> None:
        result = await dedup_service.check_file_hash("nonexistent_hash")

        assert result is None

    @pytest.mark.asyncio
    async def test_check_file_hash_empty(
        self,
        dedup_service: DedupService,
    ) -> None:
        result = await dedup_service.check_file_hash("")

        assert result is None

    @pytest.mark.asyncio
    async def test_check_file_hash_none(
        self,
        dedup_service: DedupService,
    ) -> None:
        result = await dedup_service.check_file_hash(None)

        assert result is None

    @pytest.mark.asyncio
    async def test_check_tweet_id_found(
        self,
        dedup_service: DedupService,
        test_dedup_record: DedupRecord,
    ) -> None:
        result = await dedup_service.check_tweet_id(test_dedup_record.tweet_id)

        assert result is not None
        assert result.tweet_id == test_dedup_record.tweet_id

    @pytest.mark.asyncio
    async def test_check_tweet_id_not_found(
        self,
        dedup_service: DedupService,
    ) -> None:
        result = await dedup_service.check_tweet_id("nonexistent_tweet")

        assert result is None

    @pytest.mark.asyncio
    async def test_check_tweet_id_empty(
        self,
        dedup_service: DedupService,
    ) -> None:
        result = await dedup_service.check_tweet_id("")

        assert result is None

    @pytest.mark.asyncio
    async def test_check_media_url_found(
        self,
        dedup_service: DedupService,
        test_dedup_record: DedupRecord,
    ) -> None:
        result = await dedup_service.check_media_url(test_dedup_record.media_url)

        assert result is not None
        assert result.media_url == test_dedup_record.media_url

    @pytest.mark.asyncio
    async def test_check_media_url_not_found(
        self,
        dedup_service: DedupService,
    ) -> None:
        result = await dedup_service.check_media_url("https://nonexistent.url/media.jpg")

        assert result is None

    @pytest.mark.asyncio
    async def test_check_media_url_empty(
        self,
        dedup_service: DedupService,
    ) -> None:
        result = await dedup_service.check_media_url("")

        assert result is None

    @pytest.mark.asyncio
    async def test_add_file_hash_new(
        self,
        dedup_service: DedupService,
    ) -> None:
        new_hash = "new_file_hash_abc123"
        media_id = uuid.uuid4()

        result = await dedup_service.add_file_hash(new_hash, media_id)

        assert result is not None
        assert result.file_hash == new_hash
        assert result.media_id == media_id

    @pytest.mark.asyncio
    async def test_add_file_hash_existing(
        self,
        dedup_service: DedupService,
        test_dedup_record: DedupRecord,
    ) -> None:
        result = await dedup_service.add_file_hash(test_dedup_record.file_hash)

        assert result.id == test_dedup_record.id

    @pytest.mark.asyncio
    async def test_add_tweet_id_new(
        self,
        dedup_service: DedupService,
    ) -> None:
        new_tweet_id = "new_tweet_12345"

        result = await dedup_service.add_tweet_id(new_tweet_id)

        assert result is not None
        assert result.tweet_id == new_tweet_id

    @pytest.mark.asyncio
    async def test_add_tweet_id_existing(
        self,
        dedup_service: DedupService,
        test_dedup_record: DedupRecord,
    ) -> None:
        result = await dedup_service.add_tweet_id(test_dedup_record.tweet_id)

        assert result.id == test_dedup_record.id

    @pytest.mark.asyncio
    async def test_add_media_url_new(
        self,
        dedup_service: DedupService,
    ) -> None:
        new_url = "https://example.com/new_media.jpg"
        media_id = uuid.uuid4()

        result = await dedup_service.add_media_url(new_url, media_id)

        assert result is not None
        assert result.media_url == new_url
        assert result.media_id == media_id

    @pytest.mark.asyncio
    async def test_add_media_url_existing(
        self,
        dedup_service: DedupService,
        test_dedup_record: DedupRecord,
    ) -> None:
        result = await dedup_service.add_media_url(test_dedup_record.media_url)

        assert result.id == test_dedup_record.id

    @pytest.mark.asyncio
    async def test_get_duplicate_stats(
        self,
        dedup_service: DedupService,
        test_dedup_record: DedupRecord,
    ) -> None:
        result = await dedup_service.get_duplicate_stats()

        assert isinstance(result, DedupStats)
        assert result.total_records >= 1
        assert result.hash_records >= 1
        assert result.tweet_records >= 1
        assert result.url_records >= 1

    @pytest.mark.asyncio
    async def test_get_duplicate_stats_empty(
        self,
        db_session: AsyncSession,
    ) -> None:
        empty_service = DedupService(db_session)
        result = await empty_service.get_duplicate_stats()

        assert result.total_records == 0
        assert result.hash_records == 0
        assert result.tweet_records == 0
        assert result.url_records == 0

    @pytest.mark.asyncio
    async def test_add_dedup_record_with_hash(
        self,
        dedup_service: DedupService,
    ) -> None:
        file_hash = "dedup_hash_123"

        result = await dedup_service.add_dedup_record(file_hash=file_hash)

        assert result.file_hash == file_hash

    @pytest.mark.asyncio
    async def test_add_dedup_record_with_tweet_id(
        self,
        dedup_service: DedupService,
    ) -> None:
        tweet_id = "dedup_tweet_456"

        result = await dedup_service.add_dedup_record(tweet_id=tweet_id)

        assert result.tweet_id == tweet_id

    @pytest.mark.asyncio
    async def test_add_dedup_record_with_media_url(
        self,
        dedup_service: DedupService,
    ) -> None:
        media_url = "https://example.com/dedup_media.jpg"

        result = await dedup_service.add_dedup_record(media_url=media_url)

        assert result.media_url == media_url

    @pytest.mark.asyncio
    async def test_add_dedup_record_all_fields(
        self,
        dedup_service: DedupService,
    ) -> None:
        file_hash = "all_fields_hash"
        tweet_id = "all_fields_tweet"
        media_url = "https://example.com/all_fields.jpg"
        media_id = uuid.uuid4()

        result = await dedup_service.add_dedup_record(
            file_hash=file_hash,
            tweet_id=tweet_id,
            media_url=media_url,
            media_id=media_id,
        )

        assert result.file_hash == file_hash

    @pytest.mark.asyncio
    async def test_is_duplicate_by_hash(
        self,
        dedup_service: DedupService,
        test_dedup_record: DedupRecord,
    ) -> None:
        result = await dedup_service.is_duplicate(
            file_hash=test_dedup_record.file_hash
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_is_duplicate_by_tweet_id(
        self,
        dedup_service: DedupService,
        test_dedup_record: DedupRecord,
    ) -> None:
        result = await dedup_service.is_duplicate(
            tweet_id=test_dedup_record.tweet_id
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_is_duplicate_by_media_url(
        self,
        dedup_service: DedupService,
        test_dedup_record: DedupRecord,
    ) -> None:
        result = await dedup_service.is_duplicate(
            media_url=test_dedup_record.media_url
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_is_duplicate_not_found(
        self,
        dedup_service: DedupService,
    ) -> None:
        result = await dedup_service.is_duplicate(
            file_hash="nonexistent_hash",
            tweet_id="nonexistent_tweet",
            media_url="https://nonexistent.url/media.jpg",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_get_duplicate_info_by_hash(
        self,
        dedup_service: DedupService,
        test_dedup_record: DedupRecord,
    ) -> None:
        result = await dedup_service.get_duplicate_info(
            file_hash=test_dedup_record.file_hash
        )

        assert result["is_duplicate"] is True
        assert result["duplicate_type"] == "file_hash"
        assert result["existing_media_id"] == test_dedup_record.media_id

    @pytest.mark.asyncio
    async def test_get_duplicate_info_by_tweet_id(
        self,
        dedup_service: DedupService,
        test_dedup_record: DedupRecord,
    ) -> None:
        result = await dedup_service.get_duplicate_info(
            tweet_id=test_dedup_record.tweet_id
        )

        assert result["is_duplicate"] is True
        assert result["duplicate_type"] == "tweet_id"

    @pytest.mark.asyncio
    async def test_get_duplicate_info_by_media_url(
        self,
        dedup_service: DedupService,
        test_dedup_record: DedupRecord,
    ) -> None:
        result = await dedup_service.get_duplicate_info(
            media_url=test_dedup_record.media_url
        )

        assert result["is_duplicate"] is True
        assert result["duplicate_type"] == "media_url"

    @pytest.mark.asyncio
    async def test_get_duplicate_info_not_found(
        self,
        dedup_service: DedupService,
    ) -> None:
        result = await dedup_service.get_duplicate_info(
            file_hash="nonexistent_hash",
            tweet_id="nonexistent_tweet",
            media_url="https://nonexistent.url/media.jpg",
        )

        assert result["is_duplicate"] is False
        assert result["duplicate_type"] is None
        assert result["existing_media_id"] is None

    @pytest.mark.asyncio
    async def test_remove_file_hash(
        self,
        dedup_service: DedupService,
        db_session: AsyncSession,
    ) -> None:
        new_hash = "hash_to_remove"
        await dedup_service.add_file_hash(new_hash)
        await db_session.commit()

        result = await dedup_service.remove_file_hash(new_hash)
        await db_session.commit()

        assert result is True

        check_result = await dedup_service.check_file_hash(new_hash)
        assert check_result is None

    @pytest.mark.asyncio
    async def test_remove_file_hash_not_found(
        self,
        dedup_service: DedupService,
        db_session: AsyncSession,
    ) -> None:
        result = await dedup_service.remove_file_hash("nonexistent_hash")

        assert result is False

    @pytest.mark.asyncio
    async def test_remove_tweet_id(
        self,
        dedup_service: DedupService,
        db_session: AsyncSession,
    ) -> None:
        new_tweet_id = "tweet_to_remove"
        await dedup_service.add_tweet_id(new_tweet_id)
        await db_session.commit()

        result = await dedup_service.remove_tweet_id(new_tweet_id)
        await db_session.commit()

        assert result is True

        check_result = await dedup_service.check_tweet_id(new_tweet_id)
        assert check_result is None

    @pytest.mark.asyncio
    async def test_remove_tweet_id_not_found(
        self,
        dedup_service: DedupService,
        db_session: AsyncSession,
    ) -> None:
        result = await dedup_service.remove_tweet_id("nonexistent_tweet")

        assert result is False

    @pytest.mark.asyncio
    async def test_remove_media_url(
        self,
        dedup_service: DedupService,
        db_session: AsyncSession,
    ) -> None:
        new_url = "https://example.com/url_to_remove.jpg"
        await dedup_service.add_media_url(new_url)
        await db_session.commit()

        result = await dedup_service.remove_media_url(new_url)
        await db_session.commit()

        assert result is True

        check_result = await dedup_service.check_media_url(new_url)
        assert check_result is None

    @pytest.mark.asyncio
    async def test_remove_media_url_not_found(
        self,
        dedup_service: DedupService,
        db_session: AsyncSession,
    ) -> None:
        result = await dedup_service.remove_media_url(
            "https://nonexistent.url/media.jpg"
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_cleanup_orphan_records(
        self,
        dedup_service: DedupService,
        db_session: AsyncSession,
        test_media_file: MediaFile,
    ) -> None:
        orphan_media_id = uuid.uuid4()

        orphan_record = DedupRecord(
            file_hash="orphan_hash",
            media_id=orphan_media_id,
        )
        db_session.add(orphan_record)
        await db_session.commit()

        valid_record = DedupRecord(
            file_hash="valid_hash",
            media_id=test_media_file.id,
        )
        db_session.add(valid_record)
        await db_session.commit()

        removed_count = await dedup_service.cleanup_orphan_records()
        await db_session.commit()

        assert removed_count >= 1

    @pytest.mark.asyncio
    async def test_multiple_dedup_checks(
        self,
        dedup_service: DedupService,
    ) -> None:
        file_hash = "multi_check_hash"
        tweet_id = "multi_check_tweet"
        media_url = "https://example.com/multi_check.jpg"

        await dedup_service.add_dedup_record(
            file_hash=file_hash,
            tweet_id=tweet_id,
            media_url=media_url,
        )

        assert await dedup_service.is_duplicate(file_hash=file_hash)
        assert await dedup_service.is_duplicate(tweet_id=tweet_id)
        assert await dedup_service.is_duplicate(media_url=media_url)

    @pytest.mark.asyncio
    async def test_get_duplicate_info_priority(
        self,
        dedup_service: DedupService,
    ) -> None:
        file_hash = "priority_hash"
        tweet_id = "priority_tweet"

        await dedup_service.add_file_hash(file_hash)
        await dedup_service.add_tweet_id(tweet_id)

        result = await dedup_service.get_duplicate_info(
            file_hash=file_hash,
            tweet_id=tweet_id,
        )

        assert result["is_duplicate"] is True
        assert result["duplicate_type"] == "file_hash"
