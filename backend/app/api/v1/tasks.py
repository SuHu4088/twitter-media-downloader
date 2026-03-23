from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import ActiveUser, DBSession
from app.core.exceptions import BadRequestException, NotFoundException
from app.models.download_task import DownloadTask
from app.models.twitter_account import TwitterAccount
from app.schemas.common import ApiResponse, PaginatedResponse, PaginationParams
from app.schemas.task import DownloadTaskCreate, DownloadTaskResponse

router = APIRouter(prefix="/tasks", tags=["任务管理"])


@router.get("/stats", response_model=ApiResponse[dict[str, Any]])
async def get_task_stats(
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[dict[str, Any]]:
    base_query = select(DownloadTask).where(DownloadTask.user_id == current_user.id)

    total_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(total_query)
    total_tasks = total_result.scalar() or 0

    status_query = (
        select(
            DownloadTask.status,
            func.count(DownloadTask.id).label("count"),
        )
        .where(DownloadTask.user_id == current_user.id)
        .group_by(DownloadTask.status)
    )
    status_result = await db.execute(status_query)
    by_status = {row.status: row.count for row in status_result.all()}

    type_query = (
        select(
            DownloadTask.task_type,
            func.count(DownloadTask.id).label("count"),
        )
        .where(DownloadTask.user_id == current_user.id)
        .group_by(DownloadTask.task_type)
    )
    type_result = await db.execute(type_query)
    by_type = {row.task_type: row.count for row in type_result.all()}

    sum_query = (
        select(
            func.sum(DownloadTask.downloaded_count),
            func.sum(DownloadTask.skipped_count),
        )
        .where(DownloadTask.user_id == current_user.id)
    )
    sum_result = await db.execute(sum_query)
    sums = sum_result.one()

    return ApiResponse(
        data={
            "total_tasks": total_tasks,
            "by_status": by_status,
            "by_type": by_type,
            "total_downloaded": sums[0] or 0,
            "total_skipped": sums[1] or 0,
        }
    )


@router.post("", response_model=ApiResponse[DownloadTaskResponse], status_code=status.HTTP_201_CREATED)
async def create_task(
    task_in: DownloadTaskCreate,
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[DownloadTaskResponse]:
    result = await db.execute(
        select(TwitterAccount).where(
            TwitterAccount.id == task_in.twitter_account_id,
            TwitterAccount.user_id == current_user.id,
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        raise NotFoundException(message="Twitter 账号不存在")

    if not account.is_active:
        raise BadRequestException(message="Twitter 账号未激活")

    task = DownloadTask(
        user_id=current_user.id,
        twitter_account_id=task_in.twitter_account_id,
        task_type=task_in.task_type,
        target_user_id=task_in.target_user_id,
        status="pending",
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)

    from app.core.celery_app import celery_app
    celery_app.send_task(
        "app.tasks.download_tasks.process_download_task",
        args=[str(task.id)],
    )

    return ApiResponse(
        message="下载任务已创建",
        data=DownloadTaskResponse.model_validate(task),
    )


@router.get("", response_model=ApiResponse[PaginatedResponse[DownloadTaskResponse]])
async def list_tasks(
    db: DBSession,
    current_user: ActiveUser,
    pagination: PaginationParams = None,
    status_filter: str | None = Query(None, alias="status", description="任务状态: pending, running, completed, failed, cancelled"),
    task_type: str | None = Query(None, description="任务类型: bookmarks, likes, user_tweets"),
) -> ApiResponse[PaginatedResponse[DownloadTaskResponse]]:
    if pagination is None:
        from app.schemas.common import PaginationParams
        pagination = PaginationParams()

    query = select(DownloadTask).where(DownloadTask.user_id == current_user.id)

    if status_filter:
        query = query.where(DownloadTask.status == status_filter)

    if task_type:
        query = query.where(DownloadTask.task_type == task_type)

    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    result = await db.execute(
        query
        .options(selectinload(DownloadTask.twitter_account))
        .order_by(DownloadTask.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    )
    tasks = result.scalars().all()

    return ApiResponse(
        data=PaginatedResponse.create(
            items=[DownloadTaskResponse.model_validate(t) for t in tasks],
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )
    )


@router.get("/{task_id}", response_model=ApiResponse[DownloadTaskResponse])
async def get_task(
    task_id: UUID,
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[DownloadTaskResponse]:
    result = await db.execute(
        select(DownloadTask)
        .options(selectinload(DownloadTask.twitter_account))
        .where(
            DownloadTask.id == task_id,
            DownloadTask.user_id == current_user.id,
        )
    )
    task = result.scalar_one_or_none()

    if not task:
        raise NotFoundException(message="任务不存在")

    return ApiResponse(data=DownloadTaskResponse.model_validate(task))


@router.post("/{task_id}/cancel", response_model=ApiResponse[DownloadTaskResponse])
async def cancel_task(
    task_id: UUID,
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[DownloadTaskResponse]:
    result = await db.execute(
        select(DownloadTask).where(
            DownloadTask.id == task_id,
            DownloadTask.user_id == current_user.id,
        )
    )
    task = result.scalar_one_or_none()

    if not task:
        raise NotFoundException(message="任务不存在")

    if task.status not in ["pending", "running"]:
        raise BadRequestException(message="任务已完成或已取消，无法取消")

    task.status = "cancelled"
    await db.flush()
    await db.refresh(task)

    return ApiResponse(
        message="任务已取消",
        data=DownloadTaskResponse.model_validate(task),
    )


@router.post("/{task_id}/retry", response_model=ApiResponse[DownloadTaskResponse])
async def retry_task(
    task_id: UUID,
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[DownloadTaskResponse]:
    result = await db.execute(
        select(DownloadTask).where(
            DownloadTask.id == task_id,
            DownloadTask.user_id == current_user.id,
        )
    )
    task = result.scalar_one_or_none()

    if not task:
        raise NotFoundException(message="任务不存在")

    if task.status not in ["failed", "cancelled"]:
        raise BadRequestException(message="只有失败或取消的任务可以重试")

    task.status = "pending"
    task.error_message = None
    task.downloaded_count = 0
    task.skipped_count = 0
    await db.flush()
    await db.refresh(task)

    from app.core.celery_app import celery_app
    celery_app.send_task(
        "app.tasks.download_tasks.process_download_task",
        args=[str(task.id)],
    )

    return ApiResponse(
        message="任务已重新启动",
        data=DownloadTaskResponse.model_validate(task),
    )


@router.delete("/{task_id}", response_model=ApiResponse[None])
async def delete_task(
    task_id: UUID,
    db: DBSession,
    current_user: ActiveUser,
) -> ApiResponse[None]:
    result = await db.execute(
        select(DownloadTask).where(
            DownloadTask.id == task_id,
            DownloadTask.user_id == current_user.id,
        )
    )
    task = result.scalar_one_or_none()

    if not task:
        raise NotFoundException(message="任务不存在")

    if task.status == "running":
        raise BadRequestException(message="正在运行的任务无法删除")

    await db.delete(task)

    return ApiResponse(message="任务已删除")
