"""Client for the RBP message service, called directly on its own port (local Docker only)."""

import requests

from framework import config
from framework.api.base_client import BaseClient


class MessageClient(BaseClient):
    """Message endpoints on the message service.

    Listing needs no token. Delete needs the admin token as the `token` cookie.
    The UI proxy is not used: its DELETE answers 500 when the message is missing.
    """

    COLLECTION_PATH = "/message/"

    @classmethod
    def direct(cls) -> "MessageClient":
        """Message service on its own port (not exposed on the backup environment)."""
        return cls(base_url=config.settings.message_url)

    def list_messages(self) -> requests.Response:
        return self.get(self.COLLECTION_PATH)

    def delete_message(self, message_id: int, token: str) -> requests.Response:
        return self.delete(
            f"{self.COLLECTION_PATH}{message_id}", cookies={"token": token}
        )
