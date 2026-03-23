import uuid

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class DedupRecord(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "dedup_records"

    file_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )
    tweet_id: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
    media_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        index=True,
    )
    media_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("media_files.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        Index("ix_dedup_records_file_hash_unique", "file_hash", unique=True, sqlite_where=file_hash.isnot(None)),
        Index("ix_dedup_records_tweet_id_unique", "tweet_id", unique=True, sqlite_where=tweet_id.isnot(None)),
        Index("ix_dedup_records_media_url_unique", "media_url", unique=True, sqlite_where=media_url.isnot(None)),
    )

    def __repr__(self) -> str:
        return f"<DedupRecord {self.id}>"
