"""Reports (any signed-in user) and moderation (admins only)."""

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser
from app.core import rate_limit
from app.core.rate_limit import limiter
from app.db.session import DbSession
from app.models import ReportStatus
from app.schemas.errors import error_responses
from app.schemas.social import (
    AdminReportOut,
    ModerationIn,
    ModerationOut,
    ReportIn,
    ReportOut,
    ReportTargetInfo,
)
from app.services import moderation

router = APIRouter(tags=["moderation"])


@router.post(
    "/reports",
    status_code=status.HTTP_201_CREATED,
    response_model=ReportOut,
    responses=error_responses(401, 403, 404, 409, 422, 429),
)
def create_report(data: ReportIn, user: CurrentUser, db: DbSession) -> ReportOut:
    """Report an article or comment to the administrators."""
    limiter.hit(rate_limit.REPORT, str(user.id))
    entry = moderation.report(db, user, data.target_type, data.target_id, data.reason)
    return ReportOut.model_validate(entry)


@router.get(
    "/admin/reports", response_model=list[AdminReportOut], responses=error_responses(401, 403)
)
def list_reports(
    user: CurrentUser,
    db: DbSession,
    status: ReportStatus = ReportStatus.OPEN,
    page: Annotated[int, Query(ge=1, le=10_000)] = 1,
) -> list[AdminReportOut]:
    """Admins only: reports to review, oldest first, 50 per page, each with what it points at
    (`target` is null when the content has been deleted for good)."""
    moderation.require_admin(user)
    reports = moderation.list_reports(db, status, page)
    targets = moderation.describe_targets(db, reports)
    return [
        AdminReportOut(
            **ReportOut.model_validate(r).model_dump(),
            target=ReportTargetInfo(**targets[r.target_id]) if r.target_id in targets else None,
        )
        for r in reports
    ]


@router.post(
    "/admin/moderate", response_model=ModerationOut, responses=error_responses(401, 403, 404, 422)
)
def moderate(data: ModerationIn, user: CurrentUser, db: DbSession) -> ModerationOut:
    """Admins only: hide or unhide an article or comment; closes its open reports."""
    moderation.require_admin(user)
    result = moderation.moderate(db, data.target_type, data.target_id, hide=data.action == "hide")
    return ModerationOut(
        target_type=data.target_type, target_id=data.target_id, moderation_status=result
    )
