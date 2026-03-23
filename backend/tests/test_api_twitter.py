from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.twitter_account import TwitterAccount
from app.models.user import User


class TestGetOAuthAuthorizeUrl:
    @pytest.mark.asyncio
    async def test_get_oauth_authorize_url_success(
        self,
        client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ):
        access_token = create_access_token(subject=str(test_user.id))
        with patch("app.api.v1.twitter.TwitterService") as MockTwitterService:
            mock_service = MagicMock()
            mock_service.initiate_oauth.return_value = {
                "authorization_url": "https://twitter.com/oauth/authorize?state=test_state",
                "state": "test_state",
            }
            MockTwitterService.return_value = mock_service

            response = await client.get(
                "/api/v1/twitter/oauth/authorize",
                headers={"Authorization": f"Bearer {access_token}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "authorization_url" in data["data"]
        assert "state" in data["data"]

    @pytest.mark.asyncio
    async def test_get_oauth_authorize_url_unauthorized(self, client: AsyncClient):
        response = await client.get("/api/v1/twitter/oauth/authorize")
        assert response.status_code == 401


class TestOAuthCallback:
    @pytest.mark.asyncio
    async def test_oauth_callback_success(
        self,
        client: AsyncClient,
        test_user: User,
        test_twitter_account: TwitterAccount,
    ):
        access_token = create_access_token(subject=str(test_user.id))
        with patch("app.api.v1.twitter.TwitterService") as MockTwitterService:
            mock_service = MagicMock()
            mock_service.handle_oauth_callback = AsyncMock(return_value=test_twitter_account)
            MockTwitterService.return_value = mock_service

            response = await client.post(
                "/api/v1/twitter/oauth/callback",
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "code": "test_code",
                    "state": "test_state",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Twitter 账号绑定成功"

    @pytest.mark.asyncio
    async def test_oauth_callback_invalid_state(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        access_token = create_access_token(subject=str(test_user.id))
        with patch("app.api.v1.twitter.TwitterService") as MockTwitterService:
            from app.core.exceptions import BadRequestException

            mock_service = MagicMock()
            mock_service.handle_oauth_callback = AsyncMock(
                side_effect=BadRequestException(message="无效的 OAuth 状态")
            )
            MockTwitterService.return_value = mock_service

            response = await client.post(
                "/api/v1/twitter/oauth/callback",
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "code": "test_code",
                    "state": "invalid_state",
                },
            )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_oauth_callback_unauthorized(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/twitter/oauth/callback",
            json={
                "code": "test_code",
                "state": "test_state",
            },
        )
        assert response.status_code == 401


class TestGetAccounts:
    @pytest.mark.asyncio
    async def test_get_accounts_success(
        self,
        client: AsyncClient,
        test_user: User,
        test_twitter_account: TwitterAccount,
    ):
        access_token = create_access_token(subject=str(test_user.id))
        response = await client.get(
            "/api/v1/twitter/accounts",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "items" in data["data"]
        assert "total" in data["data"]
        assert data["data"]["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_accounts_empty(
        self,
        client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ):
        new_user = User(
            id=uuid4(),
            username="user_no_accounts",
            email="no_accounts@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        db_session.add(new_user)
        await db_session.commit()

        access_token = create_access_token(subject=str(new_user.id))
        response = await client.get(
            "/api/v1/twitter/accounts",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total"] == 0
        assert len(data["data"]["items"]) == 0

    @pytest.mark.asyncio
    async def test_get_accounts_pagination(
        self,
        client: AsyncClient,
        test_user: User,
        test_twitter_account: TwitterAccount,
    ):
        access_token = create_access_token(subject=str(test_user.id))
        response = await client.get(
            "/api/v1/twitter/accounts?page=1&page_size=10",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["page"] == 1
        assert data["data"]["page_size"] == 10

    @pytest.mark.asyncio
    async def test_get_accounts_unauthorized(self, client: AsyncClient):
        response = await client.get("/api/v1/twitter/accounts")
        assert response.status_code == 401


class TestUnbindAccount:
    @pytest.mark.asyncio
    async def test_unbind_account_success(
        self,
        client: AsyncClient,
        test_user: User,
        test_twitter_account: TwitterAccount,
    ):
        access_token = create_access_token(subject=str(test_user.id))
        with patch("app.api.v1.twitter.TwitterService") as MockTwitterService:
            mock_service = MagicMock()
            mock_service.unbind_account = AsyncMock(return_value=True)
            MockTwitterService.return_value = mock_service

            response = await client.delete(
                f"/api/v1/twitter/accounts/{test_twitter_account.id}",
                headers={"Authorization": f"Bearer {access_token}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "已解绑" in data["message"]

    @pytest.mark.asyncio
    async def test_unbind_account_not_found(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        access_token = create_access_token(subject=str(test_user.id))
        with patch("app.api.v1.twitter.TwitterService") as MockTwitterService:
            from app.core.exceptions import NotFoundException

            mock_service = MagicMock()
            mock_service.unbind_account = AsyncMock(
                side_effect=NotFoundException(message="Twitter 账号不存在")
            )
            MockTwitterService.return_value = mock_service

            response = await client.delete(
                f"/api/v1/twitter/accounts/{uuid4()}",
                headers={"Authorization": f"Bearer {access_token}"},
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_unbind_account_unauthorized(self, client: AsyncClient):
        response = await client.delete(f"/api/v1/twitter/accounts/{uuid4()}")
        assert response.status_code == 401


class TestGetAccountStatus:
    @pytest.mark.asyncio
    async def test_get_account_status_success(
        self,
        client: AsyncClient,
        test_user: User,
        test_twitter_account: TwitterAccount,
    ):
        access_token = create_access_token(subject=str(test_user.id))
        with patch("app.api.v1.twitter.TwitterService") as MockTwitterService:
            mock_service = MagicMock()
            mock_service.get_account = AsyncMock(return_value=test_twitter_account)
            mock_service.get_account_status = AsyncMock(return_value={
                "account_id": str(test_twitter_account.id),
                "twitter_username": test_twitter_account.twitter_username,
                "is_active": True,
                "token_valid": True,
                "token_expires_at": None,
                "last_sync_at": None,
                "can_refresh": True,
            })
            MockTwitterService.return_value = mock_service

            response = await client.get(
                f"/api/v1/twitter/accounts/{test_twitter_account.id}/status",
                headers={"Authorization": f"Bearer {access_token}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["twitter_username"] == test_twitter_account.twitter_username

    @pytest.mark.asyncio
    async def test_get_account_status_not_found(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        access_token = create_access_token(subject=str(test_user.id))
        with patch("app.api.v1.twitter.TwitterService") as MockTwitterService:
            mock_service = MagicMock()
            mock_service.get_account = AsyncMock(return_value=None)
            MockTwitterService.return_value = mock_service

            response = await client.get(
                f"/api/v1/twitter/accounts/{uuid4()}/status",
                headers={"Authorization": f"Bearer {access_token}"},
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_account_status_unauthorized(self, client: AsyncClient):
        response = await client.get(f"/api/v1/twitter/accounts/{uuid4()}/status")
        assert response.status_code == 401
