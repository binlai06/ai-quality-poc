"""Base class for every Playwright Page Object."""

from playwright.sync_api import Page


class BasePage:
    """Holds the Playwright page. Paths are relative; the base URL comes from the test config.

    Page Objects contain actions and locators only. Assertions stay in the tests.
    """

    def __init__(self, page: Page) -> None:
        self.page = page

    def goto(self, path: str) -> None:
        """Open a path on the application under test."""
        self.page.goto(path)
