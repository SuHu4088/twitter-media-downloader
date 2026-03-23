import logging
import time
from uuid import UUID

from celery import shared_task
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import Base
from app.models.media_file import MediaFile
from app.models.telegram_upload import TelegramUpload
from app.services.tdl_service import TDLService

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.DATABASE_URL.replace("+asyncpg", ""),
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="app.tasks.telegram_tasks.upload_media_task",
)
def upload_media_task(self, upload_id: str) -> dict:
    logger.info(f"开始处理上传任务: {upload_id}")
    
    db = SessionLocal()
    try:
        result = db.execute(
            select(TelegramUpload).where(TelegramUpload.id == UUID(upload_id))
        )
        upload_record = result.scalar_one_or_none()
        
        if not upload_record:
            logger.error(f"上传记录不存在: {upload_id}")
            return {"success": False, "error": "上传记录不存在"}
        
        if upload_record.status == "completed":
            logger.info(f"上传任务已完成: {upload_id}")
            return {"success": True, "message": "上传任务已完成"}
        
        result = db.execute(
            select(MediaFile).where(MediaFile.id == upload_record.media_file_id)
        )
        media_file = result.scalar_one_or_none()
        
        if not media_file or not media_file.local_path:
            upload_record.status = "failed"
            upload_record.error_message = "媒体文件不存在或未下载"
            db.commit()
            return {"success": False, "error": "媒体文件不存在或未下载"}
        
        upload_record.status = "uploading"
        db.commit()
        
        tdl_service = TDLService()
        
        try:
            caption = _build_caption(media_file)
            
            upload_result = tdl_service.upload_file(
                file_path=media_file.local_path,
                chat_id=upload_record.chat_id,
                caption=caption,
            )
            
            if upload_result.get("success"):
                upload_record.status = "completed"
                upload_record.message_id = upload_result.get("message_id")
                upload_record.error_message = None
                db.commit()
                
                logger.info(f"上传成功: {upload_id}")
                return {
                    "success": True,
                    "message": "上传成功",
                    "upload_id": upload_id,
                }
            else:
                raise Exception(upload_result.get("error", "上传失败"))
                
        except Exception as e:
            upload_record.status = "failed"
            upload_record.error_message = str(e)
            upload_record.retry_count += 1
            db.commit()
            
            logger.error(f"上传失败: {upload_id}, 错误: {str(e)}")
            
            if upload_record.retry_count < 3:
                raise self.retry(exc=e)
            
            return {
                "success": False,
                "error": str(e),
                "upload_id": upload_id,
                "retry_count": upload_record.retry_count,
            }
            
    except Exception as e:
        logger.exception(f"上传任务异常: {upload_id}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()


@shared_task(
    bind=True,
    name="app.tasks.telegram_tasks.batch_upload_task",
)
def batch_upload_task(self, upload_ids: list[str]) -> dict:
    logger.info(f"开始批量上传任务: {len(upload_ids)}个文件")
    
    results = []
    success_count = 0
    failed_count = 0
    
    for i, upload_id in enumerate(upload_ids):
        logger.info(f"处理第 {i+1}/{len(upload_ids)} 个上传任务")
        
        result = upload_media_task(upload_id)
        results.append({
            "upload_id": upload_id,
            "result": result,
        })
        
        if result.get("success"):
            success_count += 1
        else:
            failed_count += 1
        
        if i < len(upload_ids) - 1:
            time.sleep(2)
    
    logger.info(f"批量上传完成: 成功{success_count}, 失败{failed_count}")
    
    return {
        "success": failed_count == 0,
        "total": len(upload_ids),
        "success_count": success_count,
        "failed_count": failed_count,
        "results": results,
    }


@shared_task(
    name="app.tasks.telegram_tasks.auto_upload_new_media_task",
)
def auto_upload_new_media_task() -> dict:
    logger.info("开始自动上传新媒体任务")
    
    db = SessionLocal()
    try:
        result = db.execute(
            select(TelegramUpload).where(
                TelegramUpload.status == "pending"
            ).limit(10)
        )
        pending_uploads = result.scalars().all()
        
        if not pending_uploads:
            logger.info("没有待处理的上传任务")
            return {"success": True, "message": "没有待处理的上传任务"}
        
        upload_ids = [str(upload.id) for upload in pending_uploads]
        
        result = batch_upload_task(upload_ids)
        
        return result
        
    except Exception as e:
        logger.exception("自动上传任务异常")
        return {"success": False, "error": str(e)}
    finally:
        db.close()


@shared_task(
    name="app.tasks.telegram_tasks.retry_failed_uploads_task",
)
def retry_failed_uploads_task() -> dict:
    logger.info("开始重试失败的上传任务")
    
    db = SessionLocal()
    try:
        result = db.execute(
            select(TelegramUpload).where(
                TelegramUpload.status == "failed",
                TelegramUpload.retry_count < 3,
            ).limit(10)
        )
        failed_uploads = result.scalars().all()
        
        if not failed_uploads:
            logger.info("没有需要重试的上传任务")
            return {"success": True, "message": "没有需要重试的上传任务"}
        
        for upload in failed_uploads:
            upload.status = "pending"
            db.commit()
        
        upload_ids = [str(upload.id) for upload in failed_uploads]
        
        result = batch_upload_task(upload_ids)
        
        return result
        
    except Exception as e:
        logger.exception("重试任务异常")
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def _build_caption(media_file: MediaFile) -> str:
    parts = []
    
    if media_file.tweet:
        tweet = media_file.tweet
        if tweet.text:
            text = tweet.text[:500]
            parts.append(text)
        
        if tweet.twitter_user:
            parts.append(f"\n来源: @{tweet.twitter_user.username}")
    
    parts.append(f"\n媒体类型: {media_file.media_type}")
    
    if media_file.file_size:
        size_mb = media_file.file_size / (1024 * 1024)
        parts.append(f"大小: {size_mb:.2f} MB")
    
    return "\n".join(parts)
