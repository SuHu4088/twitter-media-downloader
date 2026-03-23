from typing import Any

import httpx

from app.core.config import settings


class AsyncHttpClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        proxy_url: str | None = None,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self._proxy_url = proxy_url
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "AsyncHttpClient":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def start(self) -> None:
        if self._client is None:
            proxy = self._proxy_url or self._get_default_proxy()
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                proxy=proxy,
                follow_redirects=True,
            )

    def _get_default_proxy(self) -> str | None:
        if self._proxy_url:
            return self._proxy_url
        proxy_dict = settings.proxy_dict
        if proxy_dict:
            return proxy_dict.get("http") or proxy_dict.get("https")
        return None

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

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
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                if e.response.status_code < 500:
                    raise
                last_exception = e
            except httpx.RequestError as e:
                last_exception = e

            if attempt < self.max_retries - 1:
                import asyncio
                await asyncio.sleep(2 ** attempt)

        raise last_exception or httpx.RequestError("请求失败")

    async def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> httpx.Response:
        return await self._request_with_retry(
            "GET", url, params=params, headers=headers, **kwargs
        )

    async def post(
        self,
        url: str,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> httpx.Response:
        return await self._request_with_retry(
            "POST", url, data=data, json=json, headers=headers, **kwargs
        )

    async def put(
        self,
        url: str,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> httpx.Response:
        return await self._request_with_retry(
            "PUT", url, data=data, json=json, headers=headers, **kwargs
        )

    async def delete(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> httpx.Response:
        return await self._request_with_retry("DELETE", url, headers=headers, **kwargs)

    async def download(
        self,
        url: str,
        output_path: str,
        chunk_size: int = 8192,
    ) -> int:
        if self._client is None:
            await self.start()

        async with self._client.stream("GET", url) as response:
            response.raise_for_status()
            total_size = 0

            import aiofiles
            async with aiofiles.open(output_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size):
                    await f.write(chunk)
                    total_size += len(chunk)

            return total_size

    def set_proxy(self, proxy_url: str | None) -> None:
        self._proxy_url = proxy_url


_http_client: AsyncHttpClient | None = None


async def get_http_client() -> AsyncHttpClient:
    global _http_client
    if _http_client is None:
        _http_client = AsyncHttpClient()
        await _http_client.start()
    return _http_client


async def close_http_client() -> None:
    global _http_client
    if _http_client:
        await _http_client.close()
        _http_client = None


async def get_proxy_url() -> str | None:
    from app.services.proxy_service import ProxyService
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        service = ProxyService(db)
        config = await service.get_active_proxy()
        if config:
            return ProxyService.get_proxy_url(config)
    return None


async def create_http_client_with_proxy(
    base_url: str | None = None,
    timeout: float = 30.0,
    max_retries: int = 3,
) -> AsyncHttpClient:
    proxy_url = await get_proxy_url()
    return AsyncHttpClient(
        base_url=base_url,
        timeout=timeout,
        max_retries=max_retries,
        proxy_url=proxy_url,
    )
