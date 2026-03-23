from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.download_task import DownloadTask
from app.models.twitter_account import TwitterAccount
from app.models.user import User


class TestCreateTask:
    @pytest.mark.asyncio
    async def test_create_task_success(
        self,
        client: AsyncClient,
        test_user: User,
        test_twitter_account: TwitterAccount,
    ):
        access_token = create_access_token(subject=str(test_user.id))
        with patch("app.api.v1.tasks.celery_app") as mock_celery:
            mock_celery.send_task = MagicMock()

            response = await client.post(
                "/api/v1/tasks",
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "twitter_account_id": str(test_twitter_account.id),
                    "task_type": "bookmarks",
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "下载任务已创建"
        assert data["data"]["task_type"] == "bookmarks"
        assert data["data"]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_create_task_invalid_account(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        access_token = create_access_token(subject=str(test_user.id))
        response = await client.post(
            "/api/v1/tasks",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "twitter_account_id": str(uuid4()),
                "task_type": "bookmarks",
            },
        )
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "不存在" in data["message"]

    @pytest.mark.asyncio
    async def test_create_task_inactive_account(
        self,
        client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ):
        inactive_account = TwitterAccount(
            id=uuid4(),
            user_id=test_user.id,
            twitter_user_id="inactive_twitter",
            twitter_username="inactive_user",
            access_token="token",
            is_active=False,
        )
        db_session.add(inactive_account)
        await db_session.commit()

        access_token = create_access_token(subject=str(test_user.id))
        response = await client.post(
            "/api/v1/tasks",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "twitter_account_id": str(inactive_account.id),
                "task_type": "bookmarks",
            },
        )
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "未激活" in data["message"]

    @pytest.mark.asyncio
    async def test_create_task_invalid_type(
        self,
        client: AsyncClient,
        test_user: User,
        test_twitter_account: TwitterAccount,
    ):
        access_token = create_access_token(subject=str(test_user.id))
        response = await client.post(
            "/api/v1/tasks",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "twitter_account_id": str(test_twitter_account.id),
                "task_type": "invalid_type",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_task_unauthorized(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/tasks",
            json={
                "twitter_account_id": str(uuid4()),
                "task_type": "bookmarks",
            },
        )
        assert response.status_code == 401


class TestGetTaskList:
    @pytest.mark.asyncio
    async def test_get_task_list_success(
        self,
        client: AsyncClient,
        test_user: User,
        test_download_task: DownloadTask,
    ):
        access_token = create_access_token(subject=str(test_user.id))
        response = await client.get(
            "/api/v1/tasks",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "items" in data["data"]
        assert "total" in data["data"]
        assert data["data"]["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_task_list_empty(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        new_user = User(
            id=uuid4(),
            username="user_no_tasks",
            email="no_tasks@example.com",
            hashed_password="hashed",
            is_active=True,
        )
        db_session.add(new_user)
        await db_session.commit()

        access_token = create_access_token(subject=str(new_user.id))
        response = await client.get(
            "/api/v1/tasks",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] == 0
        assert len(data["data"]["items"]) == 0

    @pytest.mark.asyncio
    async def test_get_task_list_filter_by_status(
        self,
        client: AsyncClient,
        test_user: User,
        test_download_task: DownloadTask,
    ):
        access_token = create_access_token(subject=str(test_user.id))
        response = await client.get(
            "/api/v1/tasks?status=pending",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        for item in data["data"]["items"]:
            assert item["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_task_list_filter_by_type(
        self,
        client: AsyncClient,
        test_user: User,
        test_download_task: DownloadTask,
    ):
        access_token = create_access_token(subject=str(test_user.id))
        response = await client.get(
            "/api/v1/tasks?task_type=bookmarks",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        for item in data["data"]["items"]:
            assert item["task_type"] == "bookmarks"

    @pytest.mark.asyncio
    async def test_get_task_list_pagination(
        self,
        client: AsyncClient,
        test_user: User,
        test_download_task: DownloadTask,
    ):
        access_token = create_access_token(subject=str(test_user.id))
        response = await client.get(
            "/api/v1/tasks?page=1&page_size=10",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["page"] == 1
        assert data["data"]["page_size"] == 10

    @pytest.mark.asyncio
    async def test_get_task_list_unauthorized(self, client: AsyncClient):
        response = await client.get("/api/v1/tasks")
        assert response.status_code == 401


class TestGetTaskDetail:
    @pytest.mark.asyncio
    async def test_get_task_detail_success(
        self,
        client: AsyncClient,
        test_user: User,
        test_download_task: DownloadTask,
    ):
        access_token = create_access_token(subject=str(test_user.id))
        response = await client.get(
            f"/api/v1/tasks/{test_download_task.id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == str(test_download_task.id)
        assert data["data"]["task_type"] == test_download_task.task_type

    @pytest.mark.asyncio
    async def test_get_task_detail_not_found(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        access_token = create_access_token(subject=str(test_user.id))
        response = await client.get(
            f"/api/v1/tasks/{uuid4()}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "不存在" in data["message"]

    @pytest.mark.asyncio
    async def test_get_task_detail_unauthorized(self, client: AsyncClient):
        response = await client.get(f"/api/v1/tasks/{uuid4()}")
        assert response.status_code == 401


class TestCancelTask:
    @pytest.mark.asyncio
    async def test_cancel_task_success(
        self,
        client: AsyncClient,
        test_user: User,
        test_download_task: DownloadTask,
        db_session: AsyncSession,
    ):
        access_token = create_access_token(subject=str(test_user.id))
        response = await client.post(
            f"/api/v1/tasks/{test_download_task.id}/cancel",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "已取消" in data["message"]
        assert data["data"]["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_task_not_found(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        access_token = create_access_token(subject=str(test_user.id))
        response = await client.post(
            f"/api/v1/tasks/{uuid4()}/cancel",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_task_already_completed(
        self,
        client: AsyncClient,
        test_user: User,
        test_download_task: DownloadTask,
        db_session: AsyncSession,
    ):
        test_download_task.status = "completed"
        await db_session.commit()
        await db_session.refresh(test_download_task)

        access_token = create_access_token(subject=str(test_user.id))
        response = await client.post(
            f"/api/v1/tasks/{test_download_task.id}/cancel",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "无法取消" in data["message"]

    @pytest.mark.asyncio
    async def test_cancel_task_unauthorized(self, client: AsyncClient):
        response = await client.post(f"/api/v1/tasks/{uuid4()}/cancel")
        assert response.status_code == 401


class TestRetryTask:
    @pytest.mark.asyncio
    async def test_retry_task_success(
        self,
        client: AsyncClient,
        test_user: User,
        test_download_task: DownloadTask,
        db_session: AsyncSession,
    ):
        test_download_task.status = "failed"
        await db_session.commit()
        await db_session.refresh(test_download_task)

        access_token = create_access_token(subject=str(test_user.id))
        with patch("app.api.v1.tasks.celery_app") as mock_celery:
            mock_celery.send_task = MagicMock()

            response = await client.post(
                f"/api/v1/tasks/{test_download_task.id}/retry",
                headers={"Authorization": f"Bearer {access_token}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "重新启动" in data["message"]
        assert data["data"]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_retry_task_not_found(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        access_token = create_access_token(subject=str(test_user.id))
        response = await client.post(
            f"/api/v1/tasks/{uuid4()}/retry",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_retry_task_invalid_status(
        self,
        client: AsyncClient,
        test_user: User,
        test_download_task: DownloadTask,
    ):
        access_token = create_access_token(subject=str(test_user.id))
        response = await client.post(
            f"/api/v1/tasks/{test_download_task.id}/retry",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "可以重试" in data["message"]

    @pytest.mark.asyncio
    async def test_retry_task_unauthorized(self, client: AsyncClient):
        response = await client.post(f"/api/v1/tasks/{uuid4()}/retry")
        assert response.status_code == 401
