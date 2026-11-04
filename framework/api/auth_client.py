"""Client for the RBP auth service."""

import requests

from framework.api.base_client import BaseClient
from framework.models.auth import LoginRequest


class AuthClient(BaseClient):
    """Calls the auth service through the UI proxy at /api/auth.

    Note: the proxy answers failed logins with 401, while the auth service itself
    (port 3004) answers 403. Tests target the proxy, so they expect 401.
    """

    LOGIN_PATH = "/api/auth/login"

    def login(
        self, username: str | None = None, password: str | None = None
    ) -> requests.Response:
        """POST credentials. Arguments left as None are not sent at all."""
        body = LoginRequest(username=username, password=password)
        return self.post(self.LOGIN_PATH, json=body.model_dump(exclude_none=True))

    def login_with_raw_body(self, body: str) -> requests.Response:
        """POST a raw, possibly invalid, body with a JSON content type."""
        return self.post(
            self.LOGIN_PATH, data=body, headers={"Content-Type": "application/json"}
        )
