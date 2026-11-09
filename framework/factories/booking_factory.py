"""Builds valid booking payloads for the booking service."""

from typing import Any

from framework.factories.guest_factory import GuestFactory
from framework.models.booking import BookingPayload, GuestPayload, Stay


class BookingFactory:
    """Creates booking payloads for an existing room with a unique qa- guest."""

    @staticmethod
    def build(
        room_id: int,
        guest: GuestPayload | None = None,
        stay: Stay | None = None,
        **overrides: Any,
    ) -> BookingPayload:
        """Return a valid payload. Keyword arguments replace individual fields."""
        guest = guest or GuestFactory.build()
        stay = stay or GuestFactory.build_stay()
        fields: dict[str, Any] = {
            **guest.model_dump(),
            "roomid": room_id,
            "depositpaid": True,
            "bookingdates": stay,
        }
        fields.update(overrides)
        return BookingPayload(**fields)
