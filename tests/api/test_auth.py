"""Auth service: admin login through the UI proxy."""

import pytest
from faker import Faker

from framework.api.auth_client import AuthClient
from framework.config import settings
from framework.models.auth import ErrorResponse, LoginResponse

fake = Faker()


@pytest.mark.api
@pytest.mark.smoke
def test_login_with_valid_admin_credentials_returns_200_and_token(
    auth_client: AuthClient,
) -> None:
    response = auth_client.login(settings.admin_username, settings.admin_password)

    assert response.status_code == 200
    LoginResponse.model_validate(response.json())


@pytest.mark.api
@pytest.mark.regression
def test_login_with_wrong_password_returns_401(auth_client: AuthClient) -> None:
    response = auth_client.login(settings.admin_username, fake.password(length=12))

    assert response.status_code == 401
    body = response.json()
    ErrorResponse.model_validate(body)
    assert "token" not in body


@pytest.mark.api
@pytest.mark.regression
@pytest.mark.parametrize(
    ("username", "password"),
    [
        pytest.param("", "", id="empty-strings"),
        pytest.param(None, None, id="no-fields"),
        pytest.param(settings.admin_username, None, id="username-only"),
        pytest.param(None, settings.admin_password, id="password-only"),
    ],
)
def test_login_with_missing_or_empty_credentials_returns_401(
    auth_client: AuthClient, username: str | None, password: str | None
) -> None:
    response = auth_client.login(username, password)

    assert response.status_code == 401
    body = response.json()
    ErrorResponse.model_validate(body)
    assert "token" not in body


@pytest.mark.api
@pytest.mark.regression
@pytest.mark.issue("1")
@pytest.mark.xfail(strict=True, reason="RBP bug #1: malformed login body returns 500")
@pytest.mark.parametrize("body", ["", "not json"], ids=["no-body", "invalid-json"])
def test_login_with_malformed_body_returns_400(
    auth_client: AuthClient, body: str
) -> None:
    response = auth_client.login_with_raw_body(body)

    assert response.status_code == 400
