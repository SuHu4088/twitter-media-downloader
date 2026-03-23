import asyncio
import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.core.exceptions import RateLimitException, TwitterAPIException


class TwitterClient:
    TWITTER_AUTH_URL = "https://twitter.com/i/oauth2/authorize"
    TWITTER_TOKEN_URL = "https://api.twitter.com/2/oauth2/token"
    TWITTER_API_BASE = "https://api.twitter.com/2"

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        redirect_uri: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        self.client_id = client_id or settings.TWITTER_CLIENT_ID
        self.client_secret = client_secret or settings.TWITTER_CLIENT_SECRET
        self.redirect_uri = redirect_uri or settings.TWITTER_REDIRECT_URI
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "TwitterClient":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def start(self) -> None:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                proxy=settings.proxy_dict,
                follow_redirects=True,
            )

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _generate_pkce_verifier(self) -> str:
        return secrets.token_urlsafe(64)[:128]

    def _generate_pkce_challenge(self, verifier: str) -> str:
        digest = hashlib.sha256(verifier.encode()).digest()
        return base64.urlsafe_b64encode(digest).decode().rstrip("=")

    def get_authorization_url(
        self,
        state: str,
        code_verifier: str | None = None,
        scope: str = "tweet.read users.read bookmark.read like.read offline.access",
    ) -> tuple[str, str]:
        if code_verifier is None:
            code_verifier = self._generate_pkce_verifier()

        code_challenge = self._generate_pkce_challenge(code_verifier)

        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": scope,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        auth_url = f"{self.TWITTER_AUTH_URL}?{urlencode(params)}"
        return auth_url, code_verifier

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> httpx.Response:
        if self._client is None:
            await self.start()

        last_exception: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = await self._client.request(method, url, **kwargs)

                if response.status_code == 429:
                    reset_time = response.headers.get("x-rate-limit-reset")
                    if reset_time:
                        wait_time = int(reset_time) - int(datetime.now(timezone.utc).timestamp())
                        if wait_time > 0 and wait_time < 900:
                            await asyncio.sleep(wait_time)
                            continue
                    raise RateLimitException(
                        message="Twitter API 速率限制",
                        details={"retry_after": response.headers.get("x-rate-limit-reset")},
                    )

                if response.status_code >= 500:
                    last_exception = TwitterAPIException(
                        message=f"Twitter API 服务器错误: {response.status_code}",
                        details=response.text,
                    )
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2**attempt)
                        continue
                    raise last_exception

                response.raise_for_status()
                return response

            except httpx.HTTPStatusError as e:
                if e.response.status_code < 500:
                    error_detail = None
                    try:
                        error_detail = e.response.json()
                    except Exception:
                        error_detail = e.response.text
                    raise TwitterAPIException(
                        message=f"Twitter API 错误: {e.response.status_code}",
                        details=error_detail,
                    )
                last_exception = e
            except httpx.RequestError as e:
                last_exception = e

            if attempt < self.max_retries - 1:
                await asyncio.sleep(2**attempt)

        raise last_exception or TwitterAPIException(message="请求失败")

    async def exchange_code(
        self,
        code: str,
        code_verifier: str,
    ) -> dict[str, Any]:
        data = {
            "code": code,
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "code_verifier": code_verifier,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        if self.client_secret:
            auth_str = f"{self.client_id}:{self.client_secret}"
            auth_bytes = base64.b64encode(auth_str.encode()).decode()
            headers["Authorization"] = f"Basic {auth_bytes}"

        response = await self._request_with_retry(
            "POST",
            self.TWITTER_TOKEN_URL,
            data=data,
            headers=headers,
        )

        return response.json()

    async def refresh_access_token(self, refresh_token: str) -> dict[str, Any]:
        data = {
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "client_id": self.client_id,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        if self.client_secret:
            auth_str = f"{self.client_id}:{self.client_secret}"
            auth_bytes = base64.b64encode(auth_str.encode()).decode()
            headers["Authorization"] = f"Basic {auth_bytes}"

        response = await self._request_with_retry(
            "POST",
            self.TWITTER_TOKEN_URL,
            data=data,
            headers=headers,
        )

        return response.json()

    async def _api_request(
        self,
        access_token: str,
        endpoint: str,
        method: str = "GET",
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.TWITTER_API_BASE}{endpoint}"

        headers = {
            "Authorization": f"Bearer {access_token}",
        }

        if method == "GET":
            response = await self._request_with_retry(
                method,
                url,
                params=params,
                headers=headers,
            )
        else:
            response = await self._request_with_retry(
                method,
                url,
                json=data,
                params=params,
                headers=headers,
            )

        return response.json()

    async def get_user_info(
        self,
        access_token: str,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        if user_id:
            endpoint = f"/users/{user_id}"
        else:
            endpoint = "/users/me"

        params = {
            "user.fields": "id,name,username,profile_image_url,description,public_metrics,created_at,verified,location,url",
        }

        result = await self._api_request(access_token, endpoint, params=params)
        return result.get("data", {})

    async def get_likes(
        self,
        access_token: str,
        user_id: str,
        max_results: int = 100,
        pagination_token: str | None = None,
    ) -> dict[str, Any]:
        endpoint = f"/users/{user_id}/liked_tweets"

        params = {
            "max_results": max_results,
            "tweet.fields": "id,text,created_at,public_metrics,author_id,in_reply_to_user_id,referenced_tweets,attachments,entities,lang",
            "expansions": "author_id,referenced_tweets.id,attachments.media_keys",
            "user.fields": "id,name,username,profile_image_url,description,public_metrics,verified",
            "media.fields": "media_key,type,url,preview_image_url,variants,width,height,duration_ms",
        }

        if pagination_token:
            params["pagination_token"] = pagination_token

        return await self._api_request(access_token, endpoint, params=params)

    async def get_bookmarks(
        self,
        access_token: str,
        user_id: str,
        max_results: int = 100,
        pagination_token: str | None = None,
    ) -> dict[str, Any]:
        endpoint = f"/users/{user_id}/bookmarks"

        params = {
            "max_results": max_results,
            "tweet.fields": "id,text,created_at,public_metrics,author_id,in_reply_to_user_id,referenced_tweets,attachments,entities",
            "expansions": "author_id,referenced_tweets.id,attachments.media_keys",
            "user.fields": "id,name,username,profile_image_url",
            "media.fields": "media_key,type,url,preview_image_url,variants,width,height,duration_ms",
        }

        if pagination_token:
            params["pagination_token"] = pagination_token

        return await self._api_request(access_token, endpoint, params=params)

    async def get_following(
        self,
        access_token: str,
        user_id: str,
        max_results: int = 100,
        pagination_token: str | None = None,
    ) -> dict[str, Any]:
        endpoint = f"/users/{user_id}/following"

        params = {
            "max_results": max_results,
            "user.fields": "id,name,username,profile_image_url,description,public_metrics,verified",
        }

        if pagination_token:
            params["pagination_token"] = pagination_token

        return await self._api_request(access_token, endpoint, params=params)

    async def get_followers(
        self,
        access_token: str,
        user_id: str,
        max_results: int = 100,
        pagination_token: str | None = None,
    ) -> dict[str, Any]:
        endpoint = f"/users/{user_id}/followers"

        params = {
            "max_results": max_results,
            "user.fields": "id,name,username,profile_image_url,description,public_metrics,verified",
        }

        if pagination_token:
            params["pagination_token"] = pagination_token

        return await self._api_request(access_token, endpoint, params=params)

    async def get_user_timeline(
        self,
        access_token: str,
        user_id: str,
        max_results: int = 100,
        pagination_token: str | None = None,
        exclude: str | None = "retweets,replies",
    ) -> dict[str, Any]:
        endpoint = f"/users/{user_id}/tweets"

        params = {
            "max_results": max_results,
            "tweet.fields": "id,text,created_at,public_metrics,author_id,in_reply_to_user_id,referenced_tweets,attachments,entities",
            "expansions": "author_id,referenced_tweets.id,attachments.media_keys",
            "user.fields": "id,name,username,profile_image_url",
            "media.fields": "media_key,type,url,preview_image_url,variants,width,height,duration_ms",
        }

        if exclude:
            params["exclude"] = exclude

        if pagination_token:
            params["pagination_token"] = pagination_token

        return await self._api_request(access_token, endpoint, params=params)

    async def get_tweet(
        self,
        access_token: str,
        tweet_id: str,
    ) -> dict[str, Any]:
        endpoint = f"/tweets/{tweet_id}"

        params = {
            "tweet.fields": "id,text,created_at,public_metrics,author_id,in_reply_to_user_id,referenced_tweets,attachments,entities",
            "expansions": "author_id,referenced_tweets.id,attachments.media_keys",
            "user.fields": "id,name,username,profile_image_url",
            "media.fields": "media_key,type,url,preview_image_url,variants,width,height,duration_ms",
        }

        return await self._api_request(access_token, endpoint, params=params)

    async def get_tweets(
        self,
        access_token: str,
        tweet_ids: list[str],
    ) -> dict[str, Any]:
        endpoint = "/tweets"

        params = {
            "ids": ",".join(tweet_ids),
            "tweet.fields": "id,text,created_at,public_metrics,author_id,in_reply_to_user_id,referenced_tweets,attachments,entities,lang",
            "expansions": "author_id,referenced_tweets.id,attachments.media_keys",
            "user.fields": "id,name,username,profile_image_url,description,public_metrics,verified",
            "media.fields": "media_key,type,url,preview_image_url,variants,width,height,duration_ms",
        }

        return await self._api_request(access_token, endpoint, params=params)

    async def get_user_by_username(
        self,
        access_token: str,
        username: str,
    ) -> dict[str, Any]:
        endpoint = f"/users/by/username/{username}"

        params = {
            "user.fields": "id,name,username,profile_image_url,description,public_metrics,created_at,verified,location,url",
        }

        result = await self._api_request(access_token, endpoint, params=params)
        return result.get("data", {})

    async def get_user_by_id(
        self,
        access_token: str,
        user_id: str,
    ) -> dict[str, Any]:
        endpoint = f"/users/{user_id}"

        params = {
            "user.fields": "id,name,username,profile_image_url,description,public_metrics,created_at,verified,location,url",
        }

        result = await self._api_request(access_token, endpoint, params=params)
        return result.get("data", {})

    async def get_user_tweets(
        self,
        access_token: str,
        user_id: str,
        max_results: int = 100,
        exclude_replies: bool = True,
        pagination_token: str | None = None,
    ) -> dict[str, Any]:
        endpoint = f"/users/{user_id}/tweets"

        params = {
            "max_results": max_results,
            "tweet.fields": "id,text,created_at,public_metrics,author_id,in_reply_to_user_id,referenced_tweets,attachments,entities,lang",
            "expansions": "author_id,referenced_tweets.id,attachments.media_keys",
            "user.fields": "id,name,username,profile_image_url,description,public_metrics,verified",
            "media.fields": "media_key,type,url,preview_image_url,variants,width,height,duration_ms",
        }

        if exclude_replies:
            params["exclude"] = "replies"

        if pagination_token:
            params["pagination_token"] = pagination_token

        return await self._api_request(access_token, endpoint, params=params)

    @staticmethod
    def extract_media_urls(tweet: dict[str, Any]) -> list[dict[str, Any]]:
        media_urls = []
        attachments = tweet.get("attachments", {})
        media_keys = attachments.get("media_keys", [])

        if not media_keys:
            return media_urls

        includes = tweet.get("includes", {})
        media_list = includes.get("media", [])

        media_map = {m.get("media_key"): m for m in media_list if m.get("media_key")}

        for media_key in media_keys:
            media = media_map.get(media_key)
            if not media:
                continue

            media_type = media.get("type", "")
            media_info = {
                "media_key": media_key,
                "media_type": media_type,
                "url": None,
                "preview_url": None,
                "width": media.get("width"),
                "height": media.get("height"),
                "duration_ms": media.get("duration_ms"),
            }

            if media_type == "photo":
                media_info["url"] = media.get("url")
                media_info["preview_url"] = media.get("url")
            elif media_type in ("video", "animated_gif"):
                media_info["preview_url"] = media.get("preview_image_url")
                variants = media.get("variants", [])
                mp4_variants = [
                    v for v in variants
                    if v.get("content_type") == "video/mp4"
                ]
                if mp4_variants:
                    mp4_variants.sort(
                        key=lambda x: x.get("bit_rate", 0),
                        reverse=True
                    )
                    media_info["url"] = mp4_variants[0].get("url")
                elif variants:
                    media_info["url"] = variants[0].get("url")

            if media_info["url"]:
                media_urls.append(media_info)

        return media_urls

    @staticmethod
    def parse_tweet_data(tweet_data: dict[str, Any], includes: dict[str, Any] | None = None) -> dict[str, Any]:
        if not tweet_data:
            return {}

        public_metrics = tweet_data.get("public_metrics", {})
        referenced_tweets = tweet_data.get("referenced_tweets", [])

        is_retweet = any(rt.get("type") == "retweeted" for rt in referenced_tweets)
        is_quote = any(rt.get("type") == "quoted" for rt in referenced_tweets)

        parsed = {
            "twitter_id": tweet_data.get("id"),
            "text": tweet_data.get("text"),
            "lang": tweet_data.get("lang"),
            "author_id": tweet_data.get("author_id"),
            "retweet_count": public_metrics.get("retweet_count", 0),
            "like_count": public_metrics.get("like_count", 0),
            "reply_count": public_metrics.get("reply_count", 0),
            "quote_count": public_metrics.get("quote_count", 0),
            "is_retweet": is_retweet,
            "is_quote": is_quote,
            "created_at": tweet_data.get("created_at"),
        }

        if includes:
            users = includes.get("users", [])
            author_id = tweet_data.get("author_id")
            if author_id:
                author = next((u for u in users if u.get("id") == author_id), None)
                if author:
                    parsed["author"] = {
                        "twitter_id": author.get("id"),
                        "username": author.get("username"),
                        "name": author.get("name"),
                        "profile_image_url": author.get("profile_image_url"),
                    }

            tweet_with_includes = {**tweet_data, "includes": includes}
            parsed["media"] = TwitterClient.extract_media_urls(tweet_with_includes)

        return parsed

    async def revoke_token(self, access_token: str) -> bool:
        try:
            data = {
                "token": access_token,
                "token_type_hint": "access_token",
                "client_id": self.client_id,
            }

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
            }

            if self.client_secret:
                auth_str = f"{self.client_id}:{self.client_secret}"
                auth_bytes = base64.b64encode(auth_str.encode()).decode()
                headers["Authorization"] = f"Basic {auth_bytes}"

            response = await self._request_with_retry(
                "POST",
                "https://api.twitter.com/2/oauth2/revoke",
                data=data,
                headers=headers,
            )

            return response.status_code == 200
        except Exception:
            return False


_twitter_client: TwitterClient | None = None


async def get_twitter_client() -> TwitterClient:
    global _twitter_client
    if _twitter_client is None:
        _twitter_client = TwitterClient()
        await _twitter_client.start()
    return _twitter_client


async def close_twitter_client() -> None:
    global _twitter_client
    if _twitter_client:
        await _twitter_client.close()
        _twitter_client = None
