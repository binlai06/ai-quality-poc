"""Models for the booking journey in the UI."""

from datetime import date

from pydantic import BaseModel


class GuestPayload(BaseModel):
    """Guest details typed into the reservation form."""

    firstname: str
    lastname: str
    email: str
    phone: str


class Stay(BaseModel):
    """Check-in and check-out dates of a booking."""

    checkin: date
    checkout: date
