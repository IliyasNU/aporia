from alembic import command
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.session import engine
from app.models import Tag
from tests.conftest import alembic_config

SEEDED_TAG_SLUGS = {
    "ethics",
    "stoicism",
    "existentialism",
    "epistemology",
    "metaphysics",
    "consciousness",
    "logic",
}


def test_models_match_migrations() -> None:
    # Fails if a model was changed without a matching migration.
    command.check(alembic_config())


def test_tag_catalog_is_seeded(db_session: Session) -> None:
    slugs = set(db_session.scalars(select(Tag.slug)))

    assert slugs == SEEDED_TAG_SLUGS


def test_migrations_downgrade_to_empty_and_upgrade_again() -> None:
    config = alembic_config()

    command.downgrade(config, "base")
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT to_regclass('public.tags')")) is None

    command.upgrade(config, "head")
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM tags")) == len(SEEDED_TAG_SLUGS)
