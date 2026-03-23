import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from redis import Redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.security import decrypt_token
from app.models.twitter_account import TwitterAccount
from app.models.twitter_user import TwitterUser
from app.services.tweet_service import TweetService
from app.services.twitter_client import TwitterClient

logger = logging.getLogger(__name__)


class SyncService:
    SYNC_LOCK_PREFIX = "sync_lock:"
    SYNC_STATUS_PREFIX = "sync_status:"
    FOLLOWING_CACHE_PREFIX = "following_cache:"
    LOCK_TIMEOUT = 3600
    STATUS_TIMEOUT = 7200

    def __init__(self, db: AsyncSession, redis: Redis | None = None):
        self.db = db
        self.redis = redis or self._get_redis_client()
        self._client: TwitterClient | None = None
        self._tweet_service: TweetService | None = None

    def _get_redis_client(self) -> Redis:
        return Redis.from_url(settings.REDIS_URL, decode_responses=True)

    @property
    def client(self) -> TwitterClient:
        if self._client is None:
            self._client = TwitterClient()
        return self._client

    @property
    def tweet_service(self) -> TweetService:
        if self._tweet_service is None:
            self._tweet_service = TweetService(self.db)
        return self._tweet_service

    async def _ensure_client_started(self) -> None:
        if self._client is None:
            self._client = TwitterClient()
        if self._client._client is None:
            await self._client.start()

    def _get_lock_key(self, account_id: UUID | str, sync_type: str) -> str:
        return f"{self.SYNC_LOCK_PREFIX}{sync_type}:{account_id}"

    def _get_status_key(self, account_id: UUID | str, sync_type: str) -> str:
        return f"{self.SYNC_STATUS_PREFIX}{sync_type}:{account_id}"

    def _get_following_cache_key(self, account_id: UUID | str) -> str:
        return f"{self.FOLLOWING_CACHE_PREFIX}{account_id}"

    async def acquire_sync_lock(self, account_id: UUID | str, sync_type: str) -> bool:
        lock_key = self._get_lock_key(account_id, sync_type)
        return self.redis.set(lock_key, "1", nx=True, ex=self.LOCK_TIMEOUT)

    async def release_sync_lock(self, account_id: UUID | str, sync_type: str) -> None:
        lock_key = self._get_lock_key(account_id, sync_type)
        self.redis.delete(lock_key)

    async def update_sync_status(
        self,
        account_id: UUID | str,
        sync_type: str,
        status: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        status_key = self._get_status_key(account_id, sync_type)
        status_data = {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "details": details or {},
        }
        self.redis.set(status_key, json.dumps(status_data), ex=self.STATUS_TIMEOUT)

    async def get_sync_status(
        self, account_id: UUID | str, sync_type: str
    ) -> dict[str, Any] | None:
        status_key = self._get_status_key(account_id, sync_type)
        status_data = self.redis.get(status_key)
        if status_data:
            return json.loads(status_data)
        return None

    async def cancel_sync(self, account_id: UUID | str, sync_type: str) -> bool:
        status_key = self._get_status_key(account_id, sync_type)
        current_status = await self.get_sync_status(account_id, sync_type)
        if current_status and current_status.get("status") == "running":
            await self.update_sync_status(account_id, sync_type, "cancelled")
            return True
        return False

    async def is_sync_cancelled(self, account_id: UUID | str, sync_type: str) -> bool:
        status = await self.get_sync_status(account_id, sync_type)
        return status is not None and status.get("status") == "cancelled"

    async def _get_active_account(
        self, account_id: UUID | str
    ) -> TwitterAccount | None:
        result = await self.db.execute(
            select(TwitterAccount).where(
                TwitterAccount.id == account_id
                if isinstance(account_id, UUID)
                else TwitterAccount.id == UUID(account_id),
                TwitterAccount.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def _get_all_active_accounts(self) -> list[TwitterAccount]:
        result = await self.db.execute(
            select(TwitterAccount).where(TwitterAccount.is_active == True)
        )
        return list(result.scalars().all())

    async def sync_account_likes(
        self,
        account_id: UUID | str,
        max_results: int = 100,
        max_pages: int = 10,
    ) -> dict[str, Any]:
        sync_type = "likes"
        account_uuid = UUID(account_id) if isinstance(account_id, str) else account_id

        if not await self.acquire_sync_lock(account_uuid, sync_type):
            logger.warning(f"点赞同步任务已在运行: {account_id}")
            return {
                "success": False,
                "error": "同步任务已在运行",
                "account_id": str(account_id),
            }

        try:
            await self.update_sync_status(account_uuid, sync_type, "running")

            account = await self._get_active_account(account_uuid)
            if not account:
                await self.update_sync_status(
                    account_uuid, sync_type, "failed", {"error": "账号不存在或已禁用"}
                )
                return {
                    "success": False,
                    "error": "账号不存在或已禁用",
                    "account_id": str(account_id),
                }

            since_tweet_id = await self.tweet_service.get_latest_tweet_id(
                account_uuid, task_type="likes"
            )

            result = await self.tweet_service.fetch_and_store_likes(
                twitter_account_id=account_uuid,
                max_results=max_results,
                max_pages=max_pages,
                since_tweet_id=since_tweet_id,
            )

            account.last_sync_at = datetime.now(timezone.utc)
            await self.db.flush()

            await self.update_sync_status(account_uuid, sync_type, "completed", result)

            logger.info(
                f"点赞同步完成: account={account_id}, tweets={result['tweets_count']}, media={result['media_count']}"
            )
            return {"success": True, "account_id": str(account_id), **result}

        except Exception as e:
            logger.exception(f"点赞同步失败: {account_id}")
            await self.update_sync_status(
                account_uuid, sync_type, "failed", {"error": str(e)}
            )
            return {"success": False, "error": str(e), "account_id": str(account_id)}

        finally:
            await self.release_sync_lock(account_uuid, sync_type)

    async def sync_account_bookmarks(
        self,
        account_id: UUID | str,
        max_results: int = 100,
        max_pages: int = 10,
    ) -> dict[str, Any]:
        sync_type = "bookmarks"
        account_uuid = UUID(account_id) if isinstance(account_id, str) else account_id

        if not await self.acquire_sync_lock(account_uuid, sync_type):
            logger.warning(f"收藏同步任务已在运行: {account_id}")
            return {
                "success": False,
                "error": "同步任务已在运行",
                "account_id": str(account_id),
            }

        try:
            await self.update_sync_status(account_uuid, sync_type, "running")

            account = await self._get_active_account(account_uuid)
            if not account:
                await self.update_sync_status(
                    account_uuid, sync_type, "failed", {"error": "账号不存在或已禁用"}
                )
                return {
                    "success": False,
                    "error": "账号不存在或已禁用",
                    "account_id": str(account_id),
                }

            since_tweet_id = await self.tweet_service.get_latest_tweet_id(
                account_uuid, task_type="bookmarks"
            )

            result = await self.tweet_service.fetch_and_store_bookmarks(
                twitter_account_id=account_uuid,
                max_results=max_results,
                max_pages=max_pages,
                since_tweet_id=since_tweet_id,
            )

            account.last_sync_at = datetime.now(timezone.utc)
            await self.db.flush()

            await self.update_sync_status(account_uuid, sync_type, "completed", result)

            logger.info(
                f"收藏同步完成: account={account_id}, tweets={result['tweets_count']}, media={result['media_count']}"
            )
            return {"success": True, "account_id": str(account_id), **result}

        except Exception as e:
            logger.exception(f"收藏同步失败: {account_id}")
            await self.update_sync_status(
                account_uuid, sync_type, "failed", {"error": str(e)}
            )
            return {"success": False, "error": str(e), "account_id": str(account_id)}

        finally:
            await self.release_sync_lock(account_uuid, sync_type)

    async def sync_account_following_timeline(
        self,
        account_id: UUID | str,
        max_results: int = 100,
        max_pages: int = 5,
    ) -> dict[str, Any]:
        sync_type = "following_timeline"
        account_uuid = UUID(account_id) if isinstance(account_id, str) else account_id

        if not await self.acquire_sync_lock(account_uuid, sync_type):
            logger.warning(f"关注时间线同步任务已在运行: {account_id}")
            return {
                "success": False,
                "error": "同步任务已在运行",
                "account_id": str(account_id),
            }

        try:
            await self.update_sync_status(account_uuid, sync_type, "running")

            account = await self._get_active_account(account_uuid)
            if not account:
                await self.update_sync_status(
                    account_uuid, sync_type, "failed", {"error": "账号不存在或已禁用"}
                )
                return {
                    "success": False,
                    "error": "账号不存在或已禁用",
                    "account_id": str(account_id),
                }

            await self._ensure_client_started()
            access_token = decrypt_token(account.access_token)

            following_users = await self._get_following_users(
                access_token, account.twitter_user_id
            )

            if await self.is_sync_cancelled(account_uuid, sync_type):
                logger.info(f"关注时间线同步已取消: {account_id}")
                return {
                    "success": False,
                    "error": "同步已取消",
                    "account_id": str(account_id),
                }

            total_result = {
                "account_id": str(account_id),
                "users_synced": 0,
                "total_tweets": 0,
                "total_media": 0,
                "errors": [],
            }

            for user in following_users[:50]:
                if await self.is_sync_cancelled(account_uuid, sync_type):
                    logger.info(f"关注时间线同步已取消: {account_id}")
                    break

                user_id = user.get("id")
                username = user.get("username", "unknown")

                try:
                    result = await self.tweet_service.fetch_user_tweets(
                        twitter_account_id=account_uuid,
                        target_user_id=user_id,
                        max_results=max_results,
                        max_pages=max_pages,
                        exclude_replies=True,
                    )

                    total_result["users_synced"] += 1
                    total_result["total_tweets"] += result.get("tweets_count", 0)
                    total_result["total_media"] += result.get("media_count", 0)

                except Exception as e:
                    error_msg = f"同步用户 {username} 失败: {str(e)}"
                    total_result["errors"].append(error_msg)
                    logger.warning(error_msg)

            account.last_sync_at = datetime.now(timezone.utc)
            await self.db.flush()

            await self.update_sync_status(
                account_uuid, sync_type, "completed", total_result
            )

            logger.info(
                f"关注时间线同步完成: account={account_id}, users={total_result['users_synced']}, tweets={total_result['total_tweets']}"
            )
            return {"success": True, **total_result}

        except Exception as e:
            logger.exception(f"关注时间线同步失败: {account_id}")
            await self.update_sync_status(
                account_uuid, sync_type, "failed", {"error": str(e)}
            )
            return {"success": False, "error": str(e), "account_id": str(account_id)}

        finally:
            await self.release_sync_lock(account_uuid, sync_type)

    async def _get_following_users(
        self, access_token: str, twitter_user_id: str
    ) -> list[dict[str, Any]]:
        all_users = []
        pagination_token = None
        max_pages = 10

        for _ in range(max_pages):
            response = await self.client.get_following(
                access_token,
                twitter_user_id,
                max_results=100,
                pagination_token=pagination_token,
            )

            users = response.get("data", [])
            all_users.extend(users)

            meta = response.get("meta", {})
            next_token = meta.get("next_token")

            if not next_token:
                break

            pagination_token = next_token

        return all_users

    async def detect_new_following(
        self, account_id: UUID | str
    ) -> dict[str, Any]:
        sync_type = "following_check"
        account_uuid = UUID(account_id) if isinstance(account_id, str) else account_id

        if not await self.acquire_sync_lock(account_uuid, sync_type):
            logger.warning(f"关注检测任务已在运行: {account_id}")
            return {
                "success": False,
                "error": "检测任务已在运行",
                "account_id": str(account_id),
            }

        try:
            await self.update_sync_status(account_uuid, sync_type, "running")

            account = await self._get_active_account(account_uuid)
            if not account:
                await self.update_sync_status(
                    account_uuid, sync_type, "failed", {"error": "账号不存在或已禁用"}
                )
                return {
                    "success": False,
                    "error": "账号不存在或已禁用",
                    "account_id": str(account_id),
                }

            await self._ensure_client_started()
            access_token = decrypt_token(account.access_token)

            current_following = await self._get_following_users(
                access_token, account.twitter_user_id
            )

            current_ids = {u.get("id") for u in current_following}

            cache_key = self._get_following_cache_key(account_uuid)
            cached_data = self.redis.get(cache_key)

            previous_ids = set()
            if cached_data:
                previous_ids = set(json.loads(cached_data))

            new_following_ids = current_ids - previous_ids
            unfollowed_ids = previous_ids - current_ids

            self.redis.set(
                cache_key, json.dumps(list(current_ids)), ex=86400 * 7
            )

            new_users = []
            for user in current_following:
                if user.get("id") in new_following_ids:
                    new_users.append(user)
                    await self._store_twitter_user(user, is_following=True)

            if unfollowed_ids:
                await self._mark_users_unfollowed(unfollowed_ids)

            result = {
                "account_id": str(account_id),
                "total_following": len(current_ids),
                "new_following_count": len(new_following_ids),
                "unfollowed_count": len(unfollowed_ids),
                "new_users": new_users[:10],
            }

            await self.update_sync_status(account_uuid, sync_type, "completed", result)

            logger.info(
                f"关注检测完成: account={account_id}, new={len(new_following_ids)}, unfollowed={len(unfollowed_ids)}"
            )
            return {"success": True, **result}

        except Exception as e:
            logger.exception(f"关注检测失败: {account_id}")
            await self.update_sync_status(
                account_uuid, sync_type, "failed", {"error": str(e)}
            )
            return {"success": False, "error": str(e), "account_id": str(account_id)}

        finally:
            await self.release_sync_lock(account_uuid, sync_type)

    async def _store_twitter_user(
        self, user_data: dict[str, Any], is_following: bool = True
    ) -> TwitterUser | None:
        twitter_id = user_data.get("id")
        if not twitter_id:
            return None

        result = await self.db.execute(
            select(TwitterUser).where(TwitterUser.twitter_id == twitter_id)
        )
        existing_user = result.scalar_one_or_none()

        public_metrics = user_data.get("public_metrics", {})

        if existing_user:
            existing_user.username = user_data.get("username", existing_user.username)
            existing_user.name = user_data.get("name", existing_user.name)
            existing_user.profile_image_url = user_data.get(
                "profile_image_url", existing_user.profile_image_url
            )
            existing_user.description = user_data.get(
                "description", existing_user.description
            )
            existing_user.followers_count = public_metrics.get(
                "followers_count", existing_user.followers_count
            )
            existing_user.friends_count = public_metrics.get(
                "following_count", existing_user.friends_count
            )
            existing_user.statuses_count = public_metrics.get(
                "tweet_count", existing_user.statuses_count
            )
            existing_user.is_following = is_following
            await self.db.flush()
            await self.db.refresh(existing_user)
            return existing_user

        twitter_user = TwitterUser(
            twitter_id=twitter_id,
            username=user_data.get("username", ""),
            name=user_data.get("name"),
            profile_image_url=user_data.get("profile_image_url"),
            description=user_data.get("description"),
            followers_count=public_metrics.get("followers_count", 0),
            friends_count=public_metrics.get("following_count", 0),
            statuses_count=public_metrics.get("tweet_count", 0),
            is_following=is_following,
        )
        self.db.add(twitter_user)
        await self.db.flush()
        await self.db.refresh(twitter_user)
        return twitter_user

    async def _mark_users_unfollowed(self, user_ids: set[str]) -> None:
        if not user_ids:
            return

        await self.db.execute(
            update(TwitterUser)
            .where(TwitterUser.twitter_id.in_(user_ids))
            .values(is_following=False)
        )
        await self.db.flush()

    async def full_sync_user(
        self,
        user_id: str,
        account_id: UUID | str,
        max_results: int = 100,
        max_pages: int = 20,
    ) -> dict[str, Any]:
        sync_type = f"full_sync_user:{user_id}"
        account_uuid = UUID(account_id) if isinstance(account_id, str) else account_id

        if not await self.acquire_sync_lock(account_uuid, sync_type):
            logger.warning(f"用户全量同步任务已在运行: user={user_id}")
            return {
                "success": False,
                "error": "同步任务已在运行",
                "user_id": user_id,
            }

        try:
            await self.update_sync_status(account_uuid, sync_type, "running")

            account = await self._get_active_account(account_uuid)
            if not account:
                await self.update_sync_status(
                    account_uuid, sync_type, "failed", {"error": "账号不存在或已禁用"}
                )
                return {
                    "success": False,
                    "error": "账号不存在或已禁用",
                    "user_id": user_id,
                }

            result = await self.tweet_service.fetch_user_tweets(
                twitter_account_id=account_uuid,
                target_user_id=user_id,
                max_results=max_results,
                max_pages=max_pages,
                exclude_replies=True,
            )

            await self.update_sync_status(account_uuid, sync_type, "completed", result)

            logger.info(
                f"用户全量同步完成: user={user_id}, tweets={result['tweets_count']}, media={result['media_count']}"
            )
            return {"success": True, "user_id": user_id, **result}

        except Exception as e:
            logger.exception(f"用户全量同步失败: user={user_id}")
            await self.update_sync_status(
                account_uuid, sync_type, "failed", {"error": str(e)}
            )
            return {"success": False, "error": str(e), "user_id": user_id}

        finally:
            await self.release_sync_lock(account_uuid, sync_type)

    async def sync_all_accounts_likes(self) -> dict[str, Any]:
        accounts = await self._get_all_active_accounts()

        results = {
            "total_accounts": len(accounts),
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "details": [],
        }

        for account in accounts:
            result = await self.sync_account_likes(account.id)
            if result.get("success"):
                results["successful"] += 1
            elif result.get("error") == "同步任务已在运行":
                results["skipped"] += 1
            else:
                results["failed"] += 1
            results["details"].append(
                {
                    "account_id": str(account.id),
                    "username": account.twitter_username,
                    "success": result.get("success", False),
                    "error": result.get("error"),
                }
            )

        logger.info(
            f"所有账号点赞同步完成: total={results['total_accounts']}, success={results['successful']}, failed={results['failed']}"
        )
        return results

    async def sync_all_accounts_bookmarks(self) -> dict[str, Any]:
        accounts = await self._get_all_active_accounts()

        results = {
            "total_accounts": len(accounts),
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "details": [],
        }

        for account in accounts:
            result = await self.sync_account_bookmarks(account.id)
            if result.get("success"):
                results["successful"] += 1
            elif result.get("error") == "同步任务已在运行":
                results["skipped"] += 1
            else:
                results["failed"] += 1
            results["details"].append(
                {
                    "account_id": str(account.id),
                    "username": account.twitter_username,
                    "success": result.get("success", False),
                    "error": result.get("error"),
                }
            )

        logger.info(
            f"所有账号收藏同步完成: total={results['total_accounts']}, success={results['successful']}, failed={results['failed']}"
        )
        return results

    async def sync_all_accounts_following_timeline(self) -> dict[str, Any]:
        accounts = await self._get_all_active_accounts()

        results = {
            "total_accounts": len(accounts),
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "details": [],
        }

        for account in accounts:
            result = await self.sync_account_following_timeline(account.id)
            if result.get("success"):
                results["successful"] += 1
            elif result.get("error") == "同步任务已在运行":
                results["skipped"] += 1
            else:
                results["failed"] += 1
            results["details"].append(
                {
                    "account_id": str(account.id),
                    "username": account.twitter_username,
                    "success": result.get("success", False),
                    "error": result.get("error"),
                }
            )

        logger.info(
            f"所有账号关注时间线同步完成: total={results['total_accounts']}, success={results['successful']}, failed={results['failed']}"
        )
        return results

    async def detect_all_accounts_new_following(self) -> dict[str, Any]:
        accounts = await self._get_all_active_accounts()

        results = {
            "total_accounts": len(accounts),
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "total_new_following": 0,
            "details": [],
        }

        for account in accounts:
            result = await self.detect_new_following(account.id)
            if result.get("success"):
                results["successful"] += 1
                results["total_new_following"] += result.get(
                    "new_following_count", 0
                )
            elif result.get("error") == "检测任务已在运行":
                results["skipped"] += 1
            else:
                results["failed"] += 1
            results["details"].append(
                {
                    "account_id": str(account.id),
                    "username": account.twitter_username,
                    "success": result.get("success", False),
                    "new_following_count": result.get("new_following_count", 0),
                    "error": result.get("error"),
                }
            )

        logger.info(
            f"所有账号关注检测完成: total={results['total_accounts']}, new_following={results['total_new_following']}"
        )
        return results
