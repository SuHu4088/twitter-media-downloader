import time
import uuid
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.exceptions import AppException
from app.schemas.common import ErrorResponse


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except AppException as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content=ErrorResponse(
                    message=exc.message,
                    error_code=exc.error_code,
                    details=exc.details,
                ).model_dump(),
            )
        except Exception as exc:
            import traceback

            error_id = str(uuid.uuid4())
            error_details = None

            if settings.DEBUG:
                error_details = {
                    "error_id": error_id,
                    "traceback": traceback.format_exc(),
                    "error_type": type(exc).__name__,
                }

            return JSONResponse(
                status_code=500,
                content=ErrorResponse(
                    message="服务器内部错误" if not settings.DEBUG else str(exc),
                    error_code="INTERNAL_SERVER_ERROR",
                    details=error_details,
                ).model_dump(),
            )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.perf_counter()

        response = await call_next(request)

        process_time = time.perf_counter() - start_time

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.4f}"

        if settings.DEBUG:
            print(
                f"[{request_id}] {request.method} {request.url.path} "
                f"- {response.status_code} - {process_time:.4f}s"
            )

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response


def setup_cors(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )


def setup_middlewares(app: FastAPI) -> None:
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(ExceptionHandlerMiddleware)
    setup_cors(app)
