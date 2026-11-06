"""Pydantic models for the message service and the contact form."""

from pydantic import BaseModel


class ContactPayload(BaseModel):
    """Fields a visitor types into the contact form."""

    name: str
    email: str
    phone: str
    subject: str
    description: str


class MessageSummary(BaseModel):
    """One entry of the message list. The list does not return email, phone or body."""

    id: int
    name: str
    read: bool
    subject: str


class MessageList(BaseModel):
    """Response body of the message list endpoint."""

    messages: list[MessageSummary]
