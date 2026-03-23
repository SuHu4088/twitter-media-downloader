from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = "操作成功"
    data: T | None = None
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool

    class Config:
        from_attributes = True

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse[T]":
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        )


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error_code: str | None = None
    details: Any | None = None
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class SortParams(BaseModel):
    sort_by: str | None = Field(default=None, description="排序字段")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$", description="排序方向")
