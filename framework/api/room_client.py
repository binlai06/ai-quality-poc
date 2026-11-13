"""Client for the RBP room service, reachable directly or through the UI proxy."""

from datetime import date
from typing import Any, Self

import requests

from framework import config
from framework.api.base_client import BaseClient


def _as_text(value: date | str) -> str:
    return value.isoformat() if isinstance(value, date) else value


class RoomClient(BaseClient):
    """Room endpoints. Use `direct()` for the room service or `via_proxy()` for the UI proxy.

    Write calls take the auth token explicitly and send it as the `token` cookie,
    which is the only way RBP accepts it. Passing None sends no cookie.
    """

    def __init__(self, base_url: str, collection_path: str) -> None:
        super().__init__(base_url=base_url)
        self.collection_path = collection_path

    @classmethod
    def direct(cls) -> Self:
        """Room service on its own port (local Docker only)."""
        return cls(config.settings.room_url, "/room/")

    @classmethod
    def via_proxy(cls) -> Self:
        """Room endpoints through the UI proxy (works on every environment)."""
        return cls(config.settings.base_url, "/api/room")

    def _item_path(self, room_id: int) -> str:
        return f"{self.collection_path.rstrip('/')}/{room_id}"

    @staticmethod
    def _cookies(token: str | None) -> dict[str, str]:
        return {"token": token} if token is not None else {}

    def list_rooms(self) -> requests.Response:
        return self.get(self.collection_path)

    def list_available_rooms(
        self, checkin: date | str, checkout: date | str
    ) -> requests.Response:
        """Rooms listed for the given dates. Strings are sent as they are."""
        return self.get(
            self.collection_path,
            params={"checkin": _as_text(checkin), "checkout": _as_text(checkout)},
        )

    def get_room(self, room_id: int) -> requests.Response:
        return self.get(self._item_path(room_id))

    def create_room(
        self, payload: dict[str, Any], token: str | None
    ) -> requests.Response:
        return self.post(
            self.collection_path, json=payload, cookies=self._cookies(token)
        )

    def update_room(
        self, room_id: int, payload: dict[str, Any], token: str | None
    ) -> requests.Response:
        return self.put(
            self._item_path(room_id), json=payload, cookies=self._cookies(token)
        )

    def delete_room(self, room_id: int, token: str | None) -> requests.Response:
        return self.delete(self._item_path(room_id), cookies=self._cookies(token))
