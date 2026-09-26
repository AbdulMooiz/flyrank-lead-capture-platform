from fastapi.testclient import TestClient
import httpx
import pytest
from rq import Retry
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.main as main
from app.core.config import settings
from app.db import session as db_session
from app.db.models import Base
from app.integrations.geo import GeoEnricher
from app.services import jobs, rate_limit
from app.workers import worker as worker_module


def create_client(tmp_path):
    db_path = tmp_path / "flyrank.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    db_session.engine = engine
    db_session.SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = db_session.SessionLocal()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides.clear()
    main.app.dependency_overrides[db_session.get_db] = override_get_db
    return TestClient(main.app)


def register(client, *, email, password, tenant_name):
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "tenant_name": tenant_name},
    )
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


def test_register_login_and_widget_tenant_isolation(tmp_path):
    client = create_client(tmp_path)

    tenant_a_token = register(client, email="alpha@example.com", password="Pass1234!", tenant_name="Alpha")
    tenant_b_token = register(client, email="beta@example.com", password="Pass1234!", tenant_name="Beta")

    alpha_headers = {"Authorization": f"Bearer {tenant_a_token}"}
    beta_headers = {"Authorization": f"Bearer {tenant_b_token}"}

    create_widget = client.post(
        "/api/widgets",
        json={
            "type": "signup",
            "title": "Alpha Widget",
            "description": "Collect leads",
            "fields": [{"name": "email", "label": "Email", "type": "email", "required": True}],
            "button_text": "Join",
        },
        headers=alpha_headers,
    )
    assert create_widget.status_code == 201, create_widget.text
    widget_id = create_widget.json()["id"]

    alpha_list = client.get("/api/widgets", headers=alpha_headers)
    beta_list = client.get("/api/widgets", headers=beta_headers)
    assert alpha_list.status_code == 200 and len(alpha_list.json()) == 1
    assert beta_list.status_code == 200 and len(beta_list.json()) == 0

    beta_access = client.get(f"/api/widgets/{widget_id}", headers=beta_headers)
    assert beta_access.status_code == 404

    config = client.get(f"/api/widgets/{widget_id}/config")
    assert config.status_code == 200, config.text
    assert config.json()["submit_url"].endswith("/api/submissions")


def test_public_submission_and_dashboard_analytics(tmp_path):
    client = create_client(tmp_path)
    token = register(client, email="owner@example.com", password="Pass1234!", tenant_name="Owner")
    headers = {"Authorization": f"Bearer {token}"}

    widget = client.post(
        "/api/widgets",
        json={
            "type": "contact",
            "title": "Contact",
            "description": "Book a demo",
            "fields": [
                {"name": "name", "label": "Name", "type": "text", "required": True},
                {"name": "email", "label": "Email", "type": "email", "required": True},
            ],
            "button_text": "Send",
        },
        headers=headers,
    )
    assert widget.status_code == 201, widget.text
    widget_id = widget.json()["id"]

    first = client.post(
        "/api/submissions",
        json={"widget_id": widget_id, "data": {"name": "Ada", "email": "ada@example.com"}, "honeypot": ""},
        headers={"Idempotency-Key": "abc-123"},
    )
    assert first.status_code == 201, first.text
    first_body = first.json()
    assert first_body["status"] == "received"

    duplicate = client.post(
        "/api/submissions",
        json={"widget_id": widget_id, "data": {"name": "Ada", "email": "ada@example.com"}, "honeypot": ""},
        headers={"Idempotency-Key": "abc-123"},
    )
    assert duplicate.status_code == 201, duplicate.text
    assert duplicate.json()["status"] == "already_received"

    blocked = client.post(
        "/api/submissions",
        json={"widget_id": widget_id, "data": {"name": "Bot", "email": "bot@example.com"}, "honeypot": "yes"},
    )
    assert blocked.status_code == 400, blocked.text

    analytics = client.get("/api/dashboard/analytics", headers=headers)
    assert analytics.status_code == 200, analytics.text
    payload = analytics.json()
    assert payload["total"] >= 1
    assert payload["by_widget"].get(widget_id, 0) >= 1

    submissions = client.get("/api/dashboard/submissions", headers=headers)
    assert submissions.status_code == 200, submissions.text
    assert submissions.json()["total"] >= 1


