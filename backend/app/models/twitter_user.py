import uuid

from sqlalchemy import Boolean, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class TwitterUser(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "twitter_users"
    __table_args__ = (UniqueConstraint("twitter_id"),)

    twitter_id: Mapped[str] = mapped_column(String(50), nullable=False)
    username: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    profile_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    followers_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    friends_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    statuses_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_following: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    tweets: Mapped[list["Tweet"]] = relationship(
        "Tweet",
        back_populates="twitter_user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<TwitterUser @{self.username}>"


from app.models.tweet import Tweet
