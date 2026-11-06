"""Builds unique guest details and stay dates for booking tests."""

import uuid
from datetime import date, timedelta
from typing import Any

from faker import Faker

from framework.models.booking import GuestPayload, Stay


class GuestFactory:
    """Creates guest details with a unique name tag.

    Size rules follow the booking service: firstname 3-18, lastname 3-30, phone 11-21.
    """

    _fake = Faker()

    @classmethod
    def build(cls, **overrides: Any) -> GuestPayload:
        tag = uuid.uuid4().hex[:8]
        fields: dict[str, Any] = {
            "firstname": f"qa{tag}",
            "lastname": f"Guest{tag}",
            "email": f"qa-{tag}@example.com",
            "phone": f"0{cls._fake.random_number(digits=10, fix_len=True)}",
        }
        fields.update(overrides)
        return GuestPayload(**fields)

    @staticmethod
    def build_stay(days_ahead: int = 30, nights: int = 2) -> Stay:
        """A stay that starts `days_ahead` days from today."""
        checkin = date.today() + timedelta(days=days_ahead)
        return Stay(checkin=checkin, checkout=checkin + timedelta(days=nights))
