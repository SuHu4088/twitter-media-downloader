import uuid
from datetime import datetime
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media_file import MediaFile
from app.models.tweet import Tweet
from app.models.twitter_user import TwitterUser
from app.services.storage_service import StorageService


class TestStorageService:
    @pytest.fixture
    def storage_service(self, db_session: AsyncSession) -> StorageService:
        return StorageService(db_session)

    @pytest.mark.asyncio
    async def test_store_tweet(
        self,
        storage_service: StorageService,
        test_twitter_user: TwitterUser,
        test_twitter_account: Any,
        sample_tweet_data: dict[str, Any],
    ) -> None:
        sample_tweet_data["author_id"] = test_twitter_user.twitter_id

        result = await storage_service.store_tweet(
            tweet_data=sample_tweet_data,
            account_id=test_twitter_account.id,
        )

        assert result is not None
        assert result.twitter_id == sample_tweet_data["id"]
        assert result.text == sample_tweet_data["text"]
        assert result.lang == sample_tweet_data["lang"]

    @pytest.mark.asyncio
    async def test_store_tweet_empty_data(
        self,
        storage_service: StorageService,
        test_twitter_account: Any,
    ) -> None:
        with pytest.raises(ValueError, match="推文数据不能为空"):
            await storage_service.store_tweet(
                tweet_data={},
                account_id=test_twitter_account.id,
            )

    @pytest.mark.asyncio
    async def test_store_tweet_missing_id(
        self,
        storage_service: StorageService,
        test_twitter_account: Any,
    ) -> None:
        with pytest.raises(ValueError, match="推文ID不能为空"):
            await storage_service.store_tweet(
                tweet_data={"text": "test"},
                account_id=test_twitter_account.id,
            )

    @pytest.mark.asyncio
    async def test_store_tweet_update_existing(
        self,
        storage_service: StorageService,
        test_twitter_user: TwitterUser,
        test_twitter_account: Any,
        test_tweet: Tweet,
    ) -> None:
        updated_data = {
            "id": test_tweet.twitter_id,
            "text": "Updated tweet text",
            "author_id": test_twitter_user.twitter_id,
            "public_metrics": {
                "retweet_count": 100,
                "like_count": 200,
                "reply_count": 50,
                "quote_count": 25,
            },
            "is_liked_by_me": True,
            "is_bookmarked": True,
        }

        result = await storage_service.store_tweet(
            tweet_data=updated_data,
            account_id=test_twitter_account.id,
        )

        assert result.text == "Updated tweet text"
        assert result.retweet_count == 100
        assert result.like_count == 200
        assert result.is_liked_by_me is True
        assert result.is_bookmarked is True

    @pytest.mark.asyncio
    async def test_store_media(
        self,
        storage_service: StorageService,
        test_tweet: Tweet,
        sample_media_data: dict[str, Any],
    ) -> None:
        result = await storage_service.store_media(
            media_data=sample_media_data,
            tweet_id=test_tweet.id,
        )

        assert result is not None
        assert result.media_type == sample_media_data["media_type"]
        assert result.url == sample_media_data["url"]
        assert result.tweet_id == test_tweet.id

    @pytest.mark.asyncio
    async def test_store_media_empty_data(
        self,
        storage_service: StorageService,
        test_tweet: Tweet,
    ) -> None:
        with pytest.raises(ValueError, match="媒体数据不能为空"):
            await storage_service.store_media(
                media_data={},
                tweet_id=test_tweet.id,
            )

    @pytest.mark.asyncio
    async def test_store_media_missing_url(
        self,
        storage_service: StorageService,
        test_tweet: Tweet,
    ) -> None:
        with pytest.raises(ValueError, match="媒体URL不能为空"):
            await storage_service.store_media(
                media_data={"media_type": "photo"},
                tweet_id=test_tweet.id,
            )

    @pytest.mark.asyncio
    async def test_store_media_existing(
        self,
        storage_service: StorageService,
        test_tweet: Tweet,
        test_media_file: MediaFile,
    ) -> None:
        result = await storage_service.store_media(
            media_data={
                "url": test_media_file.url,
                "media_type": "photo",
            },
            tweet_id=test_tweet.id,
        )

        assert result.id == test_media_file.id

    @pytest.mark.asyncio
    async def test_store_twitter_user(
        self,
        storage_service: StorageService,
        sample_user_data: dict[str, Any],
    ) -> None:
        result = await storage_service.store_twitter_user(sample_user_data)

        assert result is not None
        assert result.twitter_id == sample_user_data["id"]
        assert result.username == sample_user_data["username"]
        assert result.name == sample_user_data["name"]

    @pytest.mark.asyncio
    async def test_store_twitter_user_empty_data(
        self,
        storage_service: StorageService,
    ) -> None:
        with pytest.raises(ValueError, match="用户数据不能为空"):
            await storage_service.store_twitter_user({})

    @pytest.mark.asyncio
    async def test_store_twitter_user_missing_id(
        self,
        storage_service: StorageService,
    ) -> None:
        with pytest.raises(ValueError, match="用户ID不能为空"):
            await storage_service.store_twitter_user({"username": "test"})

    @pytest.mark.asyncio
    async def test_store_twitter_user_update_existing(
        self,
        storage_service: StorageService,
        test_twitter_user: TwitterUser,
    ) -> None:
        updated_data = {
            "id": test_twitter_user.twitter_id,
            "username": "updated_username",
            "name": "Updated Name",
            "profile_image_url": "https://example.com/new_avatar.jpg",
            "public_metrics": {
                "followers_count": 500,
                "following_count": 200,
                "tweet_count": 150,
            },
        }

        result = await storage_service.store_twitter_user(updated_data)

        assert result.username == "updated_username"
        assert result.name == "Updated Name"
        assert result.followers_count == 500

    @pytest.mark.asyncio
    async def test_get_tweet_by_id(
        self,
        storage_service: StorageService,
        test_tweet: Tweet,
    ) -> None:
        result = await storage_service.get_tweet_by_id(test_tweet.id)

        assert result is not None
        assert result.id == test_tweet.id
        assert result.twitter_id == test_tweet.twitter_id

    @pytest.mark.asyncio
    async def test_get_tweet_by_id_not_found(
        self,
        storage_service: StorageService,
    ) -> None:
        result = await storage_service.get_tweet_by_id(uuid.uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_get_tweet_by_twitter_id(
        self,
        storage_service: StorageService,
        test_tweet: Tweet,
    ) -> None:
        result = await storage_service.get_tweet_by_twitter_id(test_tweet.twitter_id)

        assert result is not None
        assert result.twitter_id == test_tweet.twitter_id

    @pytest.mark.asyncio
    async def test_get_twitter_user_by_id(
        self,
        storage_service: StorageService,
        test_twitter_user: TwitterUser,
    ) -> None:
        result = await storage_service.get_twitter_user_by_id(test_twitter_user.id)

        assert result is not None
        assert result.id == test_twitter_user.id

    @pytest.mark.asyncio
    async def test_get_twitter_user_by_twitter_id(
        self,
        storage_service: StorageService,
        test_twitter_user: TwitterUser,
    ) -> None:
        result = await storage_service.get_twitter_user_by_twitter_id(
            test_twitter_user.twitter_id
        )

        assert result is not None
        assert result.twitter_id == test_twitter_user.twitter_id

    @pytest.mark.asyncio
    async def test_get_media_by_id(
        self,
        storage_service: StorageService,
        test_media_file: MediaFile,
    ) -> None:
        result = await storage_service.get_media_by_id(test_media_file.id)

        assert result is not None
        assert result.id == test_media_file.id

    @pytest.mark.asyncio
    async def test_bulk_store_tweets(
        self,
        storage_service: StorageService,
        test_twitter_user: TwitterUser,
        test_twitter_account: Any,
    ) -> None:
        tweets_data = [
            {
                "id": f"bulk_tweet_{i}",
                "text": f"Bulk tweet {i}",
                "author_id": test_twitter_user.twitter_id,
                "lang": "en",
                "public_metrics": {
                    "retweet_count": i,
                    "like_count": i * 2,
                    "reply_count": 0,
                    "quote_count": 0,
                },
            }
            for i in range(5)
        ]

        results = await storage_service.bulk_store_tweets(
            tweets_data=tweets_data,
            account_id=test_twitter_account.id,
        )

        assert len(results) == 5
        for i, result in enumerate(results):
            assert result.twitter_id == f"bulk_tweet_{i}"

    @pytest.mark.asyncio
    async def test_bulk_store_tweets_empty_list(
        self,
        storage_service: StorageService,
        test_twitter_account: Any,
    ) -> None:
        results = await storage_service.bulk_store_tweets(
            tweets_data=[],
            account_id=test_twitter_account.id,
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_bulk_store_media(
        self,
        storage_service: StorageService,
        test_tweet: Tweet,
    ) -> None:
        media_list = [
            {
                "media_type": "photo",
                "url": f"https://example.com/image_{i}.jpg",
                "file_size": 1024 * i,
            }
            for i in range(3)
        ]

        results = await storage_service.bulk_store_media(
            media_list=media_list,
            tweet_id=test_tweet.id,
        )

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_bulk_store_media_empty_list(
        self,
        storage_service: StorageService,
        test_tweet: Tweet,
    ) -> None:
        results = await storage_service.bulk_store_media(
            media_list=[],
            tweet_id=test_tweet.id,
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_bulk_store_twitter_users(
        self,
        storage_service: StorageService,
    ) -> None:
        users_data = [
            {
                "id": f"bulk_user_{i}",
                "username": f"user_{i}",
                "name": f"User {i}",
                "public_metrics": {
                    "followers_count": i * 100,
                    "following_count": i * 10,
                    "tweet_count": i,
                },
            }
            for i in range(3)
        ]

        results = await storage_service.bulk_store_twitter_users(users_data)

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_bulk_store_twitter_users_empty_list(
        self,
        storage_service: StorageService,
    ) -> None:
        results = await storage_service.bulk_store_twitter_users([])

        assert results == []

    @pytest.mark.asyncio
    async def test_delete_tweet(
        self,
        storage_service: StorageService,
        test_tweet: Tweet,
    ) -> None:
        result = await storage_service.delete_tweet(test_tweet.id)

        assert result is True

        deleted_tweet = await storage_service.get_tweet_by_id(test_tweet.id)
        assert deleted_tweet is None

    @pytest.mark.asyncio
    async def test_delete_tweet_not_found(
        self,
        storage_service: StorageService,
    ) -> None:
        result = await storage_service.delete_tweet(uuid.uuid4())

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_media(
        self,
        storage_service: StorageService,
        test_media_file: MediaFile,
    ) -> None:
        result = await storage_service.delete_media(test_media_file.id)

        assert result is True

        deleted_media = await storage_service.get_media_by_id(test_media_file.id)
        assert deleted_media is None

    @pytest.mark.asyncio
    async def test_delete_media_not_found(
        self,
        storage_service: StorageService,
    ) -> None:
        result = await storage_service.delete_media(uuid.uuid4())

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_twitter_user(
        self,
        storage_service: StorageService,
        test_twitter_user: TwitterUser,
    ) -> None:
        result = await storage_service.delete_twitter_user(test_twitter_user.id)

        assert result is True

        deleted_user = await storage_service.get_twitter_user_by_id(test_twitter_user.id)
        assert deleted_user is None

    @pytest.mark.asyncio
    async def test_delete_twitter_user_not_found(
        self,
        storage_service: StorageService,
    ) -> None:
        result = await storage_service.delete_twitter_user(uuid.uuid4())

        assert result is False

    @pytest.mark.asyncio
    async def test_get_or_create_twitter_user_create(
        self,
        storage_service: StorageService,
        sample_user_data: dict[str, Any],
    ) -> None:
        result = await storage_service.get_or_create_twitter_user(sample_user_data)

        assert result is not None
        assert result.twitter_id == sample_user_data["id"]

    @pytest.mark.asyncio
    async def test_get_or_create_twitter_user_existing(
        self,
        storage_service: StorageService,
        test_twitter_user: TwitterUser,
    ) -> None:
        user_data = {
            "id": test_twitter_user.twitter_id,
            "username": test_twitter_user.username,
            "name": test_twitter_user.name,
        }

        result = await storage_service.get_or_create_twitter_user(user_data)

        assert result.id == test_twitter_user.id

    @pytest.mark.asyncio
    async def test_store_tweet_with_published_at(
        self,
        storage_service: StorageService,
        test_twitter_user: TwitterUser,
        test_twitter_account: Any,
    ) -> None:
        tweet_data = {
            "id": "tweet_with_date",
            "text": "Tweet with date",
            "author_id": test_twitter_user.twitter_id,
            "created_at": "2024-06-15T14:30:00.000Z",
            "public_metrics": {},
        }

        result = await storage_service.store_tweet(
            tweet_data=tweet_data,
            account_id=test_twitter_account.id,
        )

        assert result.published_at is not None
        assert result.published_at.year == 2024
        assert result.published_at.month == 6
        assert result.published_at.day == 15

    @pytest.mark.asyncio
    async def test_store_tweet_with_retweet_flag(
        self,
        storage_service: StorageService,
        test_twitter_user: TwitterUser,
        test_twitter_account: Any,
    ) -> None:
        tweet_data = {
            "id": "retweet_tweet",
            "text": "RT @user: Original",
            "author_id": test_twitter_user.twitter_id,
            "public_metrics": {},
            "referenced_tweets": [{"type": "retweeted", "id": "original_123"}],
        }

        result = await storage_service.store_tweet(
            tweet_data=tweet_data,
            account_id=test_twitter_account.id,
        )

        assert result.is_retweet is True

    @pytest.mark.asyncio
    async def test_store_tweet_with_quote_flag(
        self,
        storage_service: StorageService,
        test_twitter_user: TwitterUser,
        test_twitter_account: Any,
    ) -> None:
        tweet_data = {
            "id": "quote_tweet",
            "text": "My comment",
            "author_id": test_twitter_user.twitter_id,
            "public_metrics": {},
            "referenced_tweets": [{"type": "quoted", "id": "quoted_123"}],
        }

        result = await storage_service.store_tweet(
            tweet_data=tweet_data,
            account_id=test_twitter_account.id,
        )

        assert result.is_quote is True
