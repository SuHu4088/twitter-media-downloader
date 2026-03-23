import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class TelegramUpload(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "telegram_uploads"

    media_file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("media_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chat_id: Mapped[str] = mapped_column(String(50), nullable=False)
    message_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    media_file: Mapped["MediaFile"] = relationship(
        "MediaFile",
        back_populates="telegram_uploads",
    )

    def __repr__(self) -> str:
        return f"<TelegramUpload {self.id} - {self.status}>"


from app.models.media_file import MediaFile
