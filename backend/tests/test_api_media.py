from datetime import datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.media_file import MediaFile
from app.models.tweet import Tweet
from app.models.twitter_account import TwitterAccount
from app.models.twitter_user import TwitterUser
from app.models.user import User


class TestGetMediaList:
    @pytest.mark.asyncio
    async def test_get_media_list_success(
        self,
        client: AsyncClient,
        test_user: User,
        test_media_file: MediaFile,
    ):
        access_token = create_access_token(subject=str(test_user.id))
        response = await client.get(
            "/api/v1/media",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "items" in data["data"]
        assert "total" in data["data"]
        assert data["data"]["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_media_list_empty(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        new_user = User(
            id=uuid4(),
            username="user_no_media",
            email="no_media@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        db_session.add(new_user)
        await db_session.commit()

        access_token = create_access_token(subject=str(new_user.id))
        response = await client.get(
            "/api/v1/media",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 0
        assert len(data["data"]["items"]) == 0

    @pytest.mark.asyncio
    async def test_get_media_list_pagination(
        self,
        client: AsyncClient,
        test_user: User,
        test_media_file: MediaFile,
    ):
        access_token = create_access_token(subject=str(test_user.id))
        response = await client.get(
            "/api/v1/media?page=1&page_size=10",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["page"] == 1
        assert data["data"]["page_size"] == 10

    @pytest.mark.asyncio
    async def test_get_media_list_unauthorized(self, client: AsyncClient):
        response = await client.get("/api/v1/media")
        assert response.status_code == 401


class TestGetMediaDetail:
    @pytest.mark.asyncio
    async def test_get_media_detail_success(
        self,
        client: AsyncClient,
        test_user: User,
        test_media_file: MediaFile,
    ):
        access_token = create_access_token(subject=str(test_user.id))
        response = await client.get(
            f"/api/v1/media/{test_media_file.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == str(test_media_file.id)
        assert data["data"]["media_type"] == test_media_file.media_type
        assert data["data"]["url"] == test_media_file.url

    @pytest.mark.asyncio
    async def test_get_media_detail_not_found(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        access_token = create_access_token(subject=str(test_user.id))
        response = await client.get(
            f"/api/v1/media/{uuid4()}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "不存在" in data["message"]

    @pytest.mark.asyncio
    async def test_get_media_detail_unauthorized(self, client: AsyncClient):
        response = await client.get(f"/api/v1/media/{uuid4()}")
        assert response.status_code == 401


class TestFilterMedia:
    @pytest.mark.asyncio
    async def test_filter_media_by_type(
        self,
        client: AsyncClient,
        test_user: User,
        test_media_file: MediaFile,
    ):
        access_token = create_access_token(subject=str(test_user.id))
        response = await client.get(
            "/api/v1/media?media_type=photo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        for item in data["data"]["items"]:
            assert item["media_type"] == "photo"

    @pytest.mark.asyncio
    async def test_filter_media_by_download_status(
        self,
        client: AsyncClient,
        test_user: User,
        test_media_file: MediaFile,
    ):
        access_token = create_access_token(subject=str(test_user.id))
        response = await client.get(
            "/api/v1/media?download_status=pending",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        for item in data["data"]["items"]:
            assert item["is_downloaded"] is False

    @pytest.mark.asyncio
    async def test_filter_media_by_date_range(
        self,
        client: AsyncClient,
        test_user: User,
        test_media_file: MediaFile,
    ):
        access_token = create_access_token(subject=str(test_user.id))
        start_date = datetime(2020, 1, 1).isoformat()
        end_date = datetime(2030, 12, 31).isoformat()
        response = await client.get(
            f"/api/v1/media?start_date={start_date}&end_date={end_date}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_filter_media_combined(
        self,
        client: AsyncClient,
        test_user: User,
        test_media_file: MediaFile,
    ):
        access_token = create_access_token(subject=str(test_user.id))
        response = await client.get(
            "/api/v1/media?media_type=photo&download_status=pending&page=1&page_size=20",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestDeleteMedia:
    @pytest.mark.asyncio
    async def test_delete_media_success(
        self,
        client: AsyncClient,
        test_user: User,
        test_media_file: MediaFile,
        db_session: AsyncSession,
    ):
        access_token = create_access_token(subject=str(test_user.id))
        response = await client.delete(
            f"/api/v1/media/{test_media_file.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "已删除" in data["message"]

    @pytest.mark.asyncio
    async def test_delete_media_not_found(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        access_token = create_access_token(subject=str(test_user.id))
        response = await client.delete(
            f"/api/v1/media/{uuid4()}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "不存在" in data["message"]

    @pytest.mark.asyncio
    async def test_delete_media_unauthorized(self, client: AsyncClient):
        response = await client.delete(f"/api/v1/media/{uuid4()}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_media_other_user(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_media_file: MediaFile,
    ):
        other_user = User(
            id=uuid4(),
            username="other_user",
            email="other@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        db_session.add(other_user)
        await db_session.commit()

        access_token = create_access_token(subject=str(other_user.id))
        response = await client.delete(
            f"/api/v1/media/{test_media_file.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 404
