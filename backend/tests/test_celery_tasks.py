from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media_file import MediaFile
from app.models.tweet import Tweet
from app.models.twitter_account import TwitterAccount
from app.models.twitter_user import TwitterUser
from app.models.user import User
from app.tasks.download_tasks import download_media_task
from app.tasks.sync_tasks import sync_bookmarks_task, sync_likes_task
from app.tasks.telegram_tasks import upload_media_task


class TestSyncLikesTask:
    @pytest.mark.asyncio
    async def test_sync_likes_task_success(
        self,
        db_session: AsyncSession,
        test_twitter_account: TwitterAccount,
    ):
        with patch("app.tasks.sync_tasks.AsyncSessionLocal") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch("app.tasks.sync_tasks.get_redis_client") as mock_redis:
                mock_redis.return_value = MagicMock()

                with patch("app.tasks.sync_tasks.SyncService") as MockSyncService:
                    mock_service = MagicMock()
                    mock_service.sync_account_likes = AsyncMock(return_value={
                        "success": True,
                        "likes_count": 10,
                    })
                    MockSyncService.return_value = mock_service

                    result = sync_likes_task(account_id=str(test_twitter_account.id))

        assert result["success"] is True
        assert result["likes_count"] == 10

    @pytest.mark.asyncio
    async def test_sync_likes_task_no_account(self, db_session: AsyncSession):
        with patch("app.tasks.sync_tasks.AsyncSessionLocal") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch("app.tasks.sync_tasks.get_redis_client") as mock_redis:
                mock_redis.return_value = MagicMock()

                with patch("app.tasks.sync_tasks.SyncService") as MockSyncService:
                    mock_service = MagicMock()
                    mock_service.sync_all_accounts_likes = AsyncMock(return_value={
                        "success": True,
                        "total_likes": 0,
                    })
                    MockSyncService.return_value = mock_service

                    result = sync_likes_task()

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_sync_likes_task_error(self, db_session: AsyncSession):
        with patch("app.tasks.sync_tasks.AsyncSessionLocal") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch("app.tasks.sync_tasks.get_redis_client") as mock_redis:
                mock_redis.return_value = MagicMock()

                with patch("app.tasks.sync_tasks.SyncService") as MockSyncService:
                    mock_service = MagicMock()
                    mock_service.sync_account_likes = AsyncMock(
                        side_effect=Exception("Sync error")
                    )
                    MockSyncService.return_value = mock_service

                    task = MagicMock()
                    task.request.retries = 0
                    task.max_retries = 3
                    task.retry = MagicMock(side_effect=Exception("Retry"))

                    with pytest.raises(Exception):
                        sync_likes_task.__wrapped__(
                            task,
                            account_id=str(uuid4()),
                        )


class TestSyncBookmarksTask:
    @pytest.mark.asyncio
    async def test_sync_bookmarks_task_success(
        self,
        db_session: AsyncSession,
        test_twitter_account: TwitterAccount,
    ):
        with patch("app.tasks.sync_tasks.AsyncSessionLocal") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch("app.tasks.sync_tasks.get_redis_client") as mock_redis:
                mock_redis.return_value = MagicMock()

                with patch("app.tasks.sync_tasks.SyncService") as MockSyncService:
                    mock_service = MagicMock()
                    mock_service.sync_account_bookmarks = AsyncMock(return_value={
                        "success": True,
                        "bookmarks_count": 15,
                    })
                    MockSyncService.return_value = mock_service

                    result = sync_bookmarks_task(account_id=str(test_twitter_account.id))

        assert result["success"] is True
        assert result["bookmarks_count"] == 15

    @pytest.mark.asyncio
    async def test_sync_bookmarks_task_all_accounts(self, db_session: AsyncSession):
        with patch("app.tasks.sync_tasks.AsyncSessionLocal") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch("app.tasks.sync_tasks.get_redis_client") as mock_redis:
                mock_redis.return_value = MagicMock()

                with patch("app.tasks.sync_tasks.SyncService") as MockSyncService:
                    mock_service = MagicMock()
                    mock_service.sync_all_accounts_bookmarks = AsyncMock(return_value={
                        "success": True,
                        "total_bookmarks": 30,
                        "accounts_synced": 2,
                    })
                    MockSyncService.return_value = mock_service

                    result = sync_bookmarks_task()

        assert result["success"] is True


