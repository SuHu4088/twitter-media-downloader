import os
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.dedup_service import DedupService
from app.utils.hash_utils import calculate_bytes_hash, calculate_file_hash


@dataclass
class DedupReport:
    total_checked: int
    duplicates_found: int
    unique_files: int
    by_type: dict[str, int]
    saved_space: int


async def compute_media_hash(file_path_or_data: str | bytes | BinaryIO, algorithm: str = "sha256") -> str:
    if isinstance(file_path_or_data, str):
        if os.path.exists(file_path_or_data):
            return calculate_file_hash(file_path_or_data, algorithm)
        return calculate_bytes_hash(file_path_or_data.encode("utf-8"), algorithm)
    elif isinstance(file_path_or_data, bytes):
        return calculate_bytes_hash(file_path_or_data, algorithm)
    elif hasattr(file_path_or_data, "read"):
        return calculate_stream_hash(file_path_or_data, algorithm)
    else:
        raise ValueError(f"不支持的输入类型: {type(file_path_or_data)}")


def calculate_stream_hash(stream: BinaryIO, algorithm: str = "sha256") -> str:
    import hashlib
    
    hash_func = hashlib.sha256() if algorithm == "sha256" else hashlib.md5()
    
    original_position = stream.tell()
    stream.seek(0)
    
    try:
        while chunk := stream.read(8192):
            hash_func.update(chunk)
    finally:
        stream.seek(original_position)
    
    return hash_func.hexdigest()


async def is_duplicate_file(file_hash: str, db: AsyncSession) -> bool:
    service = DedupService(db)
    record = await service.check_file_hash(file_hash)
    return record is not None


async def is_duplicate_tweet(tweet_id: str, db: AsyncSession) -> bool:
    service = DedupService(db)
    record = await service.check_tweet_id(tweet_id)
    return record is not None


async def is_duplicate_media_url(media_url: str, db: AsyncSession) -> bool:
    service = DedupService(db)
    record = await service.check_media_url(media_url)
    return record is not None


async def generate_dedup_report(db: AsyncSession) -> DedupReport:
    from app.models.media_file import MediaFile
    from sqlalchemy import func, select
    
    service = DedupService(db)
    stats = await service.get_duplicate_stats()
    
    total_query = select(func.count(MediaFile.id)).where(
        MediaFile.download_status == "completed"
    )
    total_result = await db.execute(total_query)
    total_checked = total_result.scalar() or 0
    
    hash_dup_query = select(func.count(MediaFile.id)).where(
        MediaFile.file_hash.isnot(None),
        MediaFile.download_status == "completed",
    ).group_by(MediaFile.file_hash).having(func.count(MediaFile.id) > 1)
    hash_dup_result = await db.execute(hash_dup_query)
    hash_duplicates = len(hash_dup_result.all())
    
    type_query = (
        select(MediaFile.media_type, func.count(MediaFile.id))
        .where(MediaFile.download_status == "completed")
        .group_by(MediaFile.media_type)
    )
    type_result = await db.execute(type_query)
    by_type = dict(type_result.all())
    
    size_query = select(func.sum(MediaFile.file_size)).where(
        MediaFile.file_size.isnot(None),
        MediaFile.download_status == "completed",
    )
    size_result = await db.execute(size_query)
    total_size = size_result.scalar() or 0
    
    avg_size = total_size // total_checked if total_checked > 0 else 0
    saved_space = stats.hash_records * avg_size
    
    return DedupReport(
        total_checked=total_checked,
        duplicates_found=stats.hash_records,
        unique_files=total_checked - stats.hash_records,
        by_type=by_type,
        saved_space=saved_space,
    )


async def check_and_register_media(
    db: AsyncSession,
    file_path: str | None = None,
    tweet_id: str | None = None,
    media_url: str | None = None,
    media_id=None,
) -> dict:
    service = DedupService(db)
    
    file_hash = None
    if file_path and os.path.exists(file_path):
        file_hash = calculate_file_hash(file_path)
    
    duplicate_info = await service.get_duplicate_info(
        file_hash=file_hash,
        tweet_id=tweet_id,
        media_url=media_url,
    )
    
    if not duplicate_info["is_duplicate"]:
        if file_hash:
            await service.add_file_hash(file_hash, media_id)
        if tweet_id:
            await service.add_tweet_id(tweet_id)
        if media_url:
            await service.add_media_url(media_url, media_id)
    
    return duplicate_info


def format_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


async def get_dedup_summary(db: AsyncSession) -> dict:
    service = DedupService(db)
    stats = await service.get_duplicate_stats()
    report = await generate_dedup_report(db)
    
    return {
        "total_records": stats.total_records,
        "hash_records": stats.hash_records,
        "tweet_records": stats.tweet_records,
        "url_records": stats.url_records,
        "orphan_records": stats.orphan_records,
        "total_checked": report.total_checked,
        "duplicates_found": report.duplicates_found,
        "unique_files": report.unique_files,
        "saved_space": format_size(report.saved_space),
        "by_type": report.by_type,
    }
