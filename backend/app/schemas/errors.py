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
