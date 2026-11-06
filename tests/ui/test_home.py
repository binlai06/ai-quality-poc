"""Home page: the public room list."""

import pytest
from playwright.sync_api import expect

from framework.api.room_client import RoomClient
from framework.models.room import RoomList
from framework.pages.home_page import HomePage, RoomCardInfo

pytestmark = [pytest.mark.ui, pytest.mark.public]

ROOMS_SHOWN_ON_HOME_PAGE = 3
"""By design the home page shows only the first three rooms."""


@pytest.mark.smoke
def test_home_page_lists_first_three_rooms_from_api(
    home_page: HomePage, proxy_room_client: RoomClient
) -> None:
    response = proxy_room_client.list_rooms()
    expected = sorted(
        RoomList.model_validate(response.json()).rooms, key=lambda r: r.roomid
    )
    expected_infos = [
        RoomCardInfo(room_id=r.roomid, room_type=r.type, price=r.roomPrice)
        for r in expected[:ROOMS_SHOWN_ON_HOME_PAGE]
    ]

    home_page.open()
    expect(home_page.room_cards.first).to_be_visible()

    shown = sorted(home_page.room_infos(), key=lambda info: info.room_id)
    assert shown[:ROOMS_SHOWN_ON_HOME_PAGE] == expected_infos
