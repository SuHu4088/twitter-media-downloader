import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, create_refresh_token, get_password_hash
from app.models.user import User


class TestRegisterUser:
    @pytest.mark.asyncio
    async def test_register_user_success(self, client: AsyncClient, db_session):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "newpassword123",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "注册成功"
        assert data["data"]["username"] == "newuser"
        assert data["data"]["email"] == "newuser@example.com"
        assert data["data"]["is_active"] is True
        assert "id" in data["data"]

    @pytest.mark.asyncio
    async def test_register_user_duplicate_username(self, client: AsyncClient, test_user: User):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": test_user.username,
                "email": "another@example.com",
                "password": "newpassword123",
            },
        )
        assert response.status_code == 409
        data = response.json()
        assert data["success"] is False
        assert "用户名已存在" in data["message"]

    @pytest.mark.asyncio
    async def test_register_user_duplicate_email(self, client: AsyncClient, test_user: User):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "anotheruser",
                "email": test_user.email,
                "password": "newpassword123",
            },
        )
        assert response.status_code == 409
        data = response.json()
        assert data["success"] is False
        assert "邮箱已被注册" in data["message"]

    @pytest.mark.asyncio
    async def test_register_user_invalid_username(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "ab",
                "email": "test@example.com",
                "password": "newpassword123",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_user_invalid_email(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "validuser",
                "email": "invalid-email",
                "password": "newpassword123",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_user_short_password(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "validuser",
                "email": "valid@example.com",
                "password": "short",
            },
        )
        assert response.status_code == 422


class TestLoginUser:
    @pytest.mark.asyncio
    async def test_login_user_success(self, client: AsyncClient, test_user: User):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user.username,
                "password": "testpassword123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "登录成功"
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"
        assert "expires_in" in data["data"]

    @pytest.mark.asyncio
    async def test_login_user_wrong_password(self, client: AsyncClient, test_user: User):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_user.username,
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert "用户名或密码错误" in data["message"]

    @pytest.mark.asyncio
    async def test_login_user_nonexistent_user(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "nonexistent",
                "password": "anypassword",
            },
        )
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert "用户名或密码错误" in data["message"]

    @pytest.mark.asyncio
    async def test_login_user_inactive_user(self, client: AsyncClient, inactive_user: User):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": inactive_user.username,
                "password": "testpassword123",
            },
        )
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert "用户账户已被禁用" in data["message"]


class TestRefreshToken:
    @pytest.mark.asyncio
    async def test_refresh_token_success(self, client: AsyncClient, test_user: User):
        refresh_token = create_refresh_token(subject=str(test_user.id))
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "令牌刷新成功"
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]

    @pytest.mark.asyncio
    async def test_refresh_token_invalid_token(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_token"},
        )
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert "无效的刷新令牌" in data["message"]

    @pytest.mark.asyncio
    async def test_refresh_token_with_access_token(self, client: AsyncClient, test_user: User):
        access_token = create_access_token(subject=str(test_user.id))
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token},
        )
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert "无效的刷新令牌" in data["message"]

    @pytest.mark.asyncio
    async def test_refresh_token_inactive_user(self, client: AsyncClient, inactive_user: User):
        refresh_token = create_refresh_token(subject=str(inactive_user.id))
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert "用户账户已被禁用" in data["message"]


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_get_current_user_success(self, client: AsyncClient, test_user: User):
        access_token = create_access_token(subject=str(test_user.id))
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["username"] == test_user.username
        assert data["data"]["email"] == test_user.email
        assert data["data"]["is_active"] is True

    @pytest.mark.asyncio
    async def test_get_current_user_no_token(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_get_current_user_inactive_user(self, client: AsyncClient, inactive_user: User):
        access_token = create_access_token(subject=str(inactive_user.id))
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert "用户账户已被禁用" in data["message"]


class TestUnauthorizedAccess:
    @pytest.mark.asyncio
    async def test_access_protected_route_without_token(self, client: AsyncClient):
        response = await client.get("/api/v1/twitter/accounts")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_access_protected_route_with_invalid_token(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/twitter/accounts",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_access_protected_route_with_expired_token(self, client: AsyncClient):
        from datetime import datetime, timedelta, timezone

        from jose import jwt

        expired_payload = {
            "sub": "some-user-id",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        expired_token = jwt.encode(
            expired_payload,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
        )
        response = await client.get(
            "/api/v1/twitter/accounts",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401


from app.core.config import settings
