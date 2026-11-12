"""Booking service rules: stay conflicts, name boundaries, room summary and unavailable rooms.

Every test uses its own room and exact far-future stays (see `StayFactory`). `/booking/unavailable`
is global, so those tests assert on their own room id only.
"""

import uuid

import pytest

from framework.api.booking_client import BookingClient
from framework.booking_helper import BookingHelper
from framework.cleanup import BookingCleanup
from framework.factories.booking_factory import BookingFactory
from framework.factories.guest_factory import GuestFactory
from framework.factories.stay_factory import StayFactory
from framework.models.booking import (
    BookingSummaryList,
    CreatedBooking,
    ErrorResponse,
    UnavailableRoom,
)
from framework.models.room import Room

pytestmark = [
    pytest.mark.api,
    pytest.mark.service,
    pytest.mark.story("BOOK-1"),
]

EXISTING_STAY = (10, 14)


def _unavailable_room_ids(
    booking_client: BookingClient, query: tuple[int, int]
) -> set[int]:
    stay = StayFactory.build(*query)
    response = booking_client.get_unavailable(stay.checkin, stay.checkout)
    assert response.status_code == 200
    return {UnavailableRoom.model_validate(item).roomid for item in response.json()}


@pytest.mark.regression
@pytest.mark.parametrize(
    ("first_day", "last_day"),
    [
        pytest.param(10, 10, id="checkin-equals-checkout"),
        pytest.param(12, 10, id="checkout-before-checkin"),
    ],
)
def test_create_booking_with_invalid_stay_dates_returns_409(
    booking_helper: BookingHelper, created_room: Room, first_day: int, last_day: int
) -> None:
    stay = StayFactory.build(first_day, last_day)

    response = booking_helper.create(created_room.roomid, stay)

    assert response.status_code == 409


@pytest.mark.regression
def test_create_booking_for_same_stay_in_same_room_returns_409_and_keeps_existing_booking(
    booking_client: BookingClient, booking_helper: BookingHelper, created_room: Room
) -> None:
    stay = StayFactory.build(*EXISTING_STAY)
    booking_helper.book(created_room.roomid, stay)

    response = booking_helper.create(created_room.roomid, stay)

    assert response.status_code == 409
    summary = BookingSummaryList.model_validate(
        booking_client.get_summary(created_room.roomid).json()
    )
    assert [item.bookingDates for item in summary.bookings] == [stay]


@pytest.mark.regression
def test_create_booking_overlapping_existing_stay_in_same_room_returns_409(
    booking_helper: BookingHelper, created_room: Room
) -> None:
    booking_helper.book(created_room.roomid, StayFactory.build(*EXISTING_STAY))

    response = booking_helper.create(created_room.roomid, StayFactory.build(12, 16))

    assert response.status_code == 409


@pytest.mark.regression
def test_create_booking_starting_on_existing_checkout_day_returns_201(
    booking_helper: BookingHelper, created_room: Room
) -> None:
    booking_helper.book(created_room.roomid, StayFactory.build(*EXISTING_STAY))
    stay = StayFactory.build(EXISTING_STAY[1], 16)

    response = booking_helper.create(created_room.roomid, stay)

    assert response.status_code == 201
    created = CreatedBooking.model_validate(response.json())
    assert created.booking.roomid == created_room.roomid
    assert created.booking.bookingdates == stay


@pytest.mark.regression
@pytest.mark.parametrize(
    "firstname",
    [
        pytest.param(uuid.uuid4().hex[:3], id="firstname-min-3-chars"),
        pytest.param(uuid.uuid4().hex[:18], id="firstname-max-18-chars"),
    ],
)
def test_create_booking_with_firstname_at_limit_returns_201(
    booking_helper: BookingHelper, created_room: Room, firstname: str
) -> None:
    guest = GuestFactory.build(firstname=firstname)

    response = booking_helper.create(
        created_room.roomid, StayFactory.build(*EXISTING_STAY), **guest.model_dump()
    )

    assert response.status_code == 201
    created = CreatedBooking.model_validate(response.json())
    assert created.booking.firstname == firstname


@pytest.mark.regression
def test_create_booking_with_lastname_over_max_returns_400(
    booking_helper: BookingHelper, created_room: Room
) -> None:
    lastname = uuid.uuid4().hex[:31]

    response = booking_helper.create(
        created_room.roomid, StayFactory.build(*EXISTING_STAY), lastname=lastname
    )

    assert response.status_code == 400
    error = ErrorResponse.model_validate(response.json())
    assert error.fieldErrors == ["size must be between 3 and 30"]


