"""Each test uses a fresh in-memory SQLite database, shared across threads."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from .database import get_db
from .main import create_app
from .models import CustomerDB


@pytest.fixture
def api():
    test_engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    test_sessions = sessionmaker(bind=test_engine, autoflush=False)
    app = create_app(test_engine)

    def override_get_db():
        with test_sessions() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client, test_sessions
    finally:
        app.dependency_overrides.clear()
        test_engine.dispose()


def test_task_crud_lifecycle(api):
    client, _ = api
    assert client.get("/tasks/").json() == []
    response = client.post("/tasks/", json={"title": "Learn FastAPI", "description": "Day 04"})
    assert response.status_code == 201
    task = response.json()
    assert task["title"] == "Learn FastAPI"
    assert task["description"] == "Day 04"
    assert task["status"] == "pending"
    assert isinstance(task["id"], int)
    datetime.fromisoformat(task["created_at"])
    url = f"/tasks/{task['id']}"
    assert client.get(url).json() == task
    assert client.get("/tasks/").json() == [task]

    updated = client.put(url, json={"title": "Ship API", "status": "in_progress"})
    assert updated.status_code == 200
    assert updated.json()["title"] == "Ship API"
    assert updated.json()["status"] == "in_progress"
    assert updated.json()["description"] == "Day 04"
    assert updated.json()["created_at"] == task["created_at"]
    assert client.get(url).json() == updated.json()
    cleared = client.put(url, json={"description": None, "status": "completed"})
    assert cleared.status_code == 200
    assert cleared.json()["description"] is None
    assert cleared.json()["status"] == "completed"

    deleted = client.delete(url)
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert client.get(url).status_code == 404
    assert client.get("/tasks/").json() == []


@pytest.mark.parametrize("task_status", ["pending", "in_progress", "completed"])
def test_allowed_task_statuses(api, task_status):
    client, _ = api
    response = client.post("/tasks/", json={"title": "Task", "status": task_status})
    assert response.status_code == 201
    assert response.json()["status"] == task_status


@pytest.mark.parametrize("payload", [
    {}, {"title": ""}, {"title": None},
    {"title": "Task", "status": "invalid"},
    {"title": "Task", "status": "completed\n"},
    {"title": "Task", "status": None},
])
def test_invalid_task_creation(api, payload):
    client, _ = api
    assert client.post("/tasks/", json=payload).status_code == 422
    assert client.get("/tasks/").json() == []


@pytest.mark.parametrize("payload", [
    {"status": "invalid"}, {"title": ""}, {"title": None}, {"status": None},
])
def test_invalid_update_preserves_task(api, payload):
    client, _ = api
    task = client.post("/tasks/", json={"title": "Original"}).json()
    url = f"/tasks/{task['id']}"
    assert client.put(url, json=payload).status_code == 422
    assert client.get(url).json() == task


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_missing_task(api, method):
    client, _ = api
    kwargs = {"json": {"status": "completed"}} if method == "put" else {}
    response = getattr(client, method)("/tasks/9999", **kwargs)
    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}


def test_pagination(api):
    client, _ = api
    for title in ["First", "Second", "Third"]:
        assert client.post("/tasks/", json={"title": title}).status_code == 201
    response = client.get("/tasks/?skip=1&limit=1")
    assert response.status_code == 200
    assert [task["title"] for task in response.json()] == ["Second"]
    assert client.get("/tasks/?skip=-1").status_code == 422
    assert client.get("/tasks/?limit=0").status_code == 422


def test_customer_is_persisted(api):
    client, sessions = api
    response = client.post(
        "/customers/", json={"name": "Alice Smith", "email": "alice.smith@example.com"}
    )
    assert response.status_code == 201
    customer = response.json()
    assert customer["name"] == "Alice Smith"
    assert customer["email"] == "alice.smith@example.com"
    with sessions() as db:
        stored = db.get(CustomerDB, customer["id"])
        assert stored.name == customer["name"]
        assert stored.email == customer["email"]


@pytest.mark.parametrize("payload", [
    {"name": "Bob", "email": "invalid-email-format"},
    {"name": "Bob", "email": "bob@"},
    {"name": "Bob"},
    {"email": "bob@example.com"},
    {"name": "", "email": "bob@example.com"},
])
def test_invalid_customer_is_not_persisted(api, payload):
    client, sessions = api
    assert client.post("/customers/", json=payload).status_code == 422
    with sessions() as db:
        assert db.scalars(select(CustomerDB)).all() == []
