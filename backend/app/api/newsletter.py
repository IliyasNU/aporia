"""Email subscriptions to an author (MAIL-01, MAIL-02). No account needed."""

import uuid

from fastapi import APIRouter, status

from app.db.session import DbSession
from app.schemas.articles import AuthorBrief
from app.schemas.errors import error_responses
from app.schemas.newsletter import ConfirmOut, SubscribeIn, SubscribeOut, TokenIn
from app.services import newsletter

router = APIRouter(tags=["newsletter"])

CHECK_INBOX = (
    "Thanks! If this address can receive email, a confirmation link is on its way. "
    "Nothing will be sent until you confirm."
)


@router.post(
    "/authors/{author_id}/newsletter-subscriptions",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=SubscribeOut,
    responses=error_responses(403, 404, 422),
)
def subscribe(author_id: uuid.UUID, data: SubscribeIn, db: DbSession) -> SubscribeOut:
    """Ask for new essays by email. Sends a confirmation link (double opt-in).

    The answer is the same whether the address is new, pending or already
    subscribed, so nobody can use this endpoint to learn who subscribes.
    """
    newsletter.request_subscription(db, author_id, data.email)
    return SubscribeOut(message=CHECK_INBOX)


@router.post(
    "/newsletter/confirm", response_model=ConfirmOut, responses=error_responses(400, 403, 422)
)
def confirm(data: TokenIn, db: DbSession) -> ConfirmOut:
    """Confirm a subscription with the token from the email. Safe to repeat."""
    subscription = newsletter.confirm(db, data.token)
    return ConfirmOut(author=AuthorBrief.model_validate(subscription.author))


@router.post(
    "/newsletter/unsubscribe",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(400, 403, 422),
)
def unsubscribe(data: TokenIn, db: DbSession) -> None:
    """Stop emails for this subscription (link in every email). Safe to repeat."""
    newsletter.unsubscribe(db, data.token)
