import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundException, TwitterAPIException
from app.models.media_file import MediaFile
from app.models.tweet import Tweet
from app.models.twitter_account import TwitterAccount
from app.models.twitter_user import TwitterUser
from app.services.twitter_client import TwitterClient

logger = logging.getLogger(__name__)


class TweetService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._client: TwitterClient | None = None

    @property
    def client(self) -> TwitterClient:
        if self._client is None:
            self._client = TwitterClient()
        return self._client

    async def _ensure_client_started(self) -> None:
        if self._client is None:
            self._client = TwitterClient()
        if self._client._client is None:
            await self._client.start()

    async def _get_account_with_valid_token(
        self,
        twitter_account_id: UUID | str,
    ) -> TwitterAccount:
        result = await self.db.execute(
            select(TwitterAccount).where(
                TwitterAccount.id == twitter_account_id
                if isinstance(twitter_account_id, UUID)
                else TwitterAccount.id == UUID(twitter_account_id)
            )
        )
        account = result.scalar_one_or_none()

        if not account:
            raise NotFoundException(message="Twitter 账号不存在")

        if not account.is_active:
            raise TwitterAPIException(message="Twitter 账号已失效")

        return account

    async def store_twitter_user(self, user_data: dict[str, Any]) -> TwitterUser:
        if not user_data:
            raise ValueError("用户数据不能为空")

        twitter_id = user_data.get("id")
        if not twitter_id:
            raise ValueError("用户ID不能为空")

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
        )
        self.db.add(twitter_user)
        await self.db.flush()
        await self.db.refresh(twitter_user)
        return twitter_user

    async def store_tweet(
        self,
        tweet_data: dict[str, Any],
        twitter_account_id: UUID | str,
        includes: dict[str, Any] | None = None,
        is_liked: bool = False,
        is_bookmarked: bool = False,
    ) -> Tweet | None:
        if not tweet_data:
            return None

        twitter_id = tweet_data.get("id")
        if not twitter_id:
            return None

        result = await self.db.execute(
            select(Tweet).where(Tweet.twitter_id == twitter_id)
        )
        existing_tweet = result.scalar_one_or_none()

        author_id = tweet_data.get("author_id")
        twitter_user = None

        if author_id and includes:
            users = includes.get("users", [])
            author_data = next((u for u in users if u.get("id") == author_id), None)
            if author_data:
                twitter_user = await self.store_twitter_user(author_data)

        if not twitter_user:
            result = await self.db.execute(
                select(TwitterUser).where(TwitterUser.twitter_id == author_id)
            )
            twitter_user = result.scalar_one_or_none()

        if not twitter_user:
            logger.warning(f"无法找到推文作者: {author_id}")
            return None

        public_metrics = tweet_data.get("public_metrics", {})
        referenced_tweets = tweet_data.get("referenced_tweets", [])
        is_retweet = any(rt.get("type") == "retweeted" for rt in referenced_tweets)
        is_quote = any(rt.get("type") == "quoted" for rt in referenced_tweets)

        created_at_str = tweet_data.get("created_at")
        published_at = None
        if created_at_str:
            try:
                published_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            except ValueError:
                pass

        if existing_tweet:
            existing_tweet.text = tweet_data.get("text", existing_tweet.text)
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
            if is_liked:
                existing_tweet.is_liked_by_me = True
            if is_bookmarked:
                existing_tweet.is_bookmarked = True
            await self.db.flush()
            await self.db.refresh(existing_tweet)
            tweet = existing_tweet
        else:
            tweet = Tweet(
                twitter_id=twitter_id,
                twitter_user_id=twitter_user.id,
                twitter_account_id=twitter_account_id
                if isinstance(twitter_account_id, UUID)
                else UUID(twitter_account_id),
                text=tweet_data.get("text"),
                lang=tweet_data.get("lang"),
                retweet_count=public_metrics.get("retweet_count", 0),
                like_count=public_metrics.get("like_count", 0),
                reply_count=public_metrics.get("reply_count", 0),
                quote_count=public_metrics.get("quote_count", 0),
                is_retweet=is_retweet,
                is_quote=is_quote,
                is_liked_by_me=is_liked,
                is_bookmarked=is_bookmarked,
                published_at=published_at,
            )
            self.db.add(tweet)
            await self.db.flush()
            await self.db.refresh(tweet)

        if includes:
            media_list = self._extract_media_from_includes(
                tweet_data, includes
            )
            await self._store_media_files(tweet.id, media_list)

        return tweet

    def _extract_media_from_includes(
        self,
        tweet_data: dict[str, Any],
        includes: dict[str, Any],
    ) -> list[dict[str, Any]]:
        attachments = tweet_data.get("attachments", {})
        media_keys = attachments.get("media_keys", [])

        if not media_keys:
            return []

        media_list = includes.get("media", [])
        media_map = {m.get("media_key"): m for m in media_list if m.get("media_key")}

        result = []
        for media_key in media_keys:
            media = media_map.get(media_key)
            if not media:
                continue

            media_type = media.get("type", "")
            media_info = {
                "media_key": media_key,
                "media_type": media_type,
                "url": None,
                "width": media.get("width"),
                "height": media.get("height"),
                "duration_ms": media.get("duration_ms"),
            }

            if media_type == "photo":
                media_info["url"] = media.get("url")
            elif media_type in ("video", "animated_gif"):
                media_info["preview_url"] = media.get("preview_image_url")
                variants = media.get("variants", [])
                mp4_variants = [
                    v for v in variants if v.get("content_type") == "video/mp4"
                ]
                if mp4_variants:
                    mp4_variants.sort(key=lambda x: x.get("bit_rate", 0), reverse=True)
                    media_info["url"] = mp4_variants[0].get("url")
                elif variants:
                    media_info["url"] = variants[0].get("url")

            if media_info["url"]:
                result.append(media_info)

        return result

    async def _store_media_files(
        self,
        tweet_id: UUID,
        media_list: list[dict[str, Any]],
    ) -> list[MediaFile]:
        stored_media = []

        for media_info in media_list:
            result = await self.db.execute(
                select(MediaFile).where(
                    MediaFile.tweet_id == tweet_id,
                    MediaFile.url == media_info["url"],
                )
            )
            existing_media = result.scalar_one_or_none()

            if existing_media:
                stored_media.append(existing_media)
                continue

            media_file = MediaFile(
                tweet_id=tweet_id,
                media_type=media_info["media_type"],
                url=media_info["url"],
                width=media_info.get("width"),
                height=media_info.get("height"),
                duration_ms=media_info.get("duration_ms"),
                download_status="pending",
            )
            self.db.add(media_file)
            stored_media.append(media_file)

        await self.db.flush()
        return stored_media

    async def fetch_and_store_likes(
        self,
        twitter_account_id: UUID | str,
        max_results: int = 100,
        max_pages: int = 10,
        since_tweet_id: str | None = None,
    ) -> dict[str, Any]:
        account = await self._get_account_with_valid_token(twitter_account_id)
        await self._ensure_client_started()

        from app.core.security import decrypt_token
        access_token = decrypt_token(account.access_token)

        result = {
            "account_id": str(account.id),
            "tweets_count": 0,
            "media_count": 0,
            "pages_fetched": 0,
            "errors": [],
        }

        pagination_token = None
        pages_fetched = 0

        while pages_fetched < max_pages:
            try:
                response = await self.client.get_likes(
                    access_token,
                    account.twitter_user_id,
                    max_results=max_results,
                    pagination_token=pagination_token,
                )

                tweets_data = response.get("data", [])
                includes = response.get("includes", {})

                if not tweets_data:
                    break

                for tweet_data in tweets_data:
                    if since_tweet_id and tweet_data.get("id") == since_tweet_id:
                        break

                    tweet = await self.store_tweet(
                        tweet_data,
                        account.id,
                        includes=includes,
                        is_liked=True,
                    )
                    if tweet:
                        result["tweets_count"] += 1
                        if tweet.media_files:
                            result["media_count"] += len(tweet.media_files)

                pages_fetched += 1
                result["pages_fetched"] = pages_fetched

                meta = response.get("meta", {})
                next_token = meta.get("next_token")

                if not next_token:
                    break

                pagination_token = next_token

            except Exception as e:
                result["errors"].append(str(e))
                logger.error(f"获取点赞列表失败: {e}")
                break

        return result

    async def fetch_and_store_bookmarks(
        self,
        twitter_account_id: UUID | str,
        max_results: int = 100,
        max_pages: int = 10,
        since_tweet_id: str | None = None,
    ) -> dict[str, Any]:
        account = await self._get_account_with_valid_token(twitter_account_id)
        await self._ensure_client_started()

        from app.core.security import decrypt_token
        access_token = decrypt_token(account.access_token)

        result = {
            "account_id": str(account.id),
            "tweets_count": 0,
            "media_count": 0,
            "pages_fetched": 0,
            "errors": [],
        }

        pagination_token = None
        pages_fetched = 0

        while pages_fetched < max_pages:
            try:
                response = await self.client.get_bookmarks(
                    access_token,
                    account.twitter_user_id,
                    max_results=max_results,
                    pagination_token=pagination_token,
                )

                tweets_data = response.get("data", [])
                includes = response.get("includes", {})

                if not tweets_data:
                    break

                for tweet_data in tweets_data:
                    if since_tweet_id and tweet_data.get("id") == since_tweet_id:
                        break

                    tweet = await self.store_tweet(
                        tweet_data,
                        account.id,
                        includes=includes,
                        is_bookmarked=True,
                    )
                    if tweet:
                        result["tweets_count"] += 1
                        if tweet.media_files:
                            result["media_count"] += len(tweet.media_files)

                pages_fetched += 1
                result["pages_fetched"] = pages_fetched

                meta = response.get("meta", {})
                next_token = meta.get("next_token")

                if not next_token:
                    break

                pagination_token = next_token

            except Exception as e:
                result["errors"].append(str(e))
                logger.error(f"获取收藏列表失败: {e}")
                break

        return result

    async def fetch_and_store_timeline(
        self,
        twitter_account_id: UUID | str,
        max_results: int = 100,
        max_pages: int = 10,
        since_tweet_id: str | None = None,
    ) -> dict[str, Any]:
        account = await self._get_account_with_valid_token(twitter_account_id)
        await self._ensure_client_started()

        from app.core.security import decrypt_token
        access_token = decrypt_token(account.access_token)

        result = {
            "account_id": str(account.id),
            "tweets_count": 0,
            "media_count": 0,
            "pages_fetched": 0,
            "errors": [],
        }

        pagination_token = None
        pages_fetched = 0

        while pages_fetched < max_pages:
            try:
                response = await self.client.get_user_timeline(
                    access_token,
                    account.twitter_user_id,
                    max_results=max_results,
                    pagination_token=pagination_token,
                )

                tweets_data = response.get("data", [])
                includes = response.get("includes", {})

                if not tweets_data:
                    break

                for tweet_data in tweets_data:
                    if since_tweet_id and tweet_data.get("id") == since_tweet_id:
                        break

                    tweet = await self.store_tweet(
                        tweet_data,
                        account.id,
                        includes=includes,
                    )
                    if tweet:
                        result["tweets_count"] += 1
                        if tweet.media_files:
                            result["media_count"] += len(tweet.media_files)

                pages_fetched += 1
                result["pages_fetched"] = pages_fetched

                meta = response.get("meta", {})
                next_token = meta.get("next_token")

                if not next_token:
                    break

                pagination_token = next_token

            except Exception as e:
                result["errors"].append(str(e))
                logger.error(f"获取时间线失败: {e}")
                break

        return result

    async def fetch_user_tweets(
        self,
        twitter_account_id: UUID | str,
        target_user_id: str,
        max_results: int = 100,
        max_pages: int = 10,
        exclude_replies: bool = True,
        since_tweet_id: str | None = None,
    ) -> dict[str, Any]:
        account = await self._get_account_with_valid_token(twitter_account_id)
        await self._ensure_client_started()

        from app.core.security import decrypt_token
        access_token = decrypt_token(account.access_token)

        result = {
            "account_id": str(account.id),
            "target_user_id": target_user_id,
            "tweets_count": 0,
            "media_count": 0,
            "pages_fetched": 0,
            "errors": [],
        }

        pagination_token = None
        pages_fetched = 0

        while pages_fetched < max_pages:
            try:
                response = await self.client.get_user_tweets(
                    access_token,
                    target_user_id,
                    max_results=max_results,
                    exclude_replies=exclude_replies,
                    pagination_token=pagination_token,
                )

                tweets_data = response.get("data", [])
                includes = response.get("includes", {})

                if not tweets_data:
                    break

                for tweet_data in tweets_data:
                    if since_tweet_id and tweet_data.get("id") == since_tweet_id:
                        break

                    tweet = await self.store_tweet(
                        tweet_data,
                        account.id,
                        includes=includes,
                    )
                    if tweet:
                        result["tweets_count"] += 1
                        if tweet.media_files:
                            result["media_count"] += len(tweet.media_files)

                pages_fetched += 1
                result["pages_fetched"] = pages_fetched

                meta = response.get("meta", {})
                next_token = meta.get("next_token")

                if not next_token:
                    break

                pagination_token = next_token

            except Exception as e:
                result["errors"].append(str(e))
                logger.error(f"获取用户推文失败: {e}")
                break

        return result

    async def get_media_tweets(
        self,
        twitter_account_id: UUID | str,
        task_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Tweet]:
        query = (
            select(Tweet)
            .options(selectinload(Tweet.media_files), selectinload(Tweet.twitter_user))
            .where(
                Tweet.twitter_account_id == twitter_account_id
                if isinstance(twitter_account_id, UUID)
                else Tweet.twitter_account_id == UUID(twitter_account_id)
            )
            .where(Tweet.media_files.any())
            .order_by(Tweet.published_at.desc())
            .offset(offset)
            .limit(limit)
        )

        if task_type == "likes":
            query = query.where(Tweet.is_liked_by_me == True)
        elif task_type == "bookmarks":
            query = query.where(Tweet.is_bookmarked == True)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_tweet_by_twitter_id(self, twitter_id: str) -> Tweet | None:
        result = await self.db.execute(
            select(Tweet)
            .options(selectinload(Tweet.media_files), selectinload(Tweet.twitter_user))
            .where(Tweet.twitter_id == twitter_id)
        )
        return result.scalar_one_or_none()

    async def get_latest_tweet_id(
        self,
        twitter_account_id: UUID | str,
        task_type: str | None = None,
    ) -> str | None:
        query = (
            select(Tweet.twitter_id)
            .where(
                Tweet.twitter_account_id == twitter_account_id
                if isinstance(twitter_account_id, UUID)
                else Tweet.twitter_account_id == UUID(twitter_account_id)
            )
            .order_by(Tweet.published_at.desc())
            .limit(1)
        )

        if task_type == "likes":
            query = query.where(Tweet.is_liked_by_me == True)
        elif task_type == "bookmarks":
            query = query.where(Tweet.is_bookmarked == True)

        result = await self.db.execute(query)
        row = result.scalar_one_or_none()
        return row

    async def update_tweet_download_status(
        self,
        tweet_id: UUID,
        media_type: str | None = None,
    ) -> None:
        await self.db.execute(
            update(MediaFile)
            .where(MediaFile.tweet_id == tweet_id)
            .values(download_status="completed")
        )
        await self.db.flush()
