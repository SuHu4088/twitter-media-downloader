import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException, TwitterAPIException
from app.core.security import decrypt_token, encrypt_token
from app.models.twitter_account import TwitterAccount
from app.models.user import User
from app.services.twitter_client import TwitterClient


class TwitterService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._oauth_states: dict[str, dict[str, str]] = {}
        self._client: TwitterClient | None = None

    @property
    def client(self) -> TwitterClient:
        if self._client is None:
            self._client = TwitterClient()
        return self._client

    async def _ensure_client_started(self) -> None:
        if self._client is None:
            self._client = TwitterClient()
        if self._client._client is None:
            await self._client.start()

    def initiate_oauth(
        self,
        user_id: UUID | str,
        scope: str = "tweet.read users.read bookmark.read like.read offline.access",
    ) -> dict[str, str]:
        state = secrets.token_urlsafe(32)
        code_verifier = secrets.token_urlsafe(64)[:128]

        self._oauth_states[state] = {
            "user_id": str(user_id),
            "code_verifier": code_verifier,
        }

        auth_url, _ = self.client.get_authorization_url(
            state=state,
            code_verifier=code_verifier,
            scope=scope,
        )

        return {
            "authorization_url": auth_url,
            "state": state,
        }

    def validate_oauth_state(self, state: str) -> dict[str, str] | None:
        return self._oauth_states.pop(state, None)

    async def handle_oauth_callback(
        self,
        code: str,
        state: str,
        user_id: UUID | str,
    ) -> TwitterAccount:
        state_data = self.validate_oauth_state(state)
        if not state_data:
            raise BadRequestException(message="无效的 OAuth 状态")

        if state_data["user_id"] != str(user_id):
            raise BadRequestException(message="OAuth 状态不匹配")

        code_verifier = state_data["code_verifier"]

        await self._ensure_client_started()

        try:
            token_data = await self.client.exchange_code(code, code_verifier)
        except Exception as e:
            raise TwitterAPIException(
                message="获取 Twitter 令牌失败",
                details=str(e),
            )

        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 7200)

        if not access_token:
            raise TwitterAPIException(message="未获取到访问令牌")

        try:
            user_info = await self.client.get_user_info(access_token)
        except Exception as e:
            raise TwitterAPIException(
                message="获取 Twitter 用户信息失败",
                details=str(e),
            )

        twitter_user_id = user_info.get("id")
        twitter_username = user_info.get("username")

        if not twitter_user_id or not twitter_username:
            raise TwitterAPIException(message="获取 Twitter 用户信息不完整")

        return await self.bind_account(
            user_id=user_id,
            twitter_user_id=twitter_user_id,
            twitter_username=twitter_username,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
        )

    async def bind_account(
        self,
        user_id: UUID | str,
        twitter_user_id: str,
        twitter_username: str,
        access_token: str,
        refresh_token: str | None = None,
        expires_in: int = 7200,
    ) -> TwitterAccount:
        result = await self.db.execute(
            select(TwitterAccount).where(
                TwitterAccount.twitter_user_id == twitter_user_id
            )
        )
        existing_account = result.scalar_one_or_none()

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        if existing_account:
            if str(existing_account.user_id) != str(user_id):
                raise BadRequestException(
                    message="该 Twitter 账号已被其他用户绑定"
                )

            existing_account.access_token = encrypt_token(access_token)
            if refresh_token:
                existing_account.refresh_token = encrypt_token(refresh_token)
            existing_account.token_expires_at = expires_at
            existing_account.twitter_username = twitter_username
            existing_account.is_active = True
            await self.db.flush()
            await self.db.refresh(existing_account)
            return existing_account

        account = TwitterAccount(
            user_id=user_id if isinstance(user_id, UUID) else UUID(user_id),
            twitter_user_id=twitter_user_id,
            twitter_username=twitter_username,
            access_token=encrypt_token(access_token),
            refresh_token=encrypt_token(refresh_token) if refresh_token else None,
            token_expires_at=expires_at,
            is_active=True,
        )
        self.db.add(account)
        await self.db.flush()
        await self.db.refresh(account)

        return account

    async def unbind_account(
        self,
        account_id: UUID | str,
        user_id: UUID | str,
    ) -> bool:
        result = await self.db.execute(
            select(TwitterAccount).where(
                TwitterAccount.id == account_id if isinstance(account_id, UUID) else TwitterAccount.id == UUID(account_id),
                TwitterAccount.user_id == user_id if isinstance(user_id, UUID) else TwitterAccount.user_id == UUID(user_id),
            )
        )
        account = result.scalar_one_or_none()

        if not account:
            raise NotFoundException(message="Twitter 账号不存在")

        await self.db.delete(account)
        return True

    async def get_accounts(
        self,
        user_id: UUID | str,
        active_only: bool = False,
    ) -> list[TwitterAccount]:
        query = select(TwitterAccount).where(
            TwitterAccount.user_id == user_id if isinstance(user_id, UUID) else TwitterAccount.user_id == UUID(user_id)
        )

        if active_only:
            query = query.where(TwitterAccount.is_active == True)

        query = query.order_by(TwitterAccount.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_account(
        self,
        account_id: UUID | str,
        user_id: UUID | str,
    ) -> TwitterAccount | None:
        result = await self.db.execute(
            select(TwitterAccount).where(
                TwitterAccount.id == account_id if isinstance(account_id, UUID) else TwitterAccount.id == UUID(account_id),
                TwitterAccount.user_id == user_id if isinstance(user_id, UUID) else TwitterAccount.user_id == UUID(user_id),
            )
        )
        return result.scalar_one_or_none()

    async def refresh_token_if_needed(
        self,
        account: TwitterAccount,
        buffer_seconds: int = 300,
    ) -> TwitterAccount:
        if not account.token_expires_at:
            return account

        now = datetime.now(timezone.utc)
        expires_at = account.token_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if now + timedelta(seconds=buffer_seconds) < expires_at:
            return account

        if not account.refresh_token:
            account.is_active = False
            await self.db.flush()
            await self.db.refresh(account)
            return account

        await self._ensure_client_started()

        try:
            decrypted_refresh_token = decrypt_token(account.refresh_token)
            token_data = await self.client.refresh_access_token(decrypted_refresh_token)

            new_access_token = token_data.get("access_token")
            new_refresh_token = token_data.get("refresh_token")
            expires_in = token_data.get("expires_in", 7200)

            if not new_access_token:
                raise TwitterAPIException(message="刷新令牌失败")

            account.access_token = encrypt_token(new_access_token)
            if new_refresh_token:
                account.refresh_token = encrypt_token(new_refresh_token)
            account.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            account.is_active = True

            await self.db.flush()
            await self.db.refresh(account)

            return account

        except Exception:
            account.is_active = False
            await self.db.flush()
            await self.db.refresh(account)
            return account

    async def get_account_status(
        self,
        account: TwitterAccount,
    ) -> dict[str, Any]:
        status = {
            "account_id": str(account.id),
            "twitter_username": account.twitter_username,
            "is_active": account.is_active,
            "token_valid": False,
            "token_expires_at": account.token_expires_at,
            "last_sync_at": account.last_sync_at,
            "can_refresh": bool(account.refresh_token),
        }

        if not account.is_active:
            return status

        try:
            account = await self.refresh_token_if_needed(account)
            decrypted_access_token = decrypt_token(account.access_token)

            await self._ensure_client_started()
            user_info = await self.client.get_user_info(decrypted_access_token)

            status["token_valid"] = True
            status["twitter_user_info"] = {
                "id": user_info.get("id"),
                "name": user_info.get("name"),
                "username": user_info.get("username"),
                "profile_image_url": user_info.get("profile_image_url"),
            }

        except Exception as e:
            status["error"] = str(e)

        return status

    async def get_decrypted_access_token(
        self,
        account: TwitterAccount,
    ) -> str:
        account = await self.refresh_token_if_needed(account)

        if not account.is_active:
            raise BadRequestException(message="Twitter 账号已失效，请重新绑定")

        return decrypt_token(account.access_token)

    async def sync_account_data(
        self,
        account: TwitterAccount,
    ) -> dict[str, Any]:
        access_token = await self.get_decrypted_access_token(account)

        await self._ensure_client_started()

        sync_result = {
            "account_id": str(account.id),
            "synced_at": datetime.now(timezone.utc),
            "bookmarks_count": 0,
            "likes_count": 0,
            "errors": [],
        }

        try:
            bookmarks = await self.client.get_bookmarks(
                access_token,
                account.twitter_user_id,
                max_results=100,
            )
            sync_result["bookmarks_count"] = len(bookmarks.get("data", []))
        except Exception as e:
            sync_result["errors"].append(f"同步书签失败: {str(e)}")

        try:
            likes = await self.client.get_likes(
                access_token,
                account.twitter_user_id,
                max_results=100,
            )
            sync_result["likes_count"] = len(likes.get("data", []))
        except Exception as e:
            sync_result["errors"].append(f"同步点赞失败: {str(e)}")

        account.last_sync_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(account)

        return sync_result

    async def update_last_sync(
        self,
        account: TwitterAccount,
    ) -> TwitterAccount:
        account.last_sync_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(account)
        return account

    async def deactivate_account(
        self,
        account: TwitterAccount,
    ) -> TwitterAccount:
        account.is_active = False
        await self.db.flush()
        await self.db.refresh(account)
        return account

    async def activate_account(
        self,
        account: TwitterAccount,
    ) -> TwitterAccount:
        account.is_active = True
        await self.db.flush()
        await self.db.refresh(account)
        return account
