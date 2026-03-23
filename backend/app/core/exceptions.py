from typing import Any


class AppException(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str | None = None,
        details: Any | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details
        super().__init__(self.message)


class NotFoundException(AppException):
    def __init__(
        self,
        message: str = "资源不存在",
        error_code: str | None = None,
        details: Any | None = None,
    ):
        super().__init__(
            message=message,
            status_code=404,
            error_code=error_code or "NOT_FOUND",
            details=details,
        )


class UnauthorizedException(AppException):
    def __init__(
        self,
        message: str = "未授权访问",
        error_code: str | None = None,
        details: Any | None = None,
    ):
        super().__init__(
            message=message,
            status_code=401,
            error_code=error_code or "UNAUTHORIZED",
            details=details,
        )


class ForbiddenException(AppException):
    def __init__(
        self,
        message: str = "禁止访问",
        error_code: str | None = None,
        details: Any | None = None,
    ):
        super().__init__(
            message=message,
            status_code=403,
            error_code=error_code or "FORBIDDEN",
            details=details,
        )


class BadRequestException(AppException):
    def __init__(
        self,
        message: str = "请求参数错误",
        error_code: str | None = None,
        details: Any | None = None,
    ):
        super().__init__(
            message=message,
            status_code=400,
            error_code=error_code or "BAD_REQUEST",
            details=details,
        )


class ConflictException(AppException):
    def __init__(
        self,
        message: str = "资源冲突",
        error_code: str | None = None,
        details: Any | None = None,
    ):
        super().__init__(
            message=message,
            status_code=409,
            error_code=error_code or "CONFLICT",
            details=details,
        )


class ValidationException(AppException):
    def __init__(
        self,
        message: str = "数据验证失败",
        error_code: str | None = None,
        details: Any | None = None,
    ):
        super().__init__(
            message=message,
            status_code=422,
            error_code=error_code or "VALIDATION_ERROR",
            details=details,
        )


class RateLimitException(AppException):
    def __init__(
        self,
        message: str = "请求过于频繁，请稍后再试",
        error_code: str | None = None,
        details: Any | None = None,
    ):
        super().__init__(
            message=message,
            status_code=429,
            error_code=error_code or "RATE_LIMIT_EXCEEDED",
            details=details,
        )


class TwitterAPIException(AppException):
    def __init__(
        self,
        message: str = "Twitter API 调用失败",
        error_code: str | None = None,
        details: Any | None = None,
    ):
        super().__init__(
            message=message,
            status_code=502,
            error_code=error_code or "TWITTER_API_ERROR",
            details=details,
        )


class TelegramAPIException(AppException):
    def __init__(
        self,
        message: str = "Telegram API 调用失败",
        error_code: str | None = None,
        details: Any | None = None,
    ):
        super().__init__(
            message=message,
            status_code=502,
            error_code=error_code or "TELEGRAM_API_ERROR",
            details=details,
        )


class DownloadException(AppException):
    def __init__(
        self,
        message: str = "下载任务失败",
        error_code: str | None = None,
        details: Any | None = None,
    ):
        super().__init__(
            message=message,
            status_code=500,
            error_code=error_code or "DOWNLOAD_ERROR",
            details=details,
        )