class TestDownloadMediaTask:
    @pytest.mark.asyncio
    async def test_download_media_task_success(
        self,
        db_session: AsyncSession,
        test_media_file: MediaFile,
    ):
        with patch("app.tasks.download_tasks.AsyncSessionLocal") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch("app.tasks.download_tasks.MediaService") as MockMediaService:
                mock_media_service = MagicMock()
                mock_media_service.get_media_by_id = AsyncMock(return_value=test_media_file)
                mock_media_service.mark_as_downloading = AsyncMock(return_value=True)
                mock_media_service.update_media_status = AsyncMock()
                MockMediaService.return_value = mock_media_service

                with patch("app.tasks.download_tasks.DownloadService") as MockDownloadService:
                    mock_download_service = MagicMock()
                    mock_download_service.__aenter__ = AsyncMock(return_value=mock_download_service)
                    mock_download_service.__aexit__ = AsyncMock(return_value=None)
                    mock_download_service.generate_save_path = MagicMock(
                        return_value="/tmp/test.jpg"
                    )
                    mock_download_service.get_partial_download_progress = AsyncMock(
                        return_value=0
                    )
                    mock_download_service.download_with_retry = AsyncMock(
                        return_value=MagicMock(
                            success=True,
                            file_path="/tmp/test.jpg",
                            file_size=1024,
                            file_hash="abc123",
                        )
                    )
                    MockDownloadService.return_value = mock_download_service

                    with patch("app.tasks.download_tasks.ensure_dir"):
                        with patch("app.tasks.download_tasks.uuid.UUID", return_value=test_media_file.id):
                            task = MagicMock()
                            task.request.retries = 0
                            task.max_retries = 3

                            result = download_media_task.__wrapped__(
                                task,
                                str(test_media_file.id),
                            )

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_download_media_task_media_not_found(self, db_session: AsyncSession):
        with patch("app.tasks.download_tasks.AsyncSessionLocal") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch("app.tasks.download_tasks.MediaService") as MockMediaService:
                mock_media_service = MagicMock()
                mock_media_service.get_media_by_id = AsyncMock(return_value=None)
                MockMediaService.return_value = mock_media_service

                task = MagicMock()
                result = download_media_task.__wrapped__(task, str(uuid4()))

        assert result["success"] is False
        assert "不存在" in result["error"]

    @pytest.mark.asyncio
    async def test_download_media_task_already_downloaded(
        self,
        db_session: AsyncSession,
        test_media_file: MediaFile,
    ):
        test_media_file.download_status = "completed"

        with patch("app.tasks.download_tasks.AsyncSessionLocal") as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(return_value=db_session)
            mock_session.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch("app.tasks.download_tasks.MediaService") as MockMediaService:
                mock_media_service = MagicMock()
                mock_media_service.get_media_by_id = AsyncMock(return_value=test_media_file)
                MockMediaService.return_value = mock_media_service

                task = MagicMock()
                result = download_media_task.__wrapped__(
                    task,
                    str(test_media_file.id),
                )

        assert result["success"] is True
        assert "已下载" in result["message"]


