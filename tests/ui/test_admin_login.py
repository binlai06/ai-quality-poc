"""Admin login: success reaches the room list, a wrong password shows an error."""

import pytest
from faker import Faker
from playwright.sync_api import expect

from framework.config import settings
from framework.pages.admin_login_page import AdminLoginPage
from framework.pages.admin_rooms_page import AdminRoomsPage

pytestmark = [pytest.mark.ui, pytest.mark.regression, pytest.mark.public]

fake = Faker()

INVALID_CREDENTIALS_MESSAGE = "Invalid credentials"


def test_admin_login_with_valid_credentials_shows_room_list(
    admin_login_page: AdminLoginPage, admin_rooms_page: AdminRoomsPage
) -> None:
    admin_login_page.open()

    admin_login_page.login(settings.admin_username, settings.admin_password)

    expect(admin_rooms_page.page).to_have_url(admin_rooms_page.url_pattern)
    expect(admin_rooms_page.room_number_header).to_be_visible()
    expect(admin_rooms_page.logout_button).to_be_visible()


def test_admin_login_with_wrong_password_shows_error(
    admin_login_page: AdminLoginPage, admin_rooms_page: AdminRoomsPage
) -> None:
    admin_login_page.open()

    admin_login_page.login(settings.admin_username, fake.password(length=12))

    expect(admin_login_page.error_alert).to_have_text(INVALID_CREDENTIALS_MESSAGE)
    expect(admin_rooms_page.room_number_header).to_have_count(0)
