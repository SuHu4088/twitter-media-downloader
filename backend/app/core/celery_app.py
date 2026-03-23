from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "social_media_downloader",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.download_tasks",
        "app.tasks.sync_tasks",
        "app.tasks.telegram_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    result_expires=3600,
    broker_connection_retry_on_startup=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=60,
    task_max_retries=3,
)

celery_app.conf.task_routes = {
    "app.tasks.sync_tasks.*": {"queue": "sync"},
    "app.tasks.download_tasks.*": {"queue": "download"},
    "app.tasks.telegram_tasks.*": {"queue": "telegram"},
    "app.tasks.maintenance_tasks.*": {"queue": "maintenance"},
}

celery_app.conf.task_default_queue = "default"

celery_app.conf.beat_schedule = {
    "sync-likes-every-hour": {
        "task": "app.tasks.sync_tasks.sync_likes_task",
        "schedule": crontab(minute=0),
        "options": {"queue": "sync"},
    },
    "sync-bookmarks-every-hour": {
        "task": "app.tasks.sync_tasks.sync_bookmarks_task",
        "schedule": crontab(minute=30),
        "options": {"queue": "sync"},
    },
    "sync-following-timeline-every-30-minutes": {
        "task": "app.tasks.sync_tasks.sync_following_timeline_task",
        "schedule": crontab(minute="*/30"),
        "options": {"queue": "sync"},
    },
    "check-following-changes-every-10-minutes": {
        "task": "app.tasks.sync_tasks.check_following_changes_task",
        "schedule": crontab(minute="*/10"),
        "options": {"queue": "sync"},
    },
    "refresh-twitter-tokens-every-day": {
        "task": "app.tasks.sync_tasks.refresh_all_twitter_tokens",
        "schedule": crontab(hour=4, minute=0),
        "options": {"queue": "sync"},
    },
    "cleanup-incomplete-downloads-every-hour": {
        "task": "app.tasks.download_tasks.cleanup_incomplete_downloads_task",
        "schedule": crontab(minute=15),
        "options": {"queue": "download"},
    },
    "retry-failed-downloads-every-6-hours": {
        "task": "app.tasks.download_tasks.retry_failed_downloads_task",
        "schedule": crontab(hour="*/6"),
        "options": {"queue": "download"},
    },
    "auto-upload-new-media-every-30-minutes": {
        "task": "app.tasks.telegram_tasks.auto_upload_new_media_task",
        "schedule": crontab(minute="*/30"),
        "options": {"queue": "telegram"},
    },
    "retry-failed-telegram-uploads-every-hour": {
        "task": "app.tasks.telegram_tasks.retry_failed_uploads_task",
        "schedule": crontab(minute=45),
        "options": {"queue": "telegram"},
    },
}
