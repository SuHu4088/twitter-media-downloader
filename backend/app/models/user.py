import uuid

from sqlalchemy import Boolean, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("username"), UniqueConstraint("email"))

    username: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    twitter_accounts: Mapped[list["TwitterAccount"]] = relationship(
        "TwitterAccount",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    download_tasks: Mapped[list["DownloadTask"]] = relationship(
        "DownloadTask",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User {self.username}>"


from app.models.twitter_account import TwitterAccount
from app.models.download_task import DownloadTask