def test_public_widget_config_and_cors_preflight(tmp_path):
    client = create_client(tmp_path)
    token = register(client, email="public@example.com", password="Pass1234!", tenant_name="Public")
    headers = {"Authorization": f"Bearer {token}"}
    widget = client.post(
        "/api/widgets",
        json={
            "type": "signup",
            "title": "Lead magnet",
            "description": "Sign up for updates",
            "fields": [{"name": "email", "label": "Email", "type": "email", "required": True}],
            "button_text": "Join",
        },
        headers=headers,
    )
    widget_id = widget.json()["id"]

    config = client.get(f"/api/widgets/{widget_id}/config")
    assert config.status_code == 200, config.text
    assert config.headers.get("cache-control", "").startswith("public")

    preflight = client.options(
        "/api/submissions",
        headers={
            "Origin": "http://localhost:5500",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type, Idempotency-Key",
        },
    )
    assert preflight.status_code == 200, preflight.text
    assert preflight.headers.get("access-control-allow-origin") == "http://localhost:5500"


def test_oversized_payload_and_rate_limit(tmp_path):
    rate_limit._memory.clear()
    original_limit = settings.rate_limit_requests
    settings.rate_limit_requests = 2
    try:
        client = create_client(tmp_path)
        token = register(client, email="burst@example.com", password="Pass1234!", tenant_name="Burst")
        headers = {"Authorization": f"Bearer {token}"}
        widget = client.post(
            "/api/widgets",
            json={
                "type": "contact",
                "title": "Fast form",
                "description": "Test burst handling",
                "fields": [{"name": "message", "label": "Message", "type": "text", "required": True}],
                "button_text": "Send",
            },
            headers=headers,
        )
        widget_id = widget.json()["id"]

        too_big = client.post(
            "/api/submissions",
            json={"widget_id": widget_id, "data": {"message": "x" * 50000}, "honeypot": ""},
        )
        assert too_big.status_code == 413, too_big.text

        first = client.post(
            "/api/submissions",
            json={"widget_id": widget_id, "data": {"message": "first valid request"}, "honeypot": ""},
            headers={"Idempotency-Key": "rate-1"},
        )
        assert first.status_code == 201, first.text

        second = client.post(
            "/api/submissions",
            json={"widget_id": widget_id, "data": {"message": "second valid request"}, "honeypot": ""},
            headers={"Idempotency-Key": "rate-2"},
        )
        assert second.status_code == 201, second.text

        blocked = client.post(
            "/api/submissions",
            json={"widget_id": widget_id, "data": {"message": "third valid request"}, "honeypot": ""},
            headers={"Idempotency-Key": "rate-3"},
        )
        assert blocked.status_code == 429, blocked.text
    finally:
        settings.rate_limit_requests = original_limit


def test_enqueue_notification_sets_retry_policy(monkeypatch):
    captured = {}

    class DummyQueue:
        def enqueue(self, func_name, submission_id, retry=None, **kwargs):
            captured["func_name"] = func_name
            captured["submission_id"] = submission_id
            captured["retry"] = retry
            return object()

    class DummyRedis:
        @staticmethod
        def from_url(*args, **kwargs):
            return DummyRedis()

    monkeypatch.setattr(jobs, "Queue", lambda *args, **kwargs: DummyQueue())
    monkeypatch.setattr(jobs, "Redis", DummyRedis)

    jobs.enqueue_notification("submission-123")

    assert captured["func_name"] == "app.workers.worker.process_notification"
    assert captured["submission_id"] == "submission-123"
    assert isinstance(captured["retry"], Retry)
    assert captured["retry"].max == 3


def test_worker_starts_with_scheduler(monkeypatch):
    captured = {}

    class DummyRedis:
        @staticmethod
        def from_url(*args, **kwargs):
            return object()

    class DummyWorker:
        def __init__(self, *args, **kwargs):
            pass

        def work(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(worker_module, "Redis", DummyRedis)
    monkeypatch.setattr(worker_module, "Queue", lambda *args, **kwargs: object())
    monkeypatch.setattr(worker_module, "Worker", DummyWorker)

    worker_module.main()

    assert captured == {"with_scheduler": True}


@pytest.mark.asyncio
async def test_geo_enricher_uses_second_provider_when_first_fails():
    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class FakeClient:
        def __init__(self):
            self.urls = []

        async def get(self, url):
            self.urls.append(url)
            if "ip-api.com" in url:
                raise httpx.ConnectError("primary unavailable")
            return FakeResponse({"country_name": "Canada", "country_code": "CA", "city": "Toronto", "region": "Ontario"})

    client = FakeClient()
    result = await GeoEnricher(client).enrich("203.0.113.10")

    assert result["geo_provider"] == "ipapi.co"
    assert result["country_code"] == "CA"
    assert len(client.urls) == 2


@pytest.mark.asyncio
async def test_geo_enricher_degrades_when_all_providers_fail():
    class FakeClient:
        async def get(self, url):
            raise httpx.ConnectError("provider unavailable")

    result = await GeoEnricher(FakeClient()).enrich("203.0.113.11")

    assert result == {}
