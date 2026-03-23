import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException, TelegramAPIException
from app.core.security import decrypt_token, encrypt_token
from app.models.media_file import MediaFile
from app.models.telegram_upload import TelegramUpload
from app.services.tdl_service import TDLService


class TelegramService:
    MAX_RETRY_COUNT = 3
    UPLOAD_STATUS_PENDING = "pending"
    UPLOAD_STATUS_UPLOADING = "uploading"
    UPLOAD_STATUS_COMPLETED = "completed"
    UPLOAD_STATUS_FAILED = "failed"

    def __init__(self, db: AsyncSession, tdl_service: TDLService | None = None):
        self.db = db
        self.tdl_service = tdl_service or TDLService()

    async def configure_telegram(self, config_data: dict[str, Any]) -> dict[str, Any]:
        required_fields = ["api_id", "api_hash", "phone"]
        for field in required_fields:
            if not config_data.get(field):
                raise BadRequestException(message=f"缺少必要字段: {field}")

        encrypted_hash = encrypt_token(config_data["api_hash"])
        
        result = await self.tdl_service.configure(
            api_id=config_data["api_id"],
            api_hash=config_data["api_hash"],
            phone=config_data["phone"],
        )

        return {
            "success": True,
            "message": "Telegram配置成功",
            "config": {
                "api_id": config_data["api_id"],
                "phone": config_data["phone"],
                "api_hash_encrypted": encrypted_hash,
            },
        }

    async def test_connection(self) -> dict[str, Any]:
        status = await self.tdl_service.check_login_status()
        
        if status.get("logged_in"):
            try:
                me = await self.tdl_service.get_me()
                return {
                    "success": True,
                    "message": "Telegram连接正常",
                    "user": me.get("data"),
                }
            except Exception as e:
                return {
                    "success": False,
                    "message": f"获取用户信息失败: {str(e)}",
                }
        
        return {
            "success": False,
            "message": status.get("message", "未登录Telegram"),
            "need_login": True,
        }

    async def login_telegram(self) -> dict[str, Any]:
        result = await self.tdl_service.login()
        return result

    async def upload_media(
        self,
        media_id: uuid.UUID,
        chat_id: str,
        caption: str | None = None,
    ) -> TelegramUpload:
        result = await self.db.execute(
            select(MediaFile).where(MediaFile.id == media_id)
        )
        media_file = result.scalar_one_or_none()
        
        if not media_file:
            raise NotFoundException(message="媒体文件不存在")
        
        if not media_file.local_path:
            raise BadRequestException(message="媒体文件尚未下载完成")
        
        existing = await self.db.execute(
            select(TelegramUpload).where(
                TelegramUpload.media_file_id == media_id,
                TelegramUpload.chat_id == chat_id,
                TelegramUpload.status == self.UPLOAD_STATUS_COMPLETED,
            )
        )
        if existing.scalar_one_or_none():
            raise BadRequestException(message="该媒体已成功上传到此聊天")
        
        upload_record = TelegramUpload(
            media_file_id=media_id,
            chat_id=chat_id,
            status=self.UPLOAD_STATUS_PENDING,
        )
        self.db.add(upload_record)
        await self.db.flush()
        
        return upload_record

    async def execute_upload(self, upload_id: uuid.UUID) -> dict[str, Any]:
        result = await self.db.execute(
            select(TelegramUpload).where(TelegramUpload.id == upload_id)
        )
        upload_record = result.scalar_one_or_none()
        
        if not upload_record:
            raise NotFoundException(message="上传记录不存在")
        
        result = await self.db.execute(
            select(MediaFile).where(MediaFile.id == upload_record.media_file_id)
        )
        media_file = result.scalar_one_or_none()
        
        if not media_file or not media_file.local_path:
            upload_record.status = self.UPLOAD_STATUS_FAILED
            upload_record.error_message = "媒体文件不存在或未下载"
            await self.db.flush()
            raise BadRequestException(message="媒体文件不存在或未下载")
        
        upload_record.status = self.UPLOAD_STATUS_UPLOADING
        await self.db.flush()
        
        try:
            caption = self._build_caption(media_file)
            
            result = await self.tdl_service.upload_file(
                file_path=media_file.local_path,
                chat_id=upload_record.chat_id,
                caption=caption,
            )
            
            upload_record.status = self.UPLOAD_STATUS_COMPLETED
            upload_record.message_id = result.get("message_id")
            upload_record.error_message = None
            await self.db.flush()
            
            return {
                "success": True,
                "message": "上传成功",
                "upload_id": str(upload_id),
            }
            
        except TelegramAPIException as e:
            upload_record.status = self.UPLOAD_STATUS_FAILED
            upload_record.error_message = str(e.message)
            upload_record.retry_count += 1
            await self.db.flush()
            
            return {
                "success": False,
                "message": str(e.message),
                "upload_id": str(upload_id),
                "retry_count": upload_record.retry_count,
            }
        except Exception as e:
            upload_record.status = self.UPLOAD_STATUS_FAILED
            upload_record.error_message = str(e)
            upload_record.retry_count += 1
            await self.db.flush()
            
            return {
                "success": False,
                "message": f"上传失败: {str(e)}",
                "upload_id": str(upload_id),
                "retry_count": upload_record.retry_count,
            }

    async def upload_media_batch(
        self,
        media_ids: list[uuid.UUID],
        chat_id: str,
    ) -> list[TelegramUpload]:
        upload_records = []
        
        for media_id in media_ids:
            try:
                record = await self.upload_media(media_id, chat_id)
                upload_records.append(record)
            except Exception:
                continue
        
        return upload_records

    async def get_upload_status(self, upload_id: uuid.UUID) -> TelegramUpload:
        result = await self.db.execute(
            select(TelegramUpload).where(TelegramUpload.id == upload_id)
        )
        upload_record = result.scalar_one_or_none()
        
        if not upload_record:
            raise NotFoundException(message="上传记录不存在")
        
        return upload_record

    async def retry_failed_upload(self, upload_id: uuid.UUID) -> dict[str, Any]:
        upload_record = await self.get_upload_status(upload_id)
        
        if upload_record.status != self.UPLOAD_STATUS_FAILED:
            raise BadRequestException(message="只能重试失败的上传任务")
        
        if upload_record.retry_count >= self.MAX_RETRY_COUNT:
            raise BadRequestException(
                message=f"已达到最大重试次数 ({self.MAX_RETRY_COUNT})"
            )
        
        upload_record.status = self.UPLOAD_STATUS_PENDING
        upload_record.error_message = None
        await self.db.flush()
        
        return await self.execute_upload(upload_id)

    async def get_upload_history(
        self,
        page: int = 1,
        page_size: int = 50,
        status: str | None = None,
        chat_id: str | None = None,
    ) -> tuple[list[TelegramUpload], int]:
        query = select(TelegramUpload)
        
        if status:
            query = query.where(TelegramUpload.status == status)
        
        if chat_id:
            query = query.where(TelegramUpload.chat_id == chat_id)
        
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0
        
        result = await self.db.execute(
            query.order_by(TelegramUpload.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        uploads = result.scalars().all()
        
        return list(uploads), total

    async def get_pending_uploads(self) -> list[TelegramUpload]:
        result = await self.db.execute(
            select(TelegramUpload).where(
                TelegramUpload.status == self.UPLOAD_STATUS_PENDING
            )
        )
        return list(result.scalars().all())

    async def get_failed_uploads(self) -> list[TelegramUpload]:
        result = await self.db.execute(
            select(TelegramUpload).where(
                TelegramUpload.status == self.UPLOAD_STATUS_FAILED,
                TelegramUpload.retry_count < self.MAX_RETRY_COUNT,
            )
        )
        return list(result.scalars().all())

    async def cancel_upload(self, upload_id: uuid.UUID) -> None:
        upload_record = await self.get_upload_status(upload_id)
        
        if upload_record.status == self.UPLOAD_STATUS_UPLOADING:
            raise BadRequestException(message="无法取消正在上传的任务")
        
        await self.db.delete(upload_record)

    async def get_chat_info(self, chat_id: str) -> dict[str, Any]:
        return await self.tdl_service.get_chat_info(chat_id)

    async def get_chats(self, limit: int = 50) -> dict[str, Any]:
        return await self.tdl_service.get_chats(limit)

    def _build_caption(self, media_file: MediaFile) -> str:
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
