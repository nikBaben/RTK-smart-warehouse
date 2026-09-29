from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient
from backend.main import create_app
from backend.api.deps import (
    get_product_service,
    get_delivery_service,
    get_user_service,
    get_keycloak_service,
)
from backend.domain.errors import (
    NotFound,
    Conflict,
    InvalidOperation,
    RelatedEntityError,
    StorageError,
)


@pytest.mark.parametrize(
    "error,code",
    [
        (NotFound, 404),
        (Conflict, 409),
        (InvalidOperation, 400),
        (RelatedEntityError, 422),
        (StorageError, 500),
    ],
)
def test_application_errors_become_http_responses(error, code):
    app = create_app(start_background=False)
    service = AsyncMock()
    service.edit_product.side_effect = error("Public message")
    app.dependency_overrides[get_product_service] = lambda: service
    with TestClient(app) as client:
        response = client.patch("/api/v1/products/p", json={"stock": 10})
    assert response.status_code == code
    assert response.json() == {"detail": "Public message"}


def test_registration_errors_are_not_wrapped_in_generic_500():
    app = create_app(start_background=False)
    service = AsyncMock()
    service.register.side_effect = Conflict("Email exists")
    app.dependency_overrides[get_user_service] = lambda: service
    app.dependency_overrides[get_keycloak_service] = lambda: AsyncMock()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/user",
            json={"email": "user@example.com", "name": "User", "password": "x"},
        )
    assert response.status_code == 409


def test_real_delivery_route_calls_existing_service_method():
    app = create_app(start_background=False)
    service = AsyncMock()
    service.get_delivery_by_id.return_value = None
    app.dependency_overrides[get_delivery_service] = lambda: service
    with TestClient(app) as client:
        response = client.get("/api/v1/deliveries/missing")
    assert response.status_code == 404
    service.get_delivery_by_id.assert_awaited_once_with("missing")


def test_negative_stock_rejected_at_api_boundary():
    app = create_app(start_background=False)
    service = AsyncMock()
    app.dependency_overrides[get_product_service] = lambda: service
    with TestClient(app) as client:
        response = client.patch("/api/v1/products/p", json={"stock": -1})
    assert response.status_code == 422
    service.edit_product.assert_not_awaited()
