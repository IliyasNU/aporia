"""All ORM models, imported here so Alembic sees the complete metadata."""

from app.models.tag import Tag

__all__ = ["Tag"]
