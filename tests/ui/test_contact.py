"""Contact form: a valid message shows a thank-you, an empty form shows validation errors."""

import pytest
from playwright.sync_api import expect

from framework.cleanup import MessageCleanup
from framework.factories.contact_factory import ContactFactory
from framework.pages.home_page import HomePage

# Local only for now: cleanup calls the message service port (marker: service).
pytestmark = [pytest.mark.ui, pytest.mark.regression, pytest.mark.service]

REQUIRED_FIELD_ERRORS = [
    "Name may not be blank",
    "Email may not be blank",
    "Phone may not be blank",
    "Subject may not be blank",
    "Message may not be blank",
]


def test_contact_form_with_valid_data_shows_thanks_message(
    home_page: HomePage, message_cleanup: MessageCleanup
) -> None:
    contact = ContactFactory.build()
    home_page.open()

    home_page.contact_form.send(contact)
    message_cleanup.track(contact.subject)

    form = home_page.contact_form
    expect(form.thanks_heading(contact.name)).to_be_visible()
    expect(form.page.get_by_text(contact.subject, exact=True)).to_be_visible()


def test_contact_form_empty_submit_shows_required_field_errors(
    home_page: HomePage,
) -> None:
    home_page.open()

    home_page.contact_form.submit()

    form = home_page.contact_form
    for error in REQUIRED_FIELD_ERRORS:
        expect(form.error_message(error)).to_be_visible()
