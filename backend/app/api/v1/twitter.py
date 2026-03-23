from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import ActiveUser, DBSession
from app.core.exceptions import BadRequestException, NotFoundException
from app.models.twitter_account import TwitterAccount
from app.models.tweet import Tweet
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationParams
from app.schemas.twitter import (
    TwitterAccountResponse,
    TwitterOAuthCallback,
    TwitterAccountStatus,
    TweetResponse,
)
from app.services.twitter_service import TwitterService

router = APIRouter(prefix="/twitter", tags=["Twitter"])


@router.get("/oauth/authorize")
async def get_oauth_authorize_url(
    current_user: ActiveUser,
    db: DBSession,
) -> ApiResponse:
    twitter_service = TwitterService(db)
    oauth_data = twitter_service.initiate_oauth(user_id=current_user.id)

    return ApiResponse(
        message="请访问授权URL进行Twitter账号绑定",
        data=oauth_data,
    )


@router.post("/oauth/callback", response_model=ApiResponse[TwitterAccountResponse])
async def oauth_callback(
    callback: TwitterOAuthCallback,
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[TwitterAccountResponse]:
    twitter_service = TwitterService(db)
    account = await twitter_service.handle_oauth_callback(
        code=callback.code,
        state=callback.state,
        user_id=current_user.id,
    )

    return ApiResponse(
        message="Twitter 账号绑定成功",
        data=TwitterAccountResponse.model_validate(account),
    )


@router.post("/accounts", response_model=ApiResponse[TwitterAccountResponse])
async def bind_twitter_account(
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[TwitterAccountResponse]:
    twitter_service = TwitterService(db)
    oauth_data = twitter_service.initiate_oauth(user_id=current_user.id)

    return ApiResponse(
        message="请使用返回的授权URL完成绑定",
        data={"authorization_url": oauth_data["authorization_url"], "state": oauth_data["state"]},
    )


@router.get("/accounts", response_model=ApiResponse[PaginatedResponse[TwitterAccountResponse]])
async def list_accounts(
    db: DBSession,
    current_user: ActiveUser,
    pagination: PaginationParams = Depends(),
) -> ApiResponse[PaginatedResponse[TwitterAccountResponse]]:
    count_result = await db.execute(
        select(func.count()).where(TwitterAccount.user_id == current_user.id)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(TwitterAccount)
        .where(TwitterAccount.user_id == current_user.id)
        .order_by(TwitterAccount.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    )
    accounts = result.scalars().all()

    return ApiResponse(
        data=PaginatedResponse.create(
            items=[TwitterAccountResponse.model_validate(a) for a in accounts],
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )
    )


@router.get("/accounts/{account_id}", response_model=ApiResponse[TwitterAccountResponse])
async def get_account(
    account_id: str,
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[TwitterAccountResponse]:
    from uuid import UUID

    twitter_service = TwitterService(db)
    account = await twitter_service.get_account(
        account_id=UUID(account_id),
        user_id=current_user.id,
    )

    if not account:
        raise NotFoundException(message="Twitter 账号不存在")

    return ApiResponse(
        data=TwitterAccountResponse.model_validate(account),
    )


@router.delete("/accounts/{account_id}", response_model=ApiResponse[None])
async def delete_account(
    account_id: str,
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[None]:
    from uuid import UUID

    twitter_service = TwitterService(db)
    await twitter_service.unbind_account(
        account_id=UUID(account_id),
        user_id=current_user.id,
    )

    return ApiResponse(message="Twitter 账号已解绑")


@router.get("/accounts/{account_id}/status", response_model=ApiResponse[TwitterAccountStatus])
async def get_account_status(
    account_id: str,
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[TwitterAccountStatus]:
    from uuid import UUID

    twitter_service = TwitterService(db)
    account = await twitter_service.get_account(
        account_id=UUID(account_id),
        user_id=current_user.id,
    )

    if not account:
        raise NotFoundException(message="Twitter 账号不存在")

    status = await twitter_service.get_account_status(account)

    return ApiResponse(
        data=TwitterAccountStatus.model_validate(status),
    )


@router.post("/accounts/{account_id}/sync", response_model=ApiResponse[dict])
async def sync_account(
    account_id: str,
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[dict]:
    from uuid import UUID

    twitter_service = TwitterService(db)
    account = await twitter_service.get_account(
        account_id=UUID(account_id),
        user_id=current_user.id,
    )

    if not account:
        raise NotFoundException(message="Twitter 账号不存在")

    if not account.is_active:
        raise BadRequestException(message="Twitter 账号已失效，请重新绑定")

    sync_result = await twitter_service.sync_account_data(account)

    return ApiResponse(
        message="账号数据同步完成",
        data=sync_result,
    )


@router.post("/accounts/{account_id}/refresh-token", response_model=ApiResponse[TwitterAccountResponse])
async def refresh_account_token(
    account_id: str,
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[TwitterAccountResponse]:
    from uuid import UUID

    twitter_service = TwitterService(db)
    account = await twitter_service.get_account(
        account_id=UUID(account_id),
        user_id=current_user.id,
    )

    if not account:
        raise NotFoundException(message="Twitter 账号不存在")

    account = await twitter_service.refresh_token_if_needed(account)

    return ApiResponse(
        message="令牌刷新成功" if account.is_active else "令牌刷新失败，请重新绑定账号",
        data=TwitterAccountResponse.model_validate(account),
    )


@router.get("/bookmarks", response_model=ApiResponse[PaginatedResponse[TweetResponse]])
async def list_bookmarks(
    db: DBSession,
    current_user: ActiveUser,
    pagination: PaginationParams = Depends(),
) -> ApiResponse[PaginatedResponse[TweetResponse]]:
    count_result = await db.execute(
        select(func.count())
        .select_from(Tweet)
        .join(TwitterAccount)
        .where(
            TwitterAccount.user_id == current_user.id,
            Tweet.is_bookmarked == True,
        )
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Tweet)
        .options(selectinload(Tweet.twitter_user), selectinload(Tweet.media_files))
        .join(TwitterAccount)
        .where(
            TwitterAccount.user_id == current_user.id,
            Tweet.is_bookmarked == True,
        )
        .order_by(Tweet.published_at.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    )
    tweets = result.scalars().all()

    return ApiResponse(
        data=PaginatedResponse.create(
            items=[TweetResponse.model_validate(t) for t in tweets],
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )
    )


@router.get("/likes", response_model=ApiResponse[PaginatedResponse[TweetResponse]])
async def list_likes(
    db: DBSession,
    current_user: ActiveUser,
    pagination: PaginationParams = Depends(),
) -> ApiResponse[PaginatedResponse[TweetResponse]]:
    count_result = await db.execute(
        select(func.count())
        .select_from(Tweet)
        .join(TwitterAccount)
        .where(
            TwitterAccount.user_id == current_user.id,
            Tweet.is_liked_by_me == True,
        )
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Tweet)
        .options(selectinload(Tweet.twitter_user), selectinload(Tweet.media_files))
        .join(TwitterAccount)
        .where(
            TwitterAccount.user_id == current_user.id,
            Tweet.is_liked_by_me == True,
        )
        .order_by(Tweet.published_at.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    )
    tweets = result.scalars().all()

    return ApiResponse(
        data=PaginatedResponse.create(
            items=[TweetResponse.model_validate(t) for t in tweets],
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )
    )
