import asyncio
import uuid
from typing import Any

from celery import shared_task

from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.services.download_service import DownloadService
from app.services.media_service import MediaService
from app.utils.file_utils import ensure_dir


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def download_media_task(self, media_id: str) -> dict[str, Any]:
    async def _download():
        async with AsyncSessionLocal() as db:
            media_service = MediaService(db)
            
            media = await media_service.get_media_by_id(uuid.UUID(media_id))
            if not media:
                return {"success": False, "error": "媒体记录不存在"}
            
            if media.download_status == "completed":
                return {"success": True, "message": "媒体已下载"}
            
            marked = await media_service.mark_as_downloading(media.id)
            if not marked:
                return {"success": False, "error": "无法标记为下载中"}
            
            download_service = DownloadService()
            
            try:
                async with download_service:
                    save_path = download_service.generate_save_path(
                        media.url,
                        str(media.tweet_id),
                        media.media_type,
                    )
                    
                    ensure_dir(save_path.rsplit("/", 1)[0] if "/" in save_path else save_path.rsplit("\\", 1)[0])
                    
                    partial_size = await download_service.get_partial_download_progress(save_path)
                    
                    if partial_size > 0:
                        result = await download_service.resume_download(
                            media.url,
                            save_path,
                            partial_size,
                        )
                    else:
                        result = await download_service.download_with_retry(
                            media.url,
                            save_path,
                        )
                    
                    if result.success:
                        existing = await media_service.check_duplicate_by_hash(result.file_hash)
                        
                        if existing and existing.id != media.id:
                            await media_service.update_media_status(
                                media.id,
                                "completed",
                                local_path=result.file_path,
                                file_hash=result.file_hash,
                                file_size=result.file_size,
                            )
                            return {
                                "success": True,
                                "file_path": result.file_path,
                                "file_size": result.file_size,
                                "duplicate": True,
                            }
                        
                        await media_service.update_media_status(
                            media.id,
                            "completed",
                            local_path=result.file_path,
                            file_hash=result.file_hash,
                            file_size=result.file_size,
                        )
                        
                        return {
                            "success": True,
                            "file_path": result.file_path,
                            "file_size": result.file_size,
                            "file_hash": result.file_hash,
                        }
                    else:
                        await media_service.update_media_status(
                            media.id,
                            "failed",
                            error=result.error,
                        )
                        
                        if "网络" in str(result.error) or "timeout" in str(result.error).lower():
                            raise self.retry(exc=Exception(result.error))
                        
                        return {"success": False, "error": result.error}
                        
            except Exception as e:
                await media_service.update_media_status(
                    media.id,
                    "failed",
                    error=str(e),
                )
                raise
    
    return asyncio.run(_download())


@celery_app.task(bind=True)
def batch_download_task(
    self,
    tweet_ids: list[str],
    twitter_account_id: str,
) -> dict[str, Any]:
    async def _batch_download():
        async with AsyncSessionLocal() as db:
            media_service = MediaService(db)
            
            all_media_ids = []
            
            for tweet_id_str in tweet_ids:
                tweet_id = uuid.UUID(tweet_id_str)
                media_list = await media_service.get_media_by_tweet(tweet_id)
                all_media_ids.extend([str(m.id) for m in media_list if m.download_status == "pending"])
            
            if not all_media_ids:
                return {
                    "success": True,
                    "total": 0,
                    "message": "没有待下载的媒体",
                }
            
            from celery import group
            
            job = group(download_media_task.s(media_id) for media_id in all_media_ids)
            result = job.apply_async()
            
            return {
                "success": True,
                "total": len(all_media_ids),
                "task_ids": all_media_ids,
                "group_id": result.id,
            }
    
    return asyncio.run(_batch_download())


@celery_app.task(bind=True)
def process_tweet_media_task(self, tweet_id: str) -> dict[str, Any]:
    async def _process():
        async with AsyncSessionLocal() as db:
            media_service = MediaService(db)
            
            tweet_uuid = uuid.UUID(tweet_id)
            media_list = await media_service.get_media_by_tweet(tweet_uuid)
            
            if not media_list:
                return {
                    "success": True,
                    "message": "该推文没有媒体文件",
                    "total": 0,
                }
            
            pending_media = [m for m in media_list if m.download_status == "pending"]
            
            if not pending_media:
                return {
                    "success": True,
                    "message": "所有媒体已处理",
                    "total": len(media_list),
                }
            
            task_ids = []
            for media in pending_media:
                task = download_media_task.delay(str(media.id))
                task_ids.append(task.id)
            
            return {
                "success": True,
                "total": len(pending_media),
                "task_ids": task_ids,
            }
    
    return asyncio.run(_process())


@celery_app.task
def retry_failed_downloads_task() -> dict[str, Any]:
    async def _retry():
        async with AsyncSessionLocal() as db:
            media_service = MediaService(db)
            
            count = await media_service.retry_all_failed_media()
            
            failed_media = await media_service.get_failed_media(limit=100)
            
            task_ids = []
            for media in failed_media:
                task = download_media_task.delay(str(media.id))
                task_ids.append(task.id)
            
            return {
                "success": True,
                "retried_count": count,
                "task_ids": task_ids,
            }
    
    return asyncio.run(_retry())


@celery_app.task
def cleanup_incomplete_downloads_task() -> dict[str, Any]:
    async def _cleanup():
        async with AsyncSessionLocal() as db:
            media_service = MediaService(db)
            
            from datetime import datetime, timedelta
            
            cutoff = datetime.utcnow() - timedelta(hours=1)
            
            from sqlalchemy import select, update
            from app.models.media_file import MediaFile
            
            query = (
                update(MediaFile)
                .where(MediaFile.download_status == "downloading")
                .where(MediaFile.updated_at < cutoff)
                .values(download_status="pending", error_message="下载超时，已重置")
            )
            
            result = await db.execute(query)
            await db.commit()
            
            return {
                "success": True,
                "reset_count": result.rowcount,
            }
    
    return asyncio.run(_cleanup())


@celery_app.task
def get_download_statistics_task() -> dict[str, Any]:
    async def _get_stats():
        async with AsyncSessionLocal() as db:
            media_service = MediaService(db)
            
            stats = await media_service.get_media_statistics()
            
            return {
                "success": True,
                "statistics": {
                    "total_count": stats.total_count,
                    "pending_count": stats.pending_count,
                    "downloading_count": stats.downloading_count,
                    "completed_count": stats.completed_count,
                    "failed_count": stats.failed_count,
                    "total_size": stats.total_size,
                    "by_type": stats.by_type,
                },
            }
    
    return asyncio.run(_get_stats())
