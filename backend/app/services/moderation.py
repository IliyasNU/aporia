"""Reports from users and moderation by admins (MOD-01)."""

import uuid

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import (
    Article,
    Comment,
    ModerationStatus,
    Report,
    ReportStatus,
    ReportTarget,
    User,
    UserRole,
)
from app.services.visibility import comment_visible, publicly_visible


def _target_exists_publicly(db: Session, target_type: ReportTarget, target_id: uuid.UUID) -> bool:
    if target_type == ReportTarget.ARTICLE:
        query = select(Article.id).where(Article.id == target_id, publicly_visible())
    else:
        query = (
            select(Comment.id)
            .join(Article, Article.id == Comment.article_id)
            .where(Comment.id == target_id, comment_visible(), publicly_visible())
        )
    return db.scalar(query) is not None


def report(
    db: Session, reporter: User, target_type: ReportTarget, target_id: uuid.UUID, reason: str
) -> Report:
    if not _target_exists_publicly(db, target_type, target_id):
        raise AppError(404, "not_found", "Nothing to report here")
    entry = Report(
        reporter_id=reporter.id, target_type=target_type, target_id=target_id, reason=reason
    )
    db.add(entry)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(409, "already_reported", "You have already reported this") from None
    return entry


def require_admin(user: User) -> None:
    if user.role != UserRole.ADMIN:
        raise AppError(403, "forbidden", "Only administrators can do this")


def list_reports(db: Session, status: ReportStatus) -> list[Report]:
    return list(
        db.scalars(
            select(Report)
            .where(Report.status == status)
            .order_by(Report.created_at, Report.id)
            .limit(200)
        )
    )


def moderate(
    db: Session, target_type: ReportTarget, target_id: uuid.UUID, hide: bool
) -> ModerationStatus:
    """Hide or unhide an article or comment and close its open reports."""
    model = Article if target_type == ReportTarget.ARTICLE else Comment
    status = ModerationStatus.HIDDEN if hide else ModerationStatus.VISIBLE
    result = db.execute(update(model).where(model.id == target_id).values(moderation_status=status))
    if result.rowcount == 0:  # type: ignore[attr-defined]
        raise AppError(404, "not_found", f"{target_type.value.capitalize()} not found")
    db.execute(
        update(Report)
        .where(
            Report.target_type == target_type,
            Report.target_id == target_id,
            Report.status == ReportStatus.OPEN,
        )
        .values(status=ReportStatus.RESOLVED)
    )
    db.commit()
    return status


def set_role(db: Session, email: str, role: UserRole) -> User:
    """Used by the `python -m app.cli set-role` command; there is no API for it."""
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None:
        raise LookupError(f"No user with email {email}")
    user.role = role
    db.commit()
    return user
