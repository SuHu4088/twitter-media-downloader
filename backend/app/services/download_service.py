import asyncio
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import aiofiles
import httpx

from app.core.config import settings
from app.utils.file_utils import ensure_dir, get_file_extension, get_unique_filename, sanitize_filename
from app.utils.hash_utils import calculate_file_hash_async


@dataclass
class DownloadResult:
    success: bool
    file_path: str | None = None
    file_size: int = 0
    file_hash: str | None = None
    error: str | None = None
    downloaded_bytes: int = 0
    resume_supported: bool = False
    skipped: bool = False
    skip_reason: str | None = None


@dataclass
class BatchDownloadResult:
    total: int
    successful: int
    failed: int
    skipped: int
    results: list[DownloadResult]


class DownloadService:
    def __init__(
        self,
        proxy_url: str | None = None,
        timeout: float = 60.0,
        max_retries: int = 3,
        chunk_size: int = 8192,
    ):
        self.proxy_url = proxy_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.chunk_size = chunk_size
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "DownloadService":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def start(self) -> None:
        if self._client is None:
            proxy = self.proxy_url or self._get_default_proxy()
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout, connect=30.0),
                proxy=proxy,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                },
            )

    def _get_default_proxy(self) -> str | None:
        proxy_dict = settings.proxy_dict
        if proxy_dict:
            return proxy_dict.get("https") or proxy_dict.get("http")
        return None

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def download_file(
        self,
        url: str,
        save_path: str,
        chunk_size: int = 8192,
        headers: dict[str, str] | None = None,
    ) -> DownloadResult:
        if self._client is None:
            await self.start()

        save_path = Path(save_path)
        ensure_dir(save_path.parent)

        request_headers = headers or {}

        try:
            async with self._client.stream("GET", url, headers=request_headers) as response:
                response.raise_for_status()
                
                total_size = int(response.headers.get("content-length", 0))
                downloaded_bytes = 0

                async with aiofiles.open(save_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size):
                        await f.write(chunk)
                        downloaded_bytes += len(chunk)

                file_hash = await calculate_file_hash_async(str(save_path))
                file_size = save_path.stat().st_size

                return DownloadResult(
                    success=True,
                    file_path=str(save_path),
                    file_size=file_size,
                    file_hash=file_hash,
                    downloaded_bytes=downloaded_bytes,
                )

        except httpx.HTTPStatusError as e:
            return DownloadResult(
                success=False,
                error=f"HTTP错误: {e.response.status_code}",
            )
        except httpx.RequestError as e:
            return DownloadResult(
                success=False,
                error=f"请求错误: {str(e)}",
            )
        except Exception as e:
            return DownloadResult(
                success=False,
                error=f"下载失败: {str(e)}",
            )

    async def download_with_retry(
        self,
        url: str,
        save_path: str,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ) -> DownloadResult:
        last_result: DownloadResult | None = None

        for attempt in range(max_retries):
            result = await self.download_file(url, save_path)
            
            if result.success:
                return result
            
            last_result = result
            
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (2 ** attempt))

        return last_result or DownloadResult(
            success=False,
            error="下载失败，已达到最大重试次数",
        )

    async def download_batch(
        self,
        urls: list[str],
        save_dir: str,
        max_concurrent: int = 5,
        filename_generator: callable | None = None,
    ) -> BatchDownloadResult:
        ensure_dir(save_dir)
        
        semaphore = asyncio.Semaphore(max_concurrent)
        results: list[DownloadResult] = []

        async def download_with_semaphore(url: str, index: int) -> DownloadResult:
            async with semaphore:
                if filename_generator:
                    filename = filename_generator(url, index)
                else:
                    ext = get_file_extension(url)
                    filename = f"media_{index}{ext}"
                
                filename = sanitize_filename(filename)
                filename = get_unique_filename(save_dir, filename)
                save_path = os.path.join(save_dir, filename)
                
                return await self.download_with_retry(url, save_path)

        tasks = [
            download_with_semaphore(url, i)
            for i, url in enumerate(urls)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        processed_results: list[DownloadResult] = []
        for result in results:
            if isinstance(result, Exception):
                processed_results.append(DownloadResult(
                    success=False,
                    error=str(result),
                ))
            else:
                processed_results.append(result)

        successful = sum(1 for r in processed_results if r.success and not r.skipped)
        failed = sum(1 for r in processed_results if not r.success and not r.skipped)
        skipped = sum(1 for r in processed_results if r.skipped)

        return BatchDownloadResult(
            total=len(urls),
            successful=successful,
            failed=failed,
            skipped=skipped,
            results=processed_results,
        )

    async def get_file_hash(self, file_path: str) -> str:
        return await calculate_file_hash_async(file_path)

    async def get_file_size(self, file_path: str) -> int:
        path = Path(file_path)
        if path.exists():
            return path.stat().st_size
        return 0

    async def check_file_exists(self, file_hash: str) -> bool:
        from app.services.media_service import MediaService
        from app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            service = MediaService(db)
            existing = await service.get_media_by_hash(file_hash)
            return existing is not None

    def generate_save_path(
        self,
        media_url: str,
        tweet_id: str,
        media_type: str,
        index: int = 0,
    ) -> str:
        download_dir = Path(settings.DOWNLOAD_DIR)
        
        type_dir = "images" if media_type in ("photo", "image") else "videos"
        save_dir = download_dir / type_dir / str(tweet_id)
        
        ext = get_file_extension(media_url)
        filename = f"{tweet_id}_{index}{ext}" if index > 0 else f"{tweet_id}{ext}"
        filename = sanitize_filename(filename)
        
        return str(save_dir / filename)

    async def get_partial_download_progress(self, file_path: str) -> int:
        path = Path(file_path)
        if path.exists():
            return path.stat().st_size
        return 0

    async def resume_download(
        self,
        url: str,
        file_path: str,
        start_byte: int | None = None,
    ) -> DownloadResult:
        if self._client is None:
            await self.start()

        file_path = Path(file_path)
        
        if start_byte is None:
            start_byte = await self.get_partial_download_progress(str(file_path))

        if start_byte == 0:
            return await self.download_file(url, str(file_path))

        headers = {"Range": f"bytes={start_byte}-"}

        try:
            async with self._client.stream("GET", url, headers=headers) as response:
                if response.status_code not in (206, 200):
                    if response.status_code == 416:
                        return DownloadResult(
                            success=True,
                            file_path=str(file_path),
                            file_size=start_byte,
                            resume_supported=False,
                            error="文件已完整下载",
                        )
                    response.raise_for_status()

                resume_supported = response.status_code == 206
                
                if response.status_code == 200:
                    return await self.download_file(url, str(file_path))

                total_size = int(response.headers.get("content-length", 0)) + start_byte
                downloaded_bytes = start_byte

                async with aiofiles.open(file_path, "ab") as f:
                    async for chunk in response.aiter_bytes(self.chunk_size):
                        await f.write(chunk)
                        downloaded_bytes += len(chunk)

                file_hash = await calculate_file_hash_async(str(file_path))
                file_size = file_path.stat().st_size

                return DownloadResult(
                    success=True,
                    file_path=str(file_path),
                    file_size=file_size,
                    file_hash=file_hash,
                    downloaded_bytes=downloaded_bytes - start_byte,
                    resume_supported=resume_supported,
                )

        except httpx.HTTPStatusError as e:
            return DownloadResult(
                success=False,
                error=f"HTTP错误: {e.response.status_code}",
                resume_supported=e.response.status_code == 416,
            )
        except httpx.RequestError as e:
            return DownloadResult(
                success=False,
                error=f"请求错误: {str(e)}",
            )
        except Exception as e:
            return DownloadResult(
                success=False,
                error=f"断点续传失败: {str(e)}",
            )

    async def get_remote_file_info(self, url: str) -> dict[str, Any]:
        if self._client is None:
            await self.start()

        try:
            response = await self._client.head(url)
            response.raise_for_status()

            return {
                "url": url,
                "content_length": int(response.headers.get("content-length", 0)),
                "content_type": response.headers.get("content-type", ""),
                "accept_ranges": response.headers.get("accept-ranges", ""),
                "last_modified": response.headers.get("last-modified", ""),
                "etag": response.headers.get("etag", ""),
                "supports_resume": response.headers.get("accept-ranges", "") == "bytes",
            }
        except Exception as e:
            return {
                "url": url,
                "error": str(e),
            }

    async def download_with_progress(
        self,
        url: str,
        save_path: str,
        progress_callback: callable | None = None,
    ) -> DownloadResult:
        if self._client is None:
            await self.start()

        save_path = Path(save_path)
        ensure_dir(save_path.parent)

        try:
            async with self._client.stream("GET", url) as response:
                response.raise_for_status()
                
                total_size = int(response.headers.get("content-length", 0))
                downloaded_bytes = 0

                async with aiofiles.open(save_path, "wb") as f:
                    async for chunk in response.aiter_bytes(self.chunk_size):
                        await f.write(chunk)
                        downloaded_bytes += len(chunk)
                        
                        if progress_callback:
                            await progress_callback(downloaded_bytes, total_size)

                file_hash = await calculate_file_hash_async(str(save_path))
                file_size = save_path.stat().st_size

                return DownloadResult(
                    success=True,
                    file_path=str(save_path),
                    file_size=file_size,
                    file_hash=file_hash,
                    downloaded_bytes=downloaded_bytes,
                )

        except Exception as e:
            return DownloadResult(
                success=False,
                error=str(e),
            )

    async def check_duplicate_before_download(
        self,
        media_url: str,
        tweet_id: str | None = None,
        file_hash: str | None = None,
    ) -> dict[str, Any]:
        from app.core.database import AsyncSessionLocal
        from app.services.dedup_service import DedupService

        async with AsyncSessionLocal() as db:
            service = DedupService(db)
            return await service.get_duplicate_info(
                file_hash=file_hash,
                tweet_id=tweet_id,
                media_url=media_url,
            )

    async def download_with_dedup(
        self,
        url: str,
        save_path: str,
        tweet_id: str | None = None,
        media_id: uuid.UUID | None = None,
        skip_duplicate: bool = True,
        register_after_download: bool = True,
    ) -> DownloadResult:
        from app.core.database import AsyncSessionLocal
        from app.services.dedup_service import DedupService

        duplicate_info = await self.check_duplicate_before_download(
            media_url=url,
            tweet_id=tweet_id,
        )

        if skip_duplicate and duplicate_info["is_duplicate"]:
            return DownloadResult(
                success=True,
                skipped=True,
                skip_reason=f"重复文件，类型: {duplicate_info['duplicate_type']}",
            )

        result = await self.download_file(url, save_path)

        if result.success and register_after_download and result.file_hash:
            async with AsyncSessionLocal() as db:
                service = DedupService(db)
                await service.add_dedup_record(
                    file_hash=result.file_hash,
                    tweet_id=tweet_id,
                    media_url=url,
                    media_id=media_id,
                )
                await db.commit()

        return result

    async def download_batch_with_dedup(
        self,
        urls: list[str],
        save_dir: str,
        tweet_id: str | None = None,
        max_concurrent: int = 5,
        skip_duplicate: bool = True,
        filename_generator: callable | None = None,
    ) -> BatchDownloadResult:
        ensure_dir(save_dir)

        semaphore = asyncio.Semaphore(max_concurrent)

        async def download_with_semaphore(url: str, index: int) -> DownloadResult:
            async with semaphore:
                if filename_generator:
                    filename = filename_generator(url, index)
                else:
                    ext = get_file_extension(url)
                    filename = f"media_{index}{ext}"

                filename = sanitize_filename(filename)
                filename = get_unique_filename(save_dir, filename)
                save_path = os.path.join(save_dir, filename)

                return await self.download_with_dedup(
                    url=url,
                    save_path=save_path,
                    tweet_id=tweet_id,
                    skip_duplicate=skip_duplicate,
                )

        tasks = [
            download_with_semaphore(url, i)
            for i, url in enumerate(urls)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_results: list[DownloadResult] = []
        for result in results:
            if isinstance(result, Exception):
                processed_results.append(DownloadResult(
                    success=False,
                    error=str(result),
                ))
            else:
                processed_results.append(result)

        successful = sum(1 for r in processed_results if r.success and not r.skipped)
        failed = sum(1 for r in processed_results if not r.success)
        skipped = sum(1 for r in processed_results if r.skipped)

        return BatchDownloadResult(
            total=len(urls),
            successful=successful,
            failed=failed,
            skipped=skipped,
            results=processed_results,
        )


_download_service: DownloadService | None = None


async def get_download_service() -> DownloadService:
    global _download_service
    if _download_service is None:
        from app.utils.http_client import get_proxy_url
        proxy_url = await get_proxy_url()
        _download_service = DownloadService(proxy_url=proxy_url)
        await _download_service.start()
    return _download_service


async def close_download_service() -> None:
    global _download_service
    if _download_service:
        await _download_service.close()
        _download_service = None
