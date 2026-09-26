# FlyRank Lead Capture Platform

A FastAPI-based lead capture platform for embeddable widgets, multi-tenant isolation, and dashboard analytics.

## Stack

- Python 3.12
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- Redis + RQ
- Pydantic / Pydantic Settings
- pytest
- Docker Compose

## Local run

1. Copy `.env.example` to `.env` and adjust values if needed.
2. Start the stack:
   `docker compose up --build`
3. Seed demo data:
   `docker compose exec api python scripts/seed.py`
4. Open the API docs at:
   `http://localhost:8000/docs`
5. Open the customer demo at:
   `http://localhost:5500`

## Core API endpoints

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/widgets`
- `POST /api/widgets`
- `GET /api/widgets/{widget_id}/config`
- `GET /api/widgets/{widget_id}/embed`
- `POST /api/submissions`
- `GET /api/dashboard/submissions`
- `GET /api/dashboard/analytics`
- `GET /health`

## Features implemented

- Authenticated widget CRUD for tenant-owned widgets
- Multi-tenant isolation on widget and dashboard endpoints
- Public widget configuration endpoint with cache headers
- Widget JS bundle served at `/widget.v1.js`
- Customer embed snippet generation
- Submission validation with honeypot, unknown fields, and required fields
- Cross-origin submission support for configured customer origins
- OPTIONS preflight support through FastAPI CORS middleware
- Request body limit enforcement via middleware
- Rate limiting using in-memory tracking and Redis fallback
- Geo enrichment from `ip-api.com` and `ipapi.co` with fallback behavior
- Idempotency handling via `Idempotency-Key`
- Background side-effect enqueue and retry worker
- Dashboard analytics for totals, widget grouping, countries, and recent daily counts
- Alembic migration and SQLAlchemy models for PostgreSQL persistence
- Seed script for demo tenants and widgets

## Acceptance verification

The following checks have been verified in the repository with real automated tests:

- registration/login and tenant isolation
- widget creation and public config access
- public submission + dashboard analytics
- malformed / blocked submission handling
- oversized payload rejection
- rate-limit enforcement after the configured threshold is exceeded
- CORS preflight success for the configured customer origin

## Test command

`python -m pytest tests/test_core.py -q`

## Notes

- The project is intentionally structured to keep the widget delivery and submission flows aligned with the customer website origin.
- Secrets should remain in `.env` and never be committed.
- Redis and PostgreSQL are required for the full runtime flow, especially for queueing and rate limiting.
