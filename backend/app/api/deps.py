from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db as _get_db
from app.core.exceptions import UnauthorizedException
from app.core.security import verify_token
from app.models.user import User

security = HTTPBearer()


async def get_db() -> AsyncSession:
    async for session in _get_db():
        yield session


DBSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DBSession,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> User:
    token = credentials.credentials
    payload = verify_token(token)

    if payload is None:
        raise UnauthorizedException(message="无效的认证令牌")

    user_id = payload.get("sub")
    if user_id is None:
        raise UnauthorizedException(message="无效的认证令牌")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise UnauthorizedException(message="用户不存在")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_active_user(current_user: CurrentUser) -> User:
    if not current_user.is_active:
        raise UnauthorizedException(message="用户账户已被禁用")
    return current_user


ActiveUser = Annotated[User, Depends(get_current_active_user)]
