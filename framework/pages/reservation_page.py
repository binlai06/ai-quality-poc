"""Reservation page for one room."""

from playwright.sync_api import Locator, Page

from framework.models.booking import GuestPayload, Stay
from framework.pages.base_page import BasePage


class ReservationPage(BasePage):
    """The page at `/reservation/{room id}`.

    It needs `checkin` and `checkout` in the query string, as the home page's "Book now"
    link provides. Without them the booking panel never leaves its loading spinner.
    """

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        # Shown on both steps of the booking panel, so it also means "page is ready".
        self.page_ready: Locator = page.get_by_role("heading", name="Book This Room")
        self.reserve_button: Locator = page.get_by_role("button", name="Reserve Now")
        self.firstname: Locator = page.get_by_label("Firstname")
        self.lastname: Locator = page.get_by_label("Lastname")
        self.email: Locator = page.get_by_label("Email")
        self.phone: Locator = page.get_by_label("Phone")
        self.confirmation_heading: Locator = page.get_by_role(
            "heading", name="Booking Confirmed"
        )

    def open(self, room_id: int, stay: Stay) -> None:
        self.goto(
            f"/reservation/{room_id}?checkin={stay.checkin.isoformat()}"
            f"&checkout={stay.checkout.isoformat()}"
        )

    def fill_guest(self, guest: GuestPayload) -> None:
        self.firstname.fill(guest.firstname)
        self.lastname.fill(guest.lastname)
        self.email.fill(guest.email)
        self.phone.fill(guest.phone)

    def book(self, guest: GuestPayload) -> None:
        """Confirm the selected dates, fill the guest form and reserve."""
        self.reserve_button.click()
        self.fill_guest(guest)
        self.reserve_button.click()

    def confirmed_dates(self, stay: Stay) -> Locator:
        """The check-in - check-out line shown on the confirmation."""
        return self.page.get_by_text(f"{stay.checkin} - {stay.checkout}")
