import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class MediaFile(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "media_files"

    tweet_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tweets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    media_type: Mapped[str] = mapped_column(String(20), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    local_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    download_status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    tweet: Mapped["Tweet"] = relationship("Tweet", back_populates="media_files")
    telegram_uploads: Mapped[list["TelegramUpload"]] = relationship(
        "TelegramUpload",
        back_populates="media_file",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<MediaFile {self.id} - {self.media_type}>"


from app.models.telegram_upload import TelegramUpload
from app.models.tweet import Tweet
