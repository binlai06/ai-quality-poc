"""Public home page: the room list."""

import re
from dataclasses import dataclass

from playwright.sync_api import Locator, Page

from framework.pages.base_page import BasePage
from framework.pages.contact_form import ContactForm

ROOM_LINK_PATTERN = re.compile(r"/reservation/(\d+)")
PRICE_PATTERN = re.compile(r"£(\d+)")


@dataclass(frozen=True)
class RoomCardInfo:
    """What one room card on the home page shows."""

    room_id: int
    room_type: str
    price: int


class HomePage(BasePage):
    """The RBP home page at `/`."""

    path = "/"

    def __init__(self, page: Page) -> None:
        super().__init__(page)
        # CSS only: the room card is a plain <div> with no role, label or test id.
        self.room_cards: Locator = page.locator("#rooms .room-card")
        self.contact_form = ContactForm(page)

    def open(self) -> None:
        self.goto(self.path)

    def room_infos(self) -> list[RoomCardInfo]:
        """Read id, type and price from every room card currently shown."""
        infos: list[RoomCardInfo] = []
        for card in self.room_cards.all():
            href = card.get_by_role("link", name="Book now").get_attribute("href") or ""
            room_type = card.get_by_role("heading").inner_text()
            price_text = card.get_by_text("per night").locator("..").inner_text()
            id_match = ROOM_LINK_PATTERN.search(href)
            price_match = PRICE_PATTERN.search(price_text)
            if id_match is None or price_match is None:
                raise ValueError(f"unreadable room card: {href!r} / {price_text!r}")
            infos.append(
                RoomCardInfo(
                    room_id=int(id_match.group(1)),
                    room_type=room_type,
                    price=int(price_match.group(1)),
                )
            )
        return infos
