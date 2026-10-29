# RESTful Payment Gateway API

A REST API built with **FastAPI**, **SQLAlchemy**, and **PostgreSQL** for managing clients and invoices and collecting invoice payments through **Razorpay**. The API accepts and returns JSON, validates request data with Pydantic, and publishes an interactive OpenAPI reference through Swagger UI.

This repository covers the core service and a Docker Compose development environment. XML responses, AWS API Gateway infrastructure, and a GitHub Actions deployment workflow are not currently included; see [Project scope and deployment status](#project-scope-and-deployment-status).

## Contents

- [Features](#features)
- [Architecture](#architecture)
- [Technology](#technology)
- [Requirements](#requirements)
- [Configuration](#configuration)
- [Run locally](#run-locally)
- [Run with Docker Compose](#run-with-docker-compose)
- [API reference](#api-reference)
- [Payment flow](#payment-flow)
- [Data model](#data-model)
- [Validation and errors](#validation-and-errors)
- [Tests](#tests)
- [Project structure](#project-structure)
- [Production and deployment notes](#production-and-deployment-notes)
- [Project scope and deployment status](#project-scope-and-deployment-status)

## Features

- Client create, list, retrieve, update, and delete operations.
- Invoice create, list, retrieve, update, and delete operations.
- Invoice filtering by client and payment status, with pagination.
- Razorpay order creation and payment-signature verification.
- A mock payment mode for local development and automated tests.
- PostgreSQL persistence using SQLAlchemy ORM.
- Automatic OpenAPI schema, Swagger UI, and ReDoc.
- Docker image and Docker Compose services for the API, PostgreSQL, and pgweb.

## Architecture

```text
HTTP client
    |
    | JSON over HTTP
    v
FastAPI (main.py, routers)
    |                         \
    | SQLAlchemy               \ Razorpay SDK
    v                            v
PostgreSQL                 Razorpay Orders API
```

FastAPI routers validate incoming JSON with Pydantic schemas. The route handlers use a SQLAlchemy session provided by a dependency and return response models. The lifespan handler creates database tables when the application starts and disposes the engine on shutdown.

## Technology

- Python 3.12+
- FastAPI and Uvicorn
- Pydantic Settings and Pydantic models
- SQLAlchemy 2.x with psycopg 3
- PostgreSQL
- Razorpay Python SDK
- Docker and Docker Compose
- `uv` for dependency and lockfile management
- pytest and HTTPX for API tests

## Requirements

For local development:

- Python 3.12 or newer
- [`uv`](https://docs.astral.sh/uv/) installed
- PostgreSQL reachable using the configured connection settings
- Razorpay test credentials, or mock mode enabled

For the containerized setup, Docker Engine and the Docker Compose plugin are needed.

## Configuration

Copy the sample file and edit the values for your environment:

```bash
cp .env.example .env
```

| Variable | Required | Default / example | Purpose |
|---|---:|---|---|
| `POSTGRES_HOST` | No | `localhost` (application default) | PostgreSQL hostname. Compose overrides this to `db` for the API container. |
| `POSTGRES_PORT` | No | `5432` | PostgreSQL port. |
| `POSTGRES_USER` | Yes | `postgres` in sample | Database user. |
| `POSTGRES_PASSWORD` | Yes | `change_me` in sample | Database password. Replace the sample value. |
| `POSTGRES_DB` | Yes | `payment_db` in sample | Database name. |
| `RAZORPAY_KEY_ID` | Yes | Test key placeholder in sample | Razorpay public key ID; returned in payment-order responses for checkout. |
| `RAZORPAY_KEY_SECRET` | Yes | Placeholder in sample | Secret used by the SDK and mock signature verification. Keep it private. |
| `RAZORPAY_MOCK` | No | `False` in application; `True` in sample | Enables locally generated order IDs and HMAC-based mock verification. |

The settings loader reads `.env` from the repository root and also accepts environment variables. Do not commit real credentials. For deployed environments, inject secrets using the hosting platform's secret manager rather than baking them into the image.

## Run locally

1. Create and populate `.env` as described above. Ensure PostgreSQL is running and accessible at `POSTGRES_HOST:POSTGRES_PORT`.
2. Sync dependencies and start the API:

```bash
uv sync
uv run uvicorn main:app --reload
```

The server listens at `http://127.0.0.1:8000` by default. `--reload` is intended for development.

Useful URLs:

- `GET /` — service greeting.
- `GET /health` — basic process health response.
- `/docs` — interactive Swagger UI.
- `/redoc` — ReDoc documentation.
- `/openapi.json` — generated OpenAPI document.

## Run with Docker Compose

The Compose file starts PostgreSQL, pgweb, and the API. Create `.env` first because Compose uses it for the database credentials and API secrets.

```bash
cp .env.example .env
docker compose up --build
```

Endpoints from the host:

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5432`
- pgweb: `http://localhost:5434`

The database data is stored in the named volume `pgdata`. Stop the services with `docker compose down`. To also delete persisted database data, use `docker compose down -v` (this permanently removes the Compose database volume).

The API container waits for PostgreSQL's health check before starting. Inside Compose, its database host is set to `db`; do not set it to `localhost` for the container-to-container connection.

## API reference

All request and response bodies use **JSON**. The API currently has no authentication or authorization layer, so run it only in a trusted environment until access control is added.

### Service endpoints

| Method | Path | Description | Success |
|---|---|---|---:|
| `GET` | `/` | Returns a service greeting. | `200` |
| `GET` | `/health` | Returns a basic health status. | `200` |

### Clients

| Method | Path | Description | Success |
|---|---|---|---:|
| `POST` | `/clients` | Create a client. | `201` |
| `GET` | `/clients` | List clients. | `200` |
| `GET` | `/clients/{client_id}` | Retrieve a client. | `200` |
| `PATCH` | `/clients/{client_id}` | Update supplied client fields. | `200` |
| `DELETE` | `/clients/{client_id}` | Delete a client without invoices. | `204` |

Create a client:

```bash
curl -X POST http://localhost:8000/clients \
  -H 'Content-Type: application/json' \
  -d '{"name":"Asha Rao","email":"asha@example.com"}'
```

Example response (`201 Created`):

```json
{
  "id": 1,
  "name": "Asha Rao",
  "email": "asha@example.com",
  "created_at": "2026-01-15T10:30:00Z"
}
```

List clients accepts `skip` (default `0`, minimum `0`) and `limit` (default `50`, range `1`–`100`). Client email addresses must be valid and unique. Names are trimmed and must contain 1–100 characters. `PATCH` accepts either `name`, `email`, or both; omitted fields are unchanged, and explicit `null` values are rejected. A client with one or more invoices cannot be deleted.

### Invoices

| Method | Path | Description | Success |
|---|---|---|---:|
| `POST` | `/invoices` | Create a pending invoice for an existing client. | `201` |
| `GET` | `/invoices` | List invoices, optionally filtered and paginated. | `200` |
| `GET` | `/invoices/{invoice_id}` | Retrieve an invoice. | `200` |
| `PATCH` | `/invoices/{invoice_id}` | Update description and/or amount on a pending invoice. | `200` |
| `DELETE` | `/invoices/{invoice_id}` | Delete a pending invoice. | `204` |

Create an invoice:

```bash
curl -X POST http://localhost:8000/invoices \
  -H 'Content-Type: application/json' \
  -d '{"client_id":1,"description":"Website development","amount":125000}'
```

`amount` is a positive integer in the smallest currency unit accepted by Razorpay. For INR, use **paise** (`125000` means ₹1,250.00). The API creates invoices with status `pending`.

List and filter invoices:

```bash
curl 'http://localhost:8000/invoices?client_id=1&status=pending&skip=0&limit=20'
```

Supported query parameters are `client_id`, `status` (`pending`, `paid`, or `failed`), `skip` (default `0`), and `limit` (default `50`, range `1`–`100`). Only pending invoices can be edited or deleted. The current payment verification flow marks invoices as `paid`; no endpoint currently marks an invoice as `failed`.

### Payments

| Method | Path | Description | Success |
|---|---|---|---:|
| `POST` | `/payments/orders` | Create or reuse the Razorpay order associated with a pending invoice. | `200` |
| `POST` | `/payments/verify` | Verify the Razorpay payment signature and mark the invoice paid. | `200` |

Create an order:

```bash
curl -X POST http://localhost:8000/payments/orders \
  -H 'Content-Type: application/json' \
  -d '{"invoice_id":1}'
```

Example response:

```json
{
  "order_id": "order_example",
  "amount": 125000,
  "currency": "INR",
  "key_id": "rzp_test_example"
}
```

After checkout, submit the payment details returned by Razorpay:

```bash
curl -X POST http://localhost:8000/payments/verify \
  -H 'Content-Type: application/json' \
  -d '{
    "invoice_id": 1,
    "razorpay_order_id": "order_example",
    "razorpay_payment_id": "pay_example",
    "razorpay_signature": "signature_from_razorpay"
  }'
```

The verification response is the updated invoice. The order ID must match the order saved on that invoice. Once verified, the invoice status becomes `paid`, `razorpay_payment_id` and `paid_at` are set, and repeating a valid order/payment verification request for an already paid invoice returns the invoice as-is.

For the complete field schemas, status codes, and interactive request builder, use `/docs` or `/openapi.json` while the application is running.

## Payment flow

1. Create a client with `POST /clients`.
2. Create an invoice for that client's ID using `POST /invoices`.
3. Request an order using `POST /payments/orders`. The service creates a Razorpay order using the invoice amount in paise and stores its order ID on the invoice. Repeated requests reuse the saved order ID.
4. Use the returned `key_id`, `order_id`, and `amount` in a client-side Razorpay Checkout integration.
5. Send the checkout result to `POST /payments/verify`. The service verifies the signature through the Razorpay SDK, then records the payment ID and paid timestamp.

The API does not contain a checkout page or webhook receiver. The caller is responsible for integrating the returned order data into a client checkout flow. For production payment state, consider adding webhook processing and idempotency controls in addition to the synchronous verification endpoint.

### Mock mode

Set `RAZORPAY_MOCK=True` to run without creating real Razorpay orders. The API returns a generated `order_mock_...` ID. A mock signature is the lowercase hex HMAC-SHA256 using `RAZORPAY_KEY_SECRET` as the key and the exact message `<order_id>|<payment_id>` as the payload. This mode is for local development and tests; it is not a substitute for a live gateway transaction.

## Data model

### Client

| Field | Type | Notes |
|---|---|---|
| `id` | integer | Database-generated primary key. |
| `name` | string | Required; up to 100 characters. |
| `email` | string | Required, valid email, unique; up to 255 characters. |
| `created_at` | timestamp | Set by the database. |

### Invoice

| Field | Type | Notes |
|---|---|---|
| `id` | integer | Database-generated primary key. |
| `client_id` | integer | Required reference to a client. Client deletion is restricted while invoices exist. |
| `description` | string | Required. |
| `amount` | integer | Positive amount in paise for INR. |
| `status` | enum | `pending`, `paid`, or `failed`; new invoices default to `pending`. |
| `razorpay_order_id` | string or null | Unique order ID returned by Razorpay or mock mode. |
| `razorpay_payment_id` | string or null | Set after successful verification. |
| `created_at` | timestamp | Set by the database. |
| `paid_at` | timestamp or null | Set when payment verification succeeds. |

Tables are created automatically during application startup with SQLAlchemy `create_all`. There are no migration scripts in the repository yet; use a migration tool such as Alembic before evolving schemas in deployed environments.

## Validation and errors

FastAPI/Pydantic returns `422 Unprocessable Entity` for malformed JSON, invalid fields, or missing required values. Resource and domain errors include:

| Status | Example |
|---:|---|
| `400` | Payment order ID mismatch or invalid payment signature. |
| `404` | Client or invoice does not exist. |
| `409` | Duplicate client email, deleting a client with invoices, or editing/deleting/creating an order for a non-pending invoice. |
| `502` | Razorpay order creation failed. |

Errors use FastAPI's standard JSON `detail` shape. Unhandled database and infrastructure failures are not translated into a custom API error format.

## Tests

The test suite uses pytest, FastAPI's `TestClient`, and an in-memory SQLite database. Tests cover duplicate client emails, invoice/client relationships, initial invoice state, payment signature verification, and deletion constraints. Test settings are set in `tests/conftest.py` before the application is imported; tests do not require a running PostgreSQL server or live Razorpay credentials.

```bash
uv sync --group dev
uv run pytest
```

## Project structure

```text
.
├── app/
│   ├── config.py                 # Environment-backed settings
│   ├── database/session.py       # SQLAlchemy engine, base, and session dependency
│   ├── models/                   # Client and invoice ORM models
│   ├── routers/                  # Client, invoice, and payment routes
│   ├── schemas/                  # Pydantic request and response models
│   └── services/razorpay_service.py # Razorpay SDK and mock behavior
├── tests/                       # API tests and fixtures
├── .env.example                 # Sample environment configuration
├── Dockerfile
├── docker-compose.yaml
├── main.py                      # FastAPI application and health routes
├── pyproject.toml               # Project metadata and dependencies
└── uv.lock                      # Locked dependency versions
```

## Production and deployment notes

- Use real Razorpay test credentials for gateway sandbox integration, then configure live credentials only in a protected deployment secret store.
- Set `RAZORPAY_MOCK=False` for gateway-backed order creation and verification.
- Configure HTTPS, authentication, authorization, rate limiting, and request logging at the application or edge layer before exposing the API publicly.
- Avoid publishing PostgreSQL or pgweb publicly. The Compose port mappings are for local development.
- Add database migrations before making schema changes to persistent environments. `create_all` creates missing tables but does not manage schema evolution.
- Add startup/readiness checks that validate database connectivity; the existing `/health` endpoint only returns a static healthy response.
- Configure backups and retention for PostgreSQL data.
- The current app is a standard ASGI container listening on port `8000`; it is not configured as an AWS Lambda handler.


