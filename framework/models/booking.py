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


class BookingSummary(BaseModel):
    """One booked period of a room, as shown on the public availability calendar."""

    bookingDates: Stay


class BookingSummaryList(BaseModel):
    """Response body of the booking summary endpoint."""

    bookings: list[BookingSummary]


class UnavailableRoom(BaseModel):
    """A room that has a booking inside the requested dates."""

    roomid: int
