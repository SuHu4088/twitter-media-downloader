import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class Tweet(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tweets"
    __table_args__ = (UniqueConstraint("twitter_id"),)

    twitter_id: Mapped[str] = mapped_column(String(50), nullable=False)
    twitter_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("twitter_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    twitter_account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("twitter_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    lang: Mapped[str | None] = mapped_column(String(10), nullable=True)
    retweet_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reply_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quote_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_retweet: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_quote: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_liked_by_me: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_bookmarked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)

    twitter_user: Mapped["TwitterUser"] = relationship("TwitterUser", back_populates="tweets")
    media_files: Mapped[list["MediaFile"]] = relationship(
        "MediaFile",
        back_populates="tweet",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Tweet {self.twitter_id}>"


from app.models.media_file import MediaFile
from app.models.twitter_user import TwitterUser
