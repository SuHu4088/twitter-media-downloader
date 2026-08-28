import asyncio
import os
import uuid
from collections.abc import AsyncGenerator, Generator
from datetime import datetime
from typing import Any

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin
from app.models.dedup_record import DedupRecord
from app.models.media_file import MediaFile
from app.models.tweet import Tweet
from app.models.twitter_account import TwitterAccount
from app.models.twitter_user import TwitterUser
from app.models.user import User


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session
        await session.rollback()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def test_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    from app.main import app
    from app.api.deps import get_db

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password_123",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def test_twitter_account(db_session: AsyncSession, test_user: User) -> TwitterAccount:
    account = TwitterAccount(
        id=uuid.uuid4(),
        user_id=test_user.id,
        twitter_user_id="twitter_user_123",
        twitter_username="test_twitter_user",
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        token_expires_at=datetime.utcnow(),
        is_active=True,
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)
    return account


@pytest_asyncio.fixture(scope="function")
async def test_twitter_user(db_session: AsyncSession) -> TwitterUser:
    user = TwitterUser(
        id=uuid.uuid4(),
        twitter_id="twitter_user_456",
        username="test_twitter_author",
        name="Test Author",
        profile_image_url="https://example.com/profile.jpg",
        description="Test description",
        followers_count=100,
        friends_count=50,
        statuses_count=200,
        is_following=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def test_tweet(
    db_session: AsyncSession,
    test_twitter_user: TwitterUser,
    test_twitter_account: TwitterAccount,
) -> Tweet:
    tweet = Tweet(
        id=uuid.uuid4(),
        twitter_id="tweet_123",
        twitter_user_id=test_twitter_user.id,
        twitter_account_id=test_twitter_account.id,
        text="This is a test tweet",
        lang="en",
        retweet_count=10,
        like_count=20,
        reply_count=5,
        quote_count=2,
        is_retweet=False,
        is_quote=False,
        is_liked_by_me=False,
        is_bookmarked=False,
        published_at=datetime.utcnow(),
    )
    db_session.add(tweet)
    await db_session.commit()
    await db_session.refresh(tweet)
    return tweet


@pytest_asyncio.fixture(scope="function")
async def test_media_file(db_session: AsyncSession, test_tweet: Tweet) -> MediaFile:
    media = MediaFile(
        id=uuid.uuid4(),
        tweet_id=test_tweet.id,
        media_type="photo",
        url="https://example.com/image.jpg",
        local_path="/downloads/images/test.jpg",
        file_hash="abc123def456",
        file_size=1024,
        width=800,
        height=600,
        download_status="completed",
    )
    db_session.add(media)
    await db_session.commit()
    await db_session.refresh(media)
    return media


@pytest_asyncio.fixture(scope="function")
async def test_dedup_record(db_session: AsyncSession, test_media_file: MediaFile) -> DedupRecord:
    record = DedupRecord(
        id=uuid.uuid4(),
        file_hash="test_hash_123",
        tweet_id="tweet_789",
        media_url="https://example.com/media.jpg",
        media_id=test_media_file.id,
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)
    return record


@pytest_asyncio.fixture(scope="function")
async def clean_db(db_session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    yield db_session

    for table in reversed(Base.metadata.sorted_tables):
        await db_session.execute(table.delete())
    await db_session.commit()


@pytest.fixture
def mock_twitter_api_response() -> dict[str, Any]:
    return {
        "data": {
            "id": "123456789",
            "username": "testuser",
            "name": "Test User",
            "profile_image_url": "https://pbs.twimg.com/profile_images/test.jpg",
            "description": "Test description",
            "public_metrics": {
                "followers_count": 1000,
                "following_count": 500,
                "tweet_count": 100,
            },
        }
    }


@pytest.fixture
def mock_tweets_response() -> dict[str, Any]:
    return {
        "data": [
            {
                "id": "tweet_001",
                "text": "Test tweet content",
                "created_at": "2024-01-01T12:00:00.000Z",
                "author_id": "user_001",
                "public_metrics": {
                    "retweet_count": 10,
                    "like_count": 20,
                    "reply_count": 5,
                    "quote_count": 2,
                },
                "attachments": {
                    "media_keys": ["media_001"]
                },
            }
        ],
        "includes": {
            "users": [
                {
                    "id": "user_001",
                    "username": "testuser",
                    "name": "Test User",
                    "profile_image_url": "https://example.com/profile.jpg",
                }
            ],
            "media": [
                {
                    "media_key": "media_001",
                    "type": "photo",
                    "url": "https://pbs.twimg.com/media/test.jpg",
                    "width": 1200,
                    "height": 800,
                }
            ]
        }
    }


@pytest.fixture
def mock_token_response() -> dict[str, Any]:
    return {
        "access_token": "new_access_token_123",
        "refresh_token": "new_refresh_token_456",
        "token_type": "bearer",
        "expires_in": 7200,
        "scope": "tweet.read users.read",
    }


@pytest.fixture
def mock_video_media() -> dict[str, Any]:
    return {
        "media_key": "video_001",
        "type": "video",
        "preview_image_url": "https://pbs.twimg.com/media/preview.jpg",
        "width": 1920,
        "height": 1080,
        "duration_ms": 30000,
        "variants": [
            {
                "content_type": "video/mp4",
                "url": "https://video.twimg.com/test_1080p.mp4",
                "bit_rate": 5000000,
            },
            {
                "content_type": "video/mp4",
                "url": "https://video.twimg.com/test_720p.mp4",
                "bit_rate": 2500000,
            },
        ]
    }


@pytest.fixture
def temp_download_dir(tmp_path: Any) -> Any:
    download_dir = tmp_path / "downloads"
    download_dir.mkdir()
    return download_dir


@pytest.fixture
def sample_tweet_data() -> dict[str, Any]:
    return {
        "id": "tweet_test_123",
        "text": "Sample tweet for testing",
        "created_at": "2024-01-15T10:30:00.000Z",
        "author_id": "author_123",
        "lang": "en",
        "public_metrics": {
            "retweet_count": 50,
            "like_count": 100,
            "reply_count": 10,
            "quote_count": 5,
        },
        "is_liked_by_me": True,
        "is_bookmarked": False,
    }


@pytest.fixture
def sample_user_data() -> dict[str, Any]:
    return {
        "id": "user_test_456",
        "username": "sample_user",
        "name": "Sample User",
        "profile_image_url": "https://example.com/avatar.jpg",
        "description": "Sample user description",
        "public_metrics": {
            "followers_count": 5000,
            "following_count": 200,
            "tweet_count": 1000,
        },
    }


@pytest.fixture
def sample_media_data() -> dict[str, Any]:
    return {
        "media_type": "photo",
        "url": "https://example.com/sample_image.jpg",
        "local_path": "/downloads/images/sample.jpg",
        "file_hash": "sample_hash_abc123",
        "file_size": 2048,
        "width": 1024,
        "height": 768,
        "download_status": "pending",
    }
