import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class DownloadTask(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "download_tasks"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    twitter_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("twitter_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("twitter_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
    )
    total_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    downloaded_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="download_tasks")
    twitter_account: Mapped["TwitterAccount"] = relationship(
        "TwitterAccount",
        back_populates="download_tasks",
    )

    def __repr__(self) -> str:
        return f"<DownloadTask {self.task_type} - {self.status}>"


from app.models.twitter_account import TwitterAccount
from app.models.user import User
