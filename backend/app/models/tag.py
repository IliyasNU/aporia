from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class Tag(UUIDPrimaryKeyMixin, Base):
    """A topic from the curated catalog (ethics, logic, ...). Seeded by migrations."""

    __tablename__ = "tags"

    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(64))
