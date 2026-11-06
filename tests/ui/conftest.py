"""Fixtures for UI tests: one Page Object per page, bound to the test's own browser page."""

import pytest
from playwright.sync_api import Page

from framework.pages.admin_login_page import AdminLoginPage
from framework.pages.admin_rooms_page import AdminRoomsPage
from framework.pages.home_page import HomePage
from framework.pages.reservation_page import ReservationPage


@pytest.fixture
def home_page(page: Page) -> HomePage:
    return HomePage(page)


@pytest.fixture
def admin_login_page(page: Page) -> AdminLoginPage:
    return AdminLoginPage(page)


@pytest.fixture
def admin_rooms_page(page: Page) -> AdminRoomsPage:
    return AdminRoomsPage(page)


@pytest.fixture
def reservation_page(page: Page) -> ReservationPage:
    return ReservationPage(page)
