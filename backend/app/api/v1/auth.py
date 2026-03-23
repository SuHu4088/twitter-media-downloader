from datetime import timedelta

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ActiveUser, DBSession, get_current_user
from app.core.config import settings
from app.core.exceptions import BadRequestException, ConflictException, UnauthorizedException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.user import (
    RefreshTokenRequest,
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=ApiResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: DBSession) -> ApiResponse[UserResponse]:
    result = await db.execute(select(User).where(User.username == user_in.username))
    if result.scalar_one_or_none():
        raise ConflictException(message="用户名已存在")

    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none():
        raise ConflictException(message="邮箱已被注册")

    user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    return ApiResponse(
        message="注册成功",
        data=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=ApiResponse[Token])
async def login(user_in: UserLogin, db: DBSession) -> ApiResponse[Token]:
    result = await db.execute(select(User).where(User.username == user_in.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(user_in.password, user.hashed_password):
        raise UnauthorizedException(message="用户名或密码错误")

    if not user.is_active:
        raise UnauthorizedException(message="用户账户已被禁用")

    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    return ApiResponse(
        message="登录成功",
        data=Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        ),
    )


@router.post("/refresh", response_model=ApiResponse[Token])
async def refresh_token(
    token_in: RefreshTokenRequest,
    db: DBSession,
) -> ApiResponse[Token]:
    payload = verify_token(token_in.refresh_token, token_type="refresh")
    if payload is None:
        raise UnauthorizedException(message="无效的刷新令牌")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise UnauthorizedException(message="用户不存在")

    if not user.is_active:
        raise UnauthorizedException(message="用户账户已被禁用")

    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    return ApiResponse(
        message="令牌刷新成功",
        data=Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        ),
    )


@router.get("/me", response_model=ApiResponse[UserResponse])
async def get_current_user_info(current_user: ActiveUser) -> ApiResponse[UserResponse]:
    return ApiResponse(
        data=UserResponse.model_validate(current_user),
    )
