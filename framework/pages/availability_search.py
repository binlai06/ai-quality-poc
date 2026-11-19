"""The home page section "Check Availability & Book Your Stay"."""

from datetime import date
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Locator, Page, Response

from framework.pages.base_page import BasePage


class AvailabilitySearch(BasePage):
    """Date search on the home page. It re-renders the room cards without changing the URL."""

    path = "/"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        # CSS only: the date boxes are plain text inputs with no accessible name
        # (the <label for> points to ids that do not exist), so they are found by position.
        section = page.locator("#booking")
        self.checkin_box: Locator = section.locator("input").nth(0)
        self.checkout_box: Locator = section.locator("input").nth(1)
        self.search_button: Locator = section.get_by_role(
            "button", name="Check Availability"
        )
        # CSS only: the room card is a plain <div> with no role, label or test id.
        self.room_cards: Locator = page.locator("#rooms .room-card")

    def open(self) -> None:
        self.goto(self.path)

    def fill_dates(self, checkin: date, checkout: date) -> None:
        """Type both dates as DD/MM/YYYY. Escape closes the datepicker after each box."""
        for box, day in ((self.checkin_box, checkin), (self.checkout_box, checkout)):
            box.fill(day.strftime("%d/%m/%Y"))
            self.page.keyboard.press("Escape")

    def search(self, checkin: date, checkout: date) -> Response:
        """Fill the dates, click "Check Availability", wait for and return the search answer."""
        self.fill_dates(checkin, checkout)
        with self.page.expect_response(self._is_search_response) as response_info:
            self.search_button.click()
        return response_info.value

    @staticmethod
    def _is_search_response(response: Response) -> bool:
        """True for the answer of GET /api/room?checkin=... (the availability search)."""
        url = urlparse(response.url)
        return (
            response.request.method == "GET"
            and url.path == "/api/room"
            and "checkin" in parse_qs(url.query)
        )

    def room_card(self, room_id: int) -> Locator:
        """The card of one room, found through its "Book now" link to /reservation/<id>."""
        # CSS only: the link href carries the searched dates (/reservation/1?checkin=...).
        link = self.page.locator(f'a[href^="/reservation/{room_id}?"]')
        return self.room_cards.filter(has=link)

    def book_now_link(self, room_id: int) -> Locator:
        """The "Book now" link of one room; its href carries the dates of the last search."""
        return self.room_card(room_id).get_by_role("link", name="Book now")
