from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.download_task import DownloadTask
from app.models.media_file import MediaFile
from app.models.tweet import Tweet
from app.models.twitter_account import TwitterAccount
from app.models.twitter_user import TwitterUser
from app.models.user import User


class TestCreateUser:
    @pytest.mark.asyncio
    async def test_create_user_success(self, db_session: AsyncSession):
        user = User(
            id=uuid4(),
            username="newuser",
            email="newuser@example.com",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_superuser=False,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.id is not None
        assert user.username == "newuser"
        assert user.email == "newuser@example.com"
        assert user.is_active is True
        assert user.created_at is not None
        assert user.updated_at is not None

    @pytest.mark.asyncio
    async def test_create_user_with_defaults(self, db_session: AsyncSession):
        user = User(
            username="defaultuser",
            email="default@example.com",
            hashed_password="hashed",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.is_active is True
        assert user.is_superuser is False


class TestCreateTwitterAccount:
    @pytest.mark.asyncio
    async def test_create_twitter_account_success(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        account = TwitterAccount(
            id=uuid4(),
            user_id=test_user.id,
            twitter_user_id="twitter_12345",
            twitter_username="test_twitter",
            access_token="encrypted_token",
            refresh_token="encrypted_refresh",
            is_active=True,
        )
        db_session.add(account)
        await db_session.commit()
        await db_session.refresh(account)

        assert account.id is not None
        assert account.user_id == test_user.id
        assert account.twitter_username == "test_twitter"
        assert account.is_active is True

    @pytest.mark.asyncio
    async def test_create_twitter_account_with_user_relation(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        account = TwitterAccount(
            user_id=test_user.id,
            twitter_user_id="twitter_relation",
            twitter_username="relation_user",
            access_token="token",
        )
        db_session.add(account)
        await db_session.commit()
        await db_session.refresh(account)

        result = await db_session.execute(
            select(User).where(User.id == account.user_id)
        )
        user = result.scalar_one_or_none()

        assert user is not None
        assert user.username == test_user.username


class TestCreateTweetWithMedia:
    @pytest.mark.asyncio
    async def test_create_tweet_with_media_success(
        self,
        db_session: AsyncSession,
        test_twitter_account: TwitterAccount,
        test_twitter_user: TwitterUser,
    ):
        tweet = Tweet(
            id=uuid4(),
            twitter_id="tweet_with_media_123",
            twitter_user_id=test_twitter_user.id,
            twitter_account_id=test_twitter_account.id,
            text="Tweet with media content",
            like_count=100,
            is_bookmarked=True,
        )
        db_session.add(tweet)
        await db_session.commit()
        await db_session.refresh(tweet)

        media1 = MediaFile(
            id=uuid4(),
            tweet_id=tweet.id,
            media_type="photo",
            url="https://example.com/photo1.jpg",
            download_status="pending",
        )
        media2 = MediaFile(
            id=uuid4(),
            tweet_id=tweet.id,
            media_type="video",
            url="https://example.com/video1.mp4",
            download_status="pending",
        )
        db_session.add_all([media1, media2])
        await db_session.commit()

        result = await db_session.execute(
            select(Tweet).where(Tweet.id == tweet.id)
        )
        saved_tweet = result.scalar_one_or_none()

        assert saved_tweet is not None
        assert saved_tweet.text == "Tweet with media content"
        assert len(saved_tweet.media_files) == 2

    @pytest.mark.asyncio
    async def test_create_multiple_media_for_tweet(
        self,
        db_session: AsyncSession,
        test_tweet: Tweet,
    ):
        media_files = [
            MediaFile(
                id=uuid4(),
                tweet_id=test_tweet.id,
                media_type="photo",
                url=f"https://example.com/photo{i}.jpg",
                download_status="pending",
            )
            for i in range(4)
        ]
        db_session.add_all(media_files)
        await db_session.commit()

        result = await db_session.execute(
            select(MediaFile).where(MediaFile.tweet_id == test_tweet.id)
        )
        saved_media = result.scalars().all()

        assert len(saved_media) == 4


class TestCascadeDelete:
    @pytest.mark.asyncio
    async def test_cascade_delete_user_to_twitter_account(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_twitter_account: TwitterAccount,
    ):
        account_id = test_twitter_account.id
        user_id = test_user.id

        await db_session.delete(test_user)
        await db_session.commit()

        result = await db_session.execute(
            select(TwitterAccount).where(TwitterAccount.id == account_id)
        )
        deleted_account = result.scalar_one_or_none()

        assert deleted_account is None

    @pytest.mark.asyncio
    async def test_cascade_delete_user_to_download_task(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_download_task: DownloadTask,
    ):
        task_id = test_download_task.id

        await db_session.delete(test_user)
        await db_session.commit()

        result = await db_session.execute(
            select(DownloadTask).where(DownloadTask.id == task_id)
        )
        deleted_task = result.scalar_one_or_none()

        assert deleted_task is None

    @pytest.mark.asyncio
    async def test_cascade_delete_tweet_to_media(
        self,
        db_session: AsyncSession,
        test_tweet: Tweet,
        test_media_file: MediaFile,
    ):
        media_id = test_media_file.id
        tweet_id = test_tweet.id

        await db_session.delete(test_tweet)
        await db_session.commit()

        result = await db_session.execute(
            select(MediaFile).where(MediaFile.id == media_id)
        )
        deleted_media = result.scalar_one_or_none()

        assert deleted_media is None

    @pytest.mark.asyncio
    async def test_cascade_delete_twitter_account_to_download_task(
        self,
        db_session: AsyncSession,
        test_twitter_account: TwitterAccount,
        test_download_task: DownloadTask,
    ):
        task_id = test_download_task.id

        await db_session.delete(test_twitter_account)
        await db_session.commit()

        result = await db_session.execute(
            select(DownloadTask).where(DownloadTask.id == task_id)
        )
        deleted_task = result.scalar_one_or_none()

        assert deleted_task is None


class TestUniqueConstraints:
    @pytest.mark.asyncio
    async def test_unique_username_constraint(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        duplicate_user = User(
            username=test_user.username,
            email="different@example.com",
            hashed_password="hashed",
        )
        db_session.add(duplicate_user)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_unique_email_constraint(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        duplicate_user = User(
            username="differentuser",
            email=test_user.email,
            hashed_password="hashed",
        )
        db_session.add(duplicate_user)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_unique_twitter_user_id_constraint(
        self,
        db_session: AsyncSession,
        test_twitter_account: TwitterAccount,
    ):
        duplicate_account = TwitterAccount(
            user_id=test_twitter_account.user_id,
            twitter_user_id=test_twitter_account.twitter_user_id,
            twitter_username="different_username",
            access_token="different_token",
        )
        db_session.add(duplicate_account)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_unique_tweet_twitter_id_constraint(
        self,
        db_session: AsyncSession,
        test_tweet: Tweet,
        test_twitter_user: TwitterUser,
    ):
        duplicate_tweet = Tweet(
            twitter_id=test_tweet.twitter_id,
            twitter_user_id=test_twitter_user.id,
            text="Different content",
        )
        db_session.add(duplicate_tweet)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_unique_twitter_user_twitter_id_constraint(
        self,
        db_session: AsyncSession,
        test_twitter_user: TwitterUser,
    ):
        duplicate_user = TwitterUser(
            twitter_id=test_twitter_user.twitter_id,
            username="different_username",
        )
        db_session.add(duplicate_user)

        with pytest.raises(IntegrityError):
            await db_session.commit()


class TestForeignKeyConstraints:
    @pytest.mark.asyncio
    async def test_twitter_account_user_foreign_key(self, db_session: AsyncSession):
        account = TwitterAccount(
            user_id=uuid4(),
            twitter_user_id="twitter_fk_test",
            twitter_username="fk_test_user",
            access_token="token",
        )
        db_session.add(account)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_tweet_twitter_user_foreign_key(
        self,
        db_session: AsyncSession,
        test_twitter_account: TwitterAccount,
    ):
        tweet = Tweet(
            twitter_id="fk_tweet_test",
            twitter_user_id=uuid4(),
            twitter_account_id=test_twitter_account.id,
        )
        db_session.add(tweet)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_media_file_tweet_foreign_key(self, db_session: AsyncSession):
        media = MediaFile(
            tweet_id=uuid4(),
            media_type="photo",
            url="https://example.com/fk_test.jpg",
        )
        db_session.add(media)

        with pytest.raises(IntegrityError):
            await db_session.commit()


class TestModelRelationships:
    @pytest.mark.asyncio
    async def test_user_twitter_accounts_relationship(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_twitter_account: TwitterAccount,
    ):
        result = await db_session.execute(
            select(User).where(User.id == test_user.id)
        )
        user = result.scalar_one_or_none()

        assert len(user.twitter_accounts) >= 1
        assert user.twitter_accounts[0].twitter_username == test_twitter_account.twitter_username

    @pytest.mark.asyncio
    async def test_user_download_tasks_relationship(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_download_task: DownloadTask,
    ):
        result = await db_session.execute(
            select(User).where(User.id == test_user.id)
        )
        user = result.scalar_one_or_none()

        assert len(user.download_tasks) >= 1
        assert user.download_tasks[0].task_type == test_download_task.task_type

    @pytest.mark.asyncio
    async def test_tweet_media_files_relationship(
        self,
        db_session: AsyncSession,
        test_tweet: Tweet,
        test_media_file: MediaFile,
    ):
        result = await db_session.execute(
            select(Tweet).where(Tweet.id == test_tweet.id)
        )
        tweet = result.scalar_one_or_none()

        assert len(tweet.media_files) >= 1
        assert tweet.media_files[0].media_type == test_media_file.media_type

    @pytest.mark.asyncio
    async def test_twitter_user_tweets_relationship(
        self,
        db_session: AsyncSession,
        test_twitter_user: TwitterUser,
        test_tweet: Tweet,
    ):
        result = await db_session.execute(
            select(TwitterUser).where(TwitterUser.id == test_twitter_user.id)
        )
        twitter_user = result.scalar_one_or_none()

        assert len(twitter_user.tweets) >= 1
        assert twitter_user.tweets[0].twitter_id == test_tweet.twitter_id
