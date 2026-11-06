"""Booking service smoke checks, called directly on its own port.

Both tests are read-only: they create no rooms and no bookings, so there is nothing to clean up.
"""

import pytest
from faker import Faker

from framework.api.booking_client import BookingClient
from framework.factories.guest_factory import GuestFactory
from framework.models.booking import BookingSummaryList, UnavailableRoom

pytestmark = [
    pytest.mark.api,
    pytest.mark.smoke,
    pytest.mark.service,
    pytest.mark.story("BOOK-1"),
]

fake = Faker()


def test_get_booking_summary_for_room_without_bookings_returns_200_and_empty_list(
    booking_client: BookingClient,
) -> None:
    room_id = fake.random_int(min=1_000_000, max=9_999_999)

    response = booking_client.get_summary(room_id)

    assert response.status_code == 200
    summary = BookingSummaryList.model_validate(response.json())
    assert summary.bookings == []


def test_check_unavailable_rooms_for_future_stay_returns_200_and_room_list(
    booking_client: BookingClient,
) -> None:
    stay = GuestFactory.build_stay()

    response = booking_client.get_unavailable(stay.checkin, stay.checkout)

    assert response.status_code == 200
    rooms = [UnavailableRoom.model_validate(item) for item in response.json()]
    assert len({room.roomid for room in rooms}) == len(rooms)
