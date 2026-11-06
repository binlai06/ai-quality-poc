"""Client for the RBP booking service, called directly on its own port (local Docker only)."""

from datetime import date

import requests

from framework import config
from framework.api.base_client import BaseClient


class BookingClient(BaseClient):
    """Public, read-only booking endpoints. They need no token."""

    SUMMARY_PATH = "/booking/summary"
    UNAVAILABLE_PATH = "/booking/unavailable"

    @classmethod
    def direct(cls) -> "BookingClient":
        """Booking service on its own port (not exposed on the backup environment)."""
        return cls(base_url=config.settings.booking_url)

    def get_summary(self, room_id: int) -> requests.Response:
        """Booked date ranges of one room."""
        return self.get(self.SUMMARY_PATH, params={"roomid": room_id})

    def get_unavailable(self, checkin: date, checkout: date) -> requests.Response:
        """Rooms that have a booking in the given dates."""
        return self.get(
            self.UNAVAILABLE_PATH,
            params={"checkin": checkin.isoformat(), "checkout": checkout.isoformat()},
        )
