"""Builds unique, valid room payloads for tests."""

import uuid
from typing import Any

from faker import Faker

from framework.models.room import RoomPayload

ROOM_TYPES = ["Single", "Double", "Twin", "Family", "Suite"]
ROOM_FEATURES = ["TV", "WiFi", "Safe", "Radio", "Refreshments", "Views"]
MIN_PRICE, MAX_PRICE = 1, 999


class RoomFactory:
    """Creates valid room payloads with a unique name, so parallel tests never collide."""

    _fake = Faker()

    @classmethod
    def build(cls, **overrides: Any) -> RoomPayload:
        """Return a valid payload. Keyword arguments replace individual fields."""
        fields: dict[str, Any] = {
            "roomName": f"qa-room-{uuid.uuid4().hex[:8]}",
            "type": cls._fake.random_element(ROOM_TYPES),
            "accessible": cls._fake.boolean(),
            "image": f"/images/room{cls._fake.random_int(1, 3)}.jpg",
            "description": cls._fake.sentence(nb_words=10),
            "features": cls._fake.random_elements(
                ROOM_FEATURES, length=cls._fake.random_int(1, 3), unique=True
            ),
            "roomPrice": cls._fake.random_int(MIN_PRICE, MAX_PRICE),
        }
        fields.update(overrides)
        return RoomPayload(**fields)
