from datetime import timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictException, UnauthorizedException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserResponse


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_user(self, user_in: UserCreate) -> User:
        result = await self.db.execute(
            select(User).where(User.username == user_in.username)
        )
        if result.scalar_one_or_none():
            raise ConflictException(message="用户名已存在")

        result = await self.db.execute(
            select(User).where(User.email == user_in.email)
        )
        if result.scalar_one_or_none():
            raise ConflictException(message="邮箱已被注册")

        user = User(
            username=user_in.username,
            email=user_in.email,
            hashed_password=get_password_hash(user_in.password),
            is_active=True,
            is_superuser=False,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)

        return user

    async def authenticate_user(self, username: str, password: str) -> User:
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.hashed_password):
            raise UnauthorizedException(message="用户名或密码错误")

        if not user.is_active:
            raise UnauthorizedException(message="用户账户已被禁用")

        return user

    def create_tokens(self, user_id: UUID | str) -> Token:
        user_id_str = str(user_id)

        access_token = create_access_token(subject=user_id_str)
        refresh_token = create_refresh_token(subject=user_id_str)

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh_tokens(self, refresh_token: str) -> Token:
        payload = verify_token(refresh_token, token_type="refresh")
        if payload is None:
            raise UnauthorizedException(message="无效的刷新令牌")

        user_id = payload.get("sub")
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise UnauthorizedException(message="用户不存在")

        if not user.is_active:
            raise UnauthorizedException(message="用户账户已被禁用")

        return self.create_tokens(user.id)

    async def get_user_by_id(self, user_id: UUID | str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def update_user_password(
        self,
        user_id: UUID | str,
        new_password: str
    ) -> User:
        user = await self.get_user_by_id(user_id)
        if not user:
            raise UnauthorizedException(message="用户不存在")

        user.hashed_password = get_password_hash(new_password)
        await self.db.flush()
        await self.db.refresh(user)

        return user

    async def deactivate_user(self, user_id: UUID | str) -> User:
        user = await self.get_user_by_id(user_id)
        if not user:
            raise UnauthorizedException(message="用户不存在")

        user.is_active = False
        await self.db.flush()
        await self.db.refresh(user)

        return user

    async def activate_user(self, user_id: UUID | str) -> User:
        user = await self.get_user_by_id(user_id)
        if not user:
            raise UnauthorizedException(message="用户不存在")

        user.is_active = True
        await self.db.flush()
        await self.db.refresh(user)

        return user
