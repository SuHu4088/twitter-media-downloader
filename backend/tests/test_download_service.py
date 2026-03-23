import os
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.download_service import (
    BatchDownloadResult,
    DownloadResult,
    DownloadService,
)


class TestDownloadService:
    @pytest.fixture
    def download_service(self) -> DownloadService:
        return DownloadService(
            proxy_url=None,
            timeout=60.0,
            max_retries=3,
            chunk_size=8192,
        )

    @pytest.fixture
    def temp_file(self, tmp_path: Path) -> Path:
        file_path = tmp_path / "test_download.jpg"
        file_path.write_bytes(b"test content for download")
        return file_path

    @pytest.fixture
    def temp_dir(self, tmp_path: Path) -> Path:
        download_dir = tmp_path / "downloads"
        download_dir.mkdir()
        return download_dir

    @pytest.mark.asyncio
    async def test_download_file_success(
        self, download_service: DownloadService, temp_dir: Path
    ) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-length": "100"}
        mock_response.raise_for_status = MagicMock()

        async def mock_aiter_bytes(chunk_size: int):
            yield b"test content"

        mock_response.aiter_bytes = mock_aiter_bytes

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.stream = MagicMock(return_value=mock_response)
        mock_client.stream.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_client.stream.return_value.__aexit__ = AsyncMock()

        download_service._client = mock_client

        save_path = str(temp_dir / "downloaded.jpg")

        with patch(
            "app.services.download_service.calculate_file_hash_async",
            new_callable=AsyncMock,
            return_value="test_hash_123",
        ):
            result = await download_service.download_file(
                url="https://example.com/image.jpg",
                save_path=save_path,
            )

        assert result.success is True
        assert result.file_path == save_path
        assert result.file_hash == "test_hash_123"

    @pytest.mark.asyncio
    async def test_download_file_http_error(
        self, download_service: DownloadService, temp_dir: Path
    ) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=mock_response,
            )
        )

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.stream = MagicMock(return_value=mock_response)
        mock_client.stream.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_client.stream.return_value.__aexit__ = AsyncMock()

        download_service._client = mock_client

        save_path = str(temp_dir / "failed.jpg")

        result = await download_service.download_file(
            url="https://example.com/notfound.jpg",
            save_path=save_path,
        )

        assert result.success is False
        assert "HTTP错误" in result.error

    @pytest.mark.asyncio
    async def test_download_file_request_error(
        self, download_service: DownloadService, temp_dir: Path
    ) -> None:
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.stream = MagicMock(
            side_effect=httpx.RequestError("Connection error")
        )

        download_service._client = mock_client

        save_path = str(temp_dir / "failed.jpg")

        result = await download_service.download_file(
            url="https://example.com/error.jpg",
            save_path=save_path,
        )

        assert result.success is False
        assert "请求错误" in result.error

    @pytest.mark.asyncio
    async def test_download_with_retry_success(
        self, download_service: DownloadService, temp_dir: Path
    ) -> None:
        success_result = DownloadResult(
            success=True,
            file_path=str(temp_dir / "success.jpg"),
            file_size=100,
            file_hash="hash123",
        )

        with patch.object(
            download_service,
            "download_file",
            new_callable=AsyncMock,
            return_value=success_result,
        ):
            result = await download_service.download_with_retry(
                url="https://example.com/image.jpg",
                save_path=str(temp_dir / "success.jpg"),
                max_retries=3,
                retry_delay=0.1,
            )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_download_with_retry_eventual_success(
        self, download_service: DownloadService, temp_dir: Path
    ) -> None:
        fail_result = DownloadResult(success=False, error="Network error")
        success_result = DownloadResult(
            success=True,
            file_path=str(temp_dir / "success.jpg"),
            file_size=100,
            file_hash="hash123",
        )

        with patch.object(
            download_service,
            "download_file",
            new_callable=AsyncMock,
            side_effect=[fail_result, success_result],
        ):
            result = await download_service.download_with_retry(
                url="https://example.com/image.jpg",
                save_path=str(temp_dir / "success.jpg"),
                max_retries=3,
                retry_delay=0.1,
            )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_download_with_retry_max_retries_exceeded(
        self, download_service: DownloadService, temp_dir: Path
    ) -> None:
        fail_result = DownloadResult(success=False, error="Network error")

        with patch.object(
            download_service,
            "download_file",
            new_callable=AsyncMock,
            return_value=fail_result,
        ):
            result = await download_service.download_with_retry(
                url="https://example.com/image.jpg",
                save_path=str(temp_dir / "failed.jpg"),
                max_retries=3,
                retry_delay=0.1,
            )

        assert result.success is False
        assert "下载失败" in result.error

    @pytest.mark.asyncio
    async def test_get_file_hash(
        self, download_service: DownloadService, temp_file: Path
    ) -> None:
        with patch(
            "app.services.download_service.calculate_file_hash_async",
            new_callable=AsyncMock,
            return_value="expected_hash",
        ):
            result = await download_service.get_file_hash(str(temp_file))

        assert result == "expected_hash"

    @pytest.mark.asyncio
    async def test_get_file_size_existing_file(
        self, download_service: DownloadService, temp_file: Path
    ) -> None:
        result = await download_service.get_file_size(str(temp_file))

        assert result == len(b"test content for download")

    @pytest.mark.asyncio
    async def test_get_file_size_nonexistent_file(
        self, download_service: DownloadService
    ) -> None:
        result = await download_service.get_file_size("/nonexistent/file.jpg")

        assert result == 0

    @pytest.mark.asyncio
    async def test_check_file_exists(
        self, download_service: DownloadService
    ) -> None:
        with patch(
            "app.services.download_service.AsyncSessionLocal"
        ) as mock_session:
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session.return_value.__aexit__ = AsyncMock()

            with patch(
                "app.services.download_service.MediaService"
            ) as mock_media_service:
                mock_service_instance = AsyncMock()
                mock_service_instance.get_media_by_hash = AsyncMock(return_value=None)
                mock_media_service.return_value = mock_service_instance

                result = await download_service.check_file_exists("test_hash")

                assert result is False

    @pytest.mark.asyncio
    async def test_check_file_exists_found(
        self, download_service: DownloadService
    ) -> None:
        mock_media = MagicMock()

        with patch(
            "app.services.download_service.AsyncSessionLocal"
        ) as mock_session:
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_session.return_value.__aexit__ = AsyncMock()

            with patch(
                "app.services.download_service.MediaService"
            ) as mock_media_service:
                mock_service_instance = AsyncMock()
                mock_service_instance.get_media_by_hash = AsyncMock(
                    return_value=mock_media
                )
                mock_media_service.return_value = mock_service_instance

                result = await download_service.check_file_exists("existing_hash")

                assert result is True

    def test_generate_save_path_photo(self, download_service: DownloadService) -> None:
        with patch("app.services.download_service.settings") as mock_settings:
            mock_settings.DOWNLOAD_DIR = "/downloads"

            result = download_service.generate_save_path(
                media_url="https://example.com/photo.jpg",
                tweet_id="tweet_123",
                media_type="photo",
                index=0,
            )

            assert "images" in result
            assert "tweet_123" in result
            assert result.endswith(".jpg")

    def test_generate_save_path_video(self, download_service: DownloadService) -> None:
        with patch("app.services.download_service.settings") as mock_settings:
            mock_settings.DOWNLOAD_DIR = "/downloads"

            result = download_service.generate_save_path(
                media_url="https://example.com/video.mp4",
                tweet_id="tweet_456",
                media_type="video",
                index=0,
            )

            assert "videos" in result
            assert "tweet_456" in result
            assert result.endswith(".mp4")

    def test_generate_save_path_with_index(
        self, download_service: DownloadService
    ) -> None:
        with patch("app.services.download_service.settings") as mock_settings:
            mock_settings.DOWNLOAD_DIR = "/downloads"

            result = download_service.generate_save_path(
                media_url="https://example.com/photo.jpg",
                tweet_id="tweet_789",
                media_type="photo",
                index=2,
            )

            assert "tweet_789_2" in result

    @pytest.mark.asyncio
    async def test_resume_download_from_beginning(
        self, download_service: DownloadService, temp_dir: Path
    ) -> None:
        success_result = DownloadResult(
            success=True,
            file_path=str(temp_dir / "resumed.jpg"),
            file_size=100,
            file_hash="hash123",
        )

        with patch.object(
            download_service,
            "download_file",
            new_callable=AsyncMock,
            return_value=success_result,
        ):
            result = await download_service.resume_download(
                url="https://example.com/image.jpg",
                file_path=str(temp_dir / "resumed.jpg"),
                start_byte=0,
            )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_resume_download_partial(
        self, download_service: DownloadService, temp_dir: Path
    ) -> None:
        existing_file = temp_dir / "partial.jpg"
        existing_file.write_bytes(b"existing content")

        mock_response = MagicMock()
        mock_response.status_code = 206
        mock_response.headers = {"content-length": "50"}

        async def mock_aiter_bytes(chunk_size: int):
            yield b" new content"

        mock_response.aiter_bytes = mock_aiter_bytes

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.stream = MagicMock(return_value=mock_response)
        mock_client.stream.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_client.stream.return_value.__aexit__ = AsyncMock()

        download_service._client = mock_client

        with patch(
            "app.services.download_service.calculate_file_hash_async",
            new_callable=AsyncMock,
            return_value="resumed_hash",
        ):
            result = await download_service.resume_download(
                url="https://example.com/image.jpg",
                file_path=str(existing_file),
            )

        assert result.success is True
        assert result.resume_supported is True

    @pytest.mark.asyncio
    async def test_resume_download_already_complete(
        self, download_service: DownloadService, temp_dir: Path
    ) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 416

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.stream = MagicMock(return_value=mock_response)
        mock_client.stream.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_client.stream.return_value.__aexit__ = AsyncMock()

        download_service._client = mock_client

        result = await download_service.resume_download(
            url="https://example.com/image.jpg",
            file_path=str(temp_dir / "complete.jpg"),
            start_byte=1000,
        )

        assert result.success is True
        assert "已完整下载" in result.error

    @pytest.mark.asyncio
    async def test_get_partial_download_progress_existing_file(
        self, download_service: DownloadService, temp_file: Path
    ) -> None:
        result = await download_service.get_partial_download_progress(str(temp_file))

        assert result == len(b"test content for download")

    @pytest.mark.asyncio
    async def test_get_partial_download_progress_nonexistent_file(
        self, download_service: DownloadService
    ) -> None:
        result = await download_service.get_partial_download_progress(
            "/nonexistent/file.jpg"
        )

        assert result == 0

    @pytest.mark.asyncio
    async def test_get_remote_file_info(self, download_service: DownloadService) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {
            "content-length": "1024",
            "content-type": "image/jpeg",
            "accept-ranges": "bytes",
            "last-modified": "Wed, 01 Jan 2024 00:00:00 GMT",
            "etag": '"abc123"',
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.head = AsyncMock(return_value=mock_response)

        download_service._client = mock_client

        result = await download_service.get_remote_file_info(
            "https://example.com/image.jpg"
        )

        assert result["content_length"] == 1024
        assert result["content_type"] == "image/jpeg"
        assert result["supports_resume"] is True

    @pytest.mark.asyncio
    async def test_get_remote_file_info_error(
        self, download_service: DownloadService
    ) -> None:
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.head = AsyncMock(side_effect=Exception("Network error"))

        download_service._client = mock_client

        result = await download_service.get_remote_file_info(
            "https://example.com/image.jpg"
        )

        assert "error" in result

    @pytest.mark.asyncio
    async def test_download_with_progress(
        self, download_service: DownloadService, temp_dir: Path
    ) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-length": "100"}
        mock_response.raise_for_status = MagicMock()

        async def mock_aiter_bytes(chunk_size: int):
            yield b"test content"

        mock_response.aiter_bytes = mock_aiter_bytes

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.stream = MagicMock(return_value=mock_response)
        mock_client.stream.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_client.stream.return_value.__aexit__ = AsyncMock()

        download_service._client = mock_client

        progress_calls = []

        async def progress_callback(downloaded: int, total: int) -> None:
            progress_calls.append((downloaded, total))

        save_path = str(temp_dir / "progress.jpg")

        with patch(
            "app.services.download_service.calculate_file_hash_async",
            new_callable=AsyncMock,
            return_value="progress_hash",
        ):
            result = await download_service.download_with_progress(
                url="https://example.com/image.jpg",
                save_path=save_path,
                progress_callback=progress_callback,
            )

        assert result.success is True
        assert len(progress_calls) > 0

    @pytest.mark.asyncio
    async def test_download_batch(
        self, download_service: DownloadService, temp_dir: Path
    ) -> None:
        success_result = DownloadResult(
            success=True,
            file_path=str(temp_dir / "batch_1.jpg"),
            file_size=100,
            file_hash="hash1",
        )

        with patch.object(
            download_service,
            "download_with_retry",
            new_callable=AsyncMock,
            return_value=success_result,
        ):
            result = await download_service.download_batch(
                urls=[
                    "https://example.com/image1.jpg",
                    "https://example.com/image2.jpg",
                ],
                save_dir=str(temp_dir),
                max_concurrent=2,
            )

        assert result.total == 2
        assert result.successful == 2
        assert result.failed == 0

    @pytest.mark.asyncio
    async def test_download_batch_with_failures(
        self, download_service: DownloadService, temp_dir: Path
    ) -> None:
        success_result = DownloadResult(
            success=True,
            file_path=str(temp_dir / "batch_1.jpg"),
            file_size=100,
            file_hash="hash1",
        )
        fail_result = DownloadResult(success=False, error="Download failed")

        with patch.object(
            download_service,
            "download_with_retry",
            new_callable=AsyncMock,
            side_effect=[success_result, fail_result],
        ):
            result = await download_service.download_batch(
                urls=[
                    "https://example.com/image1.jpg",
                    "https://example.com/image2.jpg",
                ],
                save_dir=str(temp_dir),
                max_concurrent=2,
            )

        assert result.total == 2
        assert result.successful == 1
        assert result.failed == 1

    @pytest.mark.asyncio
    async def test_context_manager(self, download_service: DownloadService) -> None:
        async with download_service as service:
            assert service is download_service
            assert download_service._client is not None

        assert download_service._client is None

    @pytest.mark.asyncio
    async def test_start_creates_client(self, download_service: DownloadService) -> None:
        assert download_service._client is None

        await download_service.start()

        assert download_service._client is not None

        await download_service.close()

    @pytest.mark.asyncio
    async def test_close_destroys_client(
        self, download_service: DownloadService
    ) -> None:
        await download_service.start()
        assert download_service._client is not None

        await download_service.close()

        assert download_service._client is None

    @pytest.mark.asyncio
    async def test_download_with_dedup_skip_duplicate(
        self, download_service: DownloadService, temp_dir: Path
    ) -> None:
        with patch.object(
            download_service,
            "check_duplicate_before_download",
            new_callable=AsyncMock,
            return_value={"is_duplicate": True, "duplicate_type": "file_hash"},
        ):
            result = await download_service.download_with_dedup(
                url="https://example.com/duplicate.jpg",
                save_path=str(temp_dir / "duplicate.jpg"),
                skip_duplicate=True,
            )

        assert result.success is True
        assert result.skipped is True
        assert "重复文件" in result.skip_reason

    @pytest.mark.asyncio
    async def test_download_with_dedup_new_file(
        self, download_service: DownloadService, temp_dir: Path
    ) -> None:
        success_result = DownloadResult(
            success=True,
            file_path=str(temp_dir / "new.jpg"),
            file_size=100,
            file_hash="new_hash",
        )

        with patch.object(
            download_service,
            "check_duplicate_before_download",
            new_callable=AsyncMock,
            return_value={"is_duplicate": False},
        ):
            with patch.object(
                download_service,
                "download_file",
                new_callable=AsyncMock,
                return_value=success_result,
            ):
                with patch(
                    "app.services.download_service.AsyncSessionLocal"
                ) as mock_session:
                    mock_db = AsyncMock()
                    mock_session.return_value.__aenter__ = AsyncMock(
                        return_value=mock_db
                    )
                    mock_session.return_value.__aexit__ = AsyncMock()

                    with patch(
                        "app.services.download_service.DedupService"
                    ) as mock_dedup:
                        mock_dedup_instance = AsyncMock()
                        mock_dedup.return_value = mock_dedup_instance

                        result = await download_service.download_with_dedup(
                            url="https://example.com/new.jpg",
                            save_path=str(temp_dir / "new.jpg"),
                            register_after_download=True,
                        )

        assert result.success is True
        assert result.skipped is False
