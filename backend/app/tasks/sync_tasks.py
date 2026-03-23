import asyncio
import logging
from typing import Any
from uuid import UUID

from celery import shared_task
from redis import Redis

from app.core.config import settings
from app.core.celery_app import celery_app
from app.core.database import AsyncSessionLocal
from app.services.sync_service import SyncService

logger = logging.getLogger(__name__)


def get_redis_client() -> Redis:
    return Redis.from_url(settings.REDIS_URL, decode_responses=True)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    name="app.tasks.sync_tasks.sync_likes_task",
)
def sync_likes_task(self, account_id: str | None = None) -> dict[str, Any]:
    logger.info(f"开始执行点赞同步任务: account_id={account_id}")

    async def _sync():
        async with AsyncSessionLocal() as db:
            redis = get_redis_client()
            sync_service = SyncService(db, redis)

            if account_id:
                result = await sync_service.sync_account_likes(account_id)
            else:
                result = await sync_service.sync_all_accounts_likes()

            return result

    try:
        return asyncio.run(_sync())
    except Exception as e:
        logger.exception(f"点赞同步任务失败: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        return {"success": False, "error": str(e)}


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    name="app.tasks.sync_tasks.sync_bookmarks_task",
)
def sync_bookmarks_task(self, account_id: str | None = None) -> dict[str, Any]:
    logger.info(f"开始执行收藏同步任务: account_id={account_id}")

    async def _sync():
        async with AsyncSessionLocal() as db:
            redis = get_redis_client()
            sync_service = SyncService(db, redis)

            if account_id:
                result = await sync_service.sync_account_bookmarks(account_id)
            else:
                result = await sync_service.sync_all_accounts_bookmarks()

            return result

    try:
        return asyncio.run(_sync())
    except Exception as e:
        logger.exception(f"收藏同步任务失败: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        return {"success": False, "error": str(e)}


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    name="app.tasks.sync_tasks.sync_following_timeline_task",
)
def sync_following_timeline_task(self, account_id: str | None = None) -> dict[str, Any]:
    logger.info(f"开始执行关注时间线同步任务: account_id={account_id}")

    async def _sync():
        async with AsyncSessionLocal() as db:
            redis = get_redis_client()
            sync_service = SyncService(db, redis)

            if account_id:
                result = await sync_service.sync_account_following_timeline(account_id)
            else:
                result = await sync_service.sync_all_accounts_following_timeline()

            return result

    try:
        return asyncio.run(_sync())
    except Exception as e:
        logger.exception(f"关注时间线同步任务失败: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        return {"success": False, "error": str(e)}


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="app.tasks.sync_tasks.check_following_changes_task",
)
def check_following_changes_task(self, account_id: str | None = None) -> dict[str, Any]:
    logger.info(f"开始执行关注变化检测任务: account_id={account_id}")

    async def _check():
        async with AsyncSessionLocal() as db:
            redis = get_redis_client()
            sync_service = SyncService(db, redis)

            if account_id:
                result = await sync_service.detect_new_following(account_id)

                if result.get("success") and result.get("new_following_count", 0) > 0:
                    new_users = result.get("new_users", [])
                    for user in new_users:
                        full_sync_new_following_task.delay(
                            user_id=user.get("id"),
                            account_id=account_id,
                        )
                    logger.info(
                        f"检测到新关注 {result['new_following_count']} 个，已触发全量同步任务"
                    )
            else:
                result = await sync_service.detect_all_accounts_new_following()

                if result.get("total_new_following", 0) > 0:
                    for detail in result.get("details", []):
                        if detail.get("success") and detail.get("new_following_count", 0) > 0:
                            account_id_str = detail.get("account_id")
                            detect_result = await sync_service.detect_new_following(
                                account_id_str
                            )
                            for user in detect_result.get("new_users", []):
                                full_sync_new_following_task.delay(
                                    user_id=user.get("id"),
                                    account_id=account_id_str,
                                )

            return result

    try:
        return asyncio.run(_check())
    except Exception as e:
        logger.exception(f"关注变化检测任务失败: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        return {"success": False, "error": str(e)}


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=600,
    name="app.tasks.sync_tasks.full_sync_new_following_task",
)
def full_sync_new_following_task(
    self, user_id: str, account_id: str
) -> dict[str, Any]:
    logger.info(f"开始执行新关注用户全量同步任务: user_id={user_id}, account_id={account_id}")

    async def _sync():
        async with AsyncSessionLocal() as db:
            redis = get_redis_client()
            sync_service = SyncService(db, redis)

            result = await sync_service.full_sync_user(
                user_id=user_id,
                account_id=account_id,
                max_results=100,
                max_pages=20,
            )

            return result

    try:
        return asyncio.run(_sync())
    except Exception as e:
        logger.exception(f"新关注用户全量同步任务失败: user_id={user_id}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        return {"success": False, "error": str(e), "user_id": user_id}


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    name="app.tasks.sync_tasks.sync_all_likes",
)
def sync_all_likes(self) -> dict[str, Any]:
    logger.info("开始执行所有账号点赞同步任务")

    async def _sync():
        async with AsyncSessionLocal() as db:
            redis = get_redis_client()
            sync_service = SyncService(db, redis)

            result = await sync_service.sync_all_accounts_likes()

            return result

    try:
        return asyncio.run(_sync())
    except Exception as e:
        logger.exception(f"所有账号点赞同步任务失败: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        return {"success": False, "error": str(e)}


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    name="app.tasks.sync_tasks.sync_all_bookmarks",
)
def sync_all_bookmarks(self) -> dict[str, Any]:
    logger.info("开始执行所有账号收藏同步任务")

    async def _sync():
        async with AsyncSessionLocal() as db:
            redis = get_redis_client()
            sync_service = SyncService(db, redis)

            result = await sync_service.sync_all_accounts_bookmarks()

            return result

    try:
        return asyncio.run(_sync())
    except Exception as e:
        logger.exception(f"所有账号收藏同步任务失败: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        return {"success": False, "error": str(e)}


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    name="app.tasks.sync_tasks.refresh_all_twitter_tokens",
)
def refresh_all_twitter_tokens(self) -> dict[str, Any]:
    logger.info("开始执行Twitter令牌刷新任务")

    async def _refresh():
        from sqlalchemy import select

        from app.models.twitter_account import TwitterAccount
        from app.services.twitter_service import TwitterService

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(TwitterAccount).where(TwitterAccount.is_active == True)
            )
            accounts = list(result.scalars().all())

            twitter_service = TwitterService(db)

            results = {
                "total_accounts": len(accounts),
                "refreshed": 0,
                "failed": 0,
                "details": [],
            }

            for account in accounts:
                try:
                    refreshed_account = await twitter_service.refresh_token_if_needed(
                        account
                    )

                    if refreshed_account.is_active:
                        results["refreshed"] += 1
                        results["details"].append(
                            {
                                "account_id": str(account.id),
                                "username": account.twitter_username,
                                "success": True,
                            }
                        )
                    else:
                        results["failed"] += 1
                        results["details"].append(
                            {
                                "account_id": str(account.id),
                                "username": account.twitter_username,
                                "success": False,
                                "error": "令牌刷新失败，账号已禁用",
                            }
                        )

                except Exception as e:
                    results["failed"] += 1
                    results["details"].append(
                        {
                            "account_id": str(account.id),
                            "username": account.twitter_username,
                            "success": False,
                            "error": str(e),
                        }
                    )
                    logger.error(f"刷新令牌失败: {account.twitter_username}, {e}")

            return results

    try:
        return asyncio.run(_refresh())
    except Exception as e:
        logger.exception(f"Twitter令牌刷新任务失败: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        return {"success": False, "error": str(e)}


@celery_app.task(
    name="app.tasks.sync_tasks.cancel_sync_task",
)
def cancel_sync_task(account_id: str, sync_type: str) -> dict[str, Any]:
    logger.info(f"取消同步任务: account_id={account_id}, sync_type={sync_type}")

    async def _cancel():
        async with AsyncSessionLocal() as db:
            redis = get_redis_client()
            sync_service = SyncService(db, redis)

            result = await sync_service.cancel_sync(account_id, sync_type)

            return {
                "success": result,
                "account_id": account_id,
                "sync_type": sync_type,
            }

    return asyncio.run(_cancel())


@celery_app.task(
    name="app.tasks.sync_tasks.get_sync_status_task",
)
def get_sync_status_task(account_id: str, sync_type: str) -> dict[str, Any]:
    logger.info(f"获取同步状态: account_id={account_id}, sync_type={sync_type}")

    async def _get_status():
        async with AsyncSessionLocal() as db:
            redis = get_redis_client()
            sync_service = SyncService(db, redis)

            status = await sync_service.get_sync_status(account_id, sync_type)

            return {
                "success": True,
                "account_id": account_id,
                "sync_type": sync_type,
                "status": status,
            }

    return asyncio.run(_get_status())
