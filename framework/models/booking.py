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


class BookingPayload(BaseModel):
    """Request body to create a booking on the booking service."""

    roomid: int
    firstname: str
    lastname: str
    email: str
    phone: str
    depositpaid: bool
    bookingdates: Stay


class BookingRecord(BaseModel):
    """A booking as the booking service returns it. Email and phone are not echoed."""

    bookingid: int
    roomid: int
    firstname: str
    lastname: str
    depositpaid: bool
    bookingdates: Stay


class CreatedBooking(BaseModel):
    """Response body of a successful booking creation."""

    bookingid: int
    booking: BookingRecord


class ErrorResponse(BaseModel):
    """Body of a rejected booking request."""

    error: str
    errorCode: int
    fieldErrors: list[str]
