"""Guest journey: search rooms by dates and see which room cards stay listed."""

import re
from datetime import date, timedelta

import pytest
from playwright.sync_api import expect

from framework.booking_helper import BookingHelper
from framework.factories.stay_factory import StayFactory
from framework.pages.availability_search import AvailabilitySearch

# Local only: the bookings are created through the booking service port.
pytestmark = [pytest.mark.ui, pytest.mark.service, pytest.mark.story("BOOK-2")]

SEED_ROOM = 1
OTHER_SEED_ROOMS = (2, 3)


@pytest.mark.smoke
def test_search_on_free_dates_keeps_room_1_listed(
    availability_search: AvailabilitySearch,
) -> None:
    free_checkin = date.today() + timedelta(days=StayFactory.FAR_FUTURE_DAYS + 300)
    availability_search.open()
    expect(availability_search.room_cards.first).to_be_visible()

    response = availability_search.search(
        free_checkin, free_checkin + timedelta(days=2)
    )

    assert response.ok
    assert f"checkin={free_checkin.isoformat()}" in response.url
    expect(availability_search.room_card(SEED_ROOM)).to_be_visible()
    expect(availability_search.book_now_link(SEED_ROOM)).to_have_attribute(
        "href", re.compile(f"checkin={free_checkin.isoformat()}")
    )


@pytest.mark.regression
def test_search_range_around_booking_hides_booked_room_only(
    availability_search: AvailabilitySearch, booking_helper: BookingHelper
) -> None:
    # Stay window: days 10 to 15; the search range days 8 to 17 fully contains it.
    stay = StayFactory.build(10, 15)
    booking_helper.book(SEED_ROOM, stay)
    wide = StayFactory.build(8, 17)
    availability_search.open()
    expect(availability_search.room_cards.first).to_be_visible()

    availability_search.search(wide.checkin, wide.checkout)

    expect(availability_search.room_card(SEED_ROOM)).to_be_hidden()
    for room_id in OTHER_SEED_ROOMS:
        expect(availability_search.room_card(room_id)).to_be_visible()


@pytest.mark.regression
@pytest.mark.issue("7")
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="RBP bug #7: a search range inside a booking still lists the booked room",
)
def test_search_range_inside_booking_hides_booked_room(
    availability_search: AvailabilitySearch, booking_helper: BookingHelper
) -> None:
    # Stay window: days 40 to 45; the search range days 41 to 43 lies inside it.
    stay = StayFactory.build(40, 45)
    booking_helper.book(SEED_ROOM, stay)
    inside = StayFactory.build(41, 43)
    availability_search.open()
    expect(availability_search.room_cards.first).to_be_visible()

    availability_search.search(inside.checkin, inside.checkout)

    expect(availability_search.room_card(SEED_ROOM)).to_be_hidden()
