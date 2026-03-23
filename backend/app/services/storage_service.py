import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.download_task import DownloadTask
from app.models.media_file import MediaFile
from app.models.tweet import Tweet
from app.models.twitter_user import TwitterUser

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def store_tweet(
        self,
        tweet_data: dict[str, Any],
        account_id: UUID | str,
    ) -> Tweet:
        if not tweet_data:
            raise ValueError("推文数据不能为空")

        twitter_id = tweet_data.get("id") or tweet_data.get("twitter_id")
        if not twitter_id:
            raise ValueError("推文ID不能为空")

        result = await self.db.execute(
            select(Tweet).where(Tweet.twitter_id == str(twitter_id))
        )
        existing_tweet = result.scalar_one_or_none()

        author_id = tweet_data.get("author_id") or tweet_data.get("twitter_user_id")
        twitter_user_id = None

        if author_id:
            user_result = await self.db.execute(
                select(TwitterUser).where(TwitterUser.twitter_id == str(author_id))
            )
            twitter_user = user_result.scalar_one_or_none()
            if twitter_user:
                twitter_user_id = twitter_user.id

        if not twitter_user_id:
            raise ValueError("无法找到推文作者")

        public_metrics = tweet_data.get("public_metrics", {})
        referenced_tweets = tweet_data.get("referenced_tweets", [])
        is_retweet = any(rt.get("type") == "retweeted" for rt in referenced_tweets)
        is_quote = any(rt.get("type") == "quoted" for rt in referenced_tweets)

        created_at_str = tweet_data.get("created_at") or tweet_data.get("published_at")
        published_at = None
        if created_at_str:
            try:
                if isinstance(created_at_str, str):
                    published_at = datetime.fromisoformat(
                        created_at_str.replace("Z", "+00:00")
                    )
                elif isinstance(created_at_str, datetime):
                    published_at = created_at_str
            except ValueError:
                pass

        account_uuid = (
            account_id if isinstance(account_id, UUID) else UUID(account_id)
        )

        if existing_tweet:
            existing_tweet.text = tweet_data.get("text", existing_tweet.text)
            existing_tweet.lang = tweet_data.get("lang", existing_tweet.lang)
            existing_tweet.retweet_count = public_metrics.get(
                "retweet_count", existing_tweet.retweet_count
            )
            existing_tweet.like_count = public_metrics.get(
                "like_count", existing_tweet.like_count
            )
            existing_tweet.reply_count = public_metrics.get(
                "reply_count", existing_tweet.reply_count
            )
            existing_tweet.quote_count = public_metrics.get(
                "quote_count", existing_tweet.quote_count
            )
            if tweet_data.get("is_liked_by_me"):
                existing_tweet.is_liked_by_me = True
            if tweet_data.get("is_bookmarked"):
                existing_tweet.is_bookmarked = True
            await self.db.flush()
            await self.db.refresh(existing_tweet)
            return existing_tweet

        tweet = Tweet(
            twitter_id=str(twitter_id),
            twitter_user_id=twitter_user_id,
            twitter_account_id=account_uuid,
            text=tweet_data.get("text"),
            lang=tweet_data.get("lang"),
            retweet_count=public_metrics.get("retweet_count", 0),
            like_count=public_metrics.get("like_count", 0),
            reply_count=public_metrics.get("reply_count", 0),
            quote_count=public_metrics.get("quote_count", 0),
            is_retweet=is_retweet,
            is_quote=is_quote,
            is_liked_by_me=tweet_data.get("is_liked_by_me", False),
            is_bookmarked=tweet_data.get("is_bookmarked", False),
            published_at=published_at,
        )
        self.db.add(tweet)
        await self.db.flush()
        await self.db.refresh(tweet)
        return tweet

    async def store_media(
        self,
        media_data: dict[str, Any],
        tweet_id: UUID,
    ) -> MediaFile:
        if not media_data:
            raise ValueError("媒体数据不能为空")

        url = media_data.get("url")
        if not url:
            raise ValueError("媒体URL不能为空")

        result = await self.db.execute(
            select(MediaFile).where(
                MediaFile.tweet_id == tweet_id,
                MediaFile.url == url,
            )
        )
        existing_media = result.scalar_one_or_none()

        if existing_media:
            return existing_media

        media = MediaFile(
            tweet_id=tweet_id,
            media_type=media_data.get("media_type", "unknown"),
            url=url,
            local_path=media_data.get("local_path"),
            file_hash=media_data.get("file_hash"),
            file_size=media_data.get("file_size"),
            width=media_data.get("width"),
            height=media_data.get("height"),
            duration_ms=media_data.get("duration_ms"),
            download_status=media_data.get("download_status", "pending"),
            error_message=media_data.get("error_message"),
        )
        self.db.add(media)
        await self.db.flush()
        await self.db.refresh(media)
        return media

    async def store_twitter_user(self, user_data: dict[str, Any]) -> TwitterUser:
        if not user_data:
            raise ValueError("用户数据不能为空")

        twitter_id = user_data.get("id") or user_data.get("twitter_id")
        if not twitter_id:
            raise ValueError("用户ID不能为空")

        result = await self.db.execute(
            select(TwitterUser).where(TwitterUser.twitter_id == str(twitter_id))
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
            await self.db.flush()
            await self.db.refresh(existing_user)
            return existing_user

        twitter_user = TwitterUser(
            twitter_id=str(twitter_id),
            username=user_data.get("username", ""),
            name=user_data.get("name"),
            profile_image_url=user_data.get("profile_image_url"),
            description=user_data.get("description"),
            followers_count=public_metrics.get("followers_count", 0),
            friends_count=public_metrics.get("following_count", 0),
            statuses_count=public_metrics.get("tweet_count", 0),
            is_following=user_data.get("is_following", False),
        )
        self.db.add(twitter_user)
        await self.db.flush()
        await self.db.refresh(twitter_user)
        return twitter_user

    async def store_download_task(self, task_data: dict[str, Any]) -> DownloadTask:
        if not task_data:
            raise ValueError("任务数据不能为空")

        user_id = task_data.get("user_id")
        twitter_account_id = task_data.get("twitter_account_id")
        task_type = task_data.get("task_type")

        if not user_id or not twitter_account_id or not task_type:
            raise ValueError("缺少必要的任务参数")

        task = DownloadTask(
            user_id=user_id if isinstance(user_id, UUID) else UUID(user_id),
            twitter_account_id=(
                twitter_account_id
                if isinstance(twitter_account_id, UUID)
                else UUID(twitter_account_id)
            ),
            task_type=task_type,
            target_user_id=task_data.get("target_user_id"),
            status=task_data.get("status", "pending"),
            total_count=task_data.get("total_count", 0),
            downloaded_count=task_data.get("downloaded_count", 0),
            skipped_count=task_data.get("skipped_count", 0),
            error_message=task_data.get("error_message"),
            started_at=task_data.get("started_at"),
            completed_at=task_data.get("completed_at"),
        )
        self.db.add(task)
        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def update_download_task(
        self,
        task_id: UUID,
        status: str,
        **kwargs,
    ) -> DownloadTask | None:
        task = await self.db.get(DownloadTask, task_id)

        if not task:
            return None

        task.status = status

        if "total_count" in kwargs:
            task.total_count = kwargs["total_count"]
        if "downloaded_count" in kwargs:
            task.downloaded_count = kwargs["downloaded_count"]
        if "skipped_count" in kwargs:
            task.skipped_count = kwargs["skipped_count"]
        if "error_message" in kwargs:
            task.error_message = kwargs["error_message"]
        if "started_at" in kwargs:
            task.started_at = kwargs["started_at"]
        if "completed_at" in kwargs:
            task.completed_at = kwargs["completed_at"]
        if "target_user_id" in kwargs:
            task.target_user_id = kwargs["target_user_id"]

        await self.db.flush()
        await self.db.refresh(task)
        return task

    async def get_tweet_by_id(self, tweet_id: UUID) -> Tweet | None:
        result = await self.db.execute(
            select(Tweet)
            .options(selectinload(Tweet.media_files), selectinload(Tweet.twitter_user))
            .where(Tweet.id == tweet_id)
        )
        return result.scalar_one_or_none()

    async def get_media_by_id(self, media_id: UUID) -> MediaFile | None:
        result = await self.db.execute(
            select(MediaFile)
            .options(selectinload(MediaFile.tweet))
            .where(MediaFile.id == media_id)
        )
        return result.scalar_one_or_none()

    async def get_twitter_user_by_id(self, user_id: UUID) -> TwitterUser | None:
        result = await self.db.execute(
            select(TwitterUser)
            .options(selectinload(TwitterUser.tweets))
            .where(TwitterUser.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_download_task_by_id(self, task_id: UUID) -> DownloadTask | None:
        result = await self.db.execute(
            select(DownloadTask)
            .options(
                selectinload(DownloadTask.user),
                selectinload(DownloadTask.twitter_account),
            )
            .where(DownloadTask.id == task_id)
        )
        return result.scalar_one_or_none()

    async def bulk_store_tweets(
        self,
        tweets_data: list[dict[str, Any]],
        account_id: UUID | str,
    ) -> list[Tweet]:
        if not tweets_data:
            return []

        stored_tweets = []
        account_uuid = (
            account_id if isinstance(account_id, UUID) else UUID(account_id)
        )

        for tweet_data in tweets_data:
            try:
                tweet = await self.store_tweet(tweet_data, account_uuid)
                stored_tweets.append(tweet)
            except Exception as e:
                logger.warning(f"批量存储推文失败: {e}")
                continue

        return stored_tweets

    async def bulk_store_media(
        self,
        media_list: list[dict[str, Any]],
        tweet_id: UUID,
    ) -> list[MediaFile]:
        if not media_list:
            return []

        stored_media = []

        for media_data in media_list:
            try:
                media = await self.store_media(media_data, tweet_id)
                stored_media.append(media)
            except Exception as e:
                logger.warning(f"批量存储媒体失败: {e}")
                continue

        return stored_media

    async def bulk_store_twitter_users(
        self,
        users_data: list[dict[str, Any]],
    ) -> list[TwitterUser]:
        if not users_data:
            return []

        stored_users = []

        for user_data in users_data:
            try:
                user = await self.store_twitter_user(user_data)
                stored_users.append(user)
            except Exception as e:
                logger.warning(f"批量存储用户失败: {e}")
                continue

        return stored_users

    async def get_or_create_twitter_user(
        self,
        user_data: dict[str, Any],
    ) -> TwitterUser:
        return await self.store_twitter_user(user_data)

    async def get_tweet_by_twitter_id(self, twitter_id: str) -> Tweet | None:
        result = await self.db.execute(
            select(Tweet)
            .options(selectinload(Tweet.media_files), selectinload(Tweet.twitter_user))
            .where(Tweet.twitter_id == twitter_id)
        )
        return result.scalar_one_or_none()

    async def get_twitter_user_by_twitter_id(
        self, twitter_id: str
    ) -> TwitterUser | None:
        result = await self.db.execute(
            select(TwitterUser).where(TwitterUser.twitter_id == twitter_id)
        )
        return result.scalar_one_or_none()

    async def delete_tweet(self, tweet_id: UUID) -> bool:
        tweet = await self.db.get(Tweet, tweet_id)
        if not tweet:
            return False
        await self.db.delete(tweet)
        await self.db.flush()
        return True

    async def delete_media(self, media_id: UUID) -> bool:
        media = await self.db.get(MediaFile, media_id)
        if not media:
            return False
        await self.db.delete(media)
        await self.db.flush()
        return True

    async def delete_twitter_user(self, user_id: UUID) -> bool:
        user = await self.db.get(TwitterUser, user_id)
        if not user:
            return False
        await self.db.delete(user)
        await self.db.flush()
        return True

    async def delete_download_task(self, task_id: UUID) -> bool:
        task = await self.db.get(DownloadTask, task_id)
        if not task:
            return False
        await self.db.delete(task)
        await self.db.flush()
        return True
