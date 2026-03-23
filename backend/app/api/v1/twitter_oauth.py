from fastapi import APIRouter, Request, status
from fastapi.responses import RedirectResponse

from app.api.deps import ActiveUser, DBSession
from app.core.config import settings
from app.core.exceptions import BadRequestException
from app.schemas.common import ApiResponse
from app.schemas.twitter import TwitterAccountResponse, TwitterOAuthCallback
from app.services.twitter_service import TwitterService
from app.services.twitter_client import TwitterClient

router = APIRouter(prefix="/twitter/oauth", tags=["Twitter OAuth"])


@router.get("/authorize")
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


@router.get("/callback")
async def oauth_callback_redirect(
    request: Request,
    code: str,
    state: str,
    db: DBSession,
) -> RedirectResponse:
    twitter_service = TwitterService(db)

    state_data = twitter_service.validate_oauth_state(state)
    if not state_data:
        frontend_url = settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "http://localhost:5173"
        return RedirectResponse(
            url=f"{frontend_url}/twitter/bind?error=invalid_state",
            status_code=302,
        )

    user_id = state_data.get("user_id")
    code_verifier = state_data.get("code_verifier")

    if not user_id or not code_verifier:
        frontend_url = settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "http://localhost:5173"
        return RedirectResponse(
            url=f"{frontend_url}/twitter/bind?error=missing_state_data",
            status_code=302,
        )

    try:
        twitter_client = TwitterClient()
        await twitter_client.start()

        token_data = await twitter_client.exchange_code(code, code_verifier)

        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 7200)

        if not access_token:
            raise Exception("未获取到访问令牌")

        user_info = await twitter_client.get_user_info(access_token)

        twitter_user_id = user_info.get("id")
        twitter_username = user_info.get("username")

        if not twitter_user_id or not twitter_username:
            raise Exception("获取 Twitter 用户信息不完整")

        account = await twitter_service.bind_account(
            user_id=user_id,
            twitter_user_id=twitter_user_id,
            twitter_username=twitter_username,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
        )

        frontend_url = settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "http://localhost:5173"
        return RedirectResponse(
            url=f"{frontend_url}/twitter/bind?success=true&username={account.twitter_username}",
            status_code=302,
        )

    except Exception as e:
        frontend_url = settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "http://localhost:5173"
        return RedirectResponse(
            url=f"{frontend_url}/twitter/bind?error={str(e)}",
            status_code=302,
        )


@router.post("/callback", response_model=ApiResponse[TwitterAccountResponse])
async def oauth_callback_api(
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


@router.get("/error")
async def oauth_error(
    error: str,
    error_description: str | None = None,
) -> ApiResponse:
    error_messages = {
        "access_denied": "用户拒绝授权",
        "invalid_request": "请求参数错误",
        "unauthorized_client": "客户端未授权",
        "unsupported_response_type": "不支持的响应类型",
        "invalid_scope": "无效的权限范围",
        "server_error": "服务器错误",
        "temporarily_unavailable": "服务暂时不可用",
    }

    message = error_messages.get(error, error_description or "OAuth授权失败")

    return ApiResponse(
        success=False,
        message=message,
        data={"error": error, "error_description": error_description},
    )
