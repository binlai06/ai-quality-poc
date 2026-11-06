"""Admin login page."""

import re

from playwright.sync_api import Locator, Page

from framework.pages.base_page import BasePage


class AdminLoginPage(BasePage):
    """The admin login form at `/admin`."""

    path = "/admin"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        self.username: Locator = page.get_by_label("Username")
        self.password: Locator = page.get_by_label("Password")
        self.login_button: Locator = page.get_by_role("button", name="Login")
        # Next.js adds an empty role=alert (route announcer); only the non-empty one is ours.
        self.error_alert: Locator = page.get_by_role("alert").filter(
            has_text=re.compile(r"\S")
        )

    def open(self) -> None:
        self.goto(self.path)

    def login(self, username: str, password: str) -> None:
        """Fill the form and submit it."""
        self.username.fill(username)
        self.password.fill(password)
        self.login_button.click()
