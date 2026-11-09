"""Booking service tests, called directly on its own port (local Docker only).

The smoke tests are read-only. The regression tests create a booking in a fresh room;
`booking_cleanup` deletes the booking and its message before the room fixture deletes the room.
"""

import pytest
from faker import Faker

from framework.api.booking_client import BookingClient
from framework.cleanup import BookingCleanup
from framework.factories.booking_factory import BookingFactory
from framework.factories.guest_factory import GuestFactory
from framework.models.booking import (
    BookingSummaryList,
    CreatedBooking,
    ErrorResponse,
    UnavailableRoom,
)
from framework.models.room import Room

pytestmark = [
    pytest.mark.api,
    pytest.mark.service,
    pytest.mark.story("BOOK-1"),
]

fake = Faker()


@pytest.mark.smoke
def test_get_booking_summary_for_room_without_bookings_returns_200_and_empty_list(
    booking_client: BookingClient,
) -> None:
    room_id = fake.random_int(min=1_000_000, max=9_999_999)

    response = booking_client.get_summary(room_id)

    assert response.status_code == 200
    summary = BookingSummaryList.model_validate(response.json())
    assert summary.bookings == []


@pytest.mark.smoke
def test_check_unavailable_rooms_for_future_stay_returns_200_and_room_list(
    booking_client: BookingClient,
) -> None:
    stay = GuestFactory.build_stay()

    response = booking_client.get_unavailable(stay.checkin, stay.checkout)

    assert response.status_code == 200
    rooms = [UnavailableRoom.model_validate(item) for item in response.json()]
    assert len({room.roomid for room in rooms}) == len(rooms)


@pytest.mark.regression
def test_create_booking_for_existing_room_returns_201_and_appears_in_room_summary(
    booking_client: BookingClient,
    booking_cleanup: BookingCleanup,
    created_room: Room,
) -> None:
    payload = BookingFactory.build(created_room.roomid)

    response = booking_client.create_booking(payload.model_dump(mode="json"))
    booking_cleanup.track(response)

    assert response.status_code == 201
    created = CreatedBooking.model_validate(response.json())
    assert created.booking.roomid == created_room.roomid
    assert created.booking.firstname == payload.firstname
    assert created.booking.bookingdates == payload.bookingdates
    summary = BookingSummaryList.model_validate(
        booking_client.get_summary(created_room.roomid).json()
    )
    assert [item.bookingDates for item in summary.bookings] == [payload.bookingdates]


@pytest.mark.regression
def test_create_booking_with_malformed_email_returns_400_and_creates_nothing(
    booking_client: BookingClient,
    booking_cleanup: BookingCleanup,
    created_room: Room,
) -> None:
    payload = BookingFactory.build(created_room.roomid, email="not-an-email")

    response = booking_client.create_booking(payload.model_dump(mode="json"))
    booking_cleanup.track(response)

    assert response.status_code == 400
    error = ErrorResponse.model_validate(response.json())
    assert error.fieldErrors == ["must be a well-formed email address"]
    summary = booking_client.get_summary(created_room.roomid)
    assert summary.status_code == 200
    assert BookingSummaryList.model_validate(summary.json()).bookings == []