@pytest.mark.regression
def test_get_summary_for_room_with_two_stays_returns_both_stays(
    booking_client: BookingClient, booking_helper: BookingHelper, created_room: Room
) -> None:
    stays = [StayFactory.build(10, 12), StayFactory.build(20, 22)]
    for stay in stays:
        booking_helper.book(created_room.roomid, stay)

    response = booking_client.get_summary(created_room.roomid)

    assert response.status_code == 200
    summary = BookingSummaryList.model_validate(response.json())
    assert sorted(item.bookingDates.checkin for item in summary.bookings) == [
        stay.checkin for stay in stays
    ]
    assert sorted(item.bookingDates.checkout for item in summary.bookings) == [
        stay.checkout for stay in stays
    ]


@pytest.mark.regression
def test_get_summary_exposes_only_booking_dates_returns_no_guest_details(
    booking_client: BookingClient, booking_helper: BookingHelper, created_room: Room
) -> None:
    booking_helper.book(created_room.roomid, StayFactory.build(*EXISTING_STAY))

    response = booking_client.get_summary(created_room.roomid)

    assert response.status_code == 200
    BookingSummaryList.model_validate(response.json())
    items = response.json()["bookings"]
    assert [set(item) for item in items] == [{"bookingDates"}]


@pytest.mark.smoke
def test_check_unavailable_rooms_for_range_around_booking_returns_own_room(
    booking_client: BookingClient, booking_helper: BookingHelper, created_room: Room
) -> None:
    booking_helper.book(created_room.roomid, StayFactory.build(12, 14))
    query = StayFactory.build(10, 20)

    response = booking_client.get_unavailable(query.checkin, query.checkout)

    assert response.status_code == 200
    rooms = [UnavailableRoom.model_validate(item) for item in response.json()]
    assert created_room.roomid in {room.roomid for room in rooms}


@pytest.mark.regression
@pytest.mark.issue("7")
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="RBP bug #7: unavailable rooms misses a booking that overlaps the range only partly",
)
@pytest.mark.parametrize(
    "existing",
    [
        pytest.param((8, 12), id="overlaps-start-of-range"),
        pytest.param((13, 18), id="overlaps-end-of-range"),
        pytest.param((5, 20), id="encloses-range"),
        pytest.param((9, 15), id="starts-one-day-before-range"),
    ],
)
def test_room_with_overlapping_booking_is_conflict_and_listed_as_unavailable(
    booking_client: BookingClient,
    booking_helper: BookingHelper,
    created_room: Room,
    existing: tuple[int, int],
) -> None:
    query = (10, 15)
    booking_helper.book(created_room.roomid, StayFactory.build(*existing))

    response = booking_helper.create(created_room.roomid, StayFactory.build(*query))

    if response.status_code != 409:
        raise RuntimeError(
            f"Precondition broken: overlapping booking returned {response.status_code}, expected 409"
        )
    assert created_room.roomid in _unavailable_room_ids(booking_client, query)


@pytest.mark.regression
@pytest.mark.issue("8")
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="RBP bug #8: malformed request returns 500 instead of 400",
)
def test_create_booking_without_booking_dates_returns_400(
    booking_client: BookingClient, booking_cleanup: BookingCleanup, created_room: Room
) -> None:
    payload = BookingFactory.build(created_room.roomid).model_dump(
        mode="json", exclude={"bookingdates"}
    )

    response = booking_client.create_booking(payload)
    booking_cleanup.track(response)

    assert response.status_code == 400


@pytest.mark.regression
@pytest.mark.issue("8")
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="RBP bug #8: malformed request returns 500 instead of 400",
)
def test_get_summary_with_non_numeric_roomid_returns_400(
    booking_client: BookingClient,
) -> None:
    response = booking_client.get_summary("abc")

    assert response.status_code == 400


@pytest.mark.regression
@pytest.mark.issue("8")
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="RBP bug #8: malformed request returns 500 instead of 400",
)
def test_check_unavailable_rooms_with_malformed_checkin_returns_400(
    booking_client: BookingClient,
) -> None:
    checkout = StayFactory.build(10, 15).checkout

    response = booking_client.get_unavailable("abc", checkout)

    assert response.status_code == 400
