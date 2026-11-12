"""Client for the RBP booking service, called directly on its own port (local Docker only)."""

from datetime import date
from typing import Any

import requests

from framework import config
from framework.api.base_client import BaseClient


def _as_text(value: date | str) -> str:
    return value.isoformat() if isinstance(value, date) else value


class BookingClient(BaseClient):
    """Booking endpoints. Reading and creating need no token, deleting needs the admin token."""

    SUMMARY_PATH = "/booking/summary"
    UNAVAILABLE_PATH = "/booking/unavailable"
    COLLECTION_PATH = "/booking/"

    @classmethod
    def direct(cls) -> "BookingClient":
        """Booking service on its own port (not exposed on the backup environment)."""
        return cls(base_url=config.settings.booking_url)

    def get_summary(self, room_id: int | str) -> requests.Response:
        """Booked date ranges of one room."""
        return self.get(self.SUMMARY_PATH, params={"roomid": room_id})

    def get_unavailable(
        self, checkin: date | str, checkout: date | str
    ) -> requests.Response:
        """Rooms that have a booking in the given dates. Strings are sent as they are."""
        return self.get(
            self.UNAVAILABLE_PATH,
            params={"checkin": _as_text(checkin), "checkout": _as_text(checkout)},
        )

    def create_booking(self, payload: dict[str, Any]) -> requests.Response:
        """Create a booking. The service also creates a "You have a new booking!" message."""
        return self.post(self.COLLECTION_PATH, json=payload)

    def delete_booking(self, booking_id: int, token: str) -> requests.Response:
        """Delete a booking. The admin token goes in the `token` cookie."""
        return self.delete(
            f"{self.COLLECTION_PATH}{booking_id}", cookies={"token": token}
        )
