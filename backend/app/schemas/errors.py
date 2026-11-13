from pydantic import BaseModel


class ValidationIssue(BaseModel):
    loc: list[str]
    msg: str
    type: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ValidationIssue] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


def error_responses(*status_codes: int) -> dict[int | str, dict[str, object]]:
    """OpenAPI documentation for the error statuses a route can return."""
    return {status: {"model": ErrorResponse} for status in status_codes}
