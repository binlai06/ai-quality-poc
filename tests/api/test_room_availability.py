"""Room availability search (BOOK-2): which rooms are listed for a guest's dates.

The search tests use their own room with one booking from day 10 to day 15 (see `StayFactory`)
and assert on that room id only. They go through the UI proxy, like the home page.
The malformed-date test calls the room service directly.
"""

import pytest

from framework.api.room_client import RoomClient
from framework.booking_helper import BookingHelper
from framework.factories.stay_factory import StayFactory
from framework.models.room import Room, RoomList

pytestmark = [
    pytest.mark.api,
    pytest.mark.service,
    pytest.mark.story("BOOK-2"),
]

BOOKED_STAY = (10, 15)


def _listed_room_ids(response_json: dict) -> set[int]:
    return {room.roomid for room in RoomList.model_validate(response_json).rooms}


@pytest.fixture
def booked_room(booking_helper: BookingHelper, created_room: Room) -> Room:
    """A fresh room with one booking from day 10 to day 15."""
    booking_helper.book(created_room.roomid, StayFactory.build(*BOOKED_STAY))
    return created_room


@pytest.mark.smoke
def test_search_range_without_booking_lists_own_room(
    proxy_room_client: RoomClient, booked_room: Room
) -> None:
    search = StayFactory.build(30, 35)

    response = proxy_room_client.list_available_rooms(search.checkin, search.checkout)

    assert response.status_code == 200
    assert booked_room.roomid in _listed_room_ids(response.json())


@pytest.mark.regression
def test_search_range_containing_booking_hides_own_room(
    proxy_room_client: RoomClient, booked_room: Room
) -> None:
    search = StayFactory.build(1, 20)

    response = proxy_room_client.list_available_rooms(search.checkin, search.checkout)

    assert response.status_code == 200
    assert booked_room.roomid not in _listed_room_ids(response.json())


@pytest.mark.regression
@pytest.mark.issue("7")
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="RBP bug #7: room search only hides a room whose booking lies fully inside the searched range",
)
@pytest.mark.parametrize(
    "search_days",
    [
        pytest.param((5, 12), id="overlaps-start-of-booking"),
        pytest.param((12, 20), id="overlaps-end-of-booking"),
        pytest.param((11, 13), id="inside-booking"),
    ],
)
def test_search_range_overlapping_booking_hides_own_room(
    proxy_room_client: RoomClient, booked_room: Room, search_days: tuple[int, int]
) -> None:
    search = StayFactory.build(*search_days)

    response = proxy_room_client.list_available_rooms(search.checkin, search.checkout)

    assert response.status_code == 200
    assert booked_room.roomid not in _listed_room_ids(response.json())


@pytest.mark.regression
@pytest.mark.issue("8")
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="RBP bug #8: malformed request returns 500 instead of 400",
)
def test_search_with_malformed_checkin_returns_400(
    service_room_client: RoomClient,
) -> None:
    checkout = StayFactory.build(10, 15).checkout

    response = service_room_client.list_available_rooms("abc", checkout)

    assert response.status_code == 400
