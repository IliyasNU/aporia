"""Demo content for local presentations (`python -m app.cli seed-demo`).

Everything created here is clearly labelled as demo data: handles start with
`demo_`, names with "Demo ·", and every essay says it is demo content. The
command refuses to run when APP_ENV=production.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models import Article, ArticleStatus, Bookmark, Follow, Tag, User
from app.services.articles import slugify

DEMO_PASSWORD = "demo-password"  # noqa: S105 (printed on purpose; demo accounts only)

AUTHORS = [
    ("demo_ada", "Demo · Ada", "Writes about logic and the limits of machines."),
    ("demo_simone", "Demo · Simone", "Writes about ethics and attention."),
    ("demo_marcus", "Demo · Marcus", "Writes about stoic practice."),
]

ESSAYS = [
    (
        "demo_ada",
        "Can a Rule Explain Itself?",
        "Why every formal system leans on something outside it.",
        ["logic", "epistemology"],
        "Every proof rests on rules of inference, and no proof can establish those rules "
        "without already using them.\n\nThis is not a defect of logic. It is a reminder "
        "that understanding starts before formalisation.",
    ),
    (
        "demo_ada",
        "What Machines Do Not Notice",
        "Calculation is not the same thing as caring about the answer.",
        ["consciousness", "metaphysics"],
        "A machine can follow instructions perfectly and still have no stake in the "
        "outcome.\n\n## A question\n\nIs noticing something a kind of caring about it?",
    ),
    (
        "demo_simone",
        "Attention as Generosity",
        "To attend fully to another person is a moral act.",
        ["ethics"],
        "Attention is rarer than kindness and harder to fake.\n\n> Attention is the rarest "
        "and purest form of generosity.\n\nWhat would change if we treated it as a duty?",
    ),
    (
        "demo_simone",
        "The Weight of Obligations",
        "We owe others more than rights can express.",
        ["ethics", "existentialism"],
        "Rights describe what can be claimed. Obligations describe what must be given, "
        "even when nobody claims it.",
    ),
    (
        "demo_marcus",
        "The Morning Exercise",
        "Rehearsing the day's difficulties before they arrive.",
        ["stoicism"],
        "Begin the morning by saying: today I will meet interference, ingratitude and "
        "noise.\n\nNot to become bitter, but to stay steady when it happens.",
    ),
    (
        "demo_marcus",
        "What Is Up to Us",
        "A short guide to the oldest distinction in practical philosophy.",
        ["stoicism", "ethics"],
        "Some things are up to us: judgements, intentions, effort. Most things are not.\n\n"
        "Peace begins when we stop arguing with the second list.",
    ),
]

READER = ("demo_reader", "Demo · Reader", ["ethics", "logic"])
NOTE = "\n\n---\n*Demo content created by `seed-demo` for presentations.*"


def seed_demo(db: Session) -> list[str]:
    """Create demo accounts and essays once. Returns the demo handles."""
    if get_settings().app_env == "production":
        raise RuntimeError("Refusing to create demo data with APP_ENV=production")
    if db.scalar(select(User).where(User.handle == "demo_ada")):
        return []  # already seeded

    password_hash = hash_password(DEMO_PASSWORD)
    tags = {tag.slug: tag for tag in db.scalars(select(Tag))}
    users: dict[str, User] = {}
    for handle, name, bio in [*AUTHORS, (READER[0], READER[1], "A demo reader.")]:
        users[handle] = User(
            email=f"{handle}@example.com",
            password_hash=password_hash,
            handle=handle,
            display_name=name,
            bio=f"{bio} (Demo account.)",
        )
        db.add(users[handle])
    db.flush()

    now = datetime.now(UTC)
    articles = []
    for days_ago, (handle, title, summary, tag_slugs, body) in enumerate(ESSAYS):
        article = Article(
            author_id=users[handle].id,
            title=f"Demo: {title}",
            slug=f"demo-{slugify(title)}",
            summary=summary,
            body_markdown=body + NOTE,
            status=ArticleStatus.PUBLISHED,
            published_at=now - timedelta(days=days_ago * 3),
            tags=[tags[slug] for slug in tag_slugs],
        )
        db.add(article)
        articles.append(article)
    db.flush()

    reader = users[READER[0]]
    reader.interests = [tags[slug] for slug in READER[2]]
    db.add(Follow(follower_id=reader.id, author_id=users["demo_marcus"].id))
    for article in articles[2:4]:
        for handle in ("demo_ada", "demo_marcus"):
            db.add(Bookmark(user_id=users[handle].id, article_id=article.id))
    db.commit()
    return list(users)
