import base64
import hashlib
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pytest_asyncio import fixture

from app.core.exceptions import RateLimitException, TwitterAPIException
from app.services.twitter_client import TwitterClient


class TestTwitterClient:
    @pytest.fixture
    def twitter_client(self) -> TwitterClient:
        return TwitterClient(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://localhost:8000/callback",
            timeout=30.0,
            max_retries=3,
        )

    def test_get_authorization_url(self, twitter_client: TwitterClient) -> None:
        state = "test_state_123"
        auth_url, code_verifier = twitter_client.get_authorization_url(state)

        assert "https://twitter.com/i/oauth2/authorize" in auth_url
        assert "client_id=test_client_id" in auth_url
        assert f"state={state}" in auth_url
        assert "response_type=code" in auth_url
        assert "code_challenge=" in auth_url
        assert "code_challenge_method=S256" in auth_url
        assert code_verifier is not None
        assert len(code_verifier) > 0

    def test_get_authorization_url_with_custom_scope(
        self, twitter_client: TwitterClient
    ) -> None:
        state = "test_state_456"
        custom_scope = "tweet.read users.read"
        auth_url, code_verifier = twitter_client.get_authorization_url(
            state, scope=custom_scope
        )

        assert f"scope={custom_scope.replace(' ', '%20')}" in auth_url

    def test_get_authorization_url_with_custom_verifier(
        self, twitter_client: TwitterClient
    ) -> None:
        state = "test_state_789"
        custom_verifier = "custom_verifier_string"
        auth_url, returned_verifier = twitter_client.get_authorization_url(
            state, code_verifier=custom_verifier
        )

        assert returned_verifier == custom_verifier

    def test_generate_pkce_verifier(self, twitter_client: TwitterClient) -> None:
        verifier = twitter_client._generate_pkce_verifier()
        assert isinstance(verifier, str)
        assert len(verifier) <= 128

    def test_generate_pkce_challenge(self, twitter_client: TwitterClient) -> None:
        verifier = "test_verifier_string"
        challenge = twitter_client._generate_pkce_challenge(verifier)

        expected_digest = hashlib.sha256(verifier.encode()).digest()
        expected_challenge = base64.urlsafe_b64encode(expected_digest).decode().rstrip("=")
        assert challenge == expected_challenge

    @pytest.mark.asyncio
    async def test_exchange_code(
        self,
        twitter_client: TwitterClient,
        mock_token_response: dict[str, Any],
    ) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = mock_token_response
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            twitter_client, "_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await twitter_client.exchange_code(
                code="test_code",
                code_verifier="test_verifier",
            )

            assert result == mock_token_response
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_exchange_code_with_client_secret(
        self,
        twitter_client: TwitterClient,
        mock_token_response: dict[str, Any],
    ) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = mock_token_response
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            twitter_client, "_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await twitter_client.exchange_code(
                code="test_code",
                code_verifier="test_verifier",
            )

            assert result == mock_token_response
            call_args = mock_request.call_args
            headers = call_args.kwargs.get("headers", {})
            assert "Authorization" in headers

    @pytest.mark.asyncio
    async def test_refresh_access_token(
        self,
        twitter_client: TwitterClient,
        mock_token_response: dict[str, Any],
    ) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = mock_token_response
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            twitter_client, "_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await twitter_client.refresh_access_token(
                refresh_token="test_refresh_token"
            )

            assert result == mock_token_response
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_info(
        self,
        twitter_client: TwitterClient,
        mock_twitter_api_response: dict[str, Any],
    ) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = mock_twitter_api_response
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            twitter_client, "_api_request", new_callable=AsyncMock
        ) as mock_api:
            mock_api.return_value = mock_twitter_api_response

            result = await twitter_client.get_user_info(access_token="test_token")

            assert result == mock_twitter_api_response["data"]
            mock_api.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_info_with_user_id(
        self,
        twitter_client: TwitterClient,
        mock_twitter_api_response: dict[str, Any],
    ) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = mock_twitter_api_response
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            twitter_client, "_api_request", new_callable=AsyncMock
        ) as mock_api:
            mock_api.return_value = mock_twitter_api_response

            result = await twitter_client.get_user_info(
                access_token="test_token",
                user_id="123456789",
            )

            assert result == mock_twitter_api_response["data"]

    @pytest.mark.asyncio
    async def test_get_likes(
        self,
        twitter_client: TwitterClient,
        mock_tweets_response: dict[str, Any],
    ) -> None:
        with patch.object(
            twitter_client, "_api_request", new_callable=AsyncMock
        ) as mock_api:
            mock_api.return_value = mock_tweets_response

            result = await twitter_client.get_likes(
                access_token="test_token",
                user_id="user_001",
            )

            assert result == mock_tweets_response
            mock_api.assert_called_once()
            call_args = mock_api.call_args
            assert "user_001" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_get_likes_with_pagination(
        self,
        twitter_client: TwitterClient,
        mock_tweets_response: dict[str, Any],
    ) -> None:
        with patch.object(
            twitter_client, "_api_request", new_callable=AsyncMock
        ) as mock_api:
            mock_api.return_value = mock_tweets_response

            result = await twitter_client.get_likes(
                access_token="test_token",
                user_id="user_001",
                max_results=50,
                pagination_token="next_token_123",
            )

            assert result == mock_tweets_response

    @pytest.mark.asyncio
    async def test_get_bookmarks(
        self,
        twitter_client: TwitterClient,
        mock_tweets_response: dict[str, Any],
    ) -> None:
        with patch.object(
            twitter_client, "_api_request", new_callable=AsyncMock
        ) as mock_api:
            mock_api.return_value = mock_tweets_response

            result = await twitter_client.get_bookmarks(
                access_token="test_token",
                user_id="user_001",
            )

            assert result == mock_tweets_response
            mock_api.assert_called_once()
            call_args = mock_api.call_args
            assert "bookmarks" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_get_bookmarks_with_pagination(
        self,
        twitter_client: TwitterClient,
        mock_tweets_response: dict[str, Any],
    ) -> None:
        with patch.object(
            twitter_client, "_api_request", new_callable=AsyncMock
        ) as mock_api:
            mock_api.return_value = mock_tweets_response

            result = await twitter_client.get_bookmarks(
                access_token="test_token",
                user_id="user_001",
                max_results=50,
                pagination_token="next_token_456",
            )

            assert result == mock_tweets_response

    def test_extract_media_urls_photo(self, twitter_client: TwitterClient) -> None:
        tweet = {
            "attachments": {"media_keys": ["photo_001"]},
            "includes": {
                "media": [
                    {
                        "media_key": "photo_001",
                        "type": "photo",
                        "url": "https://pbs.twimg.com/media/photo.jpg",
                        "width": 1200,
                        "height": 800,
                    }
                ]
            },
        }

        result = TwitterClient.extract_media_urls(tweet)

        assert len(result) == 1
        assert result[0]["media_type"] == "photo"
        assert result[0]["url"] == "https://pbs.twimg.com/media/photo.jpg"
        assert result[0]["width"] == 1200
        assert result[0]["height"] == 800

    def test_extract_media_urls_video(
        self, twitter_client: TwitterClient, mock_video_media: dict[str, Any]
    ) -> None:
        tweet = {
            "attachments": {"media_keys": ["video_001"]},
            "includes": {
                "media": [mock_video_media]
            },
        }

        result = TwitterClient.extract_media_urls(tweet)

        assert len(result) == 1
        assert result[0]["media_type"] == "video"
        assert result[0]["url"] == "https://video.twimg.com/test_1080p.mp4"
        assert result[0]["preview_url"] == "https://pbs.twimg.com/media/preview.jpg"
        assert result[0]["duration_ms"] == 30000

    def test_extract_media_urls_animated_gif(
        self, twitter_client: TwitterClient
    ) -> None:
        tweet = {
            "attachments": {"media_keys": ["gif_001"]},
            "includes": {
                "media": [
                    {
                        "media_key": "gif_001",
                        "type": "animated_gif",
                        "preview_image_url": "https://pbs.twimg.com/media/gif_preview.jpg",
                        "variants": [
                            {
                                "content_type": "video/mp4",
                                "url": "https://video.twimg.com/gif.mp4",
                                "bit_rate": 1000000,
                            }
                        ],
                        "width": 480,
                        "height": 360,
                    }
                ]
            },
        }

        result = TwitterClient.extract_media_urls(tweet)

        assert len(result) == 1
        assert result[0]["media_type"] == "animated_gif"
        assert result[0]["url"] == "https://video.twimg.com/gif.mp4"

    def test_extract_media_urls_no_attachments(
        self, twitter_client: TwitterClient
    ) -> None:
        tweet = {"text": "Tweet without media"}

        result = TwitterClient.extract_media_urls(tweet)

        assert result == []

    def test_extract_media_urls_empty_media_keys(
        self, twitter_client: TwitterClient
    ) -> None:
        tweet = {
            "attachments": {"media_keys": []},
            "includes": {"media": []},
        }

        result = TwitterClient.extract_media_urls(tweet)

        assert result == []

    def test_extract_media_urls_missing_media_in_includes(
        self, twitter_client: TwitterClient
    ) -> None:
        tweet = {
            "attachments": {"media_keys": ["photo_001"]},
            "includes": {
                "media": []
            },
        }

        result = TwitterClient.extract_media_urls(tweet)

        assert result == []

    def test_extract_media_urls_selects_highest_bitrate(
        self, twitter_client: TwitterClient
    ) -> None:
        tweet = {
            "attachments": {"media_keys": ["video_001"]},
            "includes": {
                "media": [
                    {
                        "media_key": "video_001",
                        "type": "video",
                        "preview_image_url": "https://example.com/preview.jpg",
                        "variants": [
                            {
                                "content_type": "video/mp4",
                                "url": "https://example.com/low.mp4",
                                "bit_rate": 1000000,
                            },
                            {
                                "content_type": "video/mp4",
                                "url": "https://example.com/high.mp4",
                                "bit_rate": 5000000,
                            },
                            {
                                "content_type": "video/mp4",
                                "url": "https://example.com/medium.mp4",
                                "bit_rate": 2500000,
                            },
                        ],
                    }
                ]
            },
        }

        result = TwitterClient.extract_media_urls(tweet)

        assert len(result) == 1
        assert result[0]["url"] == "https://example.com/high.mp4"

    @pytest.mark.asyncio
    async def test_request_with_retry_success(self, twitter_client: TwitterClient) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(return_value=mock_response)

        twitter_client._client = mock_client

        result = await twitter_client._request_with_retry("GET", "https://api.twitter.com/test")

        assert result == mock_response

    @pytest.mark.asyncio
    async def test_request_with_retry_rate_limit(self, twitter_client: TwitterClient) -> None:
        from datetime import datetime, timezone

        mock_response_429 = MagicMock(spec=httpx.Response)
        mock_response_429.status_code = 429
        mock_response_429.headers = {"x-rate-limit-reset": str(int(datetime.now(timezone.utc).timestamp()) + 1)}

        mock_response_200 = MagicMock(spec=httpx.Response)
        mock_response_200.status_code = 200
        mock_response_200.raise_for_status = MagicMock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(side_effect=[mock_response_429, mock_response_200])

        twitter_client._client = mock_client

        result = await twitter_client._request_with_retry("GET", "https://api.twitter.com/test")

        assert result == mock_response_200

    @pytest.mark.asyncio
    async def test_request_with_retry_server_error_retry(
        self, twitter_client: TwitterClient
    ) -> None:
        mock_response_500 = MagicMock(spec=httpx.Response)
        mock_response_500.status_code = 500
        mock_response_500.text = "Internal Server Error"

        mock_response_200 = MagicMock(spec=httpx.Response)
        mock_response_200.status_code = 200
        mock_response_200.raise_for_status = MagicMock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(side_effect=[mock_response_500, mock_response_200])

        twitter_client._client = mock_client

        result = await twitter_client._request_with_retry("GET", "https://api.twitter.com/test")

        assert result == mock_response_200

    @pytest.mark.asyncio
    async def test_request_with_retry_max_retries_exceeded(
        self, twitter_client: TwitterClient
    ) -> None:
        mock_response_500 = MagicMock(spec=httpx.Response)
        mock_response_500.status_code = 500
        mock_response_500.text = "Internal Server Error"

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request = AsyncMock(return_value=mock_response_500)

        twitter_client._client = mock_client

        with pytest.raises(TwitterAPIException):
            await twitter_client._request_with_retry("GET", "https://api.twitter.com/test")

    @pytest.mark.asyncio
    async def test_context_manager(self, twitter_client: TwitterClient) -> None:
        async with twitter_client as client:
            assert client is twitter_client
            assert twitter_client._client is not None

        assert twitter_client._client is None

    @pytest.mark.asyncio
    async def test_start_creates_client(self, twitter_client: TwitterClient) -> None:
        assert twitter_client._client is None

        await twitter_client.start()

        assert twitter_client._client is not None

        await twitter_client.close()

    @pytest.mark.asyncio
    async def test_close_destroys_client(self, twitter_client: TwitterClient) -> None:
        await twitter_client.start()
        assert twitter_client._client is not None

        await twitter_client.close()

        assert twitter_client._client is None

    def test_parse_tweet_data(self, twitter_client: TwitterClient) -> None:
        tweet_data = {
            "id": "tweet_123",
            "text": "Test tweet",
            "lang": "en",
            "author_id": "author_123",
            "created_at": "2024-01-01T12:00:00.000Z",
            "public_metrics": {
                "retweet_count": 10,
                "like_count": 20,
                "reply_count": 5,
                "quote_count": 2,
            },
            "referenced_tweets": [],
        }

        result = TwitterClient.parse_tweet_data(tweet_data)

        assert result["twitter_id"] == "tweet_123"
        assert result["text"] == "Test tweet"
        assert result["lang"] == "en"
        assert result["author_id"] == "author_123"
        assert result["retweet_count"] == 10
        assert result["like_count"] == 20
        assert result["is_retweet"] is False
        assert result["is_quote"] is False

    def test_parse_tweet_data_with_retweet(self, twitter_client: TwitterClient) -> None:
        tweet_data = {
            "id": "tweet_456",
            "text": "RT @user: Original tweet",
            "public_metrics": {},
            "referenced_tweets": [{"type": "retweeted", "id": "original_123"}],
        }

        result = TwitterClient.parse_tweet_data(tweet_data)

        assert result["is_retweet"] is True

    def test_parse_tweet_data_with_quote(self, twitter_client: TwitterClient) -> None:
        tweet_data = {
            "id": "tweet_789",
            "text": "My comment on this",
            "public_metrics": {},
            "referenced_tweets": [{"type": "quoted", "id": "quoted_123"}],
        }

        result = TwitterClient.parse_tweet_data(tweet_data)

        assert result["is_quote"] is True

    def test_parse_tweet_data_empty(self, twitter_client: TwitterClient) -> None:
        result = TwitterClient.parse_tweet_data({})

        assert result == {}

    @pytest.mark.asyncio
    async def test_revoke_token_success(self, twitter_client: TwitterClient) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200

        with patch.object(
            twitter_client, "_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await twitter_client.revoke_token("test_access_token")

            assert result is True

    @pytest.mark.asyncio
    async def test_revoke_token_failure(self, twitter_client: TwitterClient) -> None:
        with patch.object(
            twitter_client, "_request_with_retry", new_callable=AsyncMock
        ) as mock_request:
            mock_request.side_effect = Exception("Network error")

            result = await twitter_client.revoke_token("test_access_token")

            assert result is False
