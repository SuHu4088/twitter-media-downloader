from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class SystemConfig(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "system_configs"
    __table_args__ = (UniqueConstraint("key"),)

    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<SystemConfig {self.key}>"
