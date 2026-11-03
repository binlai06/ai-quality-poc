"""Base HTTP client that every RBP service client extends."""

from types import TracebackType
from typing import Any, Self

import requests

from framework.config import settings


class BaseClient:
    """Wraps a requests.Session with the base URL and timeout from config.

    Subclasses add one method per endpoint and pass only the path.
    """

    def __init__(
        self, base_url: str = settings.base_url, timeout: float = settings.timeout
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        kwargs.setdefault("timeout", self.timeout)
        return self.session.request(method, f"{self.base_url}{path}", **kwargs)

    def get(self, path: str, **kwargs: Any) -> requests.Response:
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> requests.Response:
        return self._request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> requests.Response:
        return self._request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> requests.Response:
        return self._request("DELETE", path, **kwargs)

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
