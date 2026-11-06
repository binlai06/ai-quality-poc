"""Booking journey: pick a room, reserve it, see the confirmation."""

import pytest
from playwright.sync_api import expect

from framework.factories.guest_factory import GuestFactory
from framework.models.room import Room
from framework.pages.reservation_page import ReservationPage

# Local only: the room comes from the `created_room` fixture, which calls the room service port.
pytestmark = [pytest.mark.ui, pytest.mark.regression, pytest.mark.service]


@pytest.mark.issue("2")
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="RBP bug #2: reservation page blank, backend 500",
)
def test_book_room_with_valid_guest_shows_confirmation(
    reservation_page: ReservationPage, created_room: Room
) -> None:
    # TODO when this strict xfail starts passing (bug #2 fixed): the run creates a booking
    # AND a "You have a new booking!" message (named after the guest). Deleting a room does
    # NOT delete its bookings (checked by API on 2026-11-06). Cleanup must delete all three:
    # the booking, that message, and the room. Add BookingClient + BookingCleanup (find by
    # unique guest name) before removing the xfail, or every run leaves orphans behind.
    guest = GuestFactory.build()
    stay = GuestFactory.build_stay()
    reservation_page.open(created_room.roomid, stay)
    expect(reservation_page.page_ready).to_be_visible()

    reservation_page.book(guest)

    expect(reservation_page.confirmation_heading).to_be_visible()
    expect(reservation_page.confirmed_dates(stay)).to_be_visible()
