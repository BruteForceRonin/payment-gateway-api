import hashlib
import hmac

from fastapi.testclient import TestClient

from app.config import settings


def create_client(client: TestClient, email: str = "client@example.com") -> dict:
    response = client.post(
        "/clients",
        json={"name": "Test Client", "email": email},
    )
    assert response.status_code == 201
    return response.json()


def create_invoice(client: TestClient, client_id: int) -> dict:
    response = client.post(
        "/invoices",
        json={
            "client_id": client_id,
            "description": "Test invoice",
            "amount": 10_000,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_duplicate_client_email(client: TestClient) -> None:
    create_client(client)

    response = client.post(
        "/clients",
        json={"name": "Another Client", "email": "client@example.com"},
    )

    assert response.status_code == 409


def test_create_invoice_for_missing_client(client: TestClient) -> None:
    response = client.post(
        "/invoices",
        json={
            "client_id": 999,
            "description": "Test invoice",
            "amount": 10_000,
        },
    )

    assert response.status_code == 404


def test_create_invoice_starts_pending(client: TestClient) -> None:
    created_client = create_client(client)
    invoice = create_invoice(client, created_client["id"])

    assert invoice["status"] == "pending"


def test_verify_payment_marks_invoice_paid(client: TestClient) -> None:
    created_client = create_client(client)
    invoice = create_invoice(client, created_client["id"])

    order_response = client.post(
        "/payments/orders",
        json={"invoice_id": invoice["id"]},
    )
    assert order_response.status_code == 200
    order_id = order_response.json()["order_id"]

    payment_id = "pay_mock_123"
    message = f"{order_id}|{payment_id}"
    signature = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()

    response = client.post(
        "/payments/verify",
        json={
            "invoice_id": invoice["id"],
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "paid"


def test_verify_payment_with_wrong_signature(client: TestClient) -> None:
    created_client = create_client(client)
    invoice = create_invoice(client, created_client["id"])

    order_response = client.post(
        "/payments/orders",
        json={"invoice_id": invoice["id"]},
    )
    order_id = order_response.json()["order_id"]

    response = client.post(
        "/payments/verify",
        json={
            "invoice_id": invoice["id"],
            "razorpay_order_id": order_id,
            "razorpay_payment_id": "pay_mock_123",
            "razorpay_signature": "wrong-signature",
        },
    )

    assert response.status_code == 400


def test_delete_client_with_invoice(client: TestClient) -> None:
    created_client = create_client(client)
    create_invoice(client, created_client["id"])

    response = client.delete(f"/clients/{created_client['id']}")

    assert response.status_code == 409
