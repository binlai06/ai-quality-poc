"""Pydantic models for the auth service, as exposed by the UI proxy at /api/auth."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Login body. A field left as None is omitted from the JSON, to test missing fields."""

    username: str | None = None
    password: str | None = None


class LoginResponse(BaseModel):
    """Successful login: the proxy returns the session token in the body."""

    token: str = Field(min_length=1)


class ErrorResponse(BaseModel):
    """Error body returned by the UI proxy."""

    error: str
