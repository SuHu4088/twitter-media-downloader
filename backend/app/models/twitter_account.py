import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class TwitterAccount(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "twitter_accounts"
    __table_args__ = (UniqueConstraint("twitter_user_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    twitter_user_id: Mapped[str] = mapped_column(String(50), nullable=False)
    twitter_username: Mapped[str] = mapped_column(String(100), nullable=False)
    access_token: Mapped[str] = mapped_column(String(500), nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(String(500), nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="twitter_accounts")
    download_tasks: Mapped[list["DownloadTask"]] = relationship(
        "DownloadTask",
        back_populates="twitter_account",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<TwitterAccount @{self.twitter_username}>"


from app.models.download_task import DownloadTask
from app.models.user import User
