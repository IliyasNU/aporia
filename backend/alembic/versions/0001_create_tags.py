"""create tags and seed the topic catalog

Revision ID: 0001
Revises:
Create Date: 2026-10-24 07:40:19.566115
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEED_TAGS = [
    ("ethics", "Ethics"),
    ("stoicism", "Stoicism"),
    ("existentialism", "Existentialism"),
    ("epistemology", "Epistemology"),
    ("metaphysics", "Metaphysics"),
    ("consciousness", "Consciousness"),
    ("logic", "Logic"),
]


def upgrade() -> None:
    tags = op.create_table(
        "tags",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tags")),
        sa.UniqueConstraint("slug", name=op.f("uq_tags_slug")),
    )
    op.bulk_insert(tags, [{"slug": slug, "name": name} for slug, name in SEED_TAGS])


def downgrade() -> None:
    op.drop_table("tags")
