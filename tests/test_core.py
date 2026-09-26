from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.main as main
from app.db import session as db_session
from app.db.models import Base


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