class TestUploadMediaTask:
    @pytest.mark.asyncio
    async def test_upload_media_task_success(
        self,
        db_session: AsyncSession,
        test_media_file: MediaFile,
    ):
        test_media_file.local_path = "/tmp/test.jpg"
        test_media_file.download_status = "completed"

        from app.models.telegram_upload import TelegramUpload

        upload_record = TelegramUpload(
            id=uuid4(),
            media_file_id=test_media_file.id,
            chat_id="test_chat_id",
            status="pending",
            retry_count=0,
        )

        with patch("app.tasks.telegram_tasks.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db

            mock_db.execute = MagicMock()
            mock_db.execute.side_effect = [
                MagicMock(scalar_one_or_none=MagicMock(return_value=upload_record)),
                MagicMock(scalar_one_or_none=MagicMock(return_value=test_media_file)),
            ]
            mock_db.commit = MagicMock()

            with patch("app.tasks.telegram_tasks.TDLService") as MockTDLService:
                mock_tdl = MagicMock()
                mock_tdl.upload_file = MagicMock(return_value={
                    "success": True,
                    "message_id": 12345,
                })
                MockTDLService.return_value = mock_tdl

                with patch("app.tasks.telegram_tasks._build_caption", return_value="Test caption"):
                    task = MagicMock()
                    result = upload_media_task.__wrapped__(
                        task,
                        str(upload_record.id),
                    )

        assert result["success"] is True
        assert result["message"] == "上传成功"

    @pytest.mark.asyncio
    async def test_upload_media_task_record_not_found(self):
        with patch("app.tasks.telegram_tasks.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db

            mock_db.execute = MagicMock()
            mock_db.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)
            mock_db.close = MagicMock()

            task = MagicMock()
            result = upload_media_task.__wrapped__(task, str(uuid4()))

        assert result["success"] is False
        assert "不存在" in result["error"]

    @pytest.mark.asyncio
    async def test_upload_media_task_media_not_downloaded(self):
        from app.models.telegram_upload import TelegramUpload

        upload_record = TelegramUpload(
            id=uuid4(),
            media_file_id=uuid4(),
            chat_id="test_chat_id",
            status="pending",
            retry_count=0,
        )

        with patch("app.tasks.telegram_tasks.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db

            mock_db.execute = MagicMock()
            mock_db.execute.side_effect = [
                MagicMock(scalar_one_or_none=MagicMock(return_value=upload_record)),
                MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
            ]
            mock_db.commit = MagicMock()
            mock_db.close = MagicMock()

            task = MagicMock()
            result = upload_media_task.__wrapped__(
                task,
                str(upload_record.id),
            )

        assert result["success"] is False
        assert "不存在或未下载" in result["error"]

    @pytest.mark.asyncio
    async def test_upload_media_task_upload_failure(self):
        from app.models.telegram_upload import TelegramUpload

        media_file = MagicMock()
        media_file.local_path = "/tmp/test.jpg"
        media_file.tweet = None

        upload_record = TelegramUpload(
            id=uuid4(),
            media_file_id=uuid4(),
            chat_id="test_chat_id",
            status="pending",
            retry_count=0,
        )

        with patch("app.tasks.telegram_tasks.SessionLocal") as mock_session:
            mock_db = MagicMock()
            mock_session.return_value = mock_db

            mock_db.execute = MagicMock()
            mock_db.execute.side_effect = [
                MagicMock(scalar_one_or_none=MagicMock(return_value=upload_record)),
                MagicMock(scalar_one_or_none=MagicMock(return_value=media_file)),
            ]
            mock_db.commit = MagicMock()
            mock_db.close = MagicMock()

            with patch("app.tasks.telegram_tasks.TDLService") as MockTDLService:
                mock_tdl = MagicMock()
                mock_tdl.upload_file = MagicMock(return_value={
                    "success": False,
                    "error": "Upload failed",
                })
                MockTDLService.return_value = mock_tdl

                with patch("app.tasks.telegram_tasks._build_caption", return_value="Test caption"):
                    task = MagicMock()
                    task.request.retries = 0
                    task.max_retries = 3

                    with pytest.raises(Exception):
                        upload_media_task.__wrapped__(
                            task,
                            str(upload_record.id),
                        )
