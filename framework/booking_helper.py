"""Creates bookings for tests and registers them for cleanup."""

from typing import Any

import requests

from framework.api.booking_client import BookingClient
from framework.cleanup import BookingCleanup
from framework.factories.booking_factory import BookingFactory
from framework.models.booking import CreatedBooking, Stay


class BookingHelper:
    """Creates bookings with exact stays. Every booking is tracked by the cleanup right away.

    Use `create` for the action under test (returns the raw response) and `book` to
    set up an existing booking (raises RuntimeError if it was not created, so a setup
    problem is never mistaken for a failed assertion).
    """

    def __init__(self, client: BookingClient, cleanup: BookingCleanup) -> None:
        self._client = client
        self._cleanup = cleanup

    def create(self, room_id: int, stay: Stay, **overrides: Any) -> requests.Response:
        """Create a booking for `stay` in the room and track it before returning."""
        payload = BookingFactory.build(room_id, stay=stay, **overrides)
        response = self._client.create_booking(payload.model_dump(mode="json"))
        self._cleanup.track(response)
        return response

    def book(self, room_id: int, stay: Stay) -> CreatedBooking:
        """Create an existing booking for test setup. Fails the setup unless the answer is 201."""
        response = self.create(room_id, stay)
        if response.status_code != 201:
            raise RuntimeError(f"booking setup failed: {response.status_code}")
        return CreatedBooking.model_validate(response.json())
