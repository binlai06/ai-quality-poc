"""Admin room list page."""

import re

from playwright.sync_api import Locator, Page

from framework.pages.base_page import BasePage


class AdminRoomsPage(BasePage):
    """The admin room list at `/admin/rooms`. Room creation is not covered yet."""

    path = "/admin/rooms"
    url_pattern = re.compile(r"/admin/rooms$")

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.room_number_header: Locator = page.get_by_text("Room #", exact=True)
        self.room_rows: Locator = page.get_by_test_id("roomlisting")
        self.logout_button: Locator = page.get_by_role("button", name="Logout")
