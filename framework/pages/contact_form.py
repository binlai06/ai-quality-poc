"""Contact form component on the home page."""

from playwright.sync_api import Locator, Page

from framework.models.message import ContactPayload


class ContactForm:
    """The "Send Us a Message" form. A component: it lives inside the home page."""

    def __init__(self, page: Page) -> None:
        self.page = page
        self.name: Locator = page.get_by_label("Name", exact=True)
        self.email: Locator = page.get_by_label("Email", exact=True)
        self.phone: Locator = page.get_by_label("Phone", exact=True)
        self.subject: Locator = page.get_by_label("Subject", exact=True)
        # The "Message" label points at id "message" but the textarea id is "description",
        # so get_by_label finds nothing. The test id is the best available locator.
        self.message: Locator = page.get_by_test_id("ContactDescription")
        self.submit_button: Locator = page.get_by_role("button", name="Submit")
        # CSS only: the error box is a <div class="alert alert-danger"> without role=alert.
        self.error_box: Locator = page.locator("#contact .alert-danger")

    def fill(self, contact: ContactPayload) -> None:
        self.name.fill(contact.name)
        self.email.fill(contact.email)
        self.phone.fill(contact.phone)
        self.subject.fill(contact.subject)
        self.message.fill(contact.description)

    def submit(self) -> None:
        self.submit_button.click()

    def send(self, contact: ContactPayload) -> None:
        """Fill every field and submit."""
        self.fill(contact)
        self.submit()

    def thanks_heading(self, name: str) -> Locator:
        """The confirmation heading shown after a successful submit."""
        return self.page.get_by_role(
            "heading", name=f"Thanks for getting in touch {name}!"
        )

    def error_message(self, text: str) -> Locator:
        """One validation message inside the error box."""
        return self.error_box.get_by_text(text, exact=True)
